#!/usr/bin/env python3
"""Run non-destructive ONNX + real ExecuTorch advisory smoke tests on the Pi 5."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "raspberry_pi"))
from inspect_image import SIZE, load_model_contract  # noqa: E402
from severity_policy import load_severity_policy  # noqa: E402

LLAMA_MODEL = ROOT / "models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"
LLAMA_TOKENIZER = ROOT / "models/llama/tokenizer.model"
LLAMA_RUNNER = ROOT / "models/llama/runtime/llama_main"
EXAMPLE_EVENT = ROOT / "schemas/example-event.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/best.onnx")
    parser.add_argument("--out", default="docs/results/pi5_runtime_smoke_test.json")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    model = Path(args.model).expanduser()
    if not model.is_absolute():
        model = ROOT / model
    output = Path(args.out).expanduser()
    if not output.is_absolute():
        output = ROOT / output

    report: dict[str, Any] = {
        "schema_version": 1,
        "measurement_type": "pi5_local_runtime_smoke_test_not_accuracy_evaluation",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": {
            "hostname": platform.node(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "vision": {"status": "NOT_RUN"},
        "advisory": {"status": "NOT_RUN"},
        "severity_policy": {"status": "NOT_RUN"},
        "limitations": [
            "The detector test uses a synthetic all-zero tensor to verify ONNX loading and CPU execution only.",
            "This smoke test does not measure PCB accuracy, false positives, false negatives or mAP.",
            "The example event sent to Llama is illustrative and is not a real PCB inspection.",
            "This test does not exercise camera, IR sensor, illumination, conveyor, dashboard timing or power draw.",
        ],
    }
    failures: list[str] = []

    try:
        if not model.is_file():
            raise FileNotFoundError(f"ONNX detector not found: {model}")
        class_order, target_map, metadata = load_model_contract(model)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(
            str(model), sess_options=options, providers=["CPUExecutionProvider"]
        )
        inputs, outputs = session.get_inputs(), session.get_outputs()
        if len(inputs) != 1 or len(outputs) != 1:
            raise RuntimeError("Expected exactly one YOLO ONNX input and one output")
        input_meta = inputs[0]
        if input_meta.shape != [1, 3, SIZE, SIZE] or input_meta.type != "tensor(float)":
            raise RuntimeError(
                f"Unexpected ONNX input contract: {input_meta.shape} / {input_meta.type}"
            )
        synthetic = np.zeros((1, 3, SIZE, SIZE), dtype=np.float32)
        started = time.perf_counter()
        prediction = session.run(None, {input_meta.name: synthetic})[0]
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not isinstance(prediction, np.ndarray) or not np.isfinite(prediction).all():
            raise RuntimeError("ONNX produced an invalid or non-finite output")
        report["vision"] = {
            "status": "PASSED",
            "provider": session.get_providers(),
            "input_shape": input_meta.shape,
            "input_type": input_meta.type,
            "output_shape": list(prediction.shape),
            "source_class_order": class_order,
            "target_class_map": target_map,
            "metadata": metadata,
            "onnx_sha256": sha256(model),
            "synthetic_zero_tensor_inference_ms": round(elapsed_ms, 2),
        }
    except Exception as exc:
        failures.append(f"Vision smoke test: {exc}")
        report["vision"] = {"status": "FAILED", "error": str(exc)}

    try:
        policy = load_severity_policy()
        report["severity_policy"] = {
            "status": "LOADED",
            "name": policy.get("policy_name"),
            "policy_status": policy.get("status"),
            "path": policy.get("_path"),
            "scope": policy.get("scope"),
            "rules": policy.get("rules"),
        }
    except Exception as exc:
        failures.append(f"Severity policy: {exc}")
        report["severity_policy"] = {"status": "FAILED", "error": str(exc)}

    try:
        for path, label in (
            (LLAMA_MODEL, "Llama PTE model"),
            (LLAMA_TOKENIZER, "Llama tokenizer"),
            (LLAMA_RUNNER, "ExecuTorch llama_main runner"),
            (EXAMPLE_EVENT, "Example event"),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"{label} missing: {path}")
        if not os.access(LLAMA_RUNNER, os.X_OK):
            raise PermissionError(f"ExecuTorch runner is not executable: {LLAMA_RUNNER}")

        advisory_path = output.with_name(output.stem + "_advisory.json")
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(LLAMA_RUNNER.parent) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        command = [
            sys.executable,
            str(ROOT / "llm_advisory/run_executorch.py"),
            "--event", str(EXAMPLE_EVENT),
            "--model", str(LLAMA_MODEL),
            "--tokenizer", str(LLAMA_TOKENIZER),
            "--runner", str(LLAMA_RUNNER),
            "--backend", "cli",
            "--seq-len", "1024",
            "--timeout-seconds", str(args.timeout_seconds),
            "--output", str(advisory_path),
        ]
        started = time.perf_counter()
        completed = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=args.timeout_seconds + 30, check=False,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "No runner output")[-4000:]
            raise RuntimeError(f"ExecuTorch exited {completed.returncode}: {detail}")
        advisory_result = json.loads(advisory_path.read_text(encoding="utf-8"))
        advisory = advisory_result.get("advisory")
        required = {"explanation", "recommended_actions", "severity_note", "log_entry"}
        if not isinstance(advisory, dict) or set(advisory) != required:
            raise RuntimeError("ExecuTorch response did not satisfy the four-field advisory contract")
        report["advisory"] = {
            "status": "PASSED",
            "runner_backend": advisory_result.get("runner_backend"),
            "total_response_ms": advisory_result.get("total_response_ms"),
            "ttft_ms": advisory_result.get("ttft_ms"),
            "tokens_per_second": advisory_result.get("tokens_per_second"),
            "process_peak_rss_kb": advisory_result.get("process_peak_rss_kb"),
            "wall_time_including_process_start_ms": round(elapsed_ms, 2),
            "model_sha256": sha256(LLAMA_MODEL),
            "tokenizer_sha256": sha256(LLAMA_TOKENIZER),
            "runner_sha256": sha256(LLAMA_RUNNER),
            "advisory_output": advisory,
            "smoke_output_path": str(advisory_path),
        }
    except subprocess.TimeoutExpired:
        failures.append(f"ExecuTorch smoke test timed out after {args.timeout_seconds} seconds")
        report["advisory"] = {"status": "FAILED", "error": failures[-1]}
    except Exception as exc:
        failures.append(f"ExecuTorch advisory smoke test: {exc}")
        report["advisory"] = {"status": "FAILED", "error": str(exc)}

    report["overall_status"] = "PASSED" if not failures else "FAILED"
    report["failures"] = failures
    write_json(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Saved Pi 5 smoke-test report: {output}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
