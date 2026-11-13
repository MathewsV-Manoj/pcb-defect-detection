# Model artifacts

Expected files from the documented latest three-class run:
- `best.pt`: original PyTorch checkpoint, for reference/re-evaluation.
- `best.onnx`: deployment model for initial Raspberry Pi 5 CPU inference.
- Optional `detector.tflite`: include only if actually exported and its graph, quantization, decoder and predictions are validated.

The Pi 5 handoff notes identify the three-class run as `runs/pcb3/` and class order as 0 `missing_hole`, 1 `open_circuit`, 2 `short_circuit`. They explicitly warn not to use the old six-class `runs/pcb/` checkpoint/ONNX. Verify the checkpoint's class map and `data.yaml`; filenames are not proof.

**No actual trained `best.pt`, `best.onnx`, or `detector.tflite` was available in the project files when this repository was populated.** This folder documents expected artifacts only. Never rename an unrelated checkpoint to the expected filename.

Use Git LFS or versioned GitHub Release assets for large model binaries. Add SHA-256 values and evaluation provenance to `release_manifest.json`. Do not commit Firebase credentials.
