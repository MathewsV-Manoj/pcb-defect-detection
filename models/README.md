# Vision and advisory model assets

The Raspberry Pi station expects the three-class YOLOv8 Nano detector at `models/best.onnx`. The deployment class order is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

Export the ONNX model from the verified three-class checkpoint using `pcb_engine_kit/train_export.py export-onnx`. Keep `best.onnx.json` with the model; it records the class order, input contract and ONNX SHA-256. Check model/checkpoint parity on held-out images and then on the target Pi.

The ExecuTorch advisory model and matching tokenizer are required for the challenge but are not included in this source checkout. Configure their paths through `PCB_LLAMA_MODEL_PATH` and `PCB_LLAMA_TOKENIZER_PATH`. See `llm_advisory/README.md`.

`release_manifest.json` records which artifacts are actually present and which validations have been completed. A source file or successful export command is not a substitute for a tested model binary.
