#!/usr/bin/env python3
"""Generate a bounded, text-only Llama advisory using ExecuTorch on-device."""
from __future__ import annotations

import argparse
import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from prompt import build_prompt

REQUIRED_KEYS = {"explanation", "recommended_actions", "severity_note", "log_entry"}
DEFAULT_MODEL = "models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"
DEFAULT_TOKENIZER = "models/llama/tokenizer.model"
DEFAULT_RUNNER = "models/llama/runtime/llama_main"


def resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def load_event(path: Path) -> dict[str, Any]:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load inspection event {path}: {exc}") from exc
    if not isinstance(event, dict):
        raise RuntimeError("Inspection event must be a JSON object")
    required = {"record_id", "board_id", "timestamp", "decision", "source", "detections"}
    missing = sorted(required.difference(event))
    if missing:
        raise RuntimeError(f"Inspection event is missing: {', '.join(missing)}")
    if not isinstance(event["detections"], list):
        raise RuntimeError("Inspection event detections must be a list")
    return event


def parse_advisory_json(raw_text: str) -> dict[str, Any] | None:
    """Find a complete advisory object even when the runner prints log lines."""
    decoder = json.JSONDecoder()
    for start, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw_text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and set(value) == REQUIRED_KEYS:
            return value
    return None


def validate_advisory(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None or set(value) != REQUIRED_KEYS:
        raise RuntimeError(
            "Llama output must contain one JSON object with exactly: "
            "explanation, recommended_actions, severity_note, log_entry"
        )
    for key in ("explanation", "severity_note", "log_entry"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise RuntimeError(f"Llama field '{key}' must be a non-empty string")
    actions = value["recommended_actions"]
    if not isinstance(actions, list) or not all(
        isinstance(item, str) and item.strip() for item in actions
    ):
        raise RuntimeError("Llama 'recommended_actions' must be an array of non-empty strings")
    return value


def parse_pytorch_observer(raw_text: str) -> dict[str, Any] | None:
    """Parse ExecuTorch's machine-readable generation statistics, if emitted."""
    found: dict[str, Any] | None = None
    for line in raw_text.splitlines():
        marker = line.find("PyTorchObserver")
        if marker < 0:
            continue
        payload = line[marker + len("PyTorchObserver"):].strip()
        try:
            stats = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(stats, dict) and {
            "inference_start_ms", "inference_end_ms", "generated_tokens"
        }.issubset(stats):
            found = stats
    return found


def observer_ttft_ms(stats: dict[str, Any] | None) -> float | None:
    if not stats:
        return None
    start = stats.get("inference_start_ms")
    first = stats.get("first_token_ms")
    if isinstance(start, (int, float)) and isinstance(first, (int, float)) and first >= start:
        return round(float(first - start), 2)
    return None


def observer_tokens_per_second(stats: dict[str, Any] | None) -> float | None:
    if not stats:
        return None
    generated = stats.get("generated_tokens")
    start = stats.get("inference_start_ms")
    end = stats.get("inference_end_ms")
    if (
        isinstance(generated, (int, float)) and generated > 0
        and isinstance(start, (int, float)) and isinstance(end, (int, float))
        and end > start
    ):
        return round(float(generated) * 1000.0 / float(end - start), 2)
    return None


def linux_peak_child_rss_kib() -> int | None:
    try:
        # Linux reports ru_maxrss in KiB. This is the maximum child-process
        # resident set size observed by this coordinator process.
        return int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    except (AttributeError, OSError, ValueError):
        return None


def run_cli(
    event: dict[str, Any], model_path: Path, tokenizer_path: Path,
    runner_path: Path, seq_len: int, timeout_seconds: int,
) -> dict[str, Any]:
    if not runner_path.is_file():
        raise RuntimeError(
            f"ExecuTorch llama_main was not found at {runner_path}. "
            "Build it with 'bash llm_advisory/build_pi5_runner.sh' on a Linux x86_64 host "
            "and copy models/llama/runtime to the Pi."
        )
    if not os.access(runner_path, os.X_OK):
        raise RuntimeError(f"ExecuTorch runner is not executable: {runner_path}")

    prompt = build_prompt(event)
    command = [
        str(runner_path),
        f"--model_path={model_path}",
        f"--tokenizer_path={tokenizer_path}",
        "--temperature=0",
        f"--seq_len={seq_len}",
        f"--prompt={prompt}",
    ]
    env = os.environ.copy()
    lib_path = str(runner_path.parent)
    env["LD_LIBRARY_PATH"] = lib_path + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=False,
            timeout=timeout_seconds, env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ExecuTorch Llama exceeded the {timeout_seconds}s timeout. "
            "Check model/runtime compatibility, available RAM and cooling."
        ) from exc
    total_ms = (time.perf_counter() - started) * 1000.0
    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "No diagnostic output")[-3000:]
        raise RuntimeError(f"ExecuTorch llama_main exited {completed.returncode}: {detail}")
    advisory = validate_advisory(parse_advisory_json(combined))
    generation_stats = parse_pytorch_observer(combined)
    ttft_ms = observer_ttft_ms(generation_stats)
    tokens_per_second = observer_tokens_per_second(generation_stats)
    return {
        "advisory": advisory,
        "advisory_text": json.dumps(advisory, ensure_ascii=False),
        "runner_backend": "executorch_cpp_llama_main",
        "ttft_ms": ttft_ms,
        "total_response_ms": round(total_ms, 2),
        "tokens_per_second": tokens_per_second,
        "generation_stats": generation_stats,
        "process_peak_rss_kb": linux_peak_child_rss_kib(),
        "telemetry_note": (
            "TTFT and tokens/second are parsed from ExecuTorch PyTorchObserver output "
            "when available; otherwise they remain null rather than being estimated."
        ),
    }


def run_python(
    event: dict[str, Any], model_path: Path, tokenizer_path: Path,
    max_new_tokens: int, temperature: float,
) -> dict[str, Any]:
    """Optional ExecuTorch Python binding backend for hosts with built pybindings."""
    try:
        from executorch.extension.llm.custom_ops import custom_ops  # noqa: F401
        from executorch.kernels import quantized  # noqa: F401
        from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner
    except ImportError as exc:
        raise RuntimeError(
            "ExecuTorch TextLLMRunner Python bindings are unavailable. "
            "Use the default C++ llama_main backend on Raspberry Pi 5, or build "
            "ExecuTorch with EXECUTORCH_BUILD_PYBIND=ON."
        ) from exc

    prompt = build_prompt(event)
    runner = TextLLMRunner(str(model_path), str(tokenizer_path))
    config = GenerationConfig(
        max_new_tokens=max_new_tokens, temperature=temperature, echo=False
    )
    chunks: list[str] = []
    stats: dict[str, Any] = {}
    started = time.perf_counter()
    ttft: float | None = None

    def token_callback(token: str) -> None:
        nonlocal ttft
        if ttft is None:
            ttft = (time.perf_counter() - started) * 1000.0
        chunks.append(str(token))

    def stats_callback(value: Any) -> None:
        for name in ("num_prompt_tokens", "num_generated_tokens",
                     "inference_start_ms", "inference_end_ms"):
            metric = getattr(value, name, None)
            if metric is not None:
                stats[name] = metric

    try:
        runner.generate(prompt, config, token_callback, stats_callback)
    finally:
        try:
            runner.reset()
        except Exception:
            pass

    total_ms = (time.perf_counter() - started) * 1000.0
    raw_text = "".join(chunks).strip()
    advisory = validate_advisory(parse_advisory_json(raw_text))
    generated = stats.get("num_generated_tokens")
    start_ms, end_ms = stats.get("inference_start_ms"), stats.get("inference_end_ms")
    tokens_per_second = None
    if generated is not None and start_ms is not None and end_ms is not None and end_ms > start_ms:
        tokens_per_second = round(float(generated) * 1000.0 / (end_ms - start_ms), 2)
    return {
        "advisory": advisory,
        "advisory_text": raw_text,
        "runner_backend": "executorch_python_text_llm_runner",
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "total_response_ms": round(total_ms, 2),
        "tokens_per_second": tokens_per_second,
        "process_peak_rss_kb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "generation_stats": stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="Structured inspection event JSON")
    parser.add_argument("--model", default=os.getenv("PCB_LLAMA_MODEL_PATH", DEFAULT_MODEL))
    parser.add_argument("--tokenizer", default=os.getenv("PCB_LLAMA_TOKENIZER_PATH", DEFAULT_TOKENIZER))
    parser.add_argument("--runner", default=os.getenv("PCB_LLAMA_RUNNER_PATH", DEFAULT_RUNNER))
    parser.add_argument("--backend", choices=("cli", "python"), default=os.getenv("PCB_LLAMA_BACKEND", "cli"))
    parser.add_argument("--seq-len", type=int, default=int(os.getenv("PCB_LLAMA_SEQ_LEN", "1024")))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("PCB_LLAMA_TIMEOUT_SECONDS", "180")))
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--output", help="Optional advisory result JSON path")
    args = parser.parse_args()

    try:
        event_path = resolve_path(args.event)
        model_path, tokenizer_path = resolve_path(args.model), resolve_path(args.tokenizer)
        if not model_path.is_file():
            raise RuntimeError(
                f"Llama .pte model not found: {model_path}. Run "
                "'python llm_advisory/download_model.py' after accepting the upstream license."
            )
        if not tokenizer_path.is_file():
            raise RuntimeError(f"Matching Llama tokenizer not found: {tokenizer_path}")
        if args.seq_len < 128 or args.timeout_seconds < 1:
            raise RuntimeError("--seq-len must be >=128 and --timeout-seconds must be positive")
        event = load_event(event_path)
        if args.backend == "cli":
            result = run_cli(
                event, model_path, tokenizer_path, resolve_path(args.runner),
                args.seq_len, args.timeout_seconds,
            )
        else:
            result = run_python(
                event, model_path, tokenizer_path, args.max_new_tokens, args.temperature
            )
        result.update({
            "record_id": event["record_id"],
            "board_id": event["board_id"],
            "runtime": "ExecuTorch",
            "model_file": model_path.name,
            "tokenizer_file": tokenizer_path.name,
            "model_path": str(model_path),
        })
        if args.output:
            output_path = resolve_path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = output_path.with_suffix(output_path.suffix + ".tmp")
            temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            temporary.replace(output_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ExecuTorch advisory failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
