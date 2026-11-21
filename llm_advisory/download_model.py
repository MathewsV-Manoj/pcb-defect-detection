#!/usr/bin/env python3
"""Download the pinned ExecuTorch-community Llama 3.2 1B SpinQuant package."""
from __future__ import annotations
import hashlib, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = REPO_ROOT / "models" / "llama"
REPOSITORY = "executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET"
REVISION = "911221e0f49d3354cbd4697a9c09feee25cadec7"
MODEL_FILE = "Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"
TOKENIZER_FILE = "tokenizer.model"
REQUIRED_FILES = (MODEL_FILE, TOKENIZER_FILE, "params.json", "config.json", "README.md")

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> int:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Missing dependency. Install: python -m pip install 'huggingface_hub>=0.30,<2'", file=sys.stderr)
        return 2
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(TARGET_DIR).free
    if free_bytes < 2_500_000_000:
        print(f"At least 2.5 GB free space is recommended; found {free_bytes / 1e9:.2f} GB.", file=sys.stderr)
        return 2
    print(f"Downloading {REPOSITORY} at immutable revision {REVISION}")
    print("The model file is about 1.14 GB; Hugging Face login/license acceptance may be required.")
    try:
        snapshot_download(repo_id=REPOSITORY, revision=REVISION, local_dir=str(TARGET_DIR),
                          allow_patterns=list(REQUIRED_FILES))
    except Exception as exc:
        print("Download failed. Confirm network access and, if requested, use 'hf auth login' "
              f"and accept the Llama 3.2 license. Details: {exc}", file=sys.stderr)
        return 1
    missing = [name for name in REQUIRED_FILES if not (TARGET_DIR / name).is_file()]
    if missing:
        print(f"Download completed without required files: {', '.join(missing)}", file=sys.stderr)
        return 1
    manifest = {
        "repository": REPOSITORY, "revision": REVISION, "license": "llama3.2",
        "model_file": MODEL_FILE, "tokenizer_file": TOKENIZER_FILE,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {name: {"size_bytes": (TARGET_DIR / name).stat().st_size,
                         "sha256": sha256_file(TARGET_DIR / name)} for name in REQUIRED_FILES},
        "warning": "Review and comply with the upstream Llama 3.2 license and acceptable-use policy."
    }
    manifest_path = TARGET_DIR / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Model: {TARGET_DIR / MODEL_FILE}")
    print(f"Tokenizer: {TARGET_DIR / TOKENIZER_FILE}")
    print(f"Local hash manifest: {manifest_path}")
    print("Next: run llm_advisory/build_pi5_runner.sh on a Linux x86_64 build host.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
