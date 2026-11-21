# PCB Automated Optical Inspection
## Technical project report

**Edge AI · Conveyor-based inspection · Raspberry Pi 5 · On-device advisory · Operator interface**

## Executive summary

The project implements a conveyor-based PCB inspection station supported by an IR presence sensor, camera acquisition and external LED illumination. A board arriving at the inspection point is detected by the IR sensor. The camera captures the illuminated board, and the edge-processing pipeline prepares the image for visual defect detection.

The vision stage uses a YOLOv8 Nano detection interface for three PCB defect categories: open circuit, short circuit and missing hole. The output is stored as a structured inspection event containing defect type, severity, image location and confidence. An independent Llama-family advisory pipeline uses ExecuTorch on the Raspberry Pi ARM CPU to explain structured findings, recommend verification actions and create log text. The operator interface presents alerts, advisory information and inspection history.

The system architecture follows the selection committee's separation of the vision and advisory runtimes. Raspberry Pi CPU inference is the base vision path; Hailo NPU acceleration is an optional vision deployment path.

## 1. Physical inspection station

The physical system comprises a conveyor assembly, IR sensor, camera and external LED strip.

- The conveyor transports the PCB into the inspection zone.
- The IR sensor detects the presence of an arriving PCB.
- The external LED strip illuminates the board during image acquisition.
- The camera captures the board for the vision pipeline.

The Raspberry Pi station-controller source supports configurable IR input and illumination-driver output. The LED strip is powered through its external driver, not directly from a GPIO pin. Conveyor motor control remains a distinct hardware-control function.

## 2. Reference architecture

![PCB inspection system architecture](inspection_workflow.svg)

### Physical and acquisition flow

1. PCB transport into the inspection zone.
2. IR sensor detects board arrival.
3. External LED illumination is enabled for capture.
4. Camera acquires the PCB frame.
5. OpenCV preprocesses the image.
6. The vision runtime detects and localizes the configured defects.
7. A structured defect record is generated.
8. Llama/ExecuTorch creates operator guidance from the record.
9. The operator interface displays the alert, advice and log.

### Separate inference pipelines

| Vision pipeline | Advisory pipeline |
|---|---|
| Raspberry Pi 5 ARM CPU with ONNX Runtime | Raspberry Pi 5 ARM CPU with ExecuTorch |
| YOLOv8 Nano detector | Llama 3.2 Instruct family, 1B or 3B class |
| Predicts, classifies and localizes defects | Explains findings, suggests actions and writes log text |
| Optional HailoRT architecture path on Hailo NPU / AI HAT+ or AI HAT+ 2 (not implemented in the current source checkout) | Remains on the Pi ARM CPU in both CPU and Hailo vision configurations |

The current source checkout implements the Raspberry Pi CPU vision path through ONNX Runtime. HailoRT on Hailo NPU / AI HAT+ / AI HAT+ 2 is a committee-listed optional architecture path, but no Hailo-compiled detector or Hailo runtime integration is included here. It does not replace the separate Llama/ExecuTorch advisory runtime.

## 3. Vision detection

The configured classes are:

| Class ID | Defect type | Inspection meaning |
|---:|---|---|
| 0 | missing_hole | Expected PCB hole absent or visibly defective |
| 1 | open_circuit | Visible discontinuity in a conductive track |
| 2 | short_circuit | Unintended conductive bridge between separate tracks |

The model produces bounding boxes, class IDs and confidence scores. The inference application maps the boxes back to the captured image and creates an annotated result. Model input size, preprocessing, output decoding, confidence filtering and non-maximum suppression form one model contract.

## 4. Structured defect record

The inspection event contains a unique record ID, board ID, timestamp, source, model identity, inference latency and detector findings.

Each finding carries four independent fields:

| Field | Meaning |
|---|---|
| Type | Detected PCB defect class |
| Severity | LOW, MEDIUM, HIGH or UNASSESSED |
| Location | Bounding box and normalized image-relative position |
| Confidence | Vision model confidence score |

Severity is not inferred from confidence. It depends on defect type, physical extent and location within the board's functional layout. Where a board-specific severity rule has not established an impact level, the event retains UNASSESSED and requires operator review.

The machine-readable contract is stored in `schemas/inspection-event.schema.json`.

## 5. Llama advisory and ExecuTorch

The Llama advisory is a separate, on-device reasoning component. A pretrained Llama 3.2 Instruct 1B or 3B model is the intended model family, with ExecuTorch as the reference runtime on the Raspberry Pi ARM CPU. The advisory does not require fine-tuning as a prerequisite; structured prompts provide the defect context.

Its input consists of defect type, severity, location, confidence and board context. It returns a concise explanation, suggested verification or corrective actions, and an inspection log entry.

The advisory does not receive raw PCB pixels and does not detect, classify or change visual findings. It does not replace the operator or independently make a product disposition decision.

The source repository contains the structured prompt builder. The ExecuTorch model package and quantized model binary are separate deployment artifacts and are not included in this source checkout.

## 6. Operator interface and inspection log

The operator interface displays the inspection result, defect type, severity, location, confidence, Llama advisory and event history. The dashboard source is in `dashboard/index.html`.

Firebase Realtime Database synchronizes the current station state at `/live` and retained inspection events at `/inspections/{record_id}`. Firebase is a data layer only; model inference is local to the edge device.

## 7. Technology stack

| Layer | Technology |
|---|---|
| Physical inspection | Conveyor, IR presence sensor, camera, external LED strip |
| Edge computer | Raspberry Pi 5 |
| Image processing | OpenCV |
| Vision detection | YOLOv8 Nano |
| Base vision runtime | ONNX Runtime CPU |
| Optional vision acceleration | Hailo NPU, HailoRT, AI HAT+ / AI HAT+ 2 |
| Advisory model | Llama 3.2 Instruct family |
| Advisory runtime | ExecuTorch on Raspberry Pi ARM CPU |
| Operator interface | HTML, CSS and JavaScript |
| Record synchronization | Firebase Realtime Database |
| Data contract | JSON Schema |

## 8. Dataset strategy

The committee reference lists MVTec AD, NEU Surface Defect and KolektorSDD as starter anomaly/surface-defect references. These are not direct substitutes for PCB target labels: NEU is a steel-surface dataset and KolektorSDD concerns electrical commutators. PCB-specific references include DeepPCB and Tiny-Defect-Detection-for-PCB, together with project camera captures.

Dataset identity, license, class mapping and split provenance are recorded separately from model evaluation. Only sources confirmed by the exact final training configuration should be described as training data.

## 9. Evaluation framework

| Area | Evaluation evidence |
|---|---|
| Detection quality | Precision, recall, F1, per-class confusion, false alarms and missed defects |
| Real-time vision | FPS, per-image latency, end-to-end latency, memory and power on Raspberry Pi 5 |
| Llama runtime | Time to first token, tokens per second, total response time and peak memory |
| Advice quality | Relevance to the structured finding, action usefulness and grounding |
| Operator experience | Alert clarity, review flow and traceable inspection history |
| Runtime architecture | Separate CPU vision and ExecuTorch advisory pipelines; optional Hailo vision path |

No performance figures are asserted without the underlying test configuration and measurement output. The source checkout does not include the final trained three-class detector binary, a complete processed dataset archive, the ExecuTorch model binary or a validated target-device benchmark report.

## 10. Source repository

- `raspberry_pi/` — IR-triggered station controller, one-board inspection orchestration, vision inference and Firebase event publishing.
- `dashboard/` — operator interface.
- `llm_advisory/` — structured prompt builder.
- `schemas/` — event contract and example.
- `models/` — class map and release metadata.
- `datasets/` — data provenance.
- `docs/` — architecture and project records.
- `tests/` — advisory-boundary and file-handling contract tests.\n- `demo_video/` — physical system demonstration.

The demonstration video is a separate submission media asset and is not embedded in this source checkout.\n\n**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection
