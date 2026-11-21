#!/usr/bin/env python3
"""Measure repeated still-image vision + Llama inspection on the actual Pi.

This invokes the production coordinator per image. It does not simulate GPIO,
camera capture, conveyor motion, illumination or browser delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = ROOT / "raspberry_pi" / "run_inspection.py"
SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], percentage: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate percentile for an empty sample")
    index = (len(ordered) - 1) * percentage / 100.0
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return round(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction, 2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, help="Folder with held-out PCB images")
    parser.add_argument("--model", default="models/best.onnx")
    parser.add_argument("--llama-model", default="models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte")
    parser.add_argument("--tokenizer", default="models/llama/tokenizer.model")
    parser.add_argument("--runner", default="models/llama/runtime/llama_main")
    parser.add_argument("--backend", choices=("cli", "python"), default="cli")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum image count; 0 means all")
    parser.add_argument("--out", default="docs/results/pi_pipeline_benchmark.json")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    image_dir = Path(args.images).expanduser().resolve()
    model = (ROOT / args.model).resolve() if not Path(args.model).is_absolute() else Path(args.model).resolve()
    llama_model = Path(args.llama_model).expanduser().resolve()
    tokenizer = Path(args.tokenizer).expanduser().resolve()
    runner = Path(args.runner).expanduser().resolve()
    output = Path(args.out).expanduser().resolve()

    if not image_dir.is_dir():
        parser.error(f"Image directory not found: {image_dir}")
    for path, label in ((model, "YOLO ONNX model"), (llama_model, "Llama PTE"),
                        (tokenizer, "Llama tokenizer")):
        if not path.is_file():
            parser.error(f"{label} not found: {path}")
    if args.backend == "cli" and not runner.is_file():
        parser.error(f"ExecuTorch llama_main not found: {runner}")
    if args.warmup < 0 or args.limit < 0 or args.timeout_seconds < 1:
        parser.error("warmup/limit must be non-negative and timeout must be positive")

    images = sorted(p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES)
    if args.limit:
        images = images[:args.limit]
    if len(images) <= args.warmup:
        parser.error("Provide more images than the number of warm-up runs")

    samples: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    wall_ms: list[float] = []
    detector_ms: list[float] = []
    llama_ms: list[float] = []
    ttft_ms: list[float] = []
    tokens_per_second: list[float] = []
    child_rss_kib: list[int] = []

    env = os.environ.copy()
    env.update({
        "PCB_LLAMA_MODEL_PATH": str(llama_model),
        "PCB_LLAMA_TOKENIZER_PATH": str(tokenizer),
        "PCB_LLAMA_RUNNER_PATH": str(runner),
        "PCB_LLAMA_BACKEND": args.backend,
        "PCB_LLAMA_REQUIRED": "true",
        "PCB_LLAMA_TIMEOUT_SECONDS": str(args.timeout_seconds),
        "PCB_FIREBASE_PUBLISH": "false",
    })

    with tempfile.TemporaryDirectory(prefix="pcb-pipeline-bench-") as temporary:
        temp_dir = Path(temporary)
        for index, image_path in enumerate(images):
            event_path = temp_dir / f"event_{index:04d}.json"
            annotated_path = temp_dir / f"annotated_{index:04d}.jpg"
            board_id = f"BENCH-{index:04d}"
            command = [
                sys.executable, str(COORDINATOR),
                "--source", str(image_path),
                "--weights", str(model),
                "--board-id", board_id,
                "--output", str(event_path),
                "--annotated", str(annotated_path),
            ]
            started = time.perf_counter()
            try:
                completed = subprocess.run(
                    command, cwd=ROOT, env=env, capture_output=True,
                    text=True, timeout=args.timeout_seconds + 60, check=False,
                )
                elapsed = (time.perf_counter() - started) * 1000.0
            except subprocess.TimeoutExpired:
                failures.append({"image": image_path.name, "reason": "pipeline process timeout"})
                continue

            if completed.returncode != 0 or not event_path.is_file():
                detail = (completed.stderr or completed.stdout or "No diagnostic output")[-2500:]
                failures.append({"image": image_path.name, "reason": detail})
                continue
            try:
                event = json.loads(event_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                failures.append({"image": image_path.name, "reason": f"invalid event JSON: {exc}"})
                continue

            advisory_runtime = event.get("advisory_runtime") or {}
            if advisory_runtime.get("status") != "COMPLETED":
                failures.append({
                    "image": image_path.name,
                    "reason": "Llama advisory did not complete: " + str(advisory_runtime),
                })
                continue

            is_warmup = index < args.warmup
            row = {
                "image": image_path.name,
                "warmup": is_warmup,
                "image_to_advisory_wall_ms": round(elapsed, 2),
                "detector_inference_ms": event.get("inference_latency_ms"),
                "llama_response_ms": advisory_runtime.get("total_response_ms"),
                "llama_ttft_ms": advisory_runtime.get("ttft_ms"),
                "llama_tokens_per_second": advisory_runtime.get("tokens_per_second"),
                "llama_process_peak_rss_kib": advisory_runtime.get("process_peak_rss_kb"),
            }
            if not is_warmup:
                samples.append(row)
                wall_ms.append(elapsed)
                if isinstance(row["detector_inference_ms"], (int, float)):
                    detector_ms.append(float(row["detector_inference_ms"]))
                if isinstance(row["llama_response_ms"], (int, float)):
                    llama_ms.append(float(row["llama_response_ms"]))
                if isinstance(row["llama_ttft_ms"], (int, float)):
                    ttft_ms.append(float(row["llama_ttft_ms"]))
                if isinstance(row["llama_tokens_per_second"], (int, float)):
                    tokens_per_second.append(float(row["llama_tokens_per_second"]))
                if isinstance(row["llama_process_peak_rss_kib"], int):
                    child_rss_kib.append(row["llama_process_peak_rss_kib"])

    if not samples:
        raise RuntimeError(f"No measured pipeline runs completed successfully. Failures: {failures}")

    def summary(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"mean": None, "p50": None, "p95": None, "max": None}
        return {
            "mean": round(statistics.fmean(values), 2),
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "max": round(max(values), 2),
        }

    report = {
        "schema_version": 1,
        "measurement_type": "still_image_vision_plus_executorch_advisory_pipeline",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": {
            "hostname": platform.node(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "models": {
            "yolo_onnx_path": str(model),
            "yolo_onnx_sha256": sha256_file(model),
            "llama_pte_path": str(llama_model),
            "llama_pte_sha256": sha256_file(llama_model),
            "tokenizer_path": str(tokenizer),
            "tokenizer_sha256": sha256_file(tokenizer),
            "llama_backend": args.backend,
            "runner_path": str(runner) if args.backend == "cli" else None,
        },
        "test": {
            "image_directory": str(image_dir),
            "image_count": len(images),
            "warmup_attempts_excluded": args.warmup,
            "measured_successful_runs": len(samples),
            "failed_runs": failures,
        },
        "timing_ms": {
            "image_to_advisory_wall": summary(wall_ms),
            "detector_inference_only": summary(detector_ms),
            "llama_response": summary(llama_ms),
            "llama_time_to_first_token": summary(ttft_ms),
        },
        "llama_generation_tokens_per_second": summary(tokens_per_second),
        "llama_process_peak_rss_kib": max(child_rss_kib) if child_rss_kib else None,
        "power_watts": None,
        "samples": samples,
        "notes": [
            "Runs the production run_inspection.py coordinator once per still image.",
            "Includes process start/model initialization and text advisory; excludes physical camera, IR trigger, conveyor, LED settling and browser rendering.",
            "ExecuTorch C++ runner currently does not expose token-level TTFT or tokens/s to this wrapper; those fields remain null rather than estimated.",
            "No accuracy metrics are calculated; labelled held-out board evaluation is separate.",
            "Power is not measured; use a calibrated external meter for power claims.",
            "Keep the input image list and model/tokenizer hashes with the report.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_output, output)
    print(json.dumps(report, indent=2))
    print(f"Saved pipeline benchmark: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
