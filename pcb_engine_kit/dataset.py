"""Import PCB images and labels with group-safe splits and provenance metadata."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import cv2
import yaml

NAMES = ["missing_hole", "open_circuit", "short_circuit"]
ALIASES = {"open": "open_circuit", "short": "short_circuit", **{name: name for name in NAMES}}
SPLITS = ("train", "val", "test")
REQUIRED_COLUMNS = {
    "split", "group", "image", "label", "format",
    "source_name", "source_url", "license_or_permission",
    "rights_review_status", "annotation_review_status",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
            raise ValueError(f"Unmapped VOC class {raw_name!r} in {label_path}; review its meaning explicitly")
        box = obj.find("bndbox")
        if box is None:
            raise ValueError(f"VOC object is missing bndbox: {label_path}")
        try:
            x1, y1, x2, y2 = [float(box.findtext(key)) for key in ("xmin", "ymin", "xmax", "ymax")]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"VOC bounding box is invalid in {label_path}") from exc
        boxes.append((NAMES.index(name), x1 - 1, y1 - 1, x2, y2))
    return boxes


def parse_deeppcb(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    # DeepPCB IDs 1 and 2 represent open and short. No hole class is inferred.
    class_map = {1: NAMES.index("open_circuit"), 2: NAMES.index("short_circuit")}
    boxes = []
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
        if class_id in class_map:
            boxes.append((class_map[class_id], x1, y1, x2, y2))
        # Other DeepPCB labels are deliberately not translated into project classes.
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
            values = list(map(float, fields))
        except ValueError as exc:
            raise ValueError(f"Non-numeric YOLO annotation in {label_path}:{line_number}") from exc
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"Non-finite YOLO annotation in {label_path}:{line_number}")
        class_value, center_x, center_y, box_width, box_height = values
        if not class_value.is_integer() or not 0 <= int(class_value) < len(NAMES):
            raise ValueError(f"YOLO class ID must be 0, 1 or 2 in {label_path}:{line_number}")
        if not (0 <= center_x <= 1 and 0 <= center_y <= 1 and 0 < box_width <= 1 and 0 < box_height <= 1):
            raise ValueError(f"YOLO coordinates must be normalized to [0, 1] in {label_path}:{line_number}")
        class_id = int(class_value)
        boxes.append((
            class_id,
            (center_x - box_width / 2) * width,
            (center_y - box_height / 2) * height,
            (center_x + box_width / 2) * width,
            (center_y + box_height / 2) * height,
        ))
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="CSV; one row per image, including source and review metadata")
    parser.add_argument("output", help="New output directory for the canonical YOLO dataset")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output directory already exists; choose a new path: {output}")
    rows = read_manifest(manifest_path)
    output.mkdir(parents=True, exist_ok=False)

    groups: dict[str, str] = {}
    seen_images: dict[str, str] = {}
    image_counts = {split: 0 for split in SPLITS}
    box_counts = {split: [0] * len(NAMES) for split in SPLITS}
    class_image_counts = {split: [0] * len(NAMES) for split in SPLITS}
    source_records: list[dict[str, Any]] = []
    provenance_issues: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        split = (row.get("split") or "").strip().lower()
        group = (row.get("group") or "").strip()
        if split not in SPLITS:
            raise ValueError(f"Invalid split {split!r} at manifest row {row_number}")
        if not group:
            raise ValueError(f"Board/capture group is empty at manifest row {row_number}")
        previous_split = groups.setdefault(group, split)
        if previous_split != split:
            raise ValueError(f"Board/capture group {group!r} crosses splits ({previous_split!r}, {split!r})")

        image_value = (row.get("image") or "").strip()
        label_value = (row.get("label") or "").strip()
        image_path = (manifest_path.parent / image_value).resolve()
        label_path = (manifest_path.parent / label_value).resolve()
        if not image_value or not image_path.is_file():
            raise FileNotFoundError(f"Image missing at manifest row {row_number}: {image_path}")
        if not label_value or not label_path.is_file():
            raise FileNotFoundError(f"Annotation file missing at manifest row {row_number}: {label_path}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"OpenCV cannot read image at manifest row {row_number}: {image_path}")
        height, width = image.shape[:2]
        image_hash = sha256_file(image_path)
        if image_hash in seen_images:
            raise ValueError(f"Duplicate image content at manifest row {row_number}; previous file: {seen_images[image_hash]}")
        seen_images[image_hash] = str(image_path)

        annotation_format = (row.get("format") or "").strip().lower()
        if annotation_format == "voc":
            boxes = parse_voc(label_path)
        elif annotation_format == "deeppcb":
            boxes = parse_deeppcb(label_path)
        elif annotation_format == "yolo":
            boxes = parse_yolo(label_path, width, height)
        else:
            raise ValueError(f"Unsupported annotation format {annotation_format!r} at manifest row {row_number}")

        label_lines = []
        classes_in_image = set()
        for class_id, x1, y1, x2, y2 in boxes:
            if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
                raise ValueError(f"Non-finite bounding box in {label_path}")
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError(f"Bounding box outside image at manifest row {row_number}: {(x1, y1, x2, y2)}")
            center_x = (x1 + x2) / (2 * width)
            center_y = (y1 + y2) / (2 * height)
            box_width = (x2 - x1) / width
            box_height = (y2 - y1) / height
            label_lines.append(f"{class_id} {center_x:.8f} {center_y:.8f} {box_width:.8f} {box_height:.8f}")
            box_counts[split][class_id] += 1
            classes_in_image.add(class_id)
        for class_id in classes_in_image:
            class_image_counts[split][class_id] += 1

        image_name = image_hash[:20] + image_path.suffix.lower()
        image_rel = Path("images") / split / image_name
        label_rel = Path("labels") / split / (image_hash[:20] + ".txt")
        image_dest = output / image_rel
        label_dest = output / label_rel
        image_dest.parent.mkdir(parents=True, exist_ok=True)
        label_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, image_dest)
        label_dest.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")

        metadata = {key: (row.get(key) or "").strip() for key in (
            "source_name", "source_url", "license_or_permission",
            "rights_review_status", "annotation_review_status",
        )}
        for key in ("source_name", "source_url", "license_or_permission"):
            if not metadata[key]:
                provenance_issues.append(f"row {row_number}: {key} is blank")
        if metadata["rights_review_status"].upper() != "CONFIRMED_BY_TEAM":
            provenance_issues.append(f"row {row_number}: data-rights review is not CONFIRMED_BY_TEAM")
        if metadata["annotation_review_status"].upper() != "REVIEWED_BY_TEAM":
            provenance_issues.append(f"row {row_number}: annotation review is not REVIEWED_BY_TEAM")

        source_records.append({
            "manifest_row": row_number,
            "split": split,
            "group": group,
            "source_image": image_value,
            "source_label": label_value,
            "processed_image": image_rel.as_posix(),
            "processed_label": label_rel.as_posix(),
            "source_image_sha256": image_hash,
            "source_label_sha256": sha256_file(label_path),
            "processed_image_sha256": sha256_file(image_dest),
            "processed_label_sha256": sha256_file(label_dest),
            "image_width": width,
            "image_height": height,
            "annotation_format": annotation_format,
            "box_count": len(boxes),
            **metadata,
        })
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
    data_yaml_path = output / "data.yaml"
    data_yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    classes_missing = {
        split: [NAMES[index] for index, count in enumerate(box_counts[split]) if count == 0]
        for split in SPLITS
    }
    groups_per_split = {
        split: sorted(group for group, group_split in groups.items() if group_split == split)
        for split in SPLITS
    }
    audit = {
        "schema_version": 2,
        "measurement_type": "dataset_structure_and_provenance_audit",
        "structure_status": "VALID",
        "provenance_status": "COMPLETE_AS_DECLARED" if not provenance_issues else "INCOMPLETE",
        "release_ready": not provenance_issues and all(not missing for missing in classes_missing.values()),
        "import_manifest_path": str(manifest_path),
        "import_manifest_sha256": sha256_file(manifest_path),
        "data_yaml_path": str(data_yaml_path),
        "data_yaml_sha256": sha256_file(data_yaml_path),
        "class_order": NAMES,
        "image_counts": image_counts,
        "box_counts": {split: dict(zip(NAMES, counts)) for split, counts in box_counts.items()},
        "class_image_counts": {split: dict(zip(NAMES, counts)) for split, counts in class_image_counts.items()},
        "classes_missing_by_split": classes_missing,
        "group_counts": {split: len(values) for split, values in groups_per_split.items()},
        "groups_by_split": groups_per_split,
        "source_names": sorted({record["source_name"] for record in source_records if record["source_name"]}),
        "provenance_issues": provenance_issues,
        "records": source_records,
        "limitations": [
            "Rights and annotation review statuses are declarations entered by the project team; this script does not provide legal advice or independently verify labels.",
            "A successful structural audit does not establish that the target classes are visually or electrically defined correctly.",
            "Board/capture groups must be stable identifiers for the same physical board, design, or capture session.",
        ],
    }
    audit_path = output / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "structure_status": audit["structure_status"],
        "provenance_status": audit["provenance_status"],
        "release_ready": audit["release_ready"],
        "image_counts": image_counts,
        "box_counts": audit["box_counts"],
        "classes_missing_by_split": classes_missing,
        "provenance_issues": provenance_issues,
        "audit_path": str(audit_path),
    }, indent=2))


if __name__ == "__main__":
    main()
