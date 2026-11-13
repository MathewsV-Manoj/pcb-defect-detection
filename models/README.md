# Model artifacts and identity

## Included in supplied ZIP
A 32.9 MB checkpoint exists in the ZIP: `pcb_engine_kit/optional_unet/pcb_ultra_resatt_unet.pth`. It is a five-channel ResAttention U-Net trace extractor, used for laptop diagnostics. It is **not** the three-class YOLO object detector. Its SHA-256 and manual GitHub upload instructions are in `pcb_engine_kit/optional_unet/CHECKPOINT_UPLOAD.md`.

## Fault detector assets still missing
No actual three-class `best.pt`, `best.onnx`, or `detector.tflite` fault-detector binary was present in the supplied ZIP. The ZIP contains code for dataset preparation and YOLOv8 training/export, not a trained detection checkpoint.

## Class mapping needs verification
The ZIP training code uses `open_circuit, short_circuit, missing_hole` order. The Pi 5 hardware handoff document uses `missing_hole, open_circuit, short_circuit`. Do not use the class map until the exact final checkpoint and `data.yaml` resolve this. See `pcb_engine_kit/CLASS_ORDER_CONFLICT.md`.

Use Git LFS or release assets for large files where appropriate. Add hashes and evaluation provenance. Never commit secrets.
