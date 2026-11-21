"""Publish a complete input image to the folder-worker queue with atomic rename."""
from __future__ import annotations

import argparse
import os
import shutil
import uuid
from pathlib import Path

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Image file to submit")
    parser.add_argument("--root", default="~/Desktop/PCBInspection", help="Folder-worker root")
    args = parser.parse_args()

    source = Path(args.image).expanduser().resolve()
    if not source.is_file():
        parser.error(f"Image does not exist: {source}")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        parser.error(f"Supported image extensions are: {', '.join(sorted(SUPPORTED_SUFFIXES))}")

    root = Path(args.root).expanduser().resolve()
    incoming = root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    destination = incoming / (uuid.uuid4().hex + source.suffix.lower())
    partial = destination.with_name(destination.name + ".part")
    try:
        shutil.copyfile(source, partial)
        # Flush data before publishing its final queue filename.
        with partial.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(partial, destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    print(destination.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
