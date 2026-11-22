# PCB Inspection Station

A conveyor-fed PCB inspection prototype built around a Raspberry Pi 5. It captures PCB images, detects three defined visual defect classes, records each inspection and presents the result in a browser on the local network.

## Implemented inspection sequence

1. At the start of a session, hold a hand in front of the IR sensor for about three seconds and release it. The station remains armed.
2. Place the PCB on the conveyor. When it reaches the IR trigger point beside the camera, the sensor signals the Raspberry Pi.
3. The Pi switches on the external LED driver, waits for the configured settling interval and captures a frame.
4. The Pi serves the captured image to the laptop browser. The operator checks the image.
5. The operator selects **Run inspection on Raspberry Pi**. The browser sends `POST /api/run-inspection`; it does not run inference.
6. The Pi applies OpenCV preprocessing and runs the selected YOLO ONNX checkpoint through ONNX Runtime on the Pi CPU. For the published six-class YOLOv8s baseline, the ONNX sidecar maps the three target defects into the application's fixed three-class event schema.
7. The Pi decodes detections, writes an annotated image and saves a structured inspection event.
8. The ExecuTorch text runner receives only the structured event and produces the operator advisory. It does not receive the image and cannot change detector results.
9. The dashboard displays the image, detections, advisory and local inspection history. The Pi can synchronize completed event records to Firebase Realtime Database when that connection is configured.

The IR sensor confirms presence at its trigger point. It does not measure the exact PCB position in the camera image; this is set by the mechanical placement of the conveyor, sensor and camera.
The Pi station controller does not start, stop or speed-control the conveyor motor. Conveyor motion is a separate subsystem; the controller reacts when a board reaches the IR trigger point.

## Defect classes and model contract

The application uses this fixed class order:

| Class ID | Class name | Visual target |
|---:|---|---|
| 0 | `missing_hole` | An absent or visibly defective hole at an expected board location |
| 1 | `open_circuit` | A visible break or discontinuity in a conductive track |
| 2 | `short_circuit` | An unintended bridge between separate conductive paths |

The detector input is a 640 × 640 RGB tensor. Preprocessing preserves aspect ratio with letterboxing, converts BGR to RGB, scales float values to [0, 1] and arranges the tensor as NCHW `[1, 3, 640, 640]`. The ONNX output is decoded by the Pi application and class-wise non-maximum suppression is applied before boxes are mapped back to the original image.

A frame with no detections is reported as `NO_TARGET_DEFECT_DETECTED`. This means none of the three configured classes was detected in that frame; it is not proof that the entire PCB is defect-free.

The detector now applies an explicit, configurable type-based screening policy: `missing_hole` = MEDIUM, `open_circuit` = HIGH and `short_circuit` = HIGH. This is marked provisional and requires approval against the actual board drawing/QA criteria; it is not a board-specific risk assessment or safety certification. Unknown classes fall back to `UNASSESSED`, and severity is never inferred from confidence. The policy is in `models/severity_policy.json`.

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

## Local inference and offline operation

**All inference algorithms are configured to run on the Raspberry Pi 5, not in the browser or through a cloud API.** OpenCV preprocessing and the YOLO ONNX detector run locally through ONNX Runtime's CPU provider. The Llama 3.2 1B advisory runs locally through the ExecuTorch C++ `llama_main` runner on the Pi CPU. The laptop browser is only an operator interface; it sends same-origin requests to the Pi-hosted station service and displays the results.

Inspection images and JSON events are stored locally on the Pi. Firebase Realtime Database synchronization is optional and disabled by default (`PCB_FIREBASE_PUBLISH=false`); it replicates records only and is not used for inference. Downloading model files and installing dependencies require internet during setup, but inference does not require internet once the model, tokenizer, runtime and packages are present locally. A laptop can connect over a private LAN without WAN access.

The intended deployment is offline-capable; a completed offline test on the final Raspberry Pi must still be recorded before claiming that offline operation has been demonstrated. See [Local execution and performance record](docs/LOCAL_EXECUTION_AND_PERFORMANCE.md) for the evaluator checklist, external reference metrics and commands for collecting actual Pi measurements.

## One-command Raspberry Pi 5 setup

The repository now includes a provisioner that installs the Pi packages, creates the Python environment, downloads the attributed PCB YOLO checkpoint, exports it to ONNX, downloads the Llama 3.2 1B PTE/tokenizer pair, builds the ExecuTorch C++ runner against the Pi's own root filesystem, and runs software smoke tests.

Requirements: 64-bit Raspberry Pi OS on a Raspberry Pi 5, internet access for first-time provisioning, at least 12 GiB free storage, and a suitable power supply/cooling. The first setup downloads large model/build dependencies and can take a while. Review and comply with the upstream Llama 3.2 license and acceptable-use policy before use.

From the repository root on the Pi:

```bash
bash scripts/provision_pi5.sh
```

Then edit `raspberry_pi/.env` and enter the **actual** IR and LED-driver BCM pin numbers/polarities for your wiring. The provisioner deliberately does not guess hardware pins. Start the station:

```bash
bash scripts/run_station_pi5.sh
```

The provisioner uses Sulojan Rajkumar's attributed six-class YOLOv8s PCB checkpoint as the initial deployment baseline. It exports a local ONNX copy and maps only `missing_hole`, `open_circuit` and `short` into the application's three-class event schema. The publisher's reported metrics remain external reference figures, not results from this project.

The script writes `docs/results/pi5_runtime_smoke_test.json`. This verifies ONNX CPU execution and a real ExecuTorch advisory call using an illustrative event; it does not establish PCB accuracy or validate the physical conveyor/camera/IR/LED cycle. Use the commissioning procedure for those tests.

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

## Published pretrained PCB YOLOv8s baseline

A MIT-licensed third-party six-class YOLOv8s PCB checkpoint is available as an
attributed baseline from Sulojan Rajkumar. Its model-card and author-reported
held-out results, training details, source links and exact checkpoint SHA-256
are documented in [docs/PCB_UPSTREAM_BASELINE.md](docs/PCB_UPSTREAM_BASELINE.md).
These are the publisher's reported results; they are not claimed as results
from this project.

Download and verify the 22.5 MB checkpoint:

```bash
python -m pip install "huggingface_hub>=0.30,<2"
python models/pretrained/download_sulojan_pcb_yolov8s.py
```

To export the six-class model for the current Raspberry Pi decoder:

```bash
python -m pip install -r pcb_engine_kit/requirements-train.txt
python pcb_engine_kit/train_export.py export-upstream-onnx \
  --weights models/pretrained/sulojan_pcb_yolov8s/best.pt \
  --size 640 --out deployment_upstream
```

Copy both `deployment_upstream/best.onnx` and
`deployment_upstream/best.onnx.json` to `models/best.onnx` and
`models/best.onnx.json` on the Pi. The sidecar defines the source six-class
order and maps only `missing_hole`, `open_circuit` and `short` to the
application's corresponding three defect classes; the other source classes
are ignored. The inspection record retains the original model class order,
mapping and checkpoint hash.

For a project-specific three-class model, use the same checkpoint only as a
transfer-learning initialization with the verified three-class dataset and
train/validation/test split. Evaluate the new checkpoint independently before
reporting its metrics.

## Published research benchmarks

Published PCB defect-detection studies report results on DeepPCB and
PKU-Market-PCB, including mAP@0.50 values around 98–99% for their own trained
models. See [the literature comparison](docs/EXTERNAL_PCB_BENCHMARKS.md) for
the datasets, scores, evaluation context and source papers. These figures are
external research references; they are not measurements of this station or
of the checkpoint currently installed by the Pi provisioner. The project
has now supplied screenshot-reported validation metrics, listed below. A
separate held-out test evaluation is still required before claiming test-set accuracy.

## Project validation results

The team supplied a training-results screenshot showing the following validation metrics:

| Metric | Result |
|---|---:|
| Precision | 98.3% |
| Recall | 98.4% |
| mAP@50 | 98.9% |
| mAP@50–95 | 62.5% |

| Defect class | Precision | Recall | mAP@50 |
|---|---:|---:|---:|
| Missing Hole | 97.8% | 98.2% | 98.5% |
| Open Circuit | 99.1% | 99.6% | 99.5% |
| Short Circuit | 97.9% | 97.6% | 98.8% |

These are reported validation scores, not independent held-out test results or Raspberry Pi 5 performance. The dataset/version, validation sample count, checkpoint hash and raw evaluator output still need to be archived. The canonical results/provenance note is [docs/results/PROJECT_VALIDATION_RESULTS.md](docs/results/PROJECT_VALIDATION_RESULTS.md); the machine-readable record is [docs/results/published_pcb_benchmarks.json](docs/results/published_pcb_benchmarks.json), and the detailed technical report is [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md).

For the Phase 1 submission links, deliverable status and final evidence checks, see [docs/PHASE1_SUBMISSION_CHECKLIST.md](docs/PHASE1_SUBMISSION_CHECKLIST.md).

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

## Deploy the required Llama advisory

The PS5 advisory path is configured for Llama 3.2 1B Instruct SpinQuant INT4/EO8
running locally through ExecuTorch on the Raspberry Pi 5 CPU. The PTE file
and matching tokenizer are licensed, large artifacts, so they are downloaded
locally instead of being committed to Git.

On a machine with access to the Hugging Face model:

    python -m pip install "huggingface_hub>=0.30,<2"
    hf auth login
    python llm_advisory/download_model.py

Build the official Pi 5 C++ runtime directly on the Pi 5 (recommended), with CMake 3.26+:

    bash llm_advisory/build_pi5_runner.sh

For a Linux x86_64 cross-build, set `EXECUTORCH_SYSROOT` to the root filesystem
from the exact target Pi OS before running the same script; do not use a generic
sysroot. When built on the Pi, the runner is already in `models/llama/runtime`.
When cross-built, copy that runtime directory to the Pi. The default
raspberry_pi/.env.example points to these paths and keeps
PCB_LLAMA_REQUIRED=true. The Llama component receives the structured
inspection event as text only and produces an operator advisory; it does not
modify detections or control machinery. Full instructions:
[models/llama/README.md](models/llama/README.md) and
[llm_advisory/README.md](llm_advisory/README.md).

## Release status and evidence

The repository contains the station controller, dashboard, OpenCV/ONNX
detector source, dataset import/training/export utilities, structured event
schema, Llama prompt and ExecuTorch runner integration, deployment scripts,
benchmark scripts, technical report and a demonstration MP4.

The Llama deployment route is now pinned and executable from the repository:
download a matching PTE/tokenizer pair, build the ExecuTorch Pi 5 runner, copy
the local files to the Pi, and run the advisory smoke test. The large model
weights and compiled runtime are not tracked in Git. The repository cannot
claim that Llama has already run on the team's physical Pi until the smoke test
and complete station cycle are recorded.

The checkout still does not include a project-trained YOLO best.pt/best.onnx,
the processed project dataset and its audit, or labelled held-out predictions.
The screenshot-reported validation scores are documented above, but the raw
run output and dataset/checkpoint provenance are not yet archived. A separate
held-out test report, ONNX parity report, real Pi runtime measurements and
physical commissioning record remain to be produced from the team's own data
and hardware. A provisional type-based severity policy is
configured (missing hole = MEDIUM; open/short circuit = HIGH), but it has not
been approved against a board drawing or QA standard. Detector confidence is
not treated as severity. The MP4 file is present and team-confirmed complete,
but its actual scenes still need human review.

No project held-out test accuracy, latency, FPS, power or end-to-end reliability
number is claimed without a reproducible measurement record. The screenshot-
reported validation values above are explicitly validation-only. Published Raspberry Pi 5 reference
results are kept separately in [docs/REFERENCE_BENCHMARKS.md](docs/REFERENCE_BENCHMARKS.md);
they are not reported as this project's performance. Use
[docs/SUBMISSION_READINESS.md](docs/SUBMISSION_READINESS.md) for remaining
evidence and evaluator checks.

## Team

<img src="assets/team-photo.webp" alt="Project team" width="420" />

- **Mathews V Manoj** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Jordan Noby Eralil** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Deon Lukose Shince** — S5, Electronics and Communication Engineering, Muthoot Institute of Technology and Science
