# PCB Automated Optical Inspection
## Technical project report

**Conveyor-based inspection · Raspberry Pi 5 · Edge vision · Llama advisory · Operator interface**

## Executive summary

This project integrates a built conveyor-based PCB inspection station with an edge-computing inspection workflow. The physical station combines PCB transport, an IR presence sensor, a camera and an externally powered LED illumination strip. When a PCB reaches the inspection point, the IR sensor triggers the capture sequence. The LED driver illuminates the board, the camera acquires a frame, and the Raspberry Pi 5 processing pipeline performs image preprocessing and defect localization.

The vision system targets three PCB defect classes: open circuit, short circuit and missing hole. The vision model produces structured findings containing defect type, severity, location and confidence. A separate Llama-family advisory pipeline runs through ExecuTorch on the Raspberry Pi ARM CPU. It receives structured findings only, explains the reported defects, recommends operator verification actions and generates an inspection log entry. The operator interface presents the inspection result, advisory and retained history.

## 1. Physical inspection station

The built station consists of the conveyor assembly, IR presence sensor, inspection camera, external LED strip and Raspberry Pi 5 edge controller.

| Hardware element | Function |
|---|---|
| Conveyor assembly | Moves the PCB into the inspection zone |
| IR presence sensor | Detects board arrival and provides the inspection trigger |
| External LED strip | Illuminates the board during image acquisition |
| LED driver stage | Switches the separately powered illumination strip |
| Camera | Captures the illuminated PCB frame |
| Raspberry Pi 5 | Coordinates the trigger-driven capture and local processing workflow |

The station controller reads the IR sensor using a configurable GPIO input and switches the external LED driver through a separate GPIO output. The illumination strip uses its own supply and driver; the Pi GPIO is a logic-level control signal. The conveyor provides board transport, while conveyor motor drive and emergency-stop circuitry remain separate from the camera-trigger controller.

## 2. Reference architecture

![PCB inspection system architecture](inspection_workflow.svg)

### End-to-end operating sequence

1. The conveyor carries a PCB towards the inspection zone.
2. The IR sensor detects the board and triggers an inspection cycle.
3. The external LED strip illuminates the PCB through its driver.
4. The station controller waits for the configured illumination-settle interval.
5. The camera captures one frame from the selected USB/UVC or CSI camera.
6. OpenCV validates and preprocesses the image.
7. YOLOv8 Nano detects and localizes the configured defect classes.
8. The application saves an annotated image and structured JSON inspection event.
9. The coordinator supplies the structured defect record to the Llama/ExecuTorch advisory pipeline.
10. The advisory text and runtime telemetry are appended to the event.
11. The completed record is retained locally and can be synchronized to Firebase Realtime Database.
12. The operator interface displays the result, advisory and inspection history.

### Separate inference pipelines

| Vision pipeline | Advisory pipeline |
|---|---|
| YOLOv8 Nano | Llama 3.2 Instruct 1B or 3B |
| OpenCV preprocessing | Structured text prompt |
| ONNX Runtime on Raspberry Pi 5 ARM CPU | ExecuTorch on Raspberry Pi 5 ARM CPU |
| Optional HailoRT on Hailo NPU / AI HAT+ / AI HAT+ 2 for vision acceleration | Mandatory on-device advisory runtime |
| Predicts defect class and location | Explains findings, recommends verification actions and generates log text |

The implemented vision path uses ONNX Runtime with CPU execution on the Raspberry Pi 5. HailoRT with a Hailo NPU is an optional vision-acceleration architecture; it does not execute the Llama advisory. The Llama advisory remains a separate ExecuTorch process on the Pi ARM CPU. A CPU-only Pi 5 is the base platform; 8 GB RAM provides more memory headroom for concurrent vision and advisory processing than a 4 GB configuration.

## 3. Vision detection and target defects

The selected vision model interface is YOLOv8 Nano. It returns localized predictions, including class scores and image-relative bounding boxes.

| Class ID | Defect class | Inspection meaning |
|---:|---|---|
| 0 | `missing_hole` | An expected PCB hole is absent or visibly defective |
| 1 | `open_circuit` | A conductive track has a visible discontinuity |
| 2 | `short_circuit` | Separate conductive paths are unintentionally bridged |

The deployment model contract defines input dimensions, RGB ordering, normalization, output tensor layout, confidence filtering, non-maximum suppression and class order. The class map is shared by the Raspberry Pi detector, dataset preparation utilities, exporter and supplementary TFLite worker.

## 4. Structured defect record and severity

Each inspection event records a unique record ID, board ID, timestamp, input source, model identity, inference latency, station state and an array of detector findings.

Each finding contains:

| Field | Meaning |
|---|---|
| Type | One of the three configured PCB defect classes |
| Severity | LOW, MEDIUM, HIGH or UNASSESSED |
| Location | Bounding box and normalized centre coordinates |
| Confidence | Detector confidence score |

Severity and confidence are separate measures. Confidence expresses the model's prediction score; severity represents the likely engineering impact of a defect. Severity is assigned from defect type, physical extent and board location. The current inference implementation records UNASSESSED where no board-specific impact profile has assigned a severity.

The current application decision states are REVIEW when configured target detections are present and NO_TARGET_DEFECT_DETECTED when no configured target is detected. The latter is not an unconditional declaration that a board is defect-free. The Llama advisory does not independently create a PASS/REJECT decision.

The event format is defined by `schemas/inspection-event.schema.json`, with an illustrative record in `schemas/example-event.json`.

## 5. Mandatory Llama advisory and ExecuTorch runtime

The advisory pipeline is a required component of the complete system. The reference model family is Llama 3.2 Instruct 1B or 3B, deployed locally through ExecuTorch on the Raspberry Pi ARM CPU. A pretrained Instruct model with structured prompting is sufficient for the advisory workflow; fine-tuning is not required.

The advisory receives defect type, severity, location, confidence, board identity and timestamp. The output contains:

- A concise explanation of the reported findings.
- Recommended operator verification actions.
- A severity note, including a human-review statement when severity is UNASSESSED.
- A structured inspection log entry.

The Llama pipeline is text-only. It does not receive the original PCB image or camera frame. It cannot add, remove, relabel or suppress detections, infer severity from confidence, or replace the independent decision policy.

The source integration comprises:

| Source | Function |
|---|---|
| `llm_advisory/prompt.py` | Builds a text-only prompt from structured findings |
| `llm_advisory/run_executorch.py` | Runs the ExecuTorch LLM Runner and captures response telemetry |
| `raspberry_pi/run_inspection.py` | Coordinates vision, advisory, local event update and optional Firebase synchronization |
| `raspberry_pi/station_controller.py` | Handles IR-triggered board arrival, LED driver control and launch of the complete inspection coordinator |

The ExecuTorch `.pte` model package and matching tokenizer are separate deployment assets. The repository contains the runner and orchestration source; the model and tokenizer files are not part of the public source release. The ExecuTorch LLM Runner Python bindings are build-dependent and are required by the advisory entry point.

## 6. Operator interface and inspection data

The operator interface is implemented in `dashboard/index.html`. It presents the latest result, board ID, camera and conveyor state, IR sensor state, LED illumination state, defect type, severity, location, confidence, Llama advisory and inspection history.

The inspection event is stored locally as JSON. Firebase Realtime Database provides optional record synchronization:

- `/live` — latest station and inspection state.
- `/inspections/{record_id}` — retained inspection events.

Firebase does not run image inference or the Llama model. The vision and advisory runtimes are local to the Raspberry Pi. The operator dashboard is a presentation layer for the event data.

## 7. Technology stack and execution profiles

| Layer | Technology |
|---|---|
| Physical inspection | Conveyor, IR presence sensor, camera and external LED strip |
| Edge device | Raspberry Pi 5 (ARM64) |
| Image preprocessing | OpenCV |
| Vision model | YOLOv8 Nano |
| Base vision runtime | ONNX Runtime CPU |
| Optional vision accelerator | Hailo NPU with HailoRT and AI HAT+ / AI HAT+ 2 |
| Advisory model | Llama 3.2 Instruct 1B or 3B |
| Advisory runtime | ExecuTorch on Pi ARM CPU |
| Operator interface | HTML, CSS and JavaScript |
| Local event record | JSON |
| Optional event synchronization | Firebase Realtime Database |

The vision pipeline may use the Pi CPU or an optional Hailo NPU. The advisory pipeline uses ExecuTorch on the Pi ARM CPU in either case. The two runtimes are documented and measured independently.

## 8. Dataset strategy

PCB-specific data references include DeepPCB, Tiny-Defect-Detection-for-PCB and project camera captures. General industrial reference datasets include MVTec AD, NEU Surface Defect and KolektorSDD.

| Dataset | Domain | Use in project context |
|---|---|---|
| DeepPCB | PCB defects | PCB-specific defect annotations |
| Tiny-Defect-Detection-for-PCB | PCB defects | PCB-specific small-defect reference |
| Project camera captures | Built inspection station | Board appearance and station-specific capture conditions |
| MVTec AD | General industrial anomaly detection | Anomaly-detection methodology reference |
| NEU Surface Defect | Steel surface defects | General surface-defect reference, not PCB labels |
| KolektorSDD | Electrical commutators | General industrial defect reference, not PCB labels |

Dataset provenance is maintained in `datasets/SOURCE_MANIFEST.csv`. The manifest distinguishes candidate references from dataset sources associated with a recorded training run. The full processed training archive is not included in the public source release.

## 9. Evaluation methodology

The evaluation framework follows the detection, performance, advisory, user-experience and integration dimensions.

| Evaluation dimension | Measurements |
|---|---|
| Detection quality | Per-class precision, recall, F1, confusion matrix, false-positive rate, missed defects and localization review |
| Real-time vision | FPS, per-image latency, end-to-end latency, peak memory and power on Raspberry Pi 5 |
| Llama performance | Time to first token, tokens per second, total response time and peak memory |
| Advisory quality | Grounding in class, severity and location; usefulness of verification actions; absence of unsupported findings |
| Operator experience | Alert clarity, board status, readable event history and log traceability |
| Integration | IR trigger handling, illumination timing, camera capture, vision/advisory event hand-off, local logging and Firebase synchronization |

A repeatable performance record includes the Pi 5 memory configuration, OS and runtime versions, model hash, dataset version and split, image resolution, test count and measurement procedure. Workstation GPU measurements are kept separate from Raspberry Pi 5 results. No numeric detection or device-performance result is published without the associated checkpoint, evaluation split and target-device measurement record.

## 10. Deliverables and source map

| Submission deliverable | Repository evidence |
|---|---|
| Source code | `raspberry_pi/`, `llm_advisory/`, `dashboard/`, `schemas/` and `tests/` |
| Application | Built conveyor station, IR arrival sensing, LED illumination, camera acquisition and Pi 5 integration source |
| Demonstration video | Separate video submission covering physical station operation and inspection output |
| Technical report | This report, architecture diagram, deployment record and evaluation methodology |

The GitHub Actions workflow runs the Python compile checks and software contract tests. These checks verify source-level interfaces and schema consistency; they are not substitutes for measured Raspberry Pi 5 benchmarks.

## 11. Implementation and release evidence

| Artifact | Public repository state |
|---|---|
| IR-triggered station controller | Source present |
| Vision inference and inspection coordinator | Source present |
| Llama prompt builder and ExecuTorch runner | Source present |
| Operator dashboard and event schema | Source present |
| Automated software contract tests | Source present |
| Trained three-class detector weights | Not packaged in this release |
| ExecuTorch `.pte` model and matching tokenizer | Not packaged in this release |
| Complete processed PCB training dataset | Not packaged in this release |
| Validated Raspberry Pi 5 vision and advisory benchmarks | No measurement report published in this release |
| Hailo-compiled vision model and HailoRT integration | Optional architecture; not part of the current implementation |

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
