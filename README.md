# PCB Inspection Station

Software for a conveyor-fed PCB inspection prototype built around a Raspberry Pi 5. The target defects are open circuits, short circuits and missing holes.

The operator does not run the model from the laptop. The Pi captures the board image, processes it locally and serves the result back to a browser on the same network.

## How an inspection is meant to run

1. At the start of a station session, hold a hand in front of the IR sensor for about three seconds, then release it. The station stays armed until the controller is restarted.
2. Put the PCB on the conveyor. When the board reaches the IR trigger point beside the camera, the sensor signals the Pi.
3. The Pi switches on the external LED driver, waits for the configured settling time and saves a camera frame.
4. Open the Pi's address in a laptop browser and check the captured image.
5. Select **Run inspection on Raspberry Pi**. The browser sends `POST /api/run-inspection`; it does not load the model or perform inference.
6. The Pi runs OpenCV preprocessing and the three-class YOLO detector. It writes an annotated image and an inspection-event JSON file.
7. The separate ExecuTorch process receives the detection record as text and prepares an operator note. It is not given the image and cannot change the detector's result.
8. The page displays the decision, boxes, confidence values, advisory and recent local records. Firebase can be enabled to copy completed records to a Realtime Database.

The IR sensor only reports presence at its trigger point. It does not measure the board's exact position in the camera image; that depends on the mechanical placement of the conveyor, sensor and camera.

## Vision model

The Pi application uses YOLOv8 Nano through ONNX Runtime on the Pi's CPU. The input is a 640 × 640, three-channel tensor:

- resize and pad while keeping the image aspect ratio;
- convert OpenCV BGR to RGB;
- convert to float32 and scale values to [0, 1];
- arrange the tensor as NCHW: `[1, 3, 640, 640]`.

The class IDs must remain in this order throughout annotation, training and deployment:

| ID | Class |
|---:|---|
| 0 | `missing_hole` |
| 1 | `open_circuit` |
| 2 | `short_circuit` |

A frame with no detections is reported as `NO_TARGET_DEFECT_DETECTED`. That means the configured detector did not find one of these three classes in that image. It is not a guarantee that the whole board is defect-free.

The current detector leaves severity as `UNASSESSED`. A board-specific severity rule has not been supplied, so the software does not guess severity from confidence.

## Raspberry Pi service and dashboard

The station controller serves `dashboard/index.html` and the API from the Pi.

| Route | Purpose |
|---|---|
| `GET /` | Operator page |
| `GET /api/health` | Service health |
| `GET /api/status` | Sensor, capture and inspection state |
| `GET /api/capture.jpg` | Original captured frame |
| `GET /api/annotated.jpg` | Annotated frame after inference |
| `GET /api/history` | Recent local inspection records |
| `POST /api/run-inspection` | Start processing on the Pi |

The service is intended for a trusted private network. Do not expose port 8080 directly to the internet.

## Run on a Raspberry Pi

Use 64-bit Raspberry Pi OS. From the repository root:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero

# Only needed for a CSI camera:
sudo apt install -y python3-picamera2

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt

cp raspberry_pi/.env.example raspberry_pi/.env
nano raspberry_pi/.env
```

Set the actual BCM GPIO numbers, sensor/driver polarity, camera mode and model paths. The controller reads environment variables; it does not load the `.env` file itself. Export the settings and start the service from the same terminal:

```bash
set -a
source raspberry_pi/.env
set +a

python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

Open `http://<RASPBERRY_PI_IP>:8080/` from a laptop on the same network. Run `hostname -I` on the Pi to see its address.

The LED strip must have its own suitable power supply and driver. Only the driver control input should connect to a Pi GPIO. Confirm that the IR sensor output is safe for the Pi's 3.3 V GPIO before wiring it.

The service expects the vision model at `models/best.onnx`. The complete inspection path also needs an ExecuTorch `.pte` model and its matching tokenizer. See [the Pi deployment notes](docs/PI5_DEPLOYMENT.md) before installing those files.

## Prepare and export a detector

The training utilities are in `pcb_engine_kit/`. Install their dependencies in a separate training environment:

```bash
cd pcb_engine_kit
python -m pip install -r requirements-train.txt
```

`datasets/SOURCE_MANIFEST.csv` records dataset sources and their reuse terms. It is not the image import list. To prepare images, copy `datasets/import_manifest.example.csv` to `datasets/import_manifest.csv`, replace the example paths with your actual image and label files, then run:

```bash
python dataset.py ../datasets/import_manifest.csv ../datasets/processed/pcb3
python train_export.py train --data ../datasets/processed/pcb3/data.yaml --weights yolov8n.pt --size 640 --epochs 100 --batch 4 --device 0
python train_export.py validate --data ../datasets/processed/pcb3/data.yaml --weights runs/pcb/weights/best.pt --size 640 --device 0
python train_export.py export-onnx --weights runs/pcb/weights/best.pt --size 640 --out deployment
```

Copy the exported `deployment/best.onnx` to `models/best.onnx` on the Pi. Keep `best.onnx.json` with it; the file records the class order, preprocessing contract and SHA-256 hash. Export metadata is not evidence that the model has been tested on the Pi.

The separate TFLite folder-worker can be exported with `export-tflite`. It is not used by the main station controller.

## Repository map

| Folder | What is in it |
|---|---|
| `raspberry_pi/` | Sensor controller, camera capture, ONNX inference, inspection coordinator and Firebase client |
| `dashboard/` | Operator website served by the Pi |
| `llm_advisory/` | Text prompt and ExecuTorch runner |
| `pcb_engine_kit/` | Dataset importer, annotator, training/export tools and TFLite folder-worker |
| `datasets/` | Dataset source list and import-manifest example |
| `models/` | Class map and release manifest |
| `schemas/` | Inspection-event schema and example |
| `firebase/` | Example Realtime Database rules |
| `tests/` | Python contract tests |
| `docs/` | Project report, flowchart, setup and evaluation notes |
| `demo_video/` | Suggested shots for recording the physical demonstration |

## Current release state

The source code and automated tests are in the repository. The final three-class YOLO checkpoint/ONNX file, ExecuTorch model and tokenizer, complete processed dataset and recorded Pi performance results are not included. The conveyor and station parts have been assembled, but the full capture-to-result cycle still needs to be checked reliably on the actual Pi with the final model files installed.

No detection score, speed figure or end-to-end success rate is claimed here without the corresponding model, test split and device measurements.

Project files: [Flowchart](docs/inspection_workflow.svg) · [Project report](docs/PROJECT_REPORT.md) · [Pi setup](docs/PI5_DEPLOYMENT.md) · [Pi commissioning checklist](docs/PI5_COMMISSIONING.md) · [Llama setup](llm_advisory/README.md) · [Pi benchmark](raspberry_pi/benchmark_onnx.py) · [Demo video shot list](demo_video/README.md).
