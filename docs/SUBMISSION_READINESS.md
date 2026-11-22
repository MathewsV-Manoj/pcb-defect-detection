# Submission readiness — PCB inspection project

**Challenge:** Bharat AI-SoC Challenge 2026–27  
**Problem statement:** PS5 — Real-time industrial defect detection and quality-control assistant  
**Phase 1 deadline recorded in the project:** 23 November 2026  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection

This document distinguishes source code from tested deliverables. It is not a claim that the physical system, trained detector or final submission has passed evaluation.

## Repository state

| Item | Evidence in current checkout | Status |
|---|---|---|
| Application source | Raspberry Pi controller, local HTTP API, dashboard, event schema, local record logic | Source present |
| Dataset importer | Manifest-driven importer with group split and per-file hash records | Source present; no actual dataset/import manifest |
| Dataset provenance audit | Portable dataset audit tool and current NOT_PROVIDED report | Tool present; audit incomplete |
| Project detector training | YAML-based random-initialization workflow with pretrained=False | Source present; no checkpoint |
| Checkpoint provenance | Sidecar writer and release auditor | Tool present; current checkpoint NOT_PROVIDED |
| ONNX export | Exporter binds model hash to checkpoint and dataset provenance hashes | Source present; no export |
| Detector validation | Held-out test report writer | Source present; no reproduced result |
| Advisory | Llama 3.2 1B Instruct + ExecuTorch integration source | Third-party model; weights/runtime not stored or target-tested |
| Dashboard | Browser operator interface | Source present; no target-device integration evidence |
| Pi controller | IR/camera/LED source | Team reports physical build/tests complete; commissioning evidence not yet committed |
| Demo video | Team reports uploaded separately; no MP4 stored in repository | Keep/check the official submission link or receipt in team records |
| Team/registration eligibility | Names are listed in README | Registration, nomination and mentor evidence not established by repo |

## Model and dataset ownership controls

The previous default PCB model download path has been removed. The current provisioner does not fetch an external PCB detector. The current training CLI rejects .pt initial weights and starts from a YOLO architecture YAML with pretrained=False. Validation, export, inference and Pi provisioning require metadata that declares project training and matches the checkpoint/model hashes.

This code-level rule does not prove who executed the training run. The team must confirm it actually ran the documented workflow and disclose any code written with assistance, adapted from examples or supplied by third parties. Ultralytics, PyTorch, OpenCV, ONNX Runtime, ExecuTorch and Llama remain third-party components. They are not represented as team inventions.

## Project metrics

A team-supplied screenshot reports validation precision 98.3%, recall 98.4%, mAP@0.50 98.9% and mAP@0.50:0.95 62.5%, with per-class values transcribed in docs/results/PROJECT_VALIDATION_RESULTS.md. The newly supplied `PCB_ENGINE_KIT(2).zip` was also inspected: it contains a five-input, one-output ResAttention U-Net trace-mask checkpoint, not the three-class fault detector. Its archive checksum matches, but the archive contains no training dataset, provenance, training log or evaluation metrics for that checkpoint. It must not be used to identify or validate the screenshot metrics. See docs/results/supplied_model_package_audit.json.

The screenshot does not identify the checkpoint, dataset version, validation sample count or raw evaluator output. The values have not been independently reproduced and must not be called held-out test accuracy or Pi performance. No numerical results from other PCB models, papers, hardware benchmarks or Llama deployments are retained as project results.

## Blocking evidence

| Missing evidence | Required action |
|---|---|
| Actual project dataset | Add the real images/labels and complete the import manifest |
| Dataset source/rights/annotation review | Record actual source, terms, team rights review and human label review |
| Group-safe split | Keep all views/crops of each board/design/capture group within one split |
| Dataset audit | Run dataset importer and release auditor; inspect all class coverage and hashes |
| Project checkpoint | Train from the architecture YAML with pretrained=False |
| Checkpoint provenance | Preserve project_training_provenance.json and exact best.pt SHA-256 |
| Held-out test | Evaluate the reserved test groups and archive per-class and overall outputs |
| ONNX validation | Run `pcb_engine_kit/compare_pt_onnx.py` over the full held-out test split and retain `project_onnx_parity.json` |
| Pi deployment | Copy project ONNX and sidecar, provision target, retain runtime smoke test |
| Physical station | Team reports physical build/tests complete; add the actual BCM pin map, sensor polarity, camera/LED details, repeated-cycle counts and existing test records to docs/results/physical_station_commissioning.json |
| Offline run | Complete a real inspection with WAN disconnected and local LAN maintained |
| Severity approval | Obtain QA/engineering approval or retain explicit provisional wording |
| Demo video | No MP4 retained in this repository; provide and review a separate final video link only if the challenge requires a demo |
| Eligibility | Confirm registration, team membership, college nomination and mentor from the original registration record |

## Audit commands

After the real dataset and checkpoint are available:

```bash
python pcb_engine_kit/dataset.py datasets/import_manifest.csv datasets/processed/pcb3
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

The reports are:
- docs/results/project_dataset_audit.json
- docs/results/project_checkpoint_audit.json
- docs/results/project_release_audit.json

Current reports deliberately say NOT_PROVIDED. Do not edit them to pass; regenerate them from actual files.

## Submission wording that is supportable now

The current repository contains the application and dashboard source, dataset/training/audit utilities, ONNX inference path, Llama/ExecuTorch integration source, Raspberry Pi deployment scripts and technical report. The uploaded package's auxiliary trace-mask checkpoint is recorded separately and is not treated as the primary defect detector. The repository retains screenshot-reported validation values with an explicit provenance limitation; the team reports that the demo video and individual-contribution/AI-assistance declaration have been submitted/are available separately. Their external receipt/copy is not archived here.

The current repository does **not** prove a primary three-class project-trained detector, completed dataset audit, independent test accuracy, target-Pi runtime or offline operation. The team reports that physical build/tests are complete, but the corresponding evidence is not yet in the repository. Do not claim independently verified results until the matching records are added.
