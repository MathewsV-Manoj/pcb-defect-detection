# Phase 1 submission readiness

**Challenge:** Bharat AI-SoC Challenge 2026–27  
**Problem statement:** PS5 — Real-time industrial defect detection and quality-control assistant  
**Official Phase 1 deadline:** 23 November 2026  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection

## Implemented source and deployment paths

- Raspberry Pi station controller for IR arming/capture, illumination and camera.
- Pi-hosted operator page and same-origin inspection API.
- OpenCV preprocessing and three-class YOLOv8 ONNX inference source.
- Detection decoding, class-wise NMS, annotated-image creation and structured inspection events.
- Mandatory text-only Llama advisory path using an ExecuTorch C++ runner on the Pi 5 CPU.
- Pinned Llama 3.2 1B Instruct SpinQuant INT4/EO8 model downloader, local hash manifest, and Pi 5 ExecuTorch runner build script.
- Local inspection history and optional Firebase Realtime Database synchronization.
- Dataset import manifest, source manifest, annotation utility, YOLO training/export source and software tests.
- Detector-only and full still-image pipeline benchmark scripts.

- On-device execution architecture documented: OpenCV + ONNX Runtime CPU detector and Llama 3.2 1B + ExecuTorch C++ advisory on the Raspberry Pi 5; no cloud inference endpoint is configured.
- Offline operating procedure and evaluator-facing explanation documented in `docs/LOCAL_EXECUTION_AND_PERFORMANCE.md`; Firebase record sync remains disabled by default.
- Technical report, workflow diagram, deployment guide, evaluator checklist and committed demonstration MP4.

## Remaining work and evidence

| Item | Repository state | Required action |
|---|---|---|
| Vision model/checkpoint identity | `best.pt` and `best.onnx` are not tracked; the validation screenshot does not identify which checkpoint produced its scores | Supply the exact checkpoint identity and SHA-256 used for the screenshot, then ensure the same model is used for export/deployment. The Pi provisioner currently defaults to an attributed third-party six-class YOLOv8s baseline; do not attach the screenshot scores to it unless the checkpoint is confirmed identical |
| Project-trained three-class model | No project-owned three-class checkpoint is committed to this repository; the screenshot's model identity is unknown | Add the actual project checkpoint or a controlled artifact location, SHA-256, training configuration and corresponding class map. If only the upstream baseline was used, report it with attribution and keep its publisher metrics separate |
| Dataset audit | Import template and source manifest exist; processed data and final import audit are absent | Add the actual image/label manifest, source licenses, board-level grouping and split audit |
| Detection quality | Screenshot-reported validation results are documented in `docs/results/PROJECT_VALIDATION_RESULTS.md`; raw evaluator output, dataset/split provenance, checkpoint identity and held-out predictions are not committed | Preserve these as validation-only figures. Archive the exact checkpoint/dataset/split metadata and raw evaluator output; then score a separate board-level held-out test set and record per-class precision/recall/F1, confusion matrix and mAP@0.50 / mAP@0.50:0.95 |
| Llama model package | Pinned downloader and model revision are committed; licensed PTE/tokenizer are not stored in Git | Download locally after accepting upstream terms; preserve download_manifest.json and hashes |
| ExecuTorch runner | Pi-native build script and one-command provisioner are committed; compiled binary is not stored in Git | Run `bash scripts/provision_pi5.sh`; retain the smoke-test output and build metadata |
| Llama integration | Production coordinator calls the runner and requires advisory by default | Run the real event smoke test and one complete station cycle; keep the model output JSON |
| Severity | Configurable provisional type-based policy is implemented | Obtain QA/engineering approval against the actual board. Until approval, describe it as provisional screening priority, not validated severity assessment |
| Pi commissioning | GPIO map, capture/illumination verification and full-cycle record are not supplied | Complete docs/PI5_COMMISSIONING.md with actual physical checks |
| Runtime measurements | Scripts are committed; no project results are committed | Run both benchmark scripts on the actual Pi and retain output JSON |
| Original work and third-party rights | The Pi provisioner references a third-party MIT-declared YOLO checkpoint; dataset use terms are not yet verified | Review all model/data/software rights against the challenge's original-work and Participant Materials rules; seek written organiser clarification before submitting a third-party checkpoint as part of the entry |
| Physical throughput | No conveyor-cycle data is committed | Time complete capture-to-dashboard cycles; log attempted/successful cycles, missed/duplicate triggers and failures |
| Demo video | MP4 is present; team confirms video production is complete | Include the repository MP4 or a shareable public/unlisted URL in the submission. Video contents have not been independently inspected in this review |
| Eligibility and registration | Public README lists three students at Muthoot Institute of Technology and Science; registration closed on 19 October 2026 | Confirm the Team Leader registered the team before closure, all student members are from the same college, college nomination was completed and a Faculty Mentor is recorded. These facts require the team's registration confirmation |

## Open-source vision baseline

The repository now includes a hash-verified downloader for Sulojan Rajkumar's
MIT-declared YOLOv8s PCB checkpoint, an ONNX export mode with a six-to-three
class mapping, and a Pi decoder that reads that metadata sidecar. The model's
published test results are documented with attribution in
`docs/PCB_UPSTREAM_BASELINE.md`. The upstream weights remain local deployment
assets and are not committed to Git; the exact SHA-256 is checked by the
downloader. The author-reported metrics are not project test metrics.

## Llama deployment: configured, not papered over

The default station configuration points to the pinned Llama 3.2 1B Instruct SpinQuant INT4/EO8 package and sets `PCB_LLAMA_REQUIRED=true`. The one-command Pi provisioner downloads the package locally and builds the runner on the Pi against its own sysroot. The model files remain local deployment assets because they are licensed and the PTE is approximately 1.14 GB.

The required sequence is:

1. On the 64-bit Raspberry Pi 5, run `bash scripts/provision_pi5.sh` with internet access and at least 12 GiB free storage.
2. Review `raspberry_pi/.env` and set the real GPIO pins/polarities; do not guess wiring.
3. Confirm `docs/results/pi5_runtime_smoke_test.json` reports successful YOLO CPU inference and ExecuTorch advisory.
4. Run a real conveyor capture and inspection; retain an event with `advisory_runtime.status = COMPLETED`.
5. Repeat the test with the WAN disconnected and Firebase disabled.

This is the implementation path. It is not valid to say the model has already
run on the team's device until steps 3–5 have been completed and evidence saved.
The model receives the structured detection record only; it does not see the
PCB image, alter detections, control actuators or make the final disposition.

## Local execution requirement

The configured inference algorithms execute on the Raspberry Pi 5 CPU: OpenCV preprocessing, YOLO through ONNX Runtime `CPUExecutionProvider`, and Llama through the ExecuTorch C++ runner. The browser is an operator terminal only. No cloud inference endpoint is configured. Firebase synchronization is disabled by default and, if enabled, carries records only.

This describes the architecture in source code, not a completed offline test. Model files, tokenizer and compiled runner must be installed locally. Before claiming demonstrated offline execution, disconnect the WAN uplink, keep the Pi and browser connected on the same private LAN, run a full inspection and retain an event with `advisory_runtime.status = "COMPLETED"`. Follow [LOCAL_EXECUTION_AND_PERFORMANCE.md](LOCAL_EXECUTION_AND_PERFORMANCE.md).

## Performance reporting

docs/REFERENCE_BENCHMARKS.md contains published Raspberry Pi 5 values for
different models/runtimes. Those are reference results only, not measurements
of this PCB station. Use raspberry_pi/benchmark_onnx.py for detector latency,
and raspberry_pi/benchmark_pipeline.py for still-image vision-plus-Llama
wall time. These do not include the physical conveyor/camera/LED/browser cycle.
Record physical cycles in docs/PI5_COMMISSIONING.md. Power must be measured
with an external meter; no value is inferred from CPU temperature.

## Current go/no-go

See [Phase 1 submission checklist](PHASE1_SUBMISSION_CHECKLIST.md) for the consolidated deliverable links and final eligibility, IP, video and target-device checks.

The source, dashboard, evaluator documentation, model provenance, one-command Pi provisioner, severity policy, benchmarking tools and team-confirmed demonstration video are in the repository. The supplied validation figures are now recorded with screenshot filename/hash provenance, but the raw evaluator output, dataset/split audit and exact checkpoint identity are not available. The final model identity must be matched to the screenshot before the values are tied to the deployed detector. Remaining external evidence includes target-Pi YOLO and Llama/ExecuTorch smoke tests, physical commissioning/offline checks, separate held-out board-level test results, severity approval and video content review. The third-party baseline remains separately attributed; dataset terms and compatibility with the challenge's original-work/Participant Materials requirements must be confirmed.

Official challenge information: https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html
