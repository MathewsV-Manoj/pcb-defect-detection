# Phase 1 deliverables and evaluation

This checklist is specific to the Bharat AI-SoC Challenge 2026–27, Problem Statement 5: Real-time industrial defect detection and quality-control assistant. The official Phase 1 deadline is **23 November 2026**. The official deliverables are source code, application, demonstration video and technical report.

## Phase 1 deliverables

| Required deliverable | Repository evidence | Status |
|---|---|---|
| Source code | Raspberry Pi controller, OpenCV/ONNX inference, ExecuTorch runner source, dashboard, schemas, dataset and training utilities | Source is present; trained/runtime model assets are not |
| Application | Pi-hosted operator page and local inspection API | Source is present; final end-to-end target-device validation is outstanding |
| Demonstration video | `demo_video/pcb-inspection-demo.mp4` | File is present; confirm the clip shows the real live sequence and final result |
| Technical report | `docs/PROJECT_REPORT.md` | Present; add final measured results and actual model/runtime identities after testing |

## Required technology check

| Challenge requirement | Project implementation | Status |
|---|---|---|
| Llama-family reasoning/advisory model | Text-only structured advisory prompt and ExecuTorch runner source | Not complete: `.pte` model and matching tokenizer are absent |
| ExecuTorch on-device runtime | `llm_advisory/run_executorch.py` uses `TextLLMRunner` | Not complete: runtime/model/tokenizer have not been verified on the Pi |
| Arm-based edge platform | Raspberry Pi 5 CPU deployment path | Described in source; target-device commissioning is not recorded |
| Industrial defect detection and operator guidance | Three-class YOLO detector source, inspection event and operator advisory interface | Model artifacts, severity policy and end-to-end validation remain outstanding |

A Raspberry Pi 5 CPU-only configuration is an accepted platform for PS5. Hailo hardware is not required for this project and is not part of the implemented station path.

## Defect model evaluation

Use a held-out test set of PCB boards or board/capture groups. Images from the same physical PCB or capture session must not be split between training and test data.

Record at minimum:

- per-class precision, recall and F1;
- confusion matrix and precision-recall curves;
- mAP@50 and mAP@50–95;
- false positives on good boards and missed target defects;
- visual examples of correct detections, false positives and false negatives;
- the exact checkpoint hash, dataset split, image size and confidence/NMS thresholds.

Do not use training images as evidence of generalization. Do not map an upstream dataset label to a target class without checking what the source annotation actually represents.

## Severity and decision wording

The current event uses `UNASSESSED` for severity. Do not replace this with LOW/MEDIUM/HIGH until a board-specific rule based on defect type, physical extent and board function has been defined and checked. Detector confidence is not severity.

The dashboard must describe an empty detection list as “No configured target defect detected in this frame”. It must not call the board “defect-free”.

## Raspberry Pi commissioning

Run the checks on the actual Raspberry Pi 5 with the final model assets installed:

1. Confirm the GPIO pins and sensor/driver polarity against the physical wiring.
2. Confirm the three-second initial arming sequence and armed state after release.
3. Confirm the next IR activation starts one capture cycle.
4. Confirm the LED driver is enabled for capture and switched off afterward.
5. Confirm the current captured frame appears in the browser.
6. Confirm the operator run button starts inference on the Pi.
7. Confirm the event JSON and annotated image are written.
8. Confirm the ExecuTorch advisory returns valid structured output.
9. Confirm the next PCB is captured without repeating the arming sequence.
10. Repeat the cycle and record attempts, successful runs, missed triggers, duplicate triggers and failures.

Use `docs/PI5_COMMISSIONING.md` to record actual pins, environment versions and results.

## Performance and reproducibility

Measure on the Raspberry Pi, not on the training workstation:

- detector preprocessing, inference and post-processing latency;
- p50 and p95 latency and sequential FPS;
- peak RAM and CPU temperature;
- complete capture-to-dashboard-result time;
- Llama time to first token, generation speed, total response time and peak RAM;
- power only if measured with an appropriate external meter.

For every figure, record the Pi model/RAM, OS, Python, OpenCV, ONNX Runtime and ExecuTorch versions, model/tokenizer hashes, dataset split, image size, thresholds, sample count and measurement method.

## Eligibility and submission-form checks

The official challenge page states that teams may have 1–3 members; student teams must be from the same college, have a faculty mentor and be nominated by their college. The Team Leader submits the registration. The public repository cannot confirm nomination, team registration or the submitted form details. Verify those against the team's registration record before submitting.

## Current assessment

The source-code and documentation deliverables are present. A demonstration MP4 is committed. The project is **not yet submission-complete** because the required Llama/ExecuTorch model package is missing, the trained YOLO release artifacts and measured test evidence are absent, severity remains unassessed, and Raspberry Pi commissioning is not recorded. Do not mark these items complete without evidence.
