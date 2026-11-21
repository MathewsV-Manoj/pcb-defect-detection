# Model artifacts

## Vision model

The edge inference interface is YOLOv8 Nano with this canonical class-ID contract:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The Raspberry Pi ONNX application expects `models/best.onnx`. Export it from the trained three-class checkpoint using `pcb_engine_kit/train_export.py export-onnx`; the script writes `best.onnx` and `best.onnx.json` with the model hash and input contract. The detector binary and its training provenance are separate release artifacts. No trained three-class detector binary is bundled in this source checkout.

## Advisory model

The committee architecture specifies Llama 3.2 Instruct 1B or 3B through ExecuTorch on the Raspberry Pi ARM CPU. The prompt builder is in `llm_advisory/prompt.py`; the text-only runtime uses ExecuTorch `TextLLMRunner`. The ExecuTorch Python binding build, `.pte` model and matching tokenizer are separate deployment assets and are not bundled here. The Python runner API is experimental and must be validated with the exact model/runtime build on the Pi.

## Release identity

`release_manifest.json` records artifact presence, hashes, validation state and dataset provenance. The repository does not publish unverified accuracy or target-device benchmark values.
