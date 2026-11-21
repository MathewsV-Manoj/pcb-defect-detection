# Deliverables and evaluation framework

## Submission deliverables

| Deliverable | Project evidence |
|---|---|
| Source code | IR station controller, vision inference, inspection coordinator, ExecuTorch advisory runner, operator dashboard, event schema and automated contract tests |
| Application | Built conveyor inspection station with IR arrival sensing, external LED illumination, camera capture and Raspberry Pi 5 edge software |
| Demonstration video | Physical station operation, image acquisition, visual findings, advisory output, operator alert and inspection logging |
| Technical report | Physical design, end-to-end flow, separate runtime pipelines, data contract, dataset strategy and evaluation methodology |

## System acceptance sequence

| Stage | Expected evidence |
|---|---|
| Board arrival | IR input changes state when a PCB reaches the inspection point |
| Illumination | External LED strip is switched through its driver before image capture |
| Image acquisition | Camera frame is saved or passed to the vision pipeline |
| Vision inference | Defect class, confidence and image location are generated |
| Severity | Severity is assigned from defect type, size and board location; confidence remains a separate measure |
| Advisory | Llama through ExecuTorch receives structured findings and returns an explanation, verification actions and log text |
| Operator interface | Alert, advisory and event history are visible |
| Local operation | Vision, advisory and event logging operate on the Pi without cloud inference |
| Record synchronization | Firebase receives completed events when synchronization is enabled |

## Runtime profiles

| Workload | Base profile | Optional profile |
|---|---|---|
| Vision | YOLOv8 Nano through ONNX Runtime on Pi 5 ARM CPU | HailoRT on Hailo NPU with AI HAT+ / AI HAT+ 2 |
| Advisory | Llama 3.2 Instruct 1B/3B through ExecuTorch on Pi 5 ARM CPU | No alternative runtime replaces ExecuTorch in the submission architecture |

The CPU-only Pi 5 path is the base deployment. Hailo is a vision accelerator option only. The advisory remains a separate ExecuTorch process on the ARM CPU. The platform guidance identifies 8 GB RAM as providing more headroom for the combined workloads; 4 GB requires careful peak-memory measurement.

## Detection quality

| Metric | Definition / evidence |
|---|---|
| Per-class precision | Correct predictions among predicted instances for each defect class |
| Per-class recall | Detected ground-truth instances among annotated instances |
| Per-class F1 | Harmonic mean of precision and recall |
| Confusion matrix | Class-wise correct and incorrect assignments |
| False positives | Normal regions incorrectly reported as defects |
| False negatives | Annotated defects missed by the detector |
| Localization review | Bounding-box alignment and localization quality on small defects |
| mAP@50 and mAP@50–95 | Detection performance at the stated IoU evaluation criteria |

Evaluation is reported on a held-out board-level test split. Images from the same physical PCB or capture group remain within the same split to reduce leakage. Representative normal boards, all target classes, multiple defect sizes and station capture conditions are included.

## Vision runtime measurements

| Metric | Measurement |
|---|---|
| Per-image inference latency | Model execution time for one input frame |
| End-to-end latency | IR trigger to completed inspection record |
| FPS / throughput | Sustained images processed per second |
| Peak RAM | Process and device memory footprint |
| Power | Device power during idle and active inspection |
| Thermal behaviour | CPU temperature during sustained runs |
| Reliability | Successful cycles, trigger misses and processing failures |

## Advisory runtime measurements

| Metric | Measurement |
|---|---|
| Time to first token | Delay from generation start to first output token |
| Tokens per second | Generation throughput |
| Total response time | Complete advisory generation duration |
| Peak memory | ExecuTorch process and device memory |
| Output validity | JSON structure and presence of required fields |
| Grounding | Advice consistency with defect class, severity and location |
| Safety boundary | No image interpretation, new detections or independent PASS/REJECT decision |

## Operator experience

Operator-facing evaluation covers clear defect alerts, visible IR and illumination state, readable advisory text, event identity, history retrieval and CSV export. The inspection log preserves the detector findings separately from Llama-generated advisory text.

## Runtime and dataset reproducibility

Each published measurement is tied to the following metadata:

- Raspberry Pi model and RAM configuration.
- Operating system and runtime versions.
- Vision model hash and class map.
- Llama `.pte` model and tokenizer identity.
- Dataset source, version, annotation mapping and held-out split.
- Image resolution, confidence threshold and NMS IoU.
- Number of boards, images and repeated timing runs.

The current public repository contains software source and test contracts. The trained detector binary, ExecuTorch model/tokenizer package, complete processed dataset and validated Raspberry Pi performance report are not packaged in the public source release. Accordingly, no numeric accuracy or device-performance results are stated in this document.

## Automated software verification

GitHub Actions checks Python compilation and runs the source-level contract tests. The tests cover class-order consistency, event-schema fields, text-only advisory input, station-controller linkage, architecture SVG validity and dashboard interface contracts. These software tests are distinct from physical-system commissioning and on-device performance evaluation.
