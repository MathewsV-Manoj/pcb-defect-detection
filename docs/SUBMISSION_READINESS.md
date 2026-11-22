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
| Demo video | Original MP4 present at [`demo_video/`](../demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4) | Sampled review shows a simulated inspection-result overlay; this is not live detector evidence; team reports separate official upload |
| Team/registration eligibility | Names are listed in README | Registration, nomination and mentor evidence not established by repo |

## Model and dataset ownership controls

The previous default PCB model download path has been removed. The current provisioner does not fetch an external PCB detector. The current training CLI rejects .pt initial weights and starts from a YOLO architecture YAML with pretrained=False. Validation, export, inference and Pi provisioning require metadata that declares project training and matches the checkpoint/model hashes.

This code-level rule does not prove who executed the training run. The team must confirm it actually ran the documented workflow and disclose any code written with assistance, adapted from examples or supplied by third parties. Ultralytics, PyTorch, OpenCV, ONNX Runtime, ExecuTorch and Llama remain third-party components. They are not represented as team inventions.

## Accuracy reporting

No verified accuracy result is included in this repository. Screenshot-derived figures were excluded because the checkpoint, dataset, split and raw evaluator output could not be identified. The current held-out test record remains `NOT_PROVIDED`; do not attribute accuracy values to this project without a reproducible test result bound to the exact checkpoint and audited dataset.

The separately supplied `PCB_ENGINE_KIT(2).zip` was inspected. Its auxiliary ResAttention U-Net is a five-input, one-output trace-mask model, not the three-class RGB fault detector. It is not used as the PCB fault detector and no accuracy is attributed to it. See `docs/results/supplied_model_package_audit.json`.

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
| Demo video | Repository MP4 present; sampled review identifies simulated UI output rather than live inference; team reports separate official upload |
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

The current repository contains the application and dashboard source, dataset/training/audit utilities, ONNX inference path, Llama/ExecuTorch integration source, Raspberry Pi deployment scripts and technical report. The uploaded package's auxiliary trace-mask checkpoint is recorded separately and is not treated as the primary defect detector. The repository does not include accuracy figures because no checkpoint/dataset-bound evaluation result is available; the original demo MP4 is present in the repository, and the team reports a separate official upload; the individual-contribution/AI-assistance declaration is also reported submitted/available separately. Their external receipt/copy is not archived here.

The current repository does **not** prove a primary three-class project-trained detector, completed dataset audit, independent test accuracy, target-Pi runtime or offline operation. The team reports that physical build/tests are complete, but the corresponding evidence is not yet in the repository. Do not claim independently verified results until the matching records are added.
