# Model artifacts

## Vision model

The edge inference interface is YOLOv8 Nano with the following class-ID contract:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The Raspberry Pi ONNX application expects `models/best.onnx`. The model binary and its training provenance are separate release artifacts. No trained three-class detector binary is bundled in the current source checkout.

## Advisory model

The committee architecture specifies Llama 3.2 Instruct 1B or 3B through ExecuTorch on the Raspberry Pi ARM CPU. The model and quantized ExecuTorch package are not bundled in the source repository.

## Release identity

`release_manifest.json` records model artifact presence, hashes, validation state and dataset provenance. No unverified model metric or device benchmark is reported.
