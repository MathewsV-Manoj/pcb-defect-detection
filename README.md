# PCB Defect Inspection — Raspberry Pi 5

YOLOv8-based PCB defect inspection prototype for the Bharat SoC AI Challenge. The repository is organized around the agreed Raspberry Pi 5 edge pipeline, with a static Firebase-connected HTML dashboard.

> **Current integration status:** the mechanical/conveyor hardware has been assembled but is not yet operating reliably. The live camera, trigger, motor-control wiring, trained model artifacts, and dataset archive have not been verified in this repository. The included software interfaces and test mode must not be presented as a completed hardware demonstration.

## Target system

```text
Camera / submitted PCB image
          |
    OpenCV acquisition
          |
  YOLOv8 Nano (3 classes)
          |
Structured inspection JSON
      |           |
      |       Llama advisory
      |       (optional; text only)
      |       ExecuTorch runtime pending
      v
Firebase Realtime Database
          |
   Single HTML dashboard
```

Firebase is the data transport/store; it does not run YOLO or Llama. The Raspberry Pi 5 runs the detector and publishes results directly to Firebase. No separate Flask/Node web backend is required.

## Intended detector class order

The Raspberry Pi handoff notes specify this exact mapping:

| Class ID | Name |
|---:|---|
| 0 | `missing_hole` |
| 1 | `open_circuit` |
| 2 | `short_circuit` |

Input is 640 × 640 RGB. The Pi 5 handoff notes describe a YOLO ONNX output similar to `[1, 7, 8400]`. The inference adapter validates the output shape and applies confidence filtering and NMS. Confirm the actual exported model input/output before using it.

**Do not use the older six-class `runs/pcb/` checkpoint or its ONNX export.** The three-class training run was documented under `runs/pcb3/`. Do not assume class order from a filename; verify the checkpoint and its training `data.yaml`.

## Repository layout

- `raspberry_pi/`: ONNX Runtime CPU inference, image/camera capture entry point, Firebase publisher and setup instructions for 64-bit Raspberry Pi OS.
- `dashboard/`: static Firebase Realtime Database dashboard. No camera preview; camera state is a status field only.
- `models/`: expected locations and release checklist for `best.pt`, `best.onnx`, and optional `detector.tflite`.
- `datasets/`: dataset source/attribution manifest and instructions. Dataset contents are not included because the exact training archive and redistribution rights have not been verified.
- `training/`: reproducibility checklist and three-class training/evaluation commands.
- `llm_advisory/`: strict boundary for an optional Llama advisory component; it consumes YOLO JSON and never detects defects or changes the detector decision.
- `schemas/`: event format and an illustrative event.
- `docs/`: supplied handoff and training/deployment notes.

## Raspberry Pi 5 setup

Use 64-bit Raspberry Pi OS. Start with CPU inference; no accelerator is assumed.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv
git clone https://github.com/MathewsV-Manoj/pcb-defect-detection.git
cd pcb-defect-detection
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt
```

Place the verified three-class `best.onnx` at `models/best.onnx`, then run:

```bash
python raspberry_pi/inspect_image.py --source /path/to/pcb.jpg --weights models/best.onnx
```

For a camera test, use `--camera 0` only after configuring and checking the physical camera. The script records image inference output; it does not operate the conveyor or GPIO motor driver.

## Firebase

Configure `raspberry_pi/.env` locally (never commit it) or export environment variables:

- `FIREBASE_DATABASE_URL`
- `FIREBASE_AUTH_TOKEN` (only when required by the database rules)

The Pi writes completed records to `/inspections/{record_id}` and the latest state to `/live`. Add the Firebase Web App configuration to the dashboard file locally. Use Authentication and restrictive Realtime Database rules. Never use public read/write rules and never put service-account private keys in browser JavaScript.

## Model artifacts and datasets

The currently accessible project files contain documentation about the three-class model and Raspberry Pi deployment, but no actual `best.pt`, `best.onnx`, `detector.tflite`, training run, or dataset archive. Placeholder directories and manifests are provided; they are **not trained model files**.

Before publishing binary artifacts:
1. Verify the model comes from the three-class `runs/pcb3/` run and exact class order above.
2. Validate it on the held-out test split and inspect per-class precision, recall, mAP@50, mAP@50–95, confusion matrix and sample predictions.
3. Compare original PyTorch and exported ONNX/TFLite predictions.
4. Add large model files with Git LFS or attach them to a GitHub Release; do not commit a fake or old six-class checkpoint.
5. Add datasets only if redistribution is permitted by their licenses/terms. The documented candidate sources include DeepPCB and Tiny-Defect-Detection-for-PCB; the exact dataset used for the final training run still needs to be matched to its `data.yaml`/training log.

See `models/README.md`, `datasets/README.md`, and `docs/POST_TRAINING_HANDOFF.md`.

## Integrity rules

- No invented accuracy, latency, FPS, RAM, board counts, or physical camera/conveyor status.
- A detection confidence score is not overall model accuracy.
- An empty detection list means “no configured target detected”, not proof that a PCB is defect-free.
- A Llama response is advisory text only. It must not create, relabel, or suppress YOLO detections.
- Keep every demo/simulated record marked `SIMULATION`.
- Do not mark the system production-ready until the actual camera, model, conveyor, Firebase path and Pi performance have been tested.
