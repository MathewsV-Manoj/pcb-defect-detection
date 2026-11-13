# Project status snapshot

## Planned architecture
Camera/image → OpenCV preprocessing → YOLOv8 Nano → structured detection record → optional Llama advisory via ExecuTorch → Firebase Realtime Database → single-page HTML dashboard.

## Present in repository
- Static Firebase-connected dashboard source.
- One-shot image/USB-camera/Picamera2 inference application for a compatible three-class ONNX model.
- Device-side Firebase REST publisher.
- Event schema, dataset provenance template, training checklist and Raspberry Pi 5 handoff documentation.
- Llama advisory prompt boundary; no model runtime or weights.

## Not present / not verified
- Trained `best.pt`, Pi `best.onnx`, or TFLite model file.
- Exact final training archive, processed dataset and annotation files.
- Verified evaluation report and exported-vs-PyTorch parity results.
- Continuous camera trigger/conveyor integration and GPIO motor-control mapping.
- Trained/fine-tuned GPT/Llama model and ExecuTorch binary.
- Raspberry Pi 5 timing/RAM/temperature results.

Do not mark these pending items complete until the artifacts and tests exist.
