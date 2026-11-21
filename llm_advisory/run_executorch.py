#!/usr/bin/env python3
"""Run a text-only Llama advisory from a structured PCB inspection event.

The ExecuTorch model receives no image or camera data. Detector findings are
kept unchanged and the generated text is stored separately under "advisory".
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
        from executorch.extension.llm.runner import (
            GenerationConfig,
            MultimodalRunner,
            make_text_input,
        )
    except ImportError as exc:
        raise RuntimeError(
            "ExecuTorch LLM Python bindings are not available. "
            "Build/install ExecuTorch with its LLM runner Python bindings on the target."
        ) from exc

    # Only structured inspection fields are serialized into the prompt.
    # No image, image path, image tensor, or camera frame is passed to ExecuTorch.
    prompt = build_prompt(event)
    runner = MultimodalRunner(str(model_path), str(tokenizer_path))
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
        ):
            metric = getattr(value, name, None)
            if metric is not None:
                stats[name] = metric

    runner.generate([make_text_input(prompt)], config, token_callback, stats_callback)
    total_ms = (time.perf_counter() - started) * 1000.0
    advisory_text = "".join(chunks).strip()
    if not advisory_text:
        raise RuntimeError("ExecuTorch returned an empty advisory")

    result: dict[str, Any] = {
        "record_id": event["record_id"],
        "board_id": event["board_id"],
        "advisory_text": advisory_text,
        "runtime": "ExecuTorch",
        "model_file": model_path.name,
        "ttft_ms": round(first_token_ms, 2) if first_token_ms is not None else None,
        "total_response_ms": round(total_ms, 2),
        "generation_stats": stats,
    }
    try:
        result["advisory"] = json.loads(advisory_text)
    except json.JSONDecodeError:
        result["advisory"] = None

    try:
        result["process_peak_rss_kb"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError):
        result["process_peak_rss_kb"] = None

    generated = stats.get("num_generated_tokens")
    start_ms = stats.get("inference_start_ms")
    end_ms = stats.get("inference_end_ms")
    if generated and start_ms is not None and end_ms is not None and end_ms > start_ms:
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
        event = load_event(Path(args.event))
        result = run_advisory(
            event,
            Path(args.model),
            Path(args.tokenizer),
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ExecuTorch advisory failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
