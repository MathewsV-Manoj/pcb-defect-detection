# PCB Defect Inspection — Bharat SoC AI Challenge

This repository collects the PCB inspection software, Raspberry Pi integration paths, Firebase dashboard, training/deployment kit and handoff documentation.

## Current state
The conveyor/mechanical assembly has been developed but is not currently in reliable working condition. The repository contains code and integration scaffolding, not a proven end-to-end hardware system. Do not present simulation results as physical inspection results.

## Architecture target
```text
Camera / PCB image
  -> OpenCV image pipeline
  -> YOLOv8 Nano (open / short / missing-hole detection)
  -> structured detection JSON
  -> optional Llama advisory (text only; ExecuTorch under evaluation)
  -> Firebase Realtime Database
  -> single-page HTML dashboard
```
Firebase stores/transports results; it does not run YOLO or Llama. The edge device runs the detector and publishes results directly. No Flask/Node backend is required.

## Repository directories
- `raspberry_pi/`: ONNX Runtime one-shot image/USB-camera/Picamera2 inference scaffold for the Pi 5 handoff.
- `pcb_engine_kit/`: source code from the supplied `PCB_ENGINE_KIT.zip`: TFLite folder worker, dataset importer, labeler, training/export scripts, reference comparison and optional U-Net trace extractor.
- `dashboard/`: static Firebase-connected operator dashboard.
- `models/`: model release manifest and class mapping notes.
- `datasets/`: dataset provenance and source manifest; raw dataset is not included.
- `training/`, `llm_advisory/`, `schemas/`, `firebase/`, `docs/`: training/evaluation, advisory boundary, event schema, security rules and project handoffs.

## Model assets — read carefully
The supplied ZIP does contain a 32.9 MB file named `pcb_ultra_resatt_unet.pth`. It is a five-channel ResAttention U-Net used to extract PCB traces. It is not the three-class open/short/missing-hole object detector. Its original code and checksum are documented in `pcb_engine_kit/optional_unet/`. The binary itself still needs a manual upload to the GitHub folder; see `CHECKPOINT_UPLOAD.md`.

The ZIP does **not** contain a trained three-class YOLO checkpoint (`best.pt`), ONNX/TFLite fault detector, or dataset archive with images and labels. It provides code to create a dataset and train/export a detector.

## Conflicting class order — unresolved
The ZIP's training/export code uses `0 open_circuit, 1 short_circuit, 2 missing_hole`. The separate Raspberry Pi 5 handoff specifies `0 missing_hole, 1 open_circuit, 2 short_circuit`. Check the actual final checkpoint and `data.yaml` before using either decoder. See `pcb_engine_kit/CLASS_ORDER_CONFLICT.md`.

## Hardware/runtime difference
The supplied kit's folder worker uses TFLite Runtime and its guide describes Raspberry Pi 4. The separate Pi 5 handoff specifies ONNX Runtime. Both code paths are kept separate; neither is declared validated on Pi 5. Test the exact model, runtime, camera, temperature, RAM and inference rate on the target board.

## Integrity
- Do not invent precision, recall, mAP, latency, FPS, RAM or hardware status.
- Detection confidence is not model accuracy.
- A Llama advisory cannot create, remove or relabel YOLO detections.
- An empty detection list means only “no configured target detected.”
- Only publish datasets if their current license/terms permit redistribution.
