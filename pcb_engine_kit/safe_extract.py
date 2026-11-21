"""Safely extract a dataset ZIP into a new directory."""
from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_UNCOMPRESSED_BYTES = 20 * 1024**3
MAX_MEMBERS = 1_000_000


def validate_archive(archive: zipfile.ZipFile, output: Path) -> None:
    members = archive.infolist()
    if len(members) > MAX_MEMBERS:
        raise ValueError(f"Archive contains too many entries ({len(members)} > {MAX_MEMBERS})")
    total_size = sum(member.file_size for member in members)
    if total_size > MAX_UNCOMPRESSED_BYTES:
        raise ValueError(
            f"Archive expands to {total_size} bytes; maximum is {MAX_UNCOMPRESSED_BYTES}"
        )

    seen: set[Path] = set()
    for member in members:
        raw_name = member.filename
        if not raw_name or "\x00" in raw_name or "\\" in raw_name:
            raise ValueError(f"Invalid archive member name: {raw_name!r}")

        relative = PurePosixPath(raw_name)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError(f"Unsafe archive member path: {raw_name!r}")
        if relative.parts and ":" in relative.parts[0]:
            raise ValueError(f"Drive-qualified archive path is not allowed: {raw_name!r}")

        destination = (output / Path(*relative.parts)).resolve()
        if destination != output and output not in destination.parents:
            raise ValueError(f"Archive member escapes the destination: {raw_name!r}")
        if destination in seen:
            raise ValueError(f"Duplicate archive destination: {raw_name!r}")
        seen.add(destination)

        mode = member.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        is_directory = member.is_dir()
        if file_type == stat.S_IFLNK:
            raise ValueError(f"Symlinks are not supported: {raw_name!r}")
        if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise ValueError(f"Special filesystem entry is not supported: {raw_name!r}")
        if is_directory and file_type == stat.S_IFREG:
            raise ValueError(f"Directory entry has a regular-file mode: {raw_name!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="Input ZIP archive")
    parser.add_argument("output", help="New extraction directory")
    args = parser.parse_args()

    archive_path = Path(args.archive).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    if not archive_path.is_file():
        parser.error(f"Archive does not exist: {archive_path}")
    if output.exists():
        parser.error(f"Destination already exists; use a new directory: {output}")

    try:
        with zipfile.ZipFile(archive_path) as source:
            validate_archive(source, output)
            bad_member = source.testzip()
            if bad_member is not None:
                raise ValueError(f"Archive CRC check failed for: {bad_member}")
            output.mkdir(parents=True, exist_ok=False)
            try:
                source.extractall(output)
            except Exception:
                # Do not leave a partially extracted dataset that could be mistaken for complete.
                import shutil
                shutil.rmtree(output, ignore_errors=True)
                raise
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        parser.exit(2, f"Extraction failed: {exc}\n")

    print(f"Extracted {archive_path.name} into {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
