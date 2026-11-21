"""Create an ORB/homography reference-board profile from a known-good PCB image."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Known-good PCB reference image")
    parser.add_argument("output", help="New output directory for reference image and profile")
    args = parser.parse_args()

    source = Path(args.image).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_file():
        parser.error(f"Reference image does not exist: {source}")
    if output.exists():
        parser.error(f"Output directory already exists: {output}")

    image = cv2.imread(str(source))
    if image is None:
        parser.error(f"OpenCV cannot read reference image: {source}")

    scale = min(1.0, 1200 / max(image.shape[:2]))
    display = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1.0 else image.copy()
    print("Select installed components only. Enter/space confirms; Escape finishes. IDs follow selection order.")

    boxes = cv2.selectROIs("Expected components", display, False)
    cv2.destroyAllWindows()
    regions = [
        {
            "id": f"CANDIDATE_{index + 1}",
            "box": [int(x), int(y), int(x + width), int(y + height)],
            "min_similarity": 0.8,
        }
        for index, (x, y, width, height) in enumerate(boxes)
        if width > 0 and height > 0
    ]
    if not regions:
        parser.error("Select at least one expected component region.")

    output.mkdir(parents=True, exist_ok=False)
    reference_path = output / "good.png"
    if not cv2.imwrite(str(reference_path), display):
        raise OSError(f"Could not write reference image: {reference_path}")
    (output / "profile.json").write_text(
        json.dumps({"reference": "good.png", "regions": regions}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Reference profile created at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
