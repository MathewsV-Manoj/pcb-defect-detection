# Final project, repository and submission audit

**Project:** PCB Defect Detection and Inspection Station  
**Challenge context recorded by the team:** Bharat AI-SoC Challenge 2026–27, PS5 — Real-time industrial defect detection and quality-control assistant  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection  
**Audit date:** 22 November 2026  
**Branch audited:** `main`  
**Purpose:** Consolidate what is implemented in source, what the team reports as completed, what was inspected from the supplied model package, and what evidence is still not present in the public repository.

> **Evidence rule:** “Source present” means the repository contains code or documentation. “Team-reported complete/uploaded” means the team has told us the work or submission has been completed. “Verified in repository” means the associated artefact or reproducible record is actually present and inspectable. These statuses are not interchangeable.

---

## 1. Executive conclusion

The repository has undergone a substantial cleanup. External PCB benchmark material and the former external PCB-checkpoint download path have been removed. The project now has a documented three-class detector contract, dataset-import and audit tools, random-initialization training/export code, checkpoint-to-ONNX parity checks, Raspberry Pi deployment scripts, a technical report, submission documentation and CI contract tests.

The team has separately confirmed that:
- the physical station has been built and physical tests have been completed;
- the original demonstration MP4 is restored in this repository, and the team reports a separate upload through the official submission channel; and
- the individual-contribution and AI-assistance declaration is available/submitted separately.

The physical-build completion, separate official video upload and declaration availability remain **team-reported statuses**. The original MP4 is now archived in this GitHub checkout at [demo_video/](../demo_video/). The official submission link/receipt and signed declaration are not archived here. The physical test record is also not yet populated with the actual pin map, device details, cycle counts or supporting logs/photos. This does not mean that the team did not do the work; it means that the public repository cannot independently reproduce or inspect it.

The uploaded `PCB_ENGINE_KIT(2).zip` was inspected. It contains an auxiliary five-channel ResAttention U-Net checkpoint producing a one-channel trace mask. Its checksum matches the archive manifest, the state dictionary loads strictly into the included architecture and a dummy forward pass produces a finite 320 × 320 output. **This is not the project's primary three-class RGB fault detector.** It cannot be used as evidence for missing-hole/open-circuit/short-circuit detection or for any verified accuracy result.

### Current judgement

- **Repository hygiene and software contract checks:** completed; latest recorded GitHub Actions run passed.
- **Physical build and tests:** team reports complete; repository evidence fields need to be populated from the original test records.
- **Demo video:** original MP4 present in `demo_video/`; sampled review shows an explicitly simulated result overlay and does not prove live detector/Llama execution; team reports a separate official upload.
- **Contribution and AI-assistance declaration:** team reports available/submitted separately; actual signed copy/receipt is not archived here.
- **Primary three-class detector, source dataset and reproducible evaluation:** not established by the currently inspected repository and supplied ZIP.
- **Full evidence-based technical release:** not yet verifiable from this repository.

Do not describe the overall project as independently validated end-to-end until the missing model/data/evaluation/runtime records are connected to the exact artefacts used.

---

## 2. Project objective and classes

The software is organised around a visual PCB screening task with three configured defect classes:

1. `missing_hole` — a missing or visibly defective hole at an expected board location.
2. `open_circuit` — a visible discontinuity or break in a conductive track.
3. `short_circuit` — a visible unintended bridge between conductive paths.

The class order used by the repository is:

| Class ID | Class name |
|---:|---|
| 0 | `missing_hole` |
| 1 | `open_circuit` |
| 2 | `short_circuit` |

The application is intended to screen visible image defects and present findings to an operator. A frame with no detections means only that the configured classes were not detected in that frame; it must not be presented as proof that the PCB is electrically defect-free. The severity mapping in `models/severity_policy.json` is explicitly provisional and requires engineering/QA approval before it is treated as a formal quality or safety decision.

---

## 3. Intended system architecture and workflow

The repository describes a Raspberry Pi 5 as the local station computer and inference target. The expected flow is:

1. An operator performs the initial sensor arming action.
2. The IR sensor detects the presence of a PCB at the trigger point.
3. The station controller commands the external LED driver and allows the configured settling interval.
4. The camera captures an image.
5. The Raspberry Pi-hosted dashboard displays the captured frame to the operator.
6. The operator starts the inspection from the dashboard.
7. The Pi-side Python application preprocesses the image and calls the three-class ONNX detector through ONNX Runtime.
8. The application formats the detections, creates an annotated image and writes a structured inspection event.
9. The text advisory component receives structured detection findings and creates an operator-facing note.
10. The dashboard displays the inspection result and local history.

The IR sensor is a presence trigger. The source does not establish precise image-position measurement from the IR device, nor does it claim to control conveyor speed or direction. Camera alignment is a mechanical/system calibration matter and must be recorded separately.

### Main software areas

| Area | Repository path | Purpose / current evidence |
|---|---|---|
| Dashboard | `dashboard/index.html` | Browser operator interface source |
| Raspberry Pi controller | `raspberry_pi/station_controller.py` | IR trigger, camera/LED coordination and local HTTP service source |
| Detector integration | `raspberry_pi/inspect_image.py` | Three-class image preprocessing and ONNX inference contract |
| Inspection coordination | `raspberry_pi/run_inspection.py` | Detector/advisory/event workflow |
| Dataset tooling | `pcb_engine_kit/dataset.py` | Manifest-based dataset import, validation and hashing |
| Training/export | `pcb_engine_kit/train_export.py` | Random-initialized YOLO training, test evaluation and ONNX export |
| Release audit | `pcb_engine_kit/audit_release.py` | Dataset/checkpoint/full-release evidence checks |
| ONNX parity | `pcb_engine_kit/compare_pt_onnx.py` | Source-checkpoint vs ONNX output comparison |
| Advisory integration | `llm_advisory/` | Structured-text advisory integration using ExecuTorch |
| Pi provisioning | `scripts/provision_pi5.sh` | Runtime preparation and project-model metadata gate |
| Event schema | `schemas/` | Structured inspection event contract |

Source presence does not prove that every component has been run successfully on the final target device.

---

## 4. Model and checkpoint audit

### 4.1 Supplied archive and checkpoint

The uploaded `PCB_ENGINE_KIT(2).zip` was inspected as a separate package. The relevant checkpoint is:

```text
pcb_engine_kit/optional_unet/pcb_ultra_resatt_unet.pth
```

| Attribute | Inspection result |
|---|---|
| Model architecture | ResAttentionUNet |
| Input channels | 5 |
| Output channels | 1 |
| Checkpoint format | PyTorch state dictionary |
| State-dictionary keys | 199 |
| State tensor elements | 8,207,071 |
| Parameter elements excluding BatchNorm buffers | 8,200,185 |
| Checkpoint size | 32,897,063 bytes |
| Checkpoint SHA-256 | `23107a1805c13e57f3bccace4aa20bd59e5b400468cb3c0b26f6dba0bce1426c` |
| Archive SHA-256 | `23f22faf49664fe245633d152557bf42a63f25f8ee09acbd0f926ebb3b5bb704` |
| Archive checksum manifest | Checkpoint checksum matches the manifest |
| Strict architecture load | Passed; no missing or unexpected keys |
| Dummy forward output | Finite tensor of shape `(1, 1, 320, 320)` |

The accompanying package documentation describes this checkpoint as a **PCB trace-mask extractor**. The documented input combines an enhanced three-channel image with two additional image-derived feature channels. The output is a single-channel mask. Its documented post-processing includes thresholding and morphology/connected-component steps.

This is not a detector with the three repository fault classes. It does not have the expected three-class RGB detector contract and is not integrated into the current Raspberry Pi YOLO/ONNX path. It is therefore recorded as an auxiliary trace-extraction model only.

### 4.2 Missing provenance for the supplied U-Net

The supplied archive does not establish:
- the training dataset and image/label manifest;
- the exact training script/configuration and training run;
- a training log or epoch history;
- a checkpoint-creation provenance record;
- who trained or owns the checkpoint;
- the redistribution licence or permission for publishing the weights; or
- validation/test metrics from a named dataset split.

The dummy forward pass checks that the state dictionary matches the architecture and produces a finite output. It is not model evaluation, a quality score or evidence of detection accuracy.

The checkpoint is therefore **not copied into the public repository**. Its ownership and redistribution permission should be confirmed before public redistribution.

### 4.3 Primary three-class detector

The public application expects a three-class YOLO-style detector with:
- the class order shown in Section 2;
- a 640 × 640 RGB input contract;
- letterbox preprocessing and normalised float input;
- ONNX Runtime CPU inference; and
- a matching project checkpoint, training-provenance record, dataset audit and ONNX metadata sidecar.

The cleaned repository's current training path is designed to start from a YOLO architecture YAML with `pretrained=False` and to bind the checkpoint to a dataset audit/provenance record. However, the actual primary `best.pt`, its provenance sidecar, the matching `best.onnx` and its sidecar are not present in the current checkout.

**Important mismatch found in the supplied ZIP:** its separate bundled YOLO utility defaults to `yolov8n.pt` and does not enforce the current repository's random-initialization/provenance policy. It is not accepted as proof that the primary detector was trained from random initialization. Do not mix that script's output or any third-party starting weights with the current provenance claim.

Machine-readable records:
- `docs/results/supplied_model_package_audit.json`
- `docs/results/project_checkpoint_audit.json`
- `models/release_manifest.json`

---

## 5. Dataset and label audit

The public repository contains dataset-import tooling and a manifest template. The supplied ZIP also contains source utilities and an example manifest, but no actual labelled training dataset was found in that archive.

The current public checkout does not contain:
- the raw training/validation/test PCB image set;
- the annotation files used for the primary detector;
- a completed per-image source/import manifest;
- the processed dataset and its `data.yaml`;
- the generated `audit.json`; or
- an independently inspectable group/split definition.

The dataset importer is intended to check image readability, label syntax, class IDs, bounding-box coordinates, duplicate image hashes, group identity and split consistency. It also records provenance fields including source URL, licence/permission review and annotation review.

For a defensible split, all images, alternate views and derived crops from the same physical PCB/design/capture group must remain in the same split. Otherwise, the evaluation may be inflated by near-duplicate board imagery leaking between training and validation/test sets.

No image counts, class distribution or dataset rights status are invented in this audit. Current machine-readable dataset status remains `NOT_PROVIDED`.

---

## 6. Accuracy and validation metrics

No numerical accuracy result is included in the submission-facing repository. A previously supplied screenshot did not identify the detector checkpoint, dataset version, board-group split manifest, evaluation settings or raw evaluator output. Its numerical values have therefore been removed from the project results and are not attributed to this implementation.

The current machine-readable held-out test record remains `NOT_PROVIDED`, with null metric fields. The evaluation script is present, but it has not generated a reproducible result from a checkpoint and dataset included in this checkout.

Do not report precision, recall, F1, mAP, false-positive/false-negative rates or detection accuracy as achieved project results unless the exact project checkpoint, training provenance, dataset audit, held-out split and raw evaluator output are connected and independently reproducible. No external PCB-model or hardware benchmark values are substituted.

---

## 7. Raspberry Pi deployment and offline operation

The software is configured for a Raspberry Pi 5 target. The documented deployment path uses:
- OpenCV for image preprocessing;
- ONNX Runtime CPU for three-class detector inference;
- ExecuTorch for the text-only advisory component;
- a Pi-hosted local dashboard/API; and
- local event/image storage.

Firebase event synchronisation is optional in the example configuration and is disabled by default. It is not required for local detector inference.

The Pi provisioner was cleaned so that it no longer fetches an external PCB detector checkpoint. It requires a project ONNX artefact and matching provenance metadata before the project vision runtime is accepted.

The repository still does not contain:
- a Pi smoke-test result tied to the final detector and advisory artefacts;
- target-device latency/FPS/RAM/temperature/power measurements;
- an end-to-end capture-to-result record tied to identified model hashes; or
- a saved offline test showing a complete inspection with the WAN disconnected.

The separate software smoke-test and physical station test are not interchangeable. A script passing with a synthetic input does not prove PCB detection accuracy or physical station reliability.

---

## 8. Physical station status

The team confirms that the physical station has been built and the physical tests have been completed. This is now reflected in the repository as:

```text
TEAM_REPORTED_COMPLETE_EVIDENCE_PENDING
```

This status respects the team's report and does **not** ask for those tests to be repeated merely to satisfy the documentation. The public commissioning record still needs the real values and files from the completed work, such as:
- Raspberry Pi/device and OS details;
- camera model and operating mode;
- actual BCM pin mapping and signal polarity;
- sensor voltage/polarity check;
- LED-driver/external-supply check;
- camera alignment and capture configuration;
- actual arm/trigger/capture sequence;
- attempted and successful cycle counts;
- missed/duplicate triggers and capture/inference failures, if any;
- operator/date; and
- supporting photographs, logs or test records.

These are data-entry and evidence-archiving tasks, not instructions to rerun already completed tests. Do not fill unknown values with estimates. The status must remain team-reported until the original records are attached and reviewed.

---

## 9. Demo video status

The original MP4 is present at [demo_video/WhatsApp Video 2026-11-21 at 5.48.59 PM.mp4](../demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4). Its SHA-256 is `fc562f5889e80173a06e5220328c2bdb5140c02e762a50c3a6640fc9a1348003`. A sampled visual review of the clip (approximately 120.7 seconds) confirms that it shows a physical conveyor/PCB setup and an operator-facing dashboard. At approximately 1:56, the displayed result explicitly says **“SIMULATED INSPECTION COMPLETE”** and records a simulated defect finding. Accordingly, this video demonstrates the physical setup and a simulated UI flow; it does not demonstrate live YOLO inference, a verified detector prediction or actual ExecuTorch/Llama execution.

The repository records the video as **present; sampled review completed; simulation-only result shown**. The video also uses a dark dashboard appearance that does not match the current light-themed `dashboard/index.html` in this repository. Either restore the actual dashboard source used in the clip or describe the clip as a separate demonstration UI, not a capture of the current committed dashboard. The sampled review did not establish the IR arming sequence, a full sensor-to-camera trigger cycle, live detector output, Llama response, or absence of credentials throughout the entire clip. Those points remain unverified. The team reports a separate official upload; its portal URL/receipt is not archived in the repository.

---

## 10. Individual contribution and AI-assistance declaration

The repository contains `docs/THIRD_PARTY_AND_ORIGINALITY_AUDIT.md`, which explicitly records that ChatGPT materially assisted with the repository cleanup and lists the affected source, tests and documentation areas.

The team has confirmed that its individual-contribution and AI-assistance declaration is already available/submitted separately. The repository records this as team-reported because the actual signed declaration or portal receipt has not been archived in the GitHub tree.

The signed declaration should accurately identify:
- each member's own implementation, integration, testing and documentation contributions;
- code, models, datasets or designs reused/adapted from other sources;
- AI-assisted code and documentation, following the actual challenge rules;
- third-party dependencies and licences; and
- each member's own review/approval.

Do not describe the repository cleanup edits as entirely hand-written by team members. Do not assign contribution ownership to a team member merely because their name appears in Git commits. Keep the separate declaration and submission receipt with the team records. The declaration should not be changed to say that the public repository independently proves authorship.

---

## 11. Third-party components and originality boundary

The repository uses or documents the following third-party software/model components:

| Component | Role | Correct attribution |
|---|---|---|
| Ultralytics / YOLO architecture | Detector framework, model construction/training/export | Third-party framework/architecture |
| PyTorch | Model backend | Third-party framework |
| OpenCV | Image preprocessing and image operations | Third-party library |
| ONNX Runtime | ONNX inference | Third-party runtime |
| ExecuTorch | Local advisory runtime | Third-party runtime |
| Llama 3.2 1B Instruct | Text-only advisory from structured findings | Third-party foundation model; not trained by the project team |
| NumPy, PyYAML, GPIO and other packages | Utility and hardware abstractions | Third-party dependencies |

The exact licence and notice requirements must be followed for every dependency and downloadable model asset used in the submitted build. The trace-mask checkpoint's own redistribution permission remains unconfirmed from the uploaded package.

Project-specific work is the integration of the hardware trigger/capture path, Pi-side application, operator dashboard, inspection-event format, severity-policy implementation, deployment scripts and project workflow. This list describes project-specific integration areas; it does not independently prove which named person authored every line.

---

## 12. Security, limitations and responsible claims

- Do not publish Firebase credentials, Wi-Fi passwords, tokens, private keys or device secrets.
- Do not claim the detector identifies all possible electrical faults; it is configured for the three visible categories.
- Do not claim that an empty detection set certifies a board as defect-free.
- Do not present the provisional severity policy as an approved electrical/QA standard.
- Do not claim a model was trained by the team without its actual training history and provenance.
- Do not claim the U-Net trace extractor is the three-class classifier.
- Do not report screenshot-derived accuracy values; their checkpoint/dataset/evaluator provenance is unavailable.
- Do not use external benchmark numbers as project performance.
- Keep the Llama component described as a text advisory over structured detections; it is not the PCB vision model and does not replace QA judgement.

---

## 13. CI and repository verification

The GitHub Actions workflow checks:
- Python source compilation;
- availability of Raspberry Pi 5 ARM64/Python 3.13 binary wheels for the pinned runtime dependencies;
- the repository contract test suite; and
- dataset utility contract tests.

The latest recorded CI run for the audited main-branch HEAD (d0be02df2ae415c98c7e8912d897e970f32356ee) completed successfully:

https://github.com/MathewsV-Manoj/pcb-defect-detection/actions/runs/45002267747

A successful CI run verifies the tests that ran in CI. It does not validate the primary model's accuracy, physical wiring, camera/conveyor cycle, external video upload or team declarations.

---

## 14. Remaining items — exact action list

The items below are what remain to make the public technical evidence complete. They are not all equal in importance.

### A. Must be resolved for a reproducible three-class detector claim

1. **Identify and supply the actual three-class detector checkpoint** used in the running application. Do not substitute the five-input/one-output trace U-Net.
2. **Provide the matching checkpoint provenance**: training entry point, initialization source, configuration, software versions and checkpoint SHA-256.
3. **Provide the actual dataset and annotation files**, completed import manifest, source/rights information, group IDs and split assignments.
4. **Generate and review the dataset audit** from those exact files.
5. **Generate a held-out test report** from the exact checkpoint and dataset. Preserve per-class and overall metrics, test support and raw evaluator output.
6. **Provide the matching ONNX export and sidecar**, then run the checkpoint-to-ONNX parity check using the corresponding held-out images.

### B. Must be archived to complete the public target-device evidence

7. Add the Pi runtime smoke-test output tied to the exact model and advisory artefacts.
8. Add target-device performance measurements only if the team actually measured them.
9. Add the completed physical commissioning values and original test evidence from the already completed hardware work. Do not repeat tests just to populate documentation.
10. Add the completed offline-operation record if offline operation was tested. If not, mark it not tested rather than assuming success.

### C. Administrative evidence — team reports these are already done

11. Keep the external demo-video upload URL or receipt with the team submission records and verify that the official submission form points to the intended final video.
12. Keep the signed/approved individual-contribution and AI-assistance declaration with the team records. Ensure the disclosure covers the ChatGPT-assisted repository cleanup and all reused/adapted code.


### D. Quality approval

13. Keep the defect severity policy explicitly provisional until an engineering/QA owner approves it against board-level requirements.

---

## 15. Final status table

| Area | Current status | Interpretation |
|---|---|---|
| Repository cleanup | COMPLETE | External benchmark content and external detector download path removed |
| Software source and documentation | PRESENT | Source is committed; not all execution paths are target-tested |
| CI contract tests | PASS | Latest recorded GitHub Actions run passed |
| Auxiliary trace-mask checkpoint | INSPECTED | Hash and architecture checks passed; no training/evaluation provenance |
| Primary three-class detector | NOT PROVIDED IN CHECKOUT | Exact checkpoint/provenance still needed |
| Dataset and labels | NOT PROVIDED IN CHECKOUT/ZIP | Actual source data and completed audit still needed |
| Accuracy metrics | NOT REPORTED | No verified checkpoint/dataset-bound evaluation included; screenshot-derived values excluded |
| ONNX parity | NOT PROVIDED | No matching primary detector export/parity report |
| Pi runtime evidence | NOT PROVIDED | Target smoke-test record absent |
| Physical build/tests | TEAM REPORTED COMPLETE | Archive existing test data; no need to repeat completed tests |
| Offline test | NOT VERIFIED IN REPOSITORY | Preserve the actual test record or state not tested |
| Demo video | REPOSITORY COPY PRESENT; SAMPLED REVIEW SHOWS SIMULATED RESULT | Physical setup and UI flow visible; no live detector or Llama execution proven; team reports separate portal upload |
| Individual contribution / AI declaration | TEAM REPORTED AVAILABLE/SUBMITTED | Keep signed copy/receipt; AI assistance is disclosed in repository |
| Severity policy | PROVISIONAL | Requires engineering/QA approval |

## 16. Overall conclusion

The cleaned repository is a substantially better and more honest source package than the earlier version. The original demo MP4 is now present in the repository and the team reports a separate official upload; the individual-contribution and AI-assistance declaration is reported available separately, and the physical build/tests are reported complete. Those team confirmations have been reflected without pretending that external submissions or unarchived test files are independently visible from GitHub.

The main unresolved technical issue is not the trace-extraction U-Net. It is the identity and provenance of the **actual three-class fault detector**, its dataset and its reproducible evaluation. The supplied U-Net checkpoint is a separate trace-mask model and cannot be used to fill that gap.

Accordingly, the repository cleanup and CI status are complete, and the administrative deliverables are team-reported complete. The public technical evidence is not yet a fully reproducible release until the primary detector/dataset/test artefacts and the remaining Pi/physical/offline records are connected to the exact system that was submitted.
