# PCB Automated Optical Inspection
## Technical project report

**Conveyor-based inspection · IR-guided positioning · Raspberry Pi 5 · Edge vision · Llama advisory**

## Executive summary

The project combines a built conveyor-based PCB inspection station with a Raspberry Pi-hosted operator interface and two independent on-device inference pipelines. The physical station uses an IR presence sensor, a conveyor, an inspection camera and an externally powered LED strip.

The station follows a latched two-phase IR sequence. At the start of a station session, the operator holds a hand in front of the IR sensor for approximately three seconds to arm the station. After release, the PCB is placed on the conveyor. Arming remains active across subsequent board inspections until the station controller is restarted. The conveyor transports the PCB to the camera position, where the next IR activation confirms board presence and triggers image capture. The Raspberry Pi illuminates the board through the external LED driver and captures a frame.

The Pi serves the captured image to a laptop browser for operator verification. The operator then selects **Run inspection on Raspberry Pi**. This sends a command to the Pi-hosted station service; the laptop does not perform inference. The Raspberry Pi preprocesses the captured image, runs YOLO-based defect localization, passes structured findings to the separate Llama/ExecuTorch advisory and returns the result to the operator UI.

The three target defect classes are open circuit, short circuit and missing hole.

## 1. Physical inspection station

| Element | Function |
|---|---|
| Conveyor assembly | Transports the PCB from loading position to the imaging zone |
| IR presence sensor | Three-second continuous activation arms the station once; subsequent active transitions detect each PCB at the camera position |
| External LED strip | Illuminates the PCB during image capture |
| External LED driver | Switches the separately powered LED strip |
| Camera | Captures the illuminated PCB frame |
| Raspberry Pi 5 | Runs the station state machine, hosts the operator website and performs edge inference |
| Laptop browser | Displays the Pi-hosted UI, previews the captured image and sends the inspection command |

The LED strip is supplied through its external driver and power source. The Raspberry Pi GPIO line is the driver's control signal. The conveyor transports the board; the inspection controller coordinates the sensor/camera workflow.

## 2. Operating sequence and operator interaction

1. **IR arming:** at the start of a station session, the operator holds a hand in front of the IR sensor for about three seconds. This latches the station into its armed state for subsequent boards.
2. **Armed state:** the sensor is released and the station enters the board-waiting state.
3. **PCB loading:** the PCB is placed on the conveyor.
4. **Conveyor transport:** the belt carries the PCB towards the inspection camera.
5. **Camera-position detection:** the IR input's next active transition identifies the board at the imaging position.
6. **Illumination:** the Pi switches the external LED driver on and waits for the configured settling interval.
7. **Frame capture:** the selected USB/UVC or CSI camera captures one frame; the Pi stores the image locally.
8. **Image preview:** the Pi-hosted web service exposes the saved frame through `GET /api/capture.jpg`; the laptop browser displays it for operator verification.
9. **Operator authorization:** the operator clicks **Run inspection on Raspberry Pi**. The dashboard sends `POST /api/run-inspection` to the same Pi-hosted service.
10. **Local inference:** the Pi reads the stored frame, runs OpenCV preprocessing and YOLO inference, then creates the annotated image and JSON event.
11. **Local advisory:** the inspection coordinator passes structured detections to the Llama/ExecuTorch pipeline.
12. **Result return:** the UI polls the Pi's status endpoint and displays the decision, findings, annotated output, advisory and history.

![PCB inspection system architecture](inspection_workflow.svg)

## 3. Pi-hosted web/API architecture

The dashboard is served directly by `raspberry_pi/station_controller.py` from `dashboard/index.html`. It is opened remotely from a laptop using the Raspberry Pi's IP address and configured port.

| Endpoint | Purpose |
|---|---|
| `GET /` | Serve the operator website |
| `GET /api/status` | Return sensor, illumination, capture and inference state |
| `GET /api/capture.jpg` | Serve the captured frame for pre-inference verification |
| `GET /api/annotated.jpg` | Serve the post-inference annotated image |
| `GET /api/history` | Return recent local JSON inspection records |
| `POST /api/run-inspection` | Start inference on the Raspberry Pi using the saved frame |

The browser is an operator console only. It does not load model weights or perform OpenCV, YOLO or ExecuTorch inference. The API and model processes execute on the Raspberry Pi.

## 4. OpenCV preprocessing and image representation

The current YOLO ONNX implementation uses a three-channel RGB tensor. The preprocessing steps in `raspberry_pi/inspect_image.py` are:

1. Read the captured frame from the Pi's local storage.
2. Resize while preserving aspect ratio using letterboxing.
3. Pad the image to 640 × 640 using the configured padding value.
4. Convert BGR to RGB.
5. Convert to float32 and normalize each channel to `[0, 1]`.
6. Convert the image array into NCHW tensor order, `[1, 3, 640, 640]`.

The current detector preprocessing does **not** convert the input to grayscale. The YOLO model requires a three-channel input under the published model contract. The detector learns visual representations of conductive-track discontinuities, unintended bridges and missing holes. A separate handcrafted grayscale, threshold/edge or trace-continuity algorithm is not present in the current inference source.

## 5. Vision pipeline

The base vision path uses YOLOv8 Nano through ONNX Runtime with CPU execution on Raspberry Pi 5.

| Class ID | Defect | Visual feature to localize |
|---:|---|---|
| 0 | `missing_hole` | An expected PCB hole is absent or visibly defective |
| 1 | `open_circuit` | A conductive path is visibly discontinuous |
| 2 | `short_circuit` | A conductive bridge appears between separate paths |

The detector produces class scores and bounding boxes. Confidence thresholding and non-maximum suppression filter predictions. Bounding boxes are mapped to the original frame and drawn on an annotated image. The event stores class ID, class name, confidence, bounding box and normalized centre.

An optional Hailo NPU through HailoRT and an AI HAT+ / AI HAT+ 2 is a vision acceleration option. The current repository's base path is ONNX Runtime on the Pi CPU; Hailo is not implemented in this source checkout.

## 6. Separate Llama advisory pipeline

The complete inspection architecture requires a local Llama-family advisory using ExecuTorch on the Raspberry Pi ARM CPU. The reference model family is Llama 3.2 Instruct 1B or 3B.

The advisory receives structured fields—board ID, timestamp, defect type, severity, image location and confidence. It returns a concise explanation, recommended operator verification actions, a severity note and log text.

The Llama model receives no camera frame or pixel payload. It cannot create, remove, relabel or suppress detector findings, infer severity from confidence or independently issue a PASS/REJECT decision. YOLO remains the visual localization source.

The source integration comprises:

- `llm_advisory/prompt.py`: text-only prompt construction.
- `llm_advisory/run_executorch.py`: ExecuTorch LLM runner and response telemetry.
- `raspberry_pi/run_inspection.py`: vision/advisory sequencing, local record update and optional Firebase sync.

The ExecuTorch `.pte` model and matching tokenizer are separate deployment files and are not included in the public source checkout.

## 7. Inspection event and operator results

Each event contains a record ID, board ID, timestamp, source, model file, class order, inference latency, station metadata and detection list. Each detection contains type, severity, location and confidence.

Severity and confidence are distinct. Severity uses defect type, physical size and functional board location. The current source uses `UNASSESSED` when no board-specific severity profile is configured. `NO_TARGET_DEFECT_DETECTED` means no configured target was detected in the given frame; it is not a blanket guarantee that the board is defect-free.

The UI displays the decision, detections, confidence, location, annotated image, advisory and inspection history. The JSON event is saved locally. Firebase Realtime Database is an optional synchronization layer; it does not execute inference.

## 8. Runtime separation

| Workload | Base runtime | Processor |
|---|---|---|
| OpenCV preprocessing | OpenCV | Raspberry Pi 5 CPU |
| Vision detection | YOLOv8 Nano / ONNX Runtime | Raspberry Pi 5 ARM CPU |
| Optional vision acceleration | YOLO-family model / HailoRT | Hailo NPU |
| Advisory reasoning | Llama 3.2 Instruct / ExecuTorch | Raspberry Pi 5 ARM CPU |
| Operator interface | Python standard-library HTTP server + HTML/CSS/JS | Raspberry Pi 5 |
| Record synchronization | Firebase Realtime Database | Optional network data service |

Hailo accelerates the vision stage only; it does not replace ExecuTorch for the advisory.

## 9. Evaluation methodology

| Dimension | Measurements |
|---|---|
| Detection quality | Per-class precision, recall, F1, confusion matrix, false positives, false negatives and localization |
| Vision runtime | FPS, per-image latency, IR-trigger-to-record latency, RAM and power |
| Advisory runtime | Time to first token, tokens/s, total response time and peak RAM |
| Advisory usefulness | Grounding in class, severity and coordinates; concise verification actions |
| Operator experience | Three-second arm response, capture preview, run-command acknowledgement, alert clarity and event history |
| Integration | IR two-phase state sequence, LED timing, camera capture, browser-to-Pi API, local processing and optional synchronization |

Performance figures are reported only with the corresponding dataset split, model hash, runtime version and Raspberry Pi configuration. Workstation results are not represented as Raspberry Pi measurements.

## 10. Source and release evidence

The repository includes source for the IR state machine, Pi-hosted HTTP service, camera capture, OpenCV/ONNX inference, vision/advisory coordinator, ExecuTorch runner, operator website, event schema and software contract tests.

The trained three-class detector, ExecuTorch `.pte` package and tokenizer, complete processed PCB dataset and validated Raspberry Pi benchmark report are separate release assets and are not bundled in the current source checkout. The source-level run button and orchestration require the matching model artifacts for a complete live inference cycle.

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
