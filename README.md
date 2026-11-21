# Edge-AI PCB Automated Optical Inspection

[![Repository checks](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions)

**A conveyor-based PCB inspection station with IR-guided positioning, controlled LED illumination, Raspberry Pi edge vision, on-device Llama advisory and a browser-based operator console.**

The system combines a physical inspection line with a two-stage operator/sensor workflow. At the start of a station session, the operator holds a hand in front of the IR sensor for approximately three seconds to arm the station. This is a one-time arming step: after the sensor is released, the station remains armed for subsequent boards until the controller is restarted. The PCB is then placed on the conveyor. The conveyor transports the board to the camera position, where the IR sensor confirms that a board is present. The LED strip illuminates the board and the camera captures an inspection frame.

The Raspberry Pi hosts the operator website. The captured frame is served to the laptop browser for visual verification. When the operator selects **Run inspection on Raspberry Pi**, the browser sends a command to the Pi station service. The Raspberry Pi—not the laptop browser—runs the image-processing, vision and advisory workloads, then returns the inspection result to the UI.

The three target classes are **open circuit**, **short circuit** and **missing hole**. The vision pipeline identifies and localizes defects. The separate Llama advisory pipeline receives structured findings only and generates an explanation, operator verification actions and log text.

**Project resources:** [Technical report](docs/PROJECT_REPORT.md) · [System flowchart](docs/inspection_workflow.svg) · [Pi station deployment](docs/PI5_DEPLOYMENT.md) · [Deliverables and evaluation](docs/DELIVERABLES_AND_EVALUATION.md) · [Operator dashboard](dashboard/index.html)

---

## 1. Physical inspection station

| Hardware element | Function |
|---|---|
| Conveyor assembly | Transports the PCB from the loading position to the camera zone |
| IR presence sensor | Provides the three-second arming event and then detects the PCB at the camera position |
| External LED strip | Illuminates the PCB during capture |
| External LED driver | Switches the separately powered LED strip |
| Inspection camera | Captures the illuminated board |
| Raspberry Pi 5 | Hosts the operator UI, handles the sensor sequence and runs local inference |

The IR input is used as a latched two-phase state sequence: a continuous activation of approximately three seconds arms the station once; after the sensor is released, the next active transition is interpreted as the PCB reaching the camera position. After an inspection completes, the controller stays armed and accepts the next board-arrival transition without requiring another hand-hold sequence. Restarting the station controller resets the arming state.

The LED strip is powered through its external driver and suitable supply. A Raspberry Pi GPIO pin is used only as the driver's logic-level control signal. Conveyor transport is provided by the physical conveyor assembly; the inspection controller coordinates sensing, illumination, capture and processing.

## 2. Exact operating workflow

1. **Arm the station:** hold a hand in front of the IR sensor for approximately three seconds.
2. **Release and load:** release the sensor; place the PCB on the conveyor.
3. **Transport:** the conveyor carries the PCB towards the camera.
4. **Confirm position:** the IR sensor detects the PCB at the camera position and triggers the capture stage.
5. **Illuminate:** the Raspberry Pi switches the external LED driver on and waits for the configured illumination-settle interval.
6. **Capture:** the camera captures one frame and the Raspberry Pi saves it locally.
7. **Laptop preview:** the Pi-hosted website serves the captured frame to the laptop browser. The operator can visually verify that the correct board and camera view were captured.
8. **Operator command:** the operator clicks **Run inspection on Raspberry Pi**. The browser sends `POST /api/run-inspection` to the Pi-hosted station service.
9. **Local processing:** the Raspberry Pi loads the saved frame, preprocesses it with OpenCV and runs the configured YOLO detector.
10. **Advisory:** the Pi passes the structured detection record to the on-device Llama/ExecuTorch process.
11. **Results:** the Pi creates the annotated image and structured event, then returns the decision, defects, coordinates, confidence and advisory to the UI.
12. **History:** the result is retained as a local JSON record and can optionally be synchronized to Firebase Realtime Database.

![PCB inspection system architecture](docs/inspection_workflow.svg)

## 3. Raspberry Pi-hosted operator UI

The website is served by the station controller running on the Raspberry Pi. An operator opens the Pi's address from a laptop browser on the same trusted local network.

The dashboard has two distinct interactions:

- **Image verification:** after IR-confirmed capture, the browser displays the frame that is stored on the Pi. The frame is served from `/api/capture.jpg`.
- **Run inspection:** the operator clicks the run button. The page sends a same-origin HTTP request to `/api/run-inspection`. The Pi reads the saved frame and starts its local processing coordinator.

The browser is an operator interface only. It does not run YOLO, ExecuTorch or image-processing algorithms. The Pi also serves status and history endpoints to the page:

| Endpoint | Function |
|---|---|
| `GET /` | Serves the operator dashboard |
| `GET /api/status` | Returns IR, illumination, capture and inference state |
| `GET /api/capture.jpg` | Serves the captured PCB frame for operator review |
| `GET /api/annotated.jpg` | Serves the detector-annotated image after inference |
| `GET /api/history` | Returns recent local inspection events |
| `POST /api/run-inspection` | Starts vision and advisory processing on the Raspberry Pi |

The station service is intended for a trusted local network. It is not designed to be exposed directly to the public internet.

## 4. Image processing and vision model

### Implemented OpenCV preprocessing

The committed ONNX inference path uses a three-channel image tensor. Its preprocessing sequence is:

1. Read the captured image from the Pi's local inspection directory.
2. Resize it using **letterboxing**, preserving the original aspect ratio.
3. Pad the resized frame to the detector's 640 × 640 input dimensions.
4. Convert the OpenCV image from **BGR to RGB**.
5. Convert pixel values to `float32` and normalize them to the range `[0, 1]`.
6. Arrange the data as an NCHW tensor with shape `[1, 3, 640, 640]`.

**Grayscale clarification:** the current YOLO deployment path does not convert the image to grayscale. It requires a three-channel RGB tensor. The detector learns visual features associated with conductive-track discontinuities, unintended conductive bridges and missing holes. A separate grayscale, thresholding, edge-detection or handcrafted trace-continuity algorithm is not part of the current inference implementation and is not claimed as an implemented stage.

### YOLO defect localization

The current base vision path uses YOLOv8 Nano through ONNX Runtime with CPU execution on the Raspberry Pi 5.

| Class ID | Defect | Visual pattern being localized |
|---:|---|---|
| 0 | `missing_hole` | An expected hole is absent or visibly defective |
| 1 | `open_circuit` | A conductive path has a visible discontinuity |
| 2 | `short_circuit` | An unintended conductive bridge appears between separate paths |

The model output is filtered by confidence and non-maximum suppression. Bounding boxes are mapped back to the original image coordinates and drawn on the annotated output. Each finding includes its class, confidence, bounding box and normalized centre.

## 5. Separate vision and advisory runtimes

The system contains two independent inference pipelines.

| Pipeline | Model/runtime | Processor | Function |
|---|---|---|---|
| Vision — implemented base path | YOLOv8 Nano + ONNX Runtime | Raspberry Pi 5 ARM CPU | Detects, classifies and localizes PCB defects |
| Vision — optional acceleration | YOLO-family detector + HailoRT | Hailo NPU via AI HAT+ / AI HAT+ 2 | Optional acceleration of vision inference |
| Advisory — required path | Llama 3.2 Instruct 1B or 3B + ExecuTorch | Raspberry Pi 5 ARM CPU | Explains structured findings, suggests operator verification and generates log text |

Hailo is an optional vision accelerator and is not part of the current ONNX source path. Hailo does not execute the Llama advisory. The required advisory model runs separately through ExecuTorch on the Raspberry Pi ARM CPU.

### Llama input and output boundary

The advisory receives the board ID, timestamp, defect type, severity, location and confidence as structured text. It does not receive the PCB pixels or camera image. Its output contains:

- A concise explanation of the reported finding.
- Suggested operator verification actions.
- A severity note.
- A structured inspection log entry.

Llama does not create, remove, relabel or suppress YOLO detections. It does not infer severity from confidence and does not independently issue a PASS/REJECT decision.

The source integration is implemented in `llm_advisory/prompt.py`, `llm_advisory/run_executorch.py` and `raspberry_pi/run_inspection.py`. The ExecuTorch `.pte` model and matching tokenizer are separate deployment assets and are not included in the public source checkout.

## 6. Defect record, severity and result handling

Each inspection event contains a record ID, board ID, timestamp, input source, model identity, inference latency, station state and an array of detections.

Each detection includes:

- **Type:** one of the three target classes.
- **Severity:** `LOW`, `MEDIUM`, `HIGH` or `UNASSESSED`.
- **Location:** bounding box and normalized image centre.
- **Confidence:** detector score for that prediction.

Severity and confidence are different measures. Severity is based on defect type, physical extent and board location. Where no board-specific impact profile assigns severity, the event retains `UNASSESSED` for operator review.

The application returns `REVIEW` when configured target defects are detected and `NO_TARGET_DEFECT_DETECTED` when no configured target is found in the frame. The latter does not guarantee that the whole PCB is defect-free. The Llama advisory does not change the detector decision.

The data contract is defined in [`schemas/inspection-event.schema.json`](schemas/inspection-event.schema.json), with an illustrative event in [`schemas/example-event.json`](schemas/example-event.json).

## 7. Operator results and record synchronization

After inference, the Pi-hosted dashboard shows:

- The original captured frame and the annotated detector output.
- Board ID and inspection decision.
- Defect class, severity, confidence and bounding-box location.
- Vision inference latency.
- Llama advisory and recommended verification actions.
- Recent inspection history and CSV export.

The local JSON event is the edge-side inspection record. Firebase Realtime Database is an optional synchronization layer using `/live` and `/inspections/{record_id}`. Firebase does not run image inference or the Llama model.

## 8. Dataset and evaluation

PCB-specific references include DeepPCB, Tiny-Defect-Detection-for-PCB and project camera captures. MVTec AD, NEU Surface Defect and KolektorSDD are broader industrial references; they are not interchangeable with PCB class labels. Dataset identity, source and annotation mapping are tracked in `datasets/SOURCE_MANIFEST.csv`.

The evaluation framework covers:

| Evaluation area | Measurements |
|---|---|
| Detection quality | Per-class precision, recall, F1, confusion matrix, false positives, missed defects and localization review |
| Real-time vision | FPS, per-image latency, IR-trigger-to-event latency, peak memory and power on Raspberry Pi 5 |
| Llama runtime | Time to first token, tokens per second, total response time and peak memory |
| Advice quality | Relevance to class, severity and location; useful, grounded operator actions |
| Operator experience | Image verification, clear alerts, visible station state and traceable event history |
| Integration | Three-second arming, IR board-position trigger, LED timing, camera capture, browser-to-Pi command and result return |

No numerical result is published without the matching checkpoint, held-out dataset split, runtime and target-device measurement record. The public source checkout does not include the final trained YOLO weights, ExecuTorch model/tokenizer package, complete processed dataset archive or a validated Pi 5 benchmark report.

## 9. Repository structure

| Path | Contents |
|---|---|
| `raspberry_pi/` | IR state machine, Pi web/API service, image inference, inspection coordinator and Firebase publisher |
| `dashboard/` | Pi-hosted operator UI |
| `llm_advisory/` | Structured prompt builder and ExecuTorch runner |
| `schemas/` | Inspection-event JSON Schema and example |
| `models/` | Canonical class map and release manifest |
| `datasets/` | Dataset provenance manifest |
| `pcb_engine_kit/` | Annotation conversion, YOLO training/export utilities and supplementary TFLite worker |
| `tests/` | Source contracts for class order, station trigger, API/UI and advisory boundary |
| `docs/` | Technical report, deployment guide, flowchart and evaluation framework |
| `firebase/` | Example Realtime Database rules |
| `demo_video/` | Physical station demonstration overview |

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
