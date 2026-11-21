# Edge-AI PCB Automated Optical Inspection

[![Repository checks](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/workflows/ci.yml)

**A conveyor-based PCB inspection system combining IR-triggered board arrival, controlled LED illumination, edge vision, on-device Llama advisory reasoning and an operator interface.**

The project integrates a physical PCB inspection station with an edge-computing workflow. A conveyor transports the board to the inspection zone. An IR presence sensor detects arrival, an externally powered LED strip illuminates the board, and the camera captures an image for inspection. On the Raspberry Pi 5, the software preprocesses the frame, localizes configured defects, generates an annotated image and structured inspection event, and passes the findings to a separate Llama advisory pipeline.

The three target defect classes are **open circuit**, **short circuit** and **missing hole**. Visual detection and advisory reasoning are deliberately separated: the vision model supplies the defect class and location; Llama explains those structured findings, suggests operator verification actions and creates advisory log text.

**Project resources:** [Technical report](docs/PROJECT_REPORT.md) · [Architecture diagram](docs/inspection_workflow.svg) · [Raspberry Pi 5 deployment](docs/PI5_DEPLOYMENT.md) · [Deliverables and evaluation](docs/DELIVERABLES_AND_EVALUATION.md) · [Demonstration](demo_video/README.md)

---

## 1. Physical inspection station

The built inspection station combines the following elements:

| Element | Role in the inspection cycle |
|---|---|
| Conveyor assembly | Transports the PCB into the inspection zone |
| IR presence sensor | Detects PCB arrival and triggers the inspection cycle |
| External LED strip | Illuminates the board during image capture |
| Inspection camera | Captures the illuminated PCB frame |
| Raspberry Pi 5 | Coordinates the sensor-triggered capture and edge-processing workflow |

The station controller reads the IR sensor through a configurable GPIO input and switches the LED strip through a separate external driver. The illumination strip is powered by its own supply and driver; the Pi GPIO is a control signal, not the LED power source. The conveyor provides board transport; motor drive and emergency-stop circuitry are separate from the camera-trigger controller.

## 2. End-to-end inspection sequence

1. **Board transport:** the conveyor carries the PCB towards the inspection position.
2. **Arrival detection:** the IR sensor detects the board and emits the trigger event.
3. **Illumination:** the external LED strip is enabled through its driver.
4. **Image acquisition:** after the configured illumination-settle interval, the camera captures one inspection frame.
5. **Preprocessing:** OpenCV validates the image, resizes it, converts the colour space and normalizes the input.
6. **Visual inference:** YOLOv8 Nano predicts defect classes and image locations.
7. **Defect record:** detections are serialized with type, severity, location, confidence, board ID and timestamp. An annotated image is saved with the localized findings.
8. **Advisory reasoning:** the Llama/ExecuTorch pipeline receives the structured event fields only. It generates an explanation, recommended verification actions and an inspection log entry.
9. **Operator interface:** the inspection result, alert, advisory and event history are presented to the operator. The completed JSON event is retained locally and can be synchronized to Firebase Realtime Database.

![PCB inspection system architecture](docs/inspection_workflow.svg)

## 3. Two separate inference pipelines

The design uses two independent local inference paths. The advisory model is mandatory in the complete inspection workflow; the Hailo accelerator is an optional vision hardware path.

| Pipeline | Model and runtime | Processor | Responsibility |
|---|---|---|---|
| Vision — base path | YOLOv8 Nano with ONNX Runtime | Raspberry Pi 5 ARM CPU | Detects, classifies and localizes PCB defects |
| Vision — accelerator option | YOLO-family detector with HailoRT | Hailo NPU through AI HAT+ / AI HAT+ 2 | Optional acceleration of the vision workload |
| Advisory — required path | Llama 3.2 Instruct 1B or 3B with ExecuTorch | Raspberry Pi 5 ARM CPU | Explains structured findings, recommends verification actions and writes advisory log text |

The current Raspberry Pi vision implementation uses ONNX Runtime on the Pi CPU. The Hailo/HailoRT route is an optional accelerator architecture and is not part of the current source implementation. Hailo applies to vision inference only; it does not replace the Llama advisory runtime.

The Llama model runs locally through ExecuTorch on the Pi ARM CPU. It receives a text prompt containing defect type, severity, location, confidence and board context, not the original PCB image. Detection, advisory generation and logging are local operations; cloud inference is not part of the architecture. Firebase is used only for optional record synchronization.

A CPU-only Raspberry Pi 5 is the base deployment path. The platform guidance identifies 8 GB RAM as providing more headroom for concurrent vision and Llama workloads; a 4 GB configuration requires tighter memory profiling.

## 4. Vision model and defect classes

The selected detector interface is YOLOv8 Nano. It returns localized bounding boxes rather than a single image-level label.

| Class ID | Defect | Inspection meaning |
|---:|---|---|
| 0 | `missing_hole` | An expected PCB hole is absent or visibly defective |
| 1 | `open_circuit` | A visible discontinuity is present in a conductive track |
| 2 | `short_circuit` | An unintended conductive bridge connects separate tracks |

The deployment class map is shared across the Raspberry Pi inference application, dataset converter, exporter and supplementary TFLite worker. The model contract includes input dimensions, colour order, normalization, output tensor layout, confidence filtering and non-maximum suppression.

## 5. Structured defect record and severity

Each inspection event includes a record ID, board ID, timestamp, source, model identity, inference latency, station state and an array of detections.

Each detection contains:

- **Type:** `missing_hole`, `open_circuit` or `short_circuit`.
- **Severity:** `LOW`, `MEDIUM`, `HIGH` or `UNASSESSED`.
- **Location:** image-coordinate bounding box and normalized centre.
- **Confidence:** the detector's confidence score.

Severity and confidence are independent. Severity is based on defect type, physical extent and location within the board's functional layout; confidence expresses the detector's certainty in its prediction. Where no board-specific impact profile has assigned a severity, the event remains `UNASSESSED` for operator review.

The current decision policy emits `REVIEW` when configured target defects are detected and `NO_TARGET_DEFECT_DETECTED` when the detector returns no configured findings. The latter means only that no configured target was detected in that frame; it is not an unconditional product-quality guarantee. The Llama advisory does not independently issue a PASS/REJECT decision.

The event contract is defined in [`schemas/inspection-event.schema.json`](schemas/inspection-event.schema.json), with a representative record in [`schemas/example-event.json`](schemas/example-event.json).

## 6. Llama advisory with ExecuTorch

The complete system includes a mandatory Llama-family advisory stage using ExecuTorch on the Raspberry Pi ARM CPU. A pretrained Llama 3.2 Instruct 1B or 3B model is the reference model family; fine-tuning is not required for the structured-prompt workflow.

The advisory receives:

- Defect type and assigned severity.
- Bounding-box location and normalized image coordinates.
- Detector confidence.
- Board ID and inspection timestamp.

It returns a concise explanation, recommended operator verification actions, a severity note and a structured log entry. The advisory is restricted to the supplied evidence: it cannot view PCB pixels, create or remove detections, relabel model output, infer severity from confidence or replace the independent inspection decision policy.

The software integration is implemented across:

| Source | Function |
|---|---|
| `llm_advisory/prompt.py` | Builds a text-only prompt from the structured inspection event |
| `llm_advisory/run_executorch.py` | Invokes the ExecuTorch LLM runner and records response telemetry |
| `raspberry_pi/run_inspection.py` | Coordinates vision inference, advisory generation, local event update and optional Firebase synchronization |
| `raspberry_pi/station_controller.py` | Responds to IR arrival events, switches the illumination driver and launches the complete inspection coordinator |

The ExecuTorch `.pte` model package and matching tokenizer are separate deployment assets and are not stored in the public source repository. The runner and orchestration source are present; target-device advisory execution depends on those matching model assets and the corresponding ExecuTorch LLM Runner build.

## 7. Operator interface and inspection history

The operator dashboard is implemented in [`dashboard/index.html`](dashboard/index.html). It presents:

- Latest inspection result and board identity.
- IR sensor and LED illumination state at capture.
- Camera and conveyor state fields.
- Detected defect types, severity, location and confidence.
- Llama advisory text.
- Inspection history and CSV export.

The dashboard is a presentation layer. It does not perform image inference or Llama generation. Firebase Realtime Database synchronizes completed records through `/live` and `/inspections/{record_id}`; it is not an inference runtime. Local JSON inspection events remain the primary edge-side records.

## 8. Dataset strategy

The dataset manifest distinguishes PCB-specific sources from broader industrial surface-defect references.

| Dataset | Domain | Relevance to this project |
|---|---|---|
| DeepPCB | PCB defects | PCB-specific annotations for open/short circuit patterns |
| Tiny-Defect-Detection-for-PCB | PCB defects | PCB-specific small-defect reference |
| Project camera captures | Actual inspection station | Captures the board appearance and illumination conditions of the built system |
| MVTec AD | General industrial anomaly detection | Reference for anomaly-detection methodology |
| NEU Surface Defect | Steel surface defects | General surface-defect reference; not a PCB label set |
| KolektorSDD | Electrical commutator surface defects | General industrial defect reference; not a PCB label set |

Dataset identity, version, annotation mapping, licence or access terms, and split provenance are tracked in [`datasets/SOURCE_MANIFEST.csv`](datasets/SOURCE_MANIFEST.csv). The manifest distinguishes candidate sources from sources recorded for a training run. The complete processed training archive is not included in this repository.

## 9. Evaluation framework

The evaluation follows five dimensions: detection quality, on-device execution, advisory quality, operator experience and runtime separation.

| Area | Evaluation measures |
|---|---|
| Detection quality | Per-class precision, recall and F1; confusion matrix; false alarms; missed defects; localization review |
| Real-time vision | FPS, per-image latency, end-to-end latency, peak memory and power on Raspberry Pi 5 |
| Llama runtime | Time to first token, tokens per second, total response time and peak memory |
| Advisory quality | Relevance to defect type, severity and location; grounded actions; no unsupported findings |
| Operator experience | Alert clarity, review flow, status visibility, readable history and traceable log entries |
| Runtime separation | Vision and advisory execution measured independently; Hailo vision path evaluated separately when present |

The measurement protocol and deliverable mapping are in [`docs/DELIVERABLES_AND_EVALUATION.md`](docs/DELIVERABLES_AND_EVALUATION.md). No numerical accuracy or device-performance value is published without a corresponding checkpoint, dataset split, runtime version and target-device measurement record.

## 10. Repository structure

| Path | Contents |
|---|---|
| `raspberry_pi/` | IR-triggered station controller, vision/advisory orchestrator, ONNX image/camera inference and Firebase publisher |
| `llm_advisory/` | Structured prompt builder and ExecuTorch runner |
| `dashboard/` | Operator dashboard |
| `schemas/` | Inspection-event JSON Schema and example |
| `models/` | Canonical class map and model release manifest |
| `datasets/` | Dataset provenance and source manifest |
| `pcb_engine_kit/` | Annotation conversion, YOLO training/export utilities and supplementary TFLite worker |
| `training/` | Example training configuration |
| `tests/` | Advisory-boundary, event-schema, class-map, dashboard and station-integration contract tests |
| `firebase/` | Example Realtime Database rules |
| `docs/` | Technical report, Raspberry Pi deployment, architecture and evaluation documentation |
| `demo_video/` | Physical-system demonstration overview |

## 11. Submission deliverables

| Deliverable | Repository evidence |
|---|---|
| Source code | Station controller, vision inference, inspection coordinator, ExecuTorch runner, dashboard, schemas and automated tests |
| Application | Built conveyor inspection station with IR arrival sensing, LED illumination and camera-based inspection |
| Demonstration video | Physical station sequence and operator-facing inspection workflow, supplied as the separate video submission |
| Technical report | System design, runtime separation, event format, dataset strategy and evaluation methodology |

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
