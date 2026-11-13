# PCB Engine Development Kit (from supplied ZIP)

This directory preserves the source code from the supplied `PCB_ENGINE_KIT.zip` (text/source files). The original ZIP was verified: all 21 internal file checksums matched.

## What's in this kit
- Dataset import and local OpenCV annotation.
- YOLO training, validation and INT8 TFLite export entry point.
- Raspberry Pi folder-worker engine, reference-board comparison and Pi evaluation.
- Atomic input submission helper and contract tests.
- Optional ResAttention U-Net trace extractor source.

## Important model distinction
The supplied ZIP includes a 32.9 MB PyTorch file, `optional_unet/pcb_ultra_resatt_unet.pth`. It is a five-channel U-Net trace-extraction checkpoint. It produces trace/binary images; it is **not** the three-class PCB defect detector. Its own documentation says it is for laptop diagnostics only. The checkpoint is provided separately for manual upload to this repository; see `optional_unet/CHECKPOINT_UPLOAD.md`.

The ZIP does **not** include trained three-class YOLO fault-detector weights or dataset images/labels.

## Class-order conflict
The training code in this folder uses:
```text
0 open_circuit
1 short_circuit
2 missing_hole
```
The separate Raspberry Pi 5 handoff document specifies:
```text
0 missing_hole
1 open_circuit
2 short_circuit
```
Do not mix weights, class names, exports or decoders until the exact final model's `data.yaml`/metadata confirms the correct order. See `CLASS_ORDER_CONFLICT.md`.

## Raspberry Pi note
The folder-worker kit uses TFLite Runtime and its deployment guide describes Raspberry Pi 4. A separate Pi 5 handoff specifies ONNX Runtime. These are retained as separate implementation paths. Neither should be represented as validated on Raspberry Pi 5 until tested there.

## Verification
The original ZIP's checksum manifest is retained as `ORIGINAL_ZIP_SHA256SUMS.json`. It records the hashes of the original ZIP entries, not the normalized GitHub text copies. The two dependency-free tests pass: atomic image publication and ZIP traversal rejection.
