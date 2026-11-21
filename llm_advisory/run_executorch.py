#!/usr/bin/env python3
"""Run a text-only Llama advisory from a structured PCB inspection event.

The ExecuTorch TextLLMRunner receives no image or camera data. Detector
findings remain unchanged; generated text is stored separately as advisory data.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

from prompt import build_prompt


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
        raise RuntimeError(f"Inspection event is missing required fields: {', '.join(missing)}")
    if not isinstance(event["detections"], list):
        raise RuntimeError("Inspection event detections must be a list")
    return event


def parse_advisory_json(text: str) -> dict[str, Any] | None:
    """Parse JSON even when the model wraps it in a Markdown code fence."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3].strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def validate_advisory(value: dict[str, Any] | None) -> dict[str, Any]:
    """Require the bounded, machine-readable response expected by the operator UI."""
    required = {"explanation", "recommended_actions", "severity_note", "log_entry"}
    if value is None or set(value) != required:
        raise RuntimeError(
            "Llama response is not the required JSON object with keys: "
            "explanation, recommended_actions, severity_note, log_entry"
        )
    if not isinstance(value["explanation"], str) or not value["explanation"].strip():
        raise RuntimeError("Llama advisory 'explanation' must be a non-empty string")
    if (
        not isinstance(value["recommended_actions"], list)
        or not all(isinstance(item, str) and item.strip() for item in value["recommended_actions"])
    ):
        raise RuntimeError("Llama advisory 'recommended_actions' must be an array of non-empty strings")
    if not isinstance(value["severity_note"], str) or not value["severity_note"].strip():
        raise RuntimeError("Llama advisory 'severity_note' must be a non-empty string")
    if not isinstance(value["log_entry"], str) or not value["log_entry"].strip():
        raise RuntimeError("Llama advisory 'log_entry' must be a non-empty string")
    return value


def run_advisory(
    event: dict[str, Any],
    model_path: Path,
    tokenizer_path: Path,
    max_new_tokens: int = 192,
    temperature: float = 0.1,
) -> dict[str, Any]:
    if not model_path.is_file():
        raise RuntimeError(f"ExecuTorch model file not found: {model_path}")
    if not tokenizer_path.is_file():
        raise RuntimeError(f"Tokenizer file not found: {tokenizer_path}")
    if max_new_tokens < 1:
        raise ValueError("max_new_tokens must be positive")
    if not 0.0 <= temperature <= 1.0:
        raise ValueError("temperature must be between 0 and 1")

    try:
        # These imports register the LLM custom kernels required by many exported PTEs.
        from executorch.extension.llm.custom_ops import custom_ops  # noqa: F401
        from executorch.kernels import quantized  # noqa: F401
        from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner
    except ImportError as exc:
        raise RuntimeError(
            "ExecuTorch TextLLMRunner Python bindings or required LLM kernels are unavailable. "
            "Build/install ExecuTorch with EXECUTORCH_BUILD_PYBIND=ON and register the "
            "custom_ops and quantized kernels for the exported model."
        ) from exc

    # Only structured inspection fields are passed to the text-only model.
    # No image, image path, image tensor, or camera frame is passed to ExecuTorch.
    prompt = build_prompt(event)
    runner = TextLLMRunner(str(model_path), str(tokenizer_path))
    config = GenerationConfig(
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        echo=False,
    )

    chunks: list[str] = []
    stats: dict[str, Any] = {}
    started = time.perf_counter()
    first_token_ms: float | None = None

    def token_callback(token: str) -> None:
        nonlocal first_token_ms
        if first_token_ms is None:
            first_token_ms = (time.perf_counter() - started) * 1000.0
        chunks.append(str(token))

    def stats_callback(value: Any) -> None:
        for name in (
            "num_prompt_tokens",
            "num_generated_tokens",
            "inference_start_ms",
            "inference_end_ms",
            "model_load_start_ms",
            "model_load_end_ms",
            "first_token_ms",
        ):
            metric = getattr(value, name, None)
            if metric is not None:
                stats[name] = metric

    try:
        # TextLLMRunner.generate(prompt, config, token_callback, stats_callback)
        # is the ExecuTorch API for text-only Llama-family models.
        runner.generate(prompt, config, token_callback, stats_callback)
    finally:
        # Clear KV-cache state before the runner is released.
        try:
            runner.reset()
        except Exception:
            pass

    total_ms = (time.perf_counter() - started) * 1000.0
    advisory_text = "".join(chunks).strip()
    if not advisory_text:
        raise RuntimeError("ExecuTorch returned an empty advisory")

    parsed_advisory = validate_advisory(parse_advisory_json(advisory_text))
    result: dict[str, Any] = {
        "record_id": event["record_id"],
        "board_id": event["board_id"],
        "advisory_text": advisory_text,
        "runtime": "ExecuTorch",
        "runner": "TextLLMRunner",
        "model_file": model_path.name,
        "ttft_ms": round(first_token_ms, 2) if first_token_ms is not None else None,
        "total_response_ms": round(total_ms, 2),
        "generation_stats": stats,
        "advisory": parsed_advisory,
    }

    try:
        # On Linux (including Raspberry Pi OS), ru_maxrss is reported in KiB.
        result["process_peak_rss_kb"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError):
        result["process_peak_rss_kb"] = None

    generated = stats.get("num_generated_tokens")
    start_ms = stats.get("inference_start_ms")
    end_ms = stats.get("inference_end_ms")
    if generated is not None and start_ms is not None and end_ms is not None and end_ms > start_ms:
        result["tokens_per_second"] = round(float(generated) * 1000.0 / (end_ms - start_ms), 2)
    else:
        result["tokens_per_second"] = None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a text-only ExecuTorch PCB advisory")
    parser.add_argument("--event", required=True, help="Structured inspection event JSON")
    parser.add_argument("--model", required=True, help="ExecuTorch Llama .pte model")
    parser.add_argument("--tokenizer", required=True, help="Matching tokenizer binary")
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--output", help="Optional advisory result JSON path")
    args = parser.parse_args()

    try:
        event = load_event(Path(args.event).expanduser().resolve())
        result = run_advisory(
            event,
            Path(args.model).expanduser().resolve(),
            Path(args.tokenizer).expanduser().resolve(),
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
            temp_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            temp_path.replace(output_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ExecuTorch advisory failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
