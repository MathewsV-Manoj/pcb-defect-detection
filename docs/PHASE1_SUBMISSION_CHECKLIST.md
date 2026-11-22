# Phase 1 submission checklist — Bharat AI-SoC Challenge 2026–27

**Problem statement:** PS5 — Real-time industrial defect detection and quality-control assistant  
**Phase 1 deadline recorded by the team:** 23 November 2026  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection

This checklist records what is visible in the repository. A file existing is not proof that a feature has passed on the target hardware.

## Deliverables

| Deliverable | Location | Status |
|---|---|---|
| Source code | Repository root, raspberry_pi/, dashboard/, pcb_engine_kit/, llm_advisory/ | Published |
| Application | Pi-targeted station API and browser dashboard | Source published; team reports physical build/tests complete; live project-model execution on target is not evidenced in this repository |
| Demonstration video | [Original MP4 in `demo_video/`](../demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4) | Team reports separate official upload; sampled review shows the on-screen result is explicitly simulated, not live detector output |
| Technical report | docs/PROJECT_REPORT.md | Published; no independently reproduced test/performance results |

## Accuracy reporting

No verified accuracy metrics are included in this repository. Screenshot-derived values were excluded because the exact checkpoint, dataset version, test/validation split and raw evaluator output could not be established. The current held-out test report remains `NOT_PROVIDED`. Do not present screenshot values as project accuracy.

## Final evidence checklist

- [ ] Include the actual three-class fault-detector checkpoint and its training-provenance sidecar if they are part of the submitted implementation. The uploaded `PCB_ENGINE_KIT(2).zip` contains a trace-mask U-Net, not this detector; do not substitute it.
- [ ] Provide the actual dataset and completed import_manifest.csv; the example CSV is only a template.
- [ ] Record actual source URLs, licence/permission basis, team rights-review declaration and human annotation-review declaration for every row.
- [ ] Use stable group IDs so every view/crop from one PCB/design/capture session remains in only one split.
- [ ] Generate the canonical dataset with pcb_engine_kit/dataset.py and inspect its audit.json.
- [ ] Train the project detector from an architecture YAML with pretrained=False. Do not start from another author's PCB detector weights.
- [ ] Preserve best.pt, project_training_provenance.json, checkpoint SHA-256, dataset YAML and audit hashes.
- [ ] Generate project_dataset_audit.json and project_checkpoint_audit.json. Both must pass before describing the detector as provenance-verified.
- [ ] Evaluate a separate held-out test split and archive raw output, test support, per-class precision/recall/F1, mAP and error examples.
- [ ] Export best.onnx with its metadata sidecar and compare ONNX predictions to the source checkpoint.
- [ ] On the actual Pi 5, provision the project ONNX artifact and retain the ONNX/ExecuTorch smoke-test JSON.
- [ ] Add the existing physical build/test evidence: verified GPIO mapping, sensor voltage/polarity, LED-driver wiring, camera capture and repeated-cycle counts. The team reports these tests are complete; do not rerun them solely to satisfy this checklist if the original records can be supplied.
- [ ] Demonstrate local inference with WAN disconnected while the Pi and operator browser remain on the same LAN.
- [ ] Obtain QA/engineering approval for the provisional severity policy or clearly state that it is an unapproved screening rule.
- [x] Team reports the demo video was uploaded separately through the official channel. The original MP4 is also stored in this repository under `demo_video/`; the external receipt/link is not archived here.
- [ ] Confirm team registration, college nomination, same-college membership, Faculty Mentor and eligibility using the original registration evidence.
- [x] Team reports the individual-contribution and AI-assistance declaration has been submitted separately. The repository discloses ChatGPT-assisted cleanup in docs/THIRD_PARTY_AND_ORIGINALITY_AUDIT.md; the signed declaration/receipt is not archived in GitHub.

## Current technical statements supported by the repository

- The repository contains the station-controller source, local browser dashboard, three-class detector interface, training/export and audit tools, Llama/ExecuTorch integration source, deployment scripts and technical report.
- The project training utility rejects pretrained .pt initial checkpoints and specifies pretrained=False for model training.
- The Pi provisioner no longer downloads a third-party PCB detector; it requires an ONNX artefact with matching project provenance metadata.
- The Llama foundation model and software frameworks are third-party components and are not claimed as trained or invented by the project team.
- No numerical accuracy result is claimed because the source checkpoint, dataset and raw evaluator output are not identified.
- The current checkout has no primary three-class detector file, raw/processed dataset, independent test report, Pi smoke-test record or offline-test evidence. The team reports the physical build/tests are complete, but the physical commissioning sheet and supporting evidence are not yet committed. The supplied trace-mask checkpoint is catalogued at docs/results/supplied_model_package_audit.json and does not fill the three-class detector requirement.

Do not mark an item as passed merely because the source code or command exists. Update this checklist only when corresponding evidence is captured and retained.
