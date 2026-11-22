# PCB inspection station
## Project technical report

## 1. Project purpose and scope

The project is a visual PCB inspection prototype intended to screen three visible defect categories:

1. Missing hole — a hole absent or visibly defective at an expected board location.
2. Open circuit — a visible break or discontinuity in a conductive track.
3. Short circuit — an unintended visible bridge between separate conductive paths.

The repository contains the software source for an operator dashboard, image preprocessing, YOLO-style detector inference, structured inspection records, a text-only advisory component, and a Raspberry Pi-targeted station controller. The source checkout does not contain the project-trained detector or dataset. It therefore documents the implemented software path and intended deployment, not a fully validated physical product.

## 2. Intended station workflow

The current station-controller source describes this sequence:

1. The operator performs an initial IR-sensor arming gesture.
2. A PCB reaches the sensor trigger point.
3. The controller commands an external LED driver and captures an image after a configured settling delay.
4. The Pi-hosted page displays the captured image to an operator.
5. The operator requests an inspection.
6. The Pi-side process preprocesses the frame and invokes the configured ONNX detector through ONNX Runtime.
7. The detector returns boxes, class labels and confidence values; the application writes an annotated image and a structured event.
8. A text-only Llama advisory component receives the structured event and returns an operator note.
9. The dashboard presents the result and local history.

The IR sensor indicates presence at its trigger point. It does not determine exact pixel coordinates or image alignment. The mechanical arrangement of conveyor, camera and sensor determines where a board appears in the frame. The source controller does not claim to control conveyor speed or direction.

**Verification boundary:** the team reports that the physical station build and physical tests are complete. The repository currently lacks the completed commissioning sheet, verified GPIO pin mapping, physical-cycle counts and supporting logs/photos, so this report records the completion as team-reported rather than independently evidenced. No repeat of the physical test is implied; the existing test records should be added to the evidence folder.

## 3. Software architecture

### 3.1 Image acquisition and operator interface

The Raspberry Pi-targeted controller contains the IR state machine, camera capture interface, LED-driver output and HTTP service. The dashboard is static HTML/JavaScript served by the controller. The browser sends requests to the Pi and displays results; it is not configured to run detector inference.

The camera may be configured as a USB camera or through the Raspberry Pi camera stack. Actual camera model, focus, exposure, illumination and mechanical calibration must be recorded during commissioning.

### 3.2 Detector preprocessing and inference

The detector source implements a fixed three-class interface and a 640 × 640 RGB input contract. The preprocessing path uses letterboxing, BGR-to-RGB conversion, float32 normalization to [0, 1] and NCHW layout. ONNX Runtime is configured to use its CPU execution provider.

The training utility now starts from an Ultralytics YOLO architecture YAML and passes pretrained=False. It rejects .pt initial weights. The script writes a project_training_provenance.json record beside the produced best.pt checkpoint, including the checkpoint hash, dataset hashes, class order and training settings. The exporter verifies that record and writes a matching ONNX metadata sidecar.

The source code and training path are present, but no primary three-class project-trained best.pt or best.onnx is included in this repository snapshot. The uploaded `PCB_ENGINE_KIT(2).zip` contains a separate ResAttentionUNet checkpoint for single-channel trace-mask extraction (five input channels, one output channel); its checksum matches the archive manifest. The archive itself documents this U-Net as a trace extractor, not a fault detector, and contains no training dataset, training log, provenance sidecar or metrics. It cannot fill the primary three-class detector record. See `docs/results/supplied_model_package_audit.json`.

### 3.3 Detection interpretation

The system reports configured target detections from a single image. An empty detection list means that none of the configured target classes was detected in that frame. It is not evidence that the PCB is defect-free.

The code uses a provisional type-based screening policy. The current mapping assigns MEDIUM to missing_hole and HIGH to open_circuit and short_circuit. The policy has not been validated against a board drawing, electrical test criteria or a qualified QA standard. It must be presented as provisional prioritization, not a validated severity or safety assessment.

### 3.4 Advisory component and third-party software

The advisory route uses the third-party Llama 3.2 1B Instruct SpinQuant model through ExecuTorch. The model receives structured text findings, not the PCB image. It does not change detections, operate the conveyor or make a final quality-release decision. The foundation model is not trained by the project team; its upstream license and use conditions must be reviewed before deployment.

Other third-party dependencies include Ultralytics, PyTorch, OpenCV, ONNX Runtime and ExecuTorch. Their contribution is acknowledged; the project does not claim authorship of those libraries or of the YOLO architecture.

## 4. Dataset preparation and provenance

The repository contains an importer and an import-manifest template, not the actual training images or processed dataset. The source register is intentionally header-only because no external dataset has been confirmed as used.

Every image row in the completed import manifest must identify its source, source URL, licence or permission basis, rights-review declaration, annotation-review declaration, and board/capture group. The importer checks file readability, label format, class IDs, normalized coordinates, bounding-box bounds, duplicate image content and group/split consistency.

The importer produces data.yaml and audit.json with source and label hashes, split counts, class coverage, group mapping and review declarations. The separate release auditor checks the generated records and checkpoint sidecar. Rights and annotation review statuses are entered by the team; the scripts cannot independently establish legal rights or semantic annotation correctness.

At the time of this repository audit:
- raw project dataset: not present;
- processed dataset: not present;
- completed import manifest: not present;
- generated dataset audit: not present;
- dataset release status: NOT_PROVIDED.

See datasets/README.md and docs/results/project_dataset_audit.json.

## 5. Model training, checkpoint provenance and evaluation

The project training workflow is configured for random initialization from a YOLO architecture YAML. It does not accept an external .pt detector checkpoint. The resulting checkpoint is tied to the exact dataset YAML and audit hashes through project_training_provenance.json.

A checkpoint is not accepted for validation or export unless:
- the training-provenance sidecar exists;
- the checkpoint SHA-256 matches the sidecar;
- the sidecar declares random initialization and no pretrained weights;
- the model class order matches the project contract;
- the current dataset YAML and audit hashes match the training record.

The independent release audit generates project_dataset_audit.json, project_checkpoint_audit.json and project_release_audit.json. Missing files are recorded as NOT_PROVIDED or INCOMPLETE, not as a pass.

At the time of this report, no three-class fault-detector checkpoint or its provenance sidecar is in the repository. The separately supplied trace-mask checkpoint is not a substitute. Consequently, no independently reproducible primary-detector test metrics can be reported.

## 6. Model evaluation and accuracy reporting

No verified accuracy result is included in this submission repository. The available screenshot transcription could not be tied to an identified detector checkpoint, dataset version, group-level split manifest, evaluation configuration or raw evaluator output. Its numerical values are therefore excluded from the project results and must not be attributed to the model described in this report.

The repository contains source code for a held-out test evaluation workflow. The machine-readable record `docs/results/project_test_metrics.json` remains `NOT_PROVIDED` with null metric fields because no matching project checkpoint and audited dataset are included in this checkout.

Accordingly, this report makes no numerical claim for precision, recall, F1, mAP, false-positive rate, false-negative rate or overall PCB inspection accuracy. It also makes no claim that the detector has been validated on the Raspberry Pi.

## 7. Raspberry Pi deployment and local operation

The documented target runtime is a Raspberry Pi 5 CPU. OpenCV preprocessing and YOLO ONNX inference are configured to run locally through ONNX Runtime. The text-only advisory is configured to run locally through ExecuTorch. Firebase event synchronization is optional and disabled by default in the example configuration; it is not an inference service.

The Pi provisioner requires an ONNX file and sidecar, checks the ONNX file hash, the declared project-training/random-initialization metadata, the class order, and the presence of checkpoint/dataset/provenance hash fields. The Pi-side loader does not possess the original training checkpoint and dataset, so it cannot independently recompute those source hashes; that linkage must be established by the development-machine audit. It downloads/builds the separately licensed Llama and ExecuTorch assets as part of setup. A successful provisioner run would still be a software smoke test, not proof of physical station operation.

No Pi smoke-test record, target-device latency result, end-to-end capture-cycle measurement, offline-operation record or external power-meter reading is currently present in the repository. The team separately reports physical build/tests complete; their detailed commissioning records have not been archived here.

## 8. Current evidence and limitations

| Item | Current evidence |
|---|---|
| Application and dashboard source | Present |
| Dataset importer and audit utility | Present; actual dataset/manifest absent |
| Random-initialized training/export code | Present; checkpoint absent |
| Project checkpoint audit | NOT_PROVIDED |
| Dataset provenance audit | NOT_PROVIDED |
| Screenshot validation values | Supplied screenshot transcription only |
| Independent held-out test results | Not available |
| Raspberry Pi runtime smoke test | Not available |
| Physical GPIO/camera/illumination commissioning | Team reports build/tests complete; detailed evidence not committed, so repository status remains unverified |
| Offline test | Not verified |
| Demo video | [Original MP4 in repository](../demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4); sampled review shows the on-screen result is explicitly simulated, not live detector evidence; team reports a separate official upload |
| Severity rules | Configured but provisional |

The project should not state that a particular accuracy, latency, frame rate, power draw, reliability level, physical cycle or offline result has been achieved unless the corresponding source data and measurement record are retained.

## 9. Required completion sequence

1. Assemble the actual dataset and complete the source/rights/annotation import fields.
2. Assign board/capture groups and rebuild the dataset with the importer.
3. Review the generated dataset audit; correct any missing class coverage or provenance gaps.
4. Train from the architecture YAML with pretrained=False.
5. Preserve best.pt and project_training_provenance.json.
6. Evaluate the separate board-grouped test split and save project_test_metrics.json.
7. Export ONNX and verify metadata against the exact checkpoint and dataset audit hashes.
8. Run `pcb_engine_kit/compare_pt_onnx.py` over the complete held-out test directory and retain `project_onnx_parity.json`; the script checks model/dataset hashes and can mark the ONNX sidecar only after a full-split pass.
9. Provision the target Pi with the project detector and separately licensed Llama model.
10. Complete the Pi smoke test, physical commissioning, repeated-cycle tests and offline test.
11. Verify that the separately submitted official video is the intended final version and retain its receipt/link if required by the challenge. The original MP4 is also retained in this repository at [demo_video/](../demo_video/). Obtain QA/engineering approval for the provisional severity policy.

The team also reports that the individual-contribution and AI-assistance declaration is available/submitted separately. The repository's originality audit discloses ChatGPT-assisted cleanup work; the signed external declaration is not stored in this checkout. See `docs/FINAL_PROJECT_AND_SUBMISSION_AUDIT.md` for the full reconciliation. This report distinguishes source-code availability from evidence of successful execution. Update it only when new artefacts and reproducible test records are available.
