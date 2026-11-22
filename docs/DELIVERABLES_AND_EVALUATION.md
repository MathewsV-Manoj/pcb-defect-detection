# Phase 1 deliverables and evaluation

**Challenge:** Bharat AI-SoC Challenge 2026–27  
**Problem statement:** PS5 — Real-time industrial defect detection and quality-control assistant  
**Phase 1 deadline recorded in project materials:** 23 November 2026

This checklist is based on the project repository and the PS5 scope documented by the team. It distinguishes source presence from demonstrated operation.

## Phase 1 deliverables

| Deliverable | Repository evidence | Current status |
|---|---|---|
| Source code | Controller, dashboard, inference, training, audit, advisory and event schema source | Present |
| Application | Pi-targeted HTTP service and browser dashboard | Source present; target hardware test absent |
| Demonstration video | No video retained in this repository (removed at team request) | Provide an approved external link through the challenge portal if a video is required |
| Technical report | docs/PROJECT_REPORT.md | Present; must be updated with real measured evidence when available |

## Functional architecture

The documented target path is Raspberry Pi 5 CPU for OpenCV preprocessing, ONNX Runtime detector execution and ExecuTorch text advisory. The browser is an operator interface. Firebase is optional record replication and disabled by default in the example configuration.

The Llama 3.2 1B Instruct foundation model is third-party software, not trained by the team. It receives structured detection findings only and does not change detector output. The project code now refuses an unproven PCB model sidecar; the Pi provisioner does not download a third-party PCB detector.

| Capability | Source implementation | Evidence required before calling it complete |
|---|---|---|
| Three-class PCB detection | ONNX decoder, class contract and training/export utility | Audited model checkpoint, ONNX parity and held-out test report |
| Data provenance | Import manifest and dataset audit | Actual dataset, source/rights review and group-safe split |
| Defect severity | Configurable provisional type rules | Approval against board-level electrical/QA requirements |
| Operator advisory | Llama/ExecuTorch text-only integration | Model/tokenizer download, target runner smoke test and valid output record |
| Inspection logging | JSON events, annotated images and local history | Real multi-board cycle and record review |
| Edge execution | CPU-only ONNX/ExecuTorch target path | Test on actual Raspberry Pi 5 |
| Offline operation | No cloud inference path; Firebase disabled by default | Full inspection with WAN disconnected and LAN retained |
| Real-time performance | Detector and pipeline benchmark scripts | Measured target-device JSON; no outside benchmark values substituted |

## Project detector evaluation

The only numeric values retained in the repository are the team's screenshot-reported validation figures:

| Metric | Reported validation |
|---|---:|
| Precision | 98.3% |
| Recall | 98.4% |
| mAP@0.50 | 98.9% |
| mAP@0.50:0.95 | 62.5% |

The per-class values are in docs/results/PROJECT_VALIDATION_RESULTS.md. The checkpoint identity, dataset/split provenance, sample counts and raw evaluator output are unknown. These numbers have not been reproduced and are not independent test scores. The separately supplied `PCB_ENGINE_KIT(2).zip` contains a ResAttention U-Net trace-mask checkpoint (5-channel input, 1-channel output), not the three-class detector; the archive does not include the U-Net training dataset, log, provenance or metrics. The trace checkpoint therefore cannot identify or validate the screenshot scores. See docs/results/supplied_model_package_audit.json.

For new results, use the audited training workflow and test split. Record per-class precision, recall and F1, mAP@0.50 and mAP@0.50:0.95, test support, confusion matrix and reviewed false positives/false negatives. All images from the same board/design/capture group must stay in one split.

## Pi target commissioning and measurement

After the project ONNX artifact and matching sidecar have been produced:

```bash
bash scripts/provision_pi5.sh
bash scripts/run_station_pi5.sh
```

The provisioner checks the ONNX hash, random-initialization provenance and dataset/checkpoint sidecar fields, then provisions the separately licensed Llama/ExecuTorch path. It does not establish physical wiring or prove the station has passed.

Complete the evidence fields in docs/PI5_COMMISSIONING.md from the team's existing physical test records. The team reports that the build and physical tests are complete; add the pin map, actual device/camera details and real repeated-cycle results rather than inventing values or repeating tests unnecessarily. Test and record the separate Pi runtime and offline-operation evidence if those were not part of the completed physical tests.

For performance, measure detector preprocessing, inference and postprocessing latency; p50/p95; sequential FPS; RAM; CPU temperature; Llama response telemetry; physical capture-to-result time; and power only using an external meter. Store the actual Pi configuration, software versions, model hashes, test image list and measurement method. No performance value from other models or devices may be entered as a project result.

## Rights, authorship and challenge eligibility

Keep attribution and license notices for all third-party libraries and the Llama model. The training workflow does not use external PCB checkpoint weights. The dataset import manifest must record actual dataset sources and team review; the source register alone does not prove use or permission.

The public repository cannot establish whether the team registration, college nomination, student eligibility and Faculty Mentor requirements were completed. Confirm those facts against the original registration record.

## Current conclusion

The repository contains the software source and evidence-generation tools. The uploaded package adds an auxiliary trace-mask checkpoint only; the primary three-class detector, actual dataset and independent test results are still absent from the checkout. The team reports physical build/tests complete, but the supporting commissioning evidence is not yet committed. No demo MP4 is stored in the repository. The challenge deliverables must be described accordingly until the remaining artefacts and team declarations are added.
