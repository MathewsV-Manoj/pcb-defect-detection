# PCB Inspection Station

A conveyor-fed PCB inspection prototype built around a Raspberry Pi 5. It captures PCB images, detects three defined visual defect classes, records each inspection and presents the result in a browser on the local network.

## Implemented inspection sequence

1. At the start of a session, hold a hand in front of the IR sensor for about three seconds and release it. The station remains armed.
2. Place the PCB on the conveyor. When it reaches the IR trigger point beside the camera, the sensor signals the Raspberry Pi.
3. The Pi switches on the external LED driver, waits for the configured settling interval and captures a frame.
4. The Pi serves the captured image to the laptop browser. The operator checks the image.
5. The operator selects **Run inspection on Raspberry Pi**. The browser sends `POST /api/run-inspection`; it does not run inference.
6. The Pi applies OpenCV preprocessing and runs the three-class YOLOv8 Nano model through ONNX Runtime on the Pi CPU.
7. The Pi decodes detections, writes an annotated image and saves a structured inspection event.
8. The ExecuTorch text runner receives only the structured event and produces the operator advisory. It does not receive the image and cannot change detector results.
9. The dashboard displays the image, detections, advisory and local inspection history. The Pi can synchronize completed event records to Firebase Realtime Database when that connection is configured.

The IR sensor confirms presence at its trigger point. It does not measure the exact PCB position in the camera image; this is set by the mechanical placement of the conveyor, sensor and camera.

## Defect classes and model contract

The application uses this fixed class order:

| Class ID | Class name | Visual target |
|---:|---|---|
| 0 | `missing_hole` | An absent or visibly defective hole at an expected board location |
| 1 | `open_circuit` | A visible break or discontinuity in a conductive track |
| 2 | `short_circuit` | An unintended bridge between separate conductive paths |

The detector input is a 640 × 640 RGB tensor. Preprocessing preserves aspect ratio with letterboxing, converts BGR to RGB, scales float values to [0, 1] and arranges the tensor as NCHW `[1, 3, 640, 640]`. The ONNX output is decoded by the Pi application and class-wise non-maximum suppression is applied before boxes are mapped back to the original image.

A frame with no detections is reported as `NO_TARGET_DEFECT_DETECTED`. This means none of the three configured classes was detected in that frame; it is not proof that the entire PCB is defect-free.

Severity is currently recorded as `UNASSESSED`. No board-specific severity rule has been supplied or validated, so the software does not invent a severity score from detector confidence.

## Raspberry Pi service and dashboard

The station controller serves `dashboard/index.html` and the API from the Raspberry Pi.

| Route | Purpose |
|---|---|
| `GET /` | Operator page |
| `GET /api/health` | Service health |
| `GET /api/status` | Sensor, capture and inspection state |
| `GET /api/capture.jpg` | Original captured frame |
| `GET /api/annotated.jpg` | Annotated detector output |
| `GET /api/history` | Recent local inspection records |
| `POST /api/run-inspection` | Start inference on the Raspberry Pi |

The service is intended for a trusted private network. Do not expose port 8080 directly to the public internet.

## Run the station on Raspberry Pi 5

Use 64-bit Raspberry Pi OS. From the repository root:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero
# Install this only when using a CSI camera:
sudo apt install -y python3-picamera2

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt

cp raspberry_pi/.env.example raspberry_pi/.env
nano raspberry_pi/.env
```

Set the actual BCM GPIO pins, sensor/driver polarity, camera mode and model paths. The controller reads environment variables; it does not load the `.env` file itself. Export the settings and start the service from the same terminal:

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

Open `http://<RASPBERRY_PI_IP>:8080/` from a laptop on the same network. Run `hostname -I` on the Pi to see its address.

The LED strip must use its own suitable power supply and driver. Only the driver control input should connect to a Pi GPIO. Confirm that the IR sensor output is safe for the Pi's 3.3 V GPIO before wiring it.

## Prepare and export the YOLO detector

The dataset preparation and training tools are in `pcb_engine_kit/`. Install the training dependencies in a separate environment:

```bash
cd pcb_engine_kit
python -m pip install -r requirements-train.txt
```

The source list in `datasets/SOURCE_MANIFEST.csv` records dataset origins and reuse terms. It is not the image import list. Copy `datasets/import_manifest.example.csv` to `datasets/import_manifest.csv`, replace the example paths with the actual image and label files, and provide a board/capture group and split for every image:

```bash
python dataset.py ../datasets/import_manifest.csv ../datasets/processed/pcb3
python train_export.py train --data ../datasets/processed/pcb3/data.yaml --weights yolov8n.pt --size 640 --epochs 100 --batch 4 --device 0
```

The training command prints the exact checkpoint path for that run. Use that printed path for validation and export; do not assume that a folder named `runs/pcb` or `runs/pcb3` belongs to the latest run.

```bash
python train_export.py validate --data ../datasets/processed/pcb3/data.yaml --weights <EXACT_BEST_PT_PATH> --size 640 --device 0
python -m pip install -r requirements-export.txt
python train_export.py export-onnx --weights <EXACT_BEST_PT_PATH> --size 640 --out deployment
```

The training script checks that the dataset class order matches the deployment class order. The validation/export script also checks the checkpoint class names. Export creates `best.onnx` and `best.onnx.json`; the metadata records the class order, input contract and model hash. Copy both files to the Pi and place the ONNX file at `models/best.onnx`.

The exported file must still be checked against held-out images and on the target Pi. Successful conversion alone is not evidence of accuracy, prediction parity or target-device performance.

## Repository map

| Folder | Contents |
|---|---|
| `raspberry_pi/` | IR controller, camera capture, OpenCV/ONNX inference, inspection coordinator and Firebase publisher |
| `dashboard/` | Pi-hosted operator page |
| `llm_advisory/` | Structured prompt and ExecuTorch text runner |
| `pcb_engine_kit/` | Dataset importer, annotation tool and YOLO training/ONNX export |
| `datasets/` | PCB dataset source list and import-manifest template |
| `models/` | Class map and release manifest |
| `schemas/` | Inspection-event schema and example |
| `firebase/` | Example Realtime Database rules |
| `tests/` | Software contract tests |
| `docs/` | Project report, workflow diagram, deployment and submission readiness |
| `demo_video/` | Recorded demonstration file and content checklist |

## Release status

The source code, operator interface, dataset utilities, YOLO training/export source, structured event schema and software tests are present. The repository currently does **not** contain the final `best.pt`, `best.onnx`, ExecuTorch `.pte` model or matching tokenizer. The processed dataset, verified test metrics, completed Raspberry Pi commissioning record and measured Pi performance results are also absent. A demonstration MP4 is present in `demo_video/`; its contents must be checked against the live demonstration sequence before submission.

The Bharat AI-SoC Challenge requires a Llama-family model deployed with ExecuTorch. The source runner is present, but the model/tokenizer package is not, so the complete required advisory path is not yet release-ready. Severity is also not implemented beyond the honest `UNASSESSED` state.

No accuracy, latency, throughput, power or full-cycle reliability value is claimed without a corresponding test record. See [Submission readiness](docs/SUBMISSION_READINESS.md) for the Phase 1 checklist and [Project report](docs/PROJECT_REPORT.md) for the implementation description.

## Team

<img src="assets/team-photo.webp" alt="Project team" width="420" />

- **Mathews V Manoj** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Jordan Noby Eralil** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Deon Lukose Shince** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
