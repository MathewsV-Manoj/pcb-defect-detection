# Edge-AI PCB Automated Optical Inspection

[![Repository checks](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/workflows/ci.yml)

**A conveyor-based PCB inspection system combining IR-triggered board detection, controlled LED illumination, computer vision, on-device advisory reasoning and an operator interface.**

We built a physical PCB inspection station around a conveyor, an IR presence sensor, an inspection camera and an externally powered LED illumination strip. When a board reaches the inspection point, the IR sensor detects its arrival and the camera captures the illuminated board for inspection. The edge-computing workflow then preprocesses the image, localizes configured PCB defects and creates a structured inspection record for the operator interface.

The three target defect classes are **open circuit**, **short circuit** and **missing hole**. The design separates visual detection from advisory reasoning: the vision model identifies and localizes defects, while a Llama-family model explains the structured findings and generates operator guidance.

## System at a glance

- **Physical inspection:** conveyor-based PCB transport, IR board-presence sensing, camera acquisition and external LED-strip illumination.
- **Edge platform:** Raspberry Pi 5.
- **Vision pipeline:** OpenCV preprocessing and YOLOv8 Nano object detection using ONNX Runtime on the Raspberry Pi 5 CPU in the current source implementation.
- **Optional accelerated vision architecture:** Hailo NPU through HailoRT and AI HAT+ / AI HAT+ 2. This is an optional committee-listed path; Hailo integration is not included in the current source checkout.
- **Advisory pipeline:** Llama 3.2 Instruct (1B or 3B class) through ExecuTorch on the Raspberry Pi ARM CPU. The station orchestrator calls a text-only runner and structured prompt builder; the model package and matching tokenizer are deployed separately. This is independent of the vision runtime and receives no raw pixels.
- **Inspection record:** defect type, severity field, location/bounding box, confidence, board ID, timestamp and runtime metadata.
- **Operator interface:** inspection alerts, advisory text and event history, with Firebase Realtime Database used for record synchronization.
- **Demonstration:** the physical conveyor, IR arrival sensing, LED illumination, image capture and inspection interface are shown in the project demonstration.

**Technical resources:** [Project report](docs/PROJECT_REPORT.md) · [Raspberry Pi 5 deployment](docs/PI5_DEPLOYMENT.md) · [System architecture](docs/inspection_workflow.svg) · [Dataset provenance](datasets/README.md) · [Demonstration scope](demo_video/README.md)

## 1. Physical inspection station

The physical station combines four elements:

| Element | Function in the inspection cycle |
|---|---|
| Conveyor assembly | Transports the PCB into the inspection zone |
| IR presence sensor | Detects when a PCB reaches the inspection position |
| Camera | Captures the board image for visual inspection |
| External LED strip | Provides illumination for repeatable image capture |

The IR sensor provides the board-arrival event used by the inspection cycle. The LED strip provides the illumination source around image capture. The Raspberry Pi software includes a configurable GPIO station controller and an inspection orchestrator so sensor input, illumination and the vision-to-advisory sequence are coordinated at the inspection station. The external LED strip is switched through its driver; a Raspberry Pi GPIO pin is not used to power the strip directly.

## 2. End-to-end inspection sequence

1. **Board transport:** the conveyor moves a PCB toward the inspection position.
2. **Presence detection:** the IR sensor detects the arriving board and provides the trigger input.
3. **Illumination and capture:** the external LED strip illuminates the PCB and the camera acquires a frame.
4. **Image preprocessing:** OpenCV validates the frame, resizes it, normalizes pixel values and prepares the model input.
5. **Visual detection:** YOLOv8 Nano detects and localizes open circuits, short circuits and missing holes. The Raspberry Pi CPU execution path uses ONNX Runtime. The committee architecture also lists HailoRT on a Hailo NPU / AI HAT+ / AI HAT+ 2 as an optional vision-acceleration route. The current repository implements the ONNX Runtime CPU path; no Hailo-compiled model or Hailo runtime integration is included in this checkout.
6. **Defect record:** detections are serialized with class, confidence, bounding-box location, board identity and timestamp. A severity value is carried separately from confidence.
7. **Advisory reasoning:** the Llama/ExecuTorch pipeline receives the structured defect record and creates an explanation, recommended verification actions and a log entry. It does not view raw PCB pixels or alter visual detections.
8. **Operator interface:** the interface presents the result, alert, advisory and inspection log. Firebase can synchronize the latest state and retained inspection records.

![PCB inspection system architecture](docs/inspection_workflow.svg)

### Runtime separation

The system contains two distinct inference pipelines:

| Pipeline | Runtime and processor | Responsibility |
|---|---|---|
| Vision — CPU path | ONNX Runtime on Raspberry Pi 5 ARM CPU | PCB image inference, class prediction and defect localization |
| Vision — accelerator option | HailoRT on Hailo NPU / AI HAT+ or AI HAT+ 2 | Committee-listed alternative; not implemented in the current source checkout |
| Advisory | Llama through ExecuTorch on Raspberry Pi 5 ARM CPU | Reasoning over structured defect findings, operator recommendations and log text |

Hailo is an optional architecture path for the vision pipeline and is not part of the current code branch. The implemented path is ONNX Runtime on the Pi CPU; Hailo does not apply to the Llama advisory. ExecuTorch is the reference runtime for the Llama advisory pipeline. Vision and advisory workloads remain separate so that a slow language-model response cannot change or block the detector's raw findings.

## 3. Vision model and target defects

The primary detector interface is YOLOv8 Nano. It produces localized object detections rather than a single image-level label.

| Defect | Inspection meaning | Record location |
|---|---|---|
| Open circuit | Visible discontinuity in a conductive track | Bounding box and image-relative centre |
| Short circuit | Unintended conductive connection between separate tracks | Bounding box and image-relative centre |
| Missing hole | Expected PCB hole absent or visibly defective | Bounding box and image-relative centre |

The deployment class map used by the Raspberry Pi inference interface is:

| Class ID | Class name |
|---:|---|
| 0 | missing_hole |
| 1 | open_circuit |
| 2 | short_circuit |

The model contract includes input dimensions, color order, normalization, output tensor layout, confidence threshold, non-maximum suppression and this class mapping. The same contract must be applied to the checkpoint, exported model and edge decoder.

## 4. Structured defect record

Each inspection event contains a board ID, timestamp, source, model identity, inference latency and an array of detections. Each detection carries:

- **Type:** one of the configured defect classes.
- **Severity:** a separate field with values `LOW`, `MEDIUM`, `HIGH` or `UNASSESSED`.
- **Location:** image-coordinate bounding box and normalized centre.
- **Confidence:** the detector's score for that prediction.

Severity is not calculated from detector confidence. It depends on defect type, physical size and board location. Where a board-specific impact rule or functional-zone map has not assigned a severity, the record retains `UNASSESSED` for operator review instead of inventing a risk value.

The JSON contract is in [`schemas/inspection-event.schema.json`](schemas/inspection-event.schema.json), with a representative event in [`schemas/example-event.json`](schemas/example-event.json).

## 5. Llama advisory pipeline

The selection architecture requires a Llama-family advisory model running locally through ExecuTorch. A pretrained Llama 3.2 Instruct 1B or 3B model is the intended model family; fine-tuning is not a prerequisite for the structured advisory workflow.

The advisory receives only the defect record fields: type, severity, location, confidence and board context. It produces:

- A concise explanation of the reported finding.
- Suggested operator verification or corrective actions.
- A structured inspection log entry.

The Llama model does not inspect the PCB image, detect or classify defects, change model confidence, add or suppress detections, or independently determine a PASS/REJECT result. The vision pipeline remains the source of visual evidence.

The complete local software sequence is coordinated by [`raspberry_pi/run_inspection.py`](raspberry_pi/run_inspection.py), which invokes vision, calls [`llm_advisory/run_executorch.py`](llm_advisory/run_executorch.py) with text-only findings, appends advisory telemetry and then optionally synchronizes the completed record. The structured prompt is built by [`llm_advisory/prompt.py`](llm_advisory/prompt.py). The ExecuTorch `.pte` model and matching tokenizer binary are separate deployment assets and are not included in this source checkout.

## 6. Operator interface and data layer

The operator interface presents the inspection result, class and severity fields, bounding-box location, confidence, advisory response and inspection history. The dashboard source is in [`dashboard/index.html`](dashboard/index.html).

Firebase Realtime Database provides data synchronization rather than model inference:

- `/live` — latest station and inspection state.
- `/inspections/{record_id}` — retained inspection events.

Image preprocessing, vision inference and the Llama advisory runtime are designed to run on the Raspberry Pi. Cloud inference is not part of the system architecture.

## 7. Datasets and evaluation

The dataset choices in the committee material include MVTec AD, NEU Surface Defect and KolektorSDD as starter industrial-anomaly or surface-defect references. These datasets are not interchangeable with the three PCB target classes: NEU concerns steel surface defects and KolektorSDD concerns electrical commutators. PCB-specific sources such as DeepPCB and Tiny-Defect-Detection-for-PCB, together with project camera captures, are relevant to the PCB defect task. A dataset is only reported as used when it is traceable to the final training configuration.

The evaluation framework covers:

| Evaluation area | Measurements and evidence |
|---|---|
| Detection quality | Per-class precision, recall, F1, confusion matrix, false alarms and missed defects |
| On-device vision | FPS, per-image latency, end-to-end latency, memory and power |
| Advisory runtime | Time to first token, tokens per second, total response time and peak memory |
| Advice quality | Relevance to class, severity and location; grounded actions; no invented detections |
| Operator experience | Clarity of alerts, ease of review, readable history and traceable log entries |
| Runtime separation | Independent vision and advisory execution, including CPU-only and optional Hailo vision paths |

No benchmark figure is included unless it is tied to the exact dataset split, checkpoint, runtime and target hardware that produced it. The source repository does not currently include the final trained three-class detector binary, a complete dataset archive, the ExecuTorch model/tokenizer assets or validated Raspberry Pi 5 benchmark results.

## 8. Repository contents

| Path | Purpose |
|---|---|
| `raspberry_pi/` | IR-triggered station controller, integrated vision/advisory orchestrator, ONNX image/camera inference and Firebase publisher |
| `dashboard/` | Operator dashboard source |
| `llm_advisory/` | Structured prompt builder and text-only ExecuTorch runner |
| `schemas/` | Inspection-event JSON schema and example |
| `models/` | Class map and model release metadata |
| `datasets/` | Dataset provenance and source manifest |
| `pcb_engine_kit/` | Annotation conversion, YOLO train/export utilities, and queued-image worker |
| `training/` | Example dataset configuration |
| `tests/` | Advisory-boundary and software contract tests |
| `firebase/` | Example Realtime Database security rules |
| `docs/` | Project report, Raspberry Pi deployment design, system architecture and implementation record |
| `demo_video/` | Demonstration scope for the physical inspection station and operator workflow |

## 9. Demonstration

The project demonstration covers the physical conveyor inspection station, PCB arrival detection through the IR sensor, external LED-strip illumination, camera acquisition, visual inspection output and operator-facing result workflow. The demonstration video is a separate submission media asset; the video file itself is not present in this source checkout.

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
