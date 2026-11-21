#!/usr/bin/env python3
"""Measure the Pi ONNX detector on a folder of representative PCB images.

This reports runtime only. It does not calculate precision, recall or mAP; those
require ground-truth labels and a separate held-out evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from inspect_image import CLASS_NAMES, SIZE, decode, letterbox, load_model_contract

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith(("model name", "model")) and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def read_os_release() -> str | None:
    path = Path("/etc/os-release")
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def read_temperature_c() -> float | None:
    candidates = sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
    values = []
    for path in candidates:
        try:
            raw = int(path.read_text().strip())
            # Linux thermal sysfs commonly reports millidegrees Celsius.
            value = raw / 1000.0 if raw > 1000 else float(raw)
            if -20.0 <= value <= 150.0:
                values.append(value)
        except (OSError, ValueError):
            continue
    return max(values) if values else None


def percentile(values: list[float], percent: float) -> float:
    return round(float(np.percentile(np.asarray(values, dtype=np.float64), percent)), 2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/best.onnx")
    parser.add_argument("--images", required=True, help="Folder containing held-out or representative PCB images")
    parser.add_argument("--out", default="pi_onnx_benchmark.json")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    model_path = Path(args.model).expanduser().resolve()
    image_dir = Path(args.images).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    if not model_path.is_file():
        parser.error(f"ONNX model not found: {model_path}")
    if not image_dir.is_dir():
        parser.error(f"Image folder not found: {image_dir}")
    if args.warmup < 0 or args.threads < 1:
        parser.error("--warmup must be >= 0 and --threads must be >= 1")
    if not (0.0 <= args.confidence <= 1.0 and 0.0 <= args.iou <= 1.0):
        parser.error("--confidence and --iou must be between 0 and 1")

    image_paths = sorted(
        path for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not image_paths:
        parser.error(f"No supported image files were found in {image_dir}")

    cv2.setNumThreads(1)
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    model_class_names, target_class_map, model_metadata = load_model_contract(model_path)
    session = ort.InferenceSession(
        str(model_path),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or len(outputs) != 1:
        raise RuntimeError("Expected one input and one output tensor for this YOLO export")
    input_meta = inputs[0]
    if input_meta.shape != [1, 3, SIZE, SIZE] or input_meta.type != "tensor(float)":
        raise RuntimeError(
            f"Expected float32 ONNX input [1,3,{SIZE},{SIZE}], got {input_meta.shape} / {input_meta.type}"
        )

    first_image = cv2.imread(str(image_paths[0]))
    if first_image is None:
        raise RuntimeError(f"Could not read image: {image_paths[0]}")

    def infer(image: np.ndarray) -> tuple[float, float, float, int]:
        start = time.perf_counter()
        padded, scale, pad = letterbox(image)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        tensor = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        pre_ms = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        prediction = session.run(None, {input_meta.name: tensor})[0]
        infer_ms = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        detections = decode(
            prediction,
            image.shape[:2],
            scale,
            pad,
            args.confidence,
            args.iou,
            model_class_names=model_class_names,
            target_class_map=target_class_map,
        )
        post_ms = (time.perf_counter() - start) * 1000.0
        return pre_ms, infer_ms, post_ms, len(detections)

    # Warm-up calls are excluded from reported sample timings.
    for _ in range(args.warmup):
        infer(first_image)

    preprocess_ms: list[float] = []
    inference_ms: list[float] = []
    postprocess_ms: list[float] = []
    total_ms: list[float] = []
    detection_counts: list[int] = []
    failed_images: list[str] = []

    temperature_start = read_temperature_c()
    for image_path in image_paths:
        image = cv2.imread(str(image_path))
        if image is None:
            failed_images.append(image_path.name)
            continue
        try:
            pre, vision, post, detections = infer(image)
        except Exception as exc:
            failed_images.append(f"{image_path.name}: {exc}")
            continue
        preprocess_ms.append(pre)
        inference_ms.append(vision)
        postprocess_ms.append(post)
        total_ms.append(pre + vision + post)
        detection_counts.append(detections)

    temperature_end = read_temperature_c()
    if not total_ms:
        raise RuntimeError("No images could be processed successfully")

    peak_rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result: dict[str, Any] = {
        "schema_version": 1,
        "measurement_type": "onnx_detector_runtime_only",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": {
            "hostname": platform.node(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
            "cpu_model": read_cpu_model(),
            "os": read_os_release(),
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "onnxruntime": ort.__version__,
            "logical_cpu_count": os.cpu_count(),
        },
        "model": {
            "path": str(model_path),
            "sha256": sha256_file(model_path),
            "class_order": CLASS_NAMES,
            "source_model_class_order": model_class_names,
            "source_model_target_class_map": target_class_map,
            "source_model_metadata": model_metadata,
            "input_shape": input_meta.shape,
            "input_type": input_meta.type,
            "provider": session.get_providers(),
            "threads": args.threads,
        },
        "test_images": {
            "folder": str(image_dir),
            "found": len(image_paths),
            "processed": len(total_ms),
            "failed": failed_images,
            "confidence_threshold": args.confidence,
            "nms_iou_threshold": args.iou,
            "warmup_runs_excluded": args.warmup,
        },
        "runtime_ms": {
            "preprocess_mean": round(statistics.fmean(preprocess_ms), 2),
            "inference_mean": round(statistics.fmean(inference_ms), 2),
            "postprocess_mean": round(statistics.fmean(postprocess_ms), 2),
            "total_mean": round(statistics.fmean(total_ms), 2),
            "total_p50": percentile(total_ms, 50),
            "total_p95": percentile(total_ms, 95),
            "total_max": round(max(total_ms), 2),
            "sequential_fps": round(1000.0 / statistics.fmean(total_ms), 2),
        },
        "process": {
            "peak_rss_kib_linux": peak_rss_kib,
            "thermal_zone_max_start_c": temperature_start,
            "thermal_zone_max_end_c": temperature_end,
        },
        "power_watts": None,
        "notes": [
            "These timings cover image preprocessing, ONNX inference and detector post-processing only.",
            "They exclude camera capture, LED settling, HTTP transfer, Llama generation and Firebase synchronization.",
            "Power is not measured by this script; use an external power meter and record its reading separately.",
            "This report contains no accuracy metric. Evaluate labelled held-out boards separately.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    print(json.dumps(result, indent=2))
    print(f"Saved benchmark: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ONNX benchmark failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
