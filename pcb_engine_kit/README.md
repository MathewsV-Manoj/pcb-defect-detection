# PCB Engine Development Kit (from supplied ZIP)

This directory preserves the source code from the supplied `PCB_ENGINE_KIT.zip` (text/source files). The original ZIP's SHA-256 manifest was checked; all 21 entries matched.

## What's in this kit
- Dataset import and local OpenCV annotation.
- YOLO training, validation and INT8 TFLite export entry point.
- Raspberry Pi folder-worker engine, reference-board comparison and Pi evaluation.
- Atomic input submission helper and contract tests.
- Optional ResAttention U-Net trace extractor source.

## Important model distinction
The included `optional_unet/pcb_ultra_resatt_unet.pth` in the source ZIP is a five-channel U-Net trace-extraction checkpoint. It produces a trace/binary image; it is **not** the three-class PCB defect detector. The ZIP's own documentation says it is for laptop diagnostics and should not be treated as fault labels or deployed on the Pi without profiling.

The ZIP does **not** include a trained three-class YOLO fault detector or the dataset images/labels.

## Class-order conflict that must be resolved
The training code in this folder uses:
```text
0 open_circuit
1 short_circuit
2 missing_hole
```
The separate Raspberry Pi 5 hardware handoff document supplied with the project specifies:
```text
0 missing_hole
1 open_circuit
2 short_circuit
```
These are incompatible. Do not mix weights, class names, ONNX/TFLite exports or decoders until the exact final model's `data.yaml`/metadata confirms the correct order. See `CLASS_ORDER_CONFLICT.md`.

## Raspberry Pi note
The folder-worker kit's deployment guide was written for Raspberry Pi 4 / TFLite Runtime. A separate Pi 5 handoff specifies ONNX Runtime. Neither should be represented as validated on Raspberry Pi 5 until tested there. The current root `raspberry_pi/` path is the ONNX one-shot integration scaffold.

## Test status
The two dependency-free tests from the ZIP pass: atomic image publication and ZIP traversal rejection. Model training, TFLite export/inference, reference alignment and target-device benchmarks were not executed.
