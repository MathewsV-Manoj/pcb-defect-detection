#!/usr/bin/env python3
"""Fetch the attributed MIT-licensed PCB YOLOv8s checkpoint and verify its hash."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST_DIR = ROOT / "models" / "pretrained" / "sulojan_pcb_yolov8s"
REPOSITORY = "Sulojan/pcb-defect-yolov8s"
REVISION = "main"
UPSTREAM_FILE_COMMIT = "c6d4b68"
FILENAME = "best.pt"
EXPECTED_SHA256 = "1acd655ce93a474f0ed00958ddd1079afb46c74868f916af6187bf63dad5bb3d"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "Missing dependency. Install with: "
            "python -m pip install 'huggingface_hub>=0.30,<2'",
            file=sys.stderr,
        )
        return 2

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cached = hf_hub_download(
            repo_id=REPOSITORY,
            filename=FILENAME,
            revision=REVISION,
            local_dir=str(DEST_DIR),
        )
    except Exception as exc:
        print(f"Could not download {REPOSITORY}/{FILENAME}: {exc}", file=sys.stderr)
        return 1

    source_path = Path(cached)
    destination = DEST_DIR / FILENAME
    if source_path.resolve() != destination.resolve():
        destination.write_bytes(source_path.read_bytes())

    digest = sha256_file(destination)
    if digest.lower() != EXPECTED_SHA256:
        destination.unlink(missing_ok=True)
        print(
            "The downloaded checkpoint does not match the published SHA-256. "
            "It has been removed. Check the upstream revision before continuing.",
            file=sys.stderr,
        )
        return 1

    manifest = {
        "artifact_role": "third_party_pretrained_initialization_and_baseline",
        "publisher": "Sulojan Rajkumar",
        "huggingface_repository": REPOSITORY,
        "source_code_repository": "https://github.com/Sulojan2027/PCB_Defect_Detect",
        "upstream_file": FILENAME,
        "upstream_file_commit": UPSTREAM_FILE_COMMIT,
        "downloaded_from_revision": REVISION,
        "sha256": digest,
        "size_bytes": destination.stat().st_size,
        "license_declared_by_model_card": "MIT",
        "dataset_reported_by_author": "Kaggle akhatova/pcb-defects",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "class_order_reported_by_author": [
            "missing_hole", "mouse_bite", "open_circuit", "short", "spur", "spurious_copper"
        ],
        "metrics_source": "docs/PCB_UPSTREAM_BASELINE.md",
        "attribution_notice": (
            "This is a third-party model checkpoint. Preserve its attribution "
            "and distinguish upstream metrics from results measured by this team."
        ),
    }
    manifest_path = DEST_DIR / "model_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified checkpoint: {destination}")
    print(f"SHA-256: {digest}")
    print(f"Manifest: {manifest_path}")
    print("Next: export with pcb_engine_kit/train_export.py export-upstream-onnx.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
