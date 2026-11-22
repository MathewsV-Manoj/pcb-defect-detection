# Third-party and originality audit

## Purpose

This document separates project-specific integration from third-party models, frameworks, libraries and datasets. It is not a declaration that every line of code was independently authored by a named team member. Repository history and source inspection cannot prove the identity of the person who wrote each line or detect every copied/adapted code fragment.

## PCB detector

**Repository policy after this cleanup:**
- No external PCB detector checkpoint is configured in the Pi provisioner.
- The former third-party PCB checkpoint download/export path and its associated baseline document have been removed.
- The project training entry point starts from an Ultralytics architecture YAML and sets `pretrained=False`.
- It rejects a .pt file supplied as the initial model.
- Validation/export and Pi inference require SHA-256-linked checkpoint, dataset-audit and training-provenance metadata.

**Current artifact state:** no project checkpoint, ONNX export, training provenance sidecar, processed dataset or completed dataset/checkpoint audit exists in the repository. Therefore the repository currently does not prove that a first-party detector has been trained. The code establishes a future training policy, not proof of a completed run.

The user-supplied screenshot metrics remain as a separate unverified validation transcription. Their model and dataset are unidentified; do not claim that they were produced by the newly introduced random-initialized workflow.

## Third-party software and model dependencies

| Component | Role in this repository | Project ownership claim |
|---|---|---|
| Ultralytics | YOLO architecture construction, training, validation and ONNX export API | Third-party framework; not an original project invention |
| PyTorch | Model training/inference backend used by Ultralytics | Third-party framework |
| OpenCV | Image loading, resize/letterbox support, annotation and NMS | Third-party library |
| ONNX Runtime | CPU execution of the exported detector | Third-party runtime |
| ExecuTorch | Local C++ runtime for text advisory | Third-party runtime |
| Llama 3.2 1B Instruct SpinQuant INT4/EO8 | Text-only advisory from structured detector findings | Third-party foundation model; not trained by the project team |
| NumPy, PyYAML, gpiozero and other declared packages | Numeric operations, configuration parsing and GPIO abstraction | Third-party dependencies |

Retain the upstream licences, notices and terms for the exact pinned dependencies and downloaded Llama artifact. This document does not substitute for a legal licence review.

## Dataset provenance

The repository contains an import manifest template and a header-only source register. It does not contain the project training images or a completed import manifest. No external PCB dataset is currently confirmed as used.

Before using any external images, record the actual revision, source URL, licence/permission basis, class definitions and annotation format. Review each class mapping manually; do not infer equivalence from similar names or numeric class IDs. Dataset sources that cannot be lawfully used or whose annotations cannot be validated must not be included.

## AI-assisted changes made during this cleanup

This repository cleanup was performed with ChatGPT assistance at the repository owner's request. The following files were created or materially rewritten with AI assistance in this session and must not be represented as entirely hand-written by the team:

- `pcb_engine_kit/dataset.py` — dataset import and source/provenance audit.
- `pcb_engine_kit/train_export.py` — random-initialized training, held-out test evaluation and ONNX export.
- `pcb_engine_kit/audit_release.py` — dataset, checkpoint and full-release evidence audit.
- `pcb_engine_kit/compare_pt_onnx.py` — checkpoint-to-ONNX prediction parity checker.
- `scripts/provision_pi5.sh` — project-only ONNX provisioning gate.
- `raspberry_pi/inspect_image.py` — strict project-model sidecar validation.
- `tests/test_submission_contract.py`, `tests/test_onnx_parity_contract.py`, and `tests/test_release_audit_tool.py` — test updates/additions.
- The README, dataset guide, technical report, submission documents, release manifest, validation/audit records and commissioning templates were also rewritten or added with AI assistance.

The team must review the actual final diff, follow the challenge's AI-assistance disclosure requirements, and decide how these contributions should be declared. This document does not claim that the assistant's generated code has been independently validated on the team's hardware or data. CI passing verifies the listed software checks only; it does not establish who wrote the code or whether the project satisfies an originality rule.

## Project-specific source areas

The following are custom project integration areas in the repository. Listing them does not independently prove authorship by a particular team member:

- `raspberry_pi/station_controller.py` — station trigger/capture and local HTTP service integration.
- `raspberry_pi/inspect_image.py` — project inference contract, image preprocessing, detections and event creation.
- `raspberry_pi/run_inspection.py` — coordination of detector, advisory and record publishing.
- `dashboard/index.html` — operator interface.
- `pcb_engine_kit/dataset.py`, `train_export.py` and `audit_release.py` — dataset import, project training/export and provenance gates.
- `llm_advisory/prompt.py` and `run_executorch.py` — text advisory prompt/runner integration around the upstream foundation model.

The team must review these files against its own working history and declare:
1. which member implemented each project-specific module;
2. which snippets were adapted from tutorials, examples, repositories or generated by AI tools;
3. which portions were modified from upstream code;
4. the required notices and licences for every reused portion.

Do not state "100% written by us" unless the team can substantiate that claim file-by-file and comply with the challenge's code originality rules.

## External metrics removed

The previous external PCB-model benchmark documents and corresponding benchmark JSON were removed. The third-party PCB checkpoint downloader/exporter was removed. The report, README, submission checklist and performance document no longer use published PCB-model or external Pi/Llama numbers as project measurements.

The only accuracy figures retained are the team's supplied screenshot transcription. The exact checkpoint, dataset and evaluator record remain unavailable, so the values stay explicitly unverified.

## Supplied PCB_ENGINE_KIT archive inspection

The team supplied `PCB_ENGINE_KIT(2).zip` for inspection. The archive is ZIP-integrity checked, and the SHA-256 of `optional_unet/pcb_ultra_resatt_unet.pth` matches the archive's `SHA256SUMS.json` entry. The checkpoint loads as a PyTorch state dictionary with `weights_only=True`. Its tensor shapes identify a five-channel input and a one-channel output, and the accompanying package documentation identifies its purpose as PCB trace-mask extraction.

This is an auxiliary trace extractor, not the project's three-class `missing_hole`, `open_circuit`, `short_circuit` detector. The archive contains no trace-model training dataset, dedicated U-Net training log, checkpoint-creation metadata, or validation metrics. The checkpoint's training ownership and redistribution licence are not established by the archive. Do not state that this model was trained by the project team unless separate original records establish that. The separate YOLO training script in the archive defaults to `yolov8n.pt` and does not enforce the repository's `pretrained=False` policy, so it is not accepted as provenance for the current project detector.

The machine-readable inspection is `docs/results/supplied_model_package_audit.json`. The binary checkpoint is not added to the repository and is not used by the current Raspberry Pi detector path.

## Current status

- [x] Remove third-party PCB checkpoint from provisioning path.
- [x] Reject external .pt initial weights in the new training CLI.
- [x] Require hash-linked dataset/checkpoint provenance for export and inference.
- [x] Remove third-party PCB benchmark and upstream-baseline result documents.
- [x] Disclose Llama as a third-party foundation model.
- [x] Record missing dataset/checkpoint evidence as NOT_PROVIDED.
- [ ] Recover and audit the actual dataset and its permissions.
- [ ] Train the project detector under the new provenance workflow.
- [ ] Reproduce a held-out test report from the matching checkpoint.
- [ ] Obtain team-level source-authorship and AI/reuse disclosures. A draft for individual review is in `docs/TEAM_DECLARATION_TEMPLATE.md`.
- [x] Inspect the supplied PCB_ENGINE_KIT archive and record the auxiliary trace-checkpoint hash and architecture.
- [ ] Confirm the trace-checkpoint's actual training owner, dataset, provenance and redistribution licence before any public redistribution.
