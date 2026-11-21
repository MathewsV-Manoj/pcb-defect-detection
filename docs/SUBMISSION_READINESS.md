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
| Vision model deployment | Model binaries are intentionally not tracked in Git | Run `bash scripts/provision_pi5.sh`; it fetches the attributed six-class YOLOv8s checkpoint, verifies its SHA-256 and exports the Pi ONNX model. This is an external baseline, not a team-trained checkpoint |
| Project-trained three-class model | No project-owned final checkpoint is present | Train only if the team has its own audited three-class dataset; otherwise report the credited upstream baseline accurately |
| Dataset audit | Import template and source manifest exist; processed data and final import audit are absent | Add the actual image/label manifest, source licenses, board-level grouping and split audit |
| Detection quality | No project test metrics or predictions are committed | Evaluate held-out boards; record per-class precision/recall/F1, confusion matrix, mAP@50 and mAP@50–95 |
| Llama model package | Pinned downloader and model revision are committed; licensed PTE/tokenizer are not stored in Git | Download locally after accepting upstream terms; preserve download_manifest.json and hashes |
| ExecuTorch runner | Pi-native build script and one-command provisioner are committed; compiled binary is not stored in Git | Run `bash scripts/provision_pi5.sh`; retain the smoke-test output and build metadata |
| Llama integration | Production coordinator calls the runner and requires advisory by default | Run the real event smoke test and one complete station cycle; keep the model output JSON |
| Severity | Configurable provisional type-based policy is implemented | Obtain QA/engineering approval against the actual board. Until approval, describe it as provisional screening priority, not validated severity assessment |
| Pi commissioning | GPIO map, capture/illumination verification and full-cycle record are not supplied | Complete docs/PI5_COMMISSIONING.md with actual physical checks |
| Runtime measurements | Scripts are committed; no project results are committed | Run both benchmark scripts on the actual Pi and retain output JSON |
| Physical throughput | No conveyor-cycle data is committed | Time complete capture-to-dashboard cycles; log attempted/successful cycles, missed/duplicate triggers and failures |
| Demo video | MP4 is present; team confirms video production is complete | Include the repository MP4 or a shareable public/unlisted URL in the submission. Video contents have not been independently inspected in this review |
| Eligibility | README lists three students from Muthoot Institute of Technology and Science | Verify Team Leader, faculty mentor, college nomination and registration details |

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

The source, dashboard, evaluator documentation, model provenance, one-command Pi provisioner, severity policy, benchmarking tools and team-confirmed demonstration video are in the repository. The remaining go/no-go items are to execute the provisioner on the actual Pi 5, verify the ONNX and ExecuTorch smoke tests, complete physical commissioning/offline checks, and produce project-owned held-out accuracy/runtime results. A separate team-trained three-class checkpoint is not currently present; the deployable fallback is the clearly attributed upstream baseline.

Official challenge information: https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html
