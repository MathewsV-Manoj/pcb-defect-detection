"""Import labeled images into a canonical YOLO dataset using an explicit split manifest."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import yaml

NAMES=['missing_hole','open_circuit','short_circuit']
ALIASES={'open':'open_circuit','short':'short_circuit',**{n:n for n in NAMES}}
SPLITS=('train','val','test')
REQUIRED_COLUMNS={'split','group','image','label','format'}


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset import manifest not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest is missing required columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("Dataset import manifest contains no image rows")
    return rows


def parse_voc(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    root = ET.parse(label_path).getroot()
    boxes = []
    for obj in root.findall("object"):
        raw_name = obj.findtext("name")
        if not raw_name:
            raise ValueError(f"VOC object is missing a class name: {label_path}")
        name = ALIASES.get(raw_name.strip().lower())
        if name is None:
            continue
        box = obj.find("bndbox")
        if box is None:
            raise ValueError(f"VOC object is missing bndbox: {label_path}")
        try:
            x1, y1, x2, y2 = [
                float(box.findtext(key)) for key in ("xmin", "ymin", "xmax", "ymax")
            ]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"VOC bounding box is invalid in {label_path}") from exc
        # Convert Pascal VOC's 1-based inclusive coordinates to 0-based image bounds.
        boxes.append((NAMES.index(name), x1 - 1, y1 - 1, x2, y2))
    return boxes


def parse_deeppcb(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    boxes = []
    deeppcb_map = {1: NAMES.index("open_circuit"), 2: NAMES.index("short_circuit")}
    for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.replace(",", " ").split()
        if len(fields) != 5:
            raise ValueError(f"Expected x1 y1 x2 y2 class in {label_path}:{line_number}")
        try:
            x1, y1, x2, y2, raw_class = map(float, fields)
        except ValueError as exc:
            raise ValueError(f"Non-numeric DeepPCB annotation in {label_path}:{line_number}") from exc
        if not raw_class.is_integer():
            raise ValueError(f"DeepPCB class ID must be an integer in {label_path}:{line_number}")
        class_id = int(raw_class)
        if class_id in deeppcb_map:
            boxes.append((deeppcb_map[class_id], x1, y1, x2, y2))
        # Other DeepPCB labels are intentionally not reinterpreted as missing_hole.
    return boxes


def parse_yolo(label_path: Path, width: int, height: int) -> list[tuple[int, float, float, float, float]]:
    boxes = []
    for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Expected class x_center y_center width height in {label_path}:{line_number}")
        try:
            class_value, center_x, center_y, box_width, box_height = map(float, fields)
        except ValueError as exc:
            raise ValueError(f"Non-numeric YOLO annotation in {label_path}:{line_number}") from exc
        if not class_value.is_integer() or not 0 <= int(class_value) < len(NAMES):
            raise ValueError(f"YOLO class ID must be 0, 1 or 2 in {label_path}:{line_number}")
        if box_width <= 0 or box_height <= 0:
            raise ValueError(f"YOLO box width and height must be positive in {label_path}:{line_number}")
        class_id = int(class_value)
        boxes.append(
            (
                class_id,
                (center_x - box_width / 2) * width,
                (center_y - box_height / 2) * height,
                (center_x + box_width / 2) * width,
                (center_y + box_height / 2) * height,
            )
        )
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="CSV with split, group, image, label and format columns")
    parser.add_argument("output", help="New output directory for the canonical YOLO dataset")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output directory already exists; choose a new path: {output}")

    rows = read_manifest(manifest_path)
    output.mkdir(parents=True, exist_ok=False)
    base = manifest_path.parent
    groups: dict[str, str] = {}
    hashes: dict[str, str] = {}
    image_counts = {split: 0 for split in SPLITS}
    box_counts = {split: [0] * len(NAMES) for split in SPLITS}

    for row_number, row in enumerate(rows, start=2):
        split = (row.get("split") or "").strip().lower()
        group = (row.get("group") or "").strip()
        if split not in SPLITS:
            raise ValueError(f"Invalid split {split!r} at manifest row {row_number}")
        if not group:
            raise ValueError(f"Board/capture group is empty at manifest row {row_number}")
        previous_split = groups.setdefault(group, split)
        if previous_split != split:
            raise ValueError(
                f"Board group {group!r} crosses splits ({previous_split!r}, {split!r})"
            )

        image_value = (row.get("image") or "").strip()
        label_value = (row.get("label") or "").strip()
        image_path = (base / image_value).resolve()
        label_path = (base / label_value).resolve()
        if not image_value or not image_path.is_file():
            raise FileNotFoundError(f"Image missing at manifest row {row_number}: {image_path}")
        if not label_value or not label_path.is_file():
            raise FileNotFoundError(f"Annotation file missing at manifest row {row_number}: {label_path}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"OpenCV cannot read image at manifest row {row_number}: {image_path}")
        height, width = image.shape[:2]
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError(
                f"Duplicate image content at manifest row {row_number}: {image_path} "
                f"(already present in split {hashes[digest]!r})"
            )
        hashes[digest] = split

        image_format = (row.get("format") or "").strip().lower()
        if image_format == "voc":
            boxes = parse_voc(label_path)
        elif image_format == "deeppcb":
            boxes = parse_deeppcb(label_path)
        elif image_format == "yolo":
            boxes = parse_yolo(label_path, width, height)
        else:
            raise ValueError(
                f"Unsupported annotation format {image_format!r} at manifest row {row_number}"
            )

        label_lines = []
        for class_id, x1, y1, x2, y2 in boxes:
            if not all(map(lambda value: value == value and abs(value) != float("inf"), (x1, y1, x2, y2))):
                raise ValueError(f"Non-finite bounding box in {label_path}")
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError(
                    f"Bounding box outside image at manifest row {row_number}: "
                    f"{(x1, y1, x2, y2)} for image size {(width, height)}"
                )
            center_x = (x1 + x2) / (2 * width)
            center_y = (y1 + y2) / (2 * height)
            box_width = (x2 - x1) / width
            box_height = (y2 - y1) / height
            label_lines.append(
                f"{class_id} {center_x:.8f} {center_y:.8f} {box_width:.8f} {box_height:.8f}"
            )
            box_counts[split][class_id] += 1

        stem = digest[:20]
        image_dir = output / "images" / split
        label_dir = output / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, image_dir / (stem + image_path.suffix.lower()))
        (label_dir / (stem + ".txt")).write_text(
            "\n".join(label_lines) + ("\n" if label_lines else ""),
            encoding="utf-8",
        )
        image_counts[split] += 1

    missing_splits = [split for split, count in image_counts.items() if count == 0]
    if missing_splits:
        raise ValueError(f"Dataset must contain images in train, val and test splits: {missing_splits}")

    data = {
        "path": str(output),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": NAMES,
    }
    (output / "data.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    (output / "audit.json").write_text(
        json.dumps({"image_counts": image_counts, "box_counts": box_counts, "groups": groups}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"image_counts": image_counts, "box_counts": box_counts}, indent=2))
    for split, counts in box_counts.items():
        missing_classes = [NAMES[index] for index, count in enumerate(counts) if count == 0]
        if missing_classes:
            print(
                f"WARNING: {split} split has no annotations for: {', '.join(missing_classes)}. "
                "Check coverage before training or reporting per-class metrics."
            )


if __name__ == "__main__":
    main()
