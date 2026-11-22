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
| Demonstration video | [`demo_video/WhatsApp Video 2026-11-21 at 5.48.59 PM.mp4`](../demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4) | MP4 present; sampled review confirms the on-screen inspection result is explicitly simulated, not live detector evidence; team reports separate official upload |
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

No verified numerical accuracy result is included in this repository. The screenshot-derived values previously documented could not be tied to an identified checkpoint, dataset, split manifest or raw evaluator output, so they have been excluded from the project results.

The repository contains the training and held-out test evaluation source, but the primary three-class detector checkpoint and audited dataset are not part of this checkout. The machine-readable held-out metrics record is `NOT_PROVIDED`. Do not report accuracy, precision, recall, F1 or mAP as achieved project results until the exact model and test evidence are available.

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

The repository contains the software source and evidence-generation tools. The uploaded package adds an auxiliary trace-mask checkpoint only; the primary three-class detector, actual dataset and independent test results are still absent from the checkout. The team reports physical build/tests complete, the demo video is present in the repository and is also reported uploaded separately, and the individual-contribution/AI-assistance declaration available separately. Their external submission receipt/copy and the detailed physical commissioning evidence are not archived here. The public technical evidence therefore remains incomplete until the primary detector/data/test artefacts and the Pi/offline/physical records are connected to the submitted system.
