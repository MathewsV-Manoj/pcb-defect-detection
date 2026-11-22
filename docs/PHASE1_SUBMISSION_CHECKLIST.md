# Phase 1 submission checklist — Bharat AI-SoC Challenge 2026–27

**Problem statement:** PS5 — Real-time industrial defect detection & quality-control assistant  
**Phase 1 deadline:** 23 November 2026  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection  
**Official challenge page:** https://armbharatchallenge.com/

The official Phase 1 deliverables are source code, application, demonstration video and technical report. PS5 also specifies Llama and ExecuTorch as required technologies, with the Llama advisory/reasoning component deployed on an Arm-based device. Raspberry Pi 5 CPU-only is an eligible platform.

## Submission links

| Deliverable | Repository location | Status |
|---|---|---|
| Source code | [GitHub repository](https://github.com/MathewsV-Manoj/pcb-defect-detection) | Published |
| Application | Raspberry Pi 5 station controller and local dashboard in `raspberry_pi/` and `dashboard/` | Source published; target hardware validation not evidenced in this repository |
| Demonstration video | [pcb-inspection-demo.mp4](https://github.com/MathewsV-Manoj/pcb-defect-detection/blob/main/demo_video/pcb-inspection-demo.mp4) | 23.68 MB file present; team confirms it is complete; content has not been independently reviewed in this audit |
| Technical report | [PROJECT_REPORT.md](PROJECT_REPORT.md) | Published; includes the supplied validation metrics and limits |

## Project validation metrics supplied by the team

| Metric | Validation result |
|---|---:|
| Precision | 98.3% |
| Recall | 98.4% |
| mAP@0.50 | 98.9% |
| mAP@0.50:0.95 | 62.5% |

| Defect class | Precision | Recall | mAP@0.50 |
|---|---:|---:|---:|
| Missing Hole | 97.8% | 98.2% | 98.5% |
| Open Circuit | 99.1% | 99.6% | 99.5% |
| Short Circuit | 97.9% | 97.6% | 98.8% |

These are screenshot-reported **validation** metrics only. They are not held-out test results, Pi 5 runtime measurements, or the upstream publisher's results. The supplied screenshot is archived at [results/project-validation-screenshot.png](results/project-validation-screenshot.png), with its source filename and original SHA-256 recorded in [results/PROJECT_VALIDATION_RESULTS.md](results/PROJECT_VALIDATION_RESULTS.md). The underlying checkpoint, dataset/split and raw evaluator output remain to be archived.

## Final checks before submitting

- [ ] Confirm that the Team Leader completed registration by 19 October 2026. The challenge registration is now closed; the public page does not allow a new registration at this stage.
- [ ] Confirm student eligibility, same-college membership, college nomination and the required Faculty Mentor from the original registration record.
- [ ] Confirm the exact YOLO checkpoint that produced the reported validation screenshot. Add its identity and SHA-256 to the release record; the current Git source does not contain `best.pt` or `best.onnx`.
- [ ] Preserve the dataset source terms, actual import manifest, board/capture-group split audit and validation log. The example CSV is only a template.
- [ ] Evaluate a separate held-out board-level test set if it already exists. If it does not, report test performance as not measured; do not reuse validation data as test data.
- [ ] On the actual Raspberry Pi 5, run `bash scripts/provision_pi5.sh`, configure the real GPIO pins/polarities, and retain the ONNX + ExecuTorch smoke-test JSON.
- [ ] Verify a complete physical inspection cycle, including IR trigger, LED-driver timing, camera capture, local YOLO inference and the Llama advisory through ExecuTorch on the Pi.
- [ ] Demonstrate offline operation with WAN disconnected while the Pi and operator laptop remain on the same private LAN.
- [ ] Review the MP4 against `demo_video/README.md` and confirm that the required live hardware/model sequence is visible.
- [ ] Obtain QA/engineering approval for the provisional severity policy, or explicitly state that it is a prototype screening rule awaiting approval.
- [ ] Check third-party model/dataset rights and the challenge's **Original work** requirement (original-work / sole-ownership rule) and Participant Materials rules. The current Pi provisioner downloads a separately authored six-class YOLOv8s checkpoint whose model card declares MIT; the model's attribution and licence do not by themselves verify the dataset's terms or settle the organisers' interpretation of the originality requirement. Ask the organisers for written clarification if this checkpoint is part of the final entry.

## Technical claims that are safe to make now

- The repository contains the Raspberry Pi station source, browser dashboard, YOLO/ONNX inference path, Llama/ExecuTorch integration source, provisioner, technical report, benchmark scripts and a demonstration MP4.
- The supplied screenshot reports the validation metrics tabulated above.
- Published PCB-paper metrics are included only as external literature references.
- The Pi deployment recipe is present, but this repository does not contain target-Pi smoke-test evidence, a completed commissioning sheet, offline test evidence or Pi runtime measurements.
- No independent held-out test score is currently archived.

Do not state that the final Pi hardware cycle, live ExecuTorch execution, offline operation, severity approval, or independent test evaluation has passed until its evidence has been captured and committed.
