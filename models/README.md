# Model artifacts

## Vision model

The edge inference interface is YOLOv8 Nano with this canonical class-ID contract:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The Raspberry Pi ONNX application expects `models/best.onnx`. The detector binary and its training provenance are separate release artifacts. No trained three-class detector binary is bundled in this source checkout.

## Advisory model

The committee architecture specifies Llama 3.2 Instruct 1B or 3B through ExecuTorch on the Raspberry Pi ARM CPU. The prompt builder is in `llm_advisory/prompt.py`; the ExecuTorch runtime package and quantized model binary are separate deployment assets and are not bundled here.

## Release identity

`release_manifest.json` records artifact presence, hashes, validation state and dataset provenance. The repository does not publish unverified accuracy or target-device benchmark values.
