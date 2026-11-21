#!/usr/bin/env python3
"""Coordinate one PCB inspection: vision -> Llama advisory -> local log -> Firebase."""
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
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a complete local PCB inspection cycle")
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

    event_path = Path(args.output).expanduser()
    annotated_path = Path(args.annotated).expanduser()
    if not event_path.is_absolute():
        event_path = ROOT / event_path
    if not annotated_path.is_absolute():
        annotated_path = ROOT / annotated_path

    if not VISION_ENTRY.is_file() or not ADVISORY_ENTRY.is_file():
        raise RuntimeError("Vision or advisory entry point is missing from the source tree")

    vision_command = [
        sys.executable, str(VISION_ENTRY),
        "--weights", str(Path(args.weights).resolve() if not Path(args.weights).is_absolute() else Path(args.weights)),
        "--output", str(event_path),
        "--annotated", str(annotated_path),
        "--conf", str(args.conf),
        "--iou", str(args.iou),
    ]
    if args.board_id:
        vision_command.extend(["--board-id", args.board_id])
    if args.source:
        vision_command.extend(["--source", args.source])
    elif args.picamera2:
        vision_command.append("--picamera2")
    else:
        vision_command.extend(["--camera", str(args.camera)])

    vision_run = subprocess.run(vision_command, cwd=ROOT, check=False)
    if vision_run.returncode != 0:
        return vision_run.returncode

    event = read_json(event_path)
    model_path = Path(os.getenv("PCB_LLAMA_MODEL_PATH", "")).expanduser()
    tokenizer_path = Path(os.getenv("PCB_LLAMA_TOKENIZER_PATH", "")).expanduser()
    require_advisory = env_bool("PCB_LLAMA_REQUIRED", True)

    advisory_result_path = event_path.with_name(event_path.stem + "_advisory.json")
    if not model_path.is_file() or not tokenizer_path.is_file():
        event["advisory"] = {
            "status": "MODEL_ASSETS_MISSING",
            "message": "The ExecuTorch model and matching tokenizer were not found.",
        }
        event["advisory_runtime"] = {"runtime": "ExecuTorch", "status": "NOT_RUN"}
        write_json(event_path, event)
        print(f"[inspection] Vision event saved; advisory model assets are missing: {event_path}", file=sys.stderr)
        if require_advisory:
            print(
                "[inspection] Complete inspection requires PCB_LLAMA_MODEL_PATH and "
                "PCB_LLAMA_TOKENIZER_PATH. Set PCB_LLAMA_REQUIRED=false only for vision-only commissioning.",
                file=sys.stderr,
            )
            return 2
    else:
        advisory_command = [
            sys.executable, str(ADVISORY_ENTRY),
            "--event", str(event_path),
            "--model", str(model_path.resolve()),
            "--tokenizer", str(tokenizer_path.resolve()),
            "--output", str(advisory_result_path),
        ]
        advisory_run = subprocess.run(advisory_command, cwd=ADVISORY_ENTRY.parent, check=False)
        if advisory_run.returncode != 0:
            event["advisory"] = {
                "status": "INFERENCE_FAILED",
                "message": "ExecuTorch advisory generation failed; human review is required.",
            }
            event["advisory_runtime"] = {"runtime": "ExecuTorch", "status": "FAILED"}
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

    # Local JSON is the inspection log. Firebase is an optional synchronization layer.
    if args.publish:
        from firebase_client import publish_event
        publish_event(event)

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
