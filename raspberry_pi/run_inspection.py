#!/usr/bin/env python3
"""Coordinate one PCB inspection: vision -> ExecuTorch advisory -> local log -> optional Firebase."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VISION_ENTRY = ROOT / "raspberry_pi" / "inspect_image.py"
ADVISORY_ENTRY = ROOT / "llm_advisory" / "run_executorch.py"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_path(value: str | Path) -> Path:
    """Resolve deployment paths relative to the repository, not the caller's CWD."""
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one complete local PCB inspection cycle")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", help="PCB image file")
    source.add_argument("--camera", type=int, help="USB/UVC camera index")
    source.add_argument("--picamera2", action="store_true", help="Capture one CSI camera frame")
    parser.add_argument("--weights", default="models/best.onnx")
    parser.add_argument("--board-id")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--output", default="inspection_event.json")
    parser.add_argument("--annotated", default="inspection_annotated.jpg")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    if not (0.0 <= args.conf <= 1.0 and 0.0 <= args.iou <= 1.0):
        parser.error("--conf and --iou must both be between 0 and 1")

    event_path = resolve_path(args.output)
    annotated_path = resolve_path(args.annotated)
    weights_path = resolve_path(args.weights)
    source_path = resolve_path(args.source) if args.source else None

    if source_path and not source_path.is_file():
        parser.error(f"Source image does not exist: {source_path}")
    if not weights_path.is_file():
        parser.error(f"Vision model does not exist: {weights_path}")
    if not VISION_ENTRY.is_file() or not ADVISORY_ENTRY.is_file():
        raise RuntimeError("Vision or advisory entry point is missing from the source tree")

    event_path.parent.mkdir(parents=True, exist_ok=True)
    annotated_path.parent.mkdir(parents=True, exist_ok=True)

    vision_command = [
        sys.executable, str(VISION_ENTRY),
        "--weights", str(weights_path),
        "--output", str(event_path),
        "--annotated", str(annotated_path),
        "--conf", str(args.conf),
        "--iou", str(args.iou),
    ]
    if args.board_id:
        vision_command.extend(["--board-id", args.board_id])
    if source_path:
        vision_command.extend(["--source", str(source_path)])
    elif args.picamera2:
        vision_command.append("--picamera2")
    else:
        vision_command.extend(["--camera", str(args.camera)])

    vision_run = subprocess.run(vision_command, cwd=ROOT, check=False)
    if vision_run.returncode != 0:
        return vision_run.returncode

    event = read_json(event_path)
    model_path = resolve_path(os.getenv("PCB_LLAMA_MODEL_PATH", ""))
    tokenizer_path = resolve_path(os.getenv("PCB_LLAMA_TOKENIZER_PATH", ""))
    require_advisory = env_bool("PCB_LLAMA_REQUIRED", True)
    advisory_result_path = event_path.with_name(event_path.stem + "_advisory.json")

    if not model_path.is_file() or not tokenizer_path.is_file():
        event["advisory"] = {
            "status": "MODEL_ASSETS_MISSING",
            "message": "The ExecuTorch model and matching tokenizer were not found on the Raspberry Pi.",
        }
        event["advisory_runtime"] = {"runtime": "ExecuTorch", "status": "NOT_RUN"}
        event["firebase_sync"] = {"status": "NOT_ATTEMPTED"}
        write_json(event_path, event)
        print(f"[inspection] Vision event saved; advisory model assets are missing: {event_path}", file=sys.stderr)
        if require_advisory:
            print(
                "[inspection] Complete inspection requires valid PCB_LLAMA_MODEL_PATH and "
                "PCB_LLAMA_TOKENIZER_PATH files. PCB_LLAMA_REQUIRED=false is reserved for "
                "vision-only commissioning.",
                file=sys.stderr,
            )
            return 2
    else:
        advisory_command = [
            sys.executable, str(ADVISORY_ENTRY),
            "--event", str(event_path),
            "--model", str(model_path),
            "--tokenizer", str(tokenizer_path),
            "--output", str(advisory_result_path),
        ]
        advisory_run = subprocess.run(advisory_command, cwd=ROOT, check=False)
        if advisory_run.returncode != 0:
            event["advisory"] = {
                "status": "INFERENCE_FAILED",
                "message": "ExecuTorch advisory generation failed; human review is required.",
            }
            event["advisory_runtime"] = {"runtime": "ExecuTorch", "status": "FAILED"}
            event["firebase_sync"] = {"status": "NOT_ATTEMPTED"}
            write_json(event_path, event)
            if require_advisory:
                return advisory_run.returncode or 2
        else:
            advisory_result = read_json(advisory_result_path)
            event["advisory"] = advisory_result.get("advisory") or {
                "explanation": advisory_result.get("advisory_text", "")
            }
            event["advisory_runtime"] = {
                "runtime": "ExecuTorch",
                "status": "COMPLETED",
                "model_file": advisory_result.get("model_file"),
                "ttft_ms": advisory_result.get("ttft_ms"),
                "total_response_ms": advisory_result.get("total_response_ms"),
                "tokens_per_second": advisory_result.get("tokens_per_second"),
                "process_peak_rss_kb": advisory_result.get("process_peak_rss_kb"),
            }
            write_json(event_path, event)

    # The local event is the primary inspection log. Firebase is optional synchronization.
    if args.publish:
        try:
            from firebase_client import publish_event
            publish_event(event)
            event["firebase_sync"] = {"status": "PUBLISHED"}
            write_json(event_path, event)
        except Exception as exc:
            event["firebase_sync"] = {"status": "FAILED", "message": str(exc)}
            write_json(event_path, event)
            print(
                f"[inspection] Local inspection record is saved, but Firebase synchronization failed: {exc}",
                file=sys.stderr,
            )
            return 3
    else:
        event["firebase_sync"] = {"status": "DISABLED"}
        write_json(event_path, event)

    print(f"[inspection] Complete event: {event_path}")
    print(f"[inspection] Annotated image: {annotated_path}")
    if advisory_result_path.exists():
        print(f"[inspection] Advisory telemetry: {advisory_result_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Inspection orchestration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
