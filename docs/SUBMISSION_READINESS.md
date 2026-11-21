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
- Technical report, workflow diagram, deployment guide, evaluator checklist and committed demonstration MP4.

## Remaining work and evidence

| Item | Repository state | Required action |
|---|---|---|
| Final vision checkpoint | best.pt is not in the repository | Use the verified three-class training run; retain checkpoint path and SHA-256 |
| Final ONNX detector | best.onnx and metadata are not in the repository | Export from the same checkpoint; check input/output contract and prediction parity |
| Dataset audit | Import template and source manifest exist; processed data and final import audit are absent | Add the actual image/label manifest, source licenses, board-level grouping and split audit |
| Detection quality | No project test metrics or predictions are committed | Evaluate held-out boards; record per-class precision/recall/F1, confusion matrix, mAP@50 and mAP@50–95 |
| Llama model package | Pinned downloader and model revision are committed; licensed PTE/tokenizer are not stored in Git | Download locally after accepting upstream terms; preserve download_manifest.json and hashes |
| ExecuTorch runner | Pi 5 build script is committed; compiled binary is not stored in Git | Build on Linux x86_64, copy runtime to Pi, record exact ExecuTorch commit and smoke-test there |
| Llama integration | Production coordinator calls the runner and requires advisory by default | Run the real event smoke test and one complete station cycle; keep the model output JSON |
| Severity | Current event severity is UNASSESSED | Define and validate a board-specific severity policy with an electrical/QA owner; until then retain UNASSESSED |
| Pi commissioning | GPIO map, capture/illumination verification and full-cycle record are not supplied | Complete docs/PI5_COMMISSIONING.md with actual physical checks |
| Runtime measurements | Scripts are committed; no project results are committed | Run both benchmark scripts on the actual Pi and retain output JSON |
| Physical throughput | No conveyor-cycle data is committed | Time complete capture-to-dashboard cycles; log attempted/successful cycles, missed/duplicate triggers and failures |
| Demo content | MP4 file is present but not independently reviewed | Watch it and confirm the current hardware, detector output, Llama advisory and dashboard are shown |
| Eligibility | README lists three students from Muthoot Institute of Technology and Science | Verify Team Leader, faculty mentor, college nomination and registration details |

## Llama deployment: configured, not papered over

The default station configuration now points to the pinned Llama 3.2 1B
Instruct SpinQuant INT4/EO8 ExecuTorch package and sets PCB_LLAMA_REQUIRED=true.
The package downloader and Pi 5 runner build script are in the repository.
The model files are intentionally downloaded locally because the upstream
model is licensed and the PTE is approximately 1.14 GB.

The required sequence is:

1. Accept the upstream model terms and run llm_advisory/download_model.py.
2. Run llm_advisory/build_pi5_runner.sh on a Linux x86_64 build host.
3. Copy models/llama, including runtime, to the Raspberry Pi.
4. Run the smoke test in models/llama/README.md.
5. Run one real inspection and verify that advisory_runtime.status is COMPLETED.

This is the implementation path. It is not valid to say the model has already
run on the team's device until steps 3–5 have been completed and evidence saved.
The model receives the structured detection record only; it does not see the
PCB image, alter detections, control actuators or make the final disposition.

## Performance reporting

docs/REFERENCE_BENCHMARKS.md contains published Raspberry Pi 5 values for
different models/runtimes. Those are reference results only, not measurements
of this PCB station. Use raspberry_pi/benchmark_onnx.py for detector latency,
and raspberry_pi/benchmark_pipeline.py for still-image vision-plus-Llama
wall time. These do not include the physical conveyor/camera/LED/browser cycle.
Record physical cycles in docs/PI5_COMMISSIONING.md. Power must be measured
with an external meter; no value is inferred from CPU temperature.

## Current go/no-go

The implementation and reproducible deployment route are now in the source
repository. The remaining gap is target-specific evidence and project-owned
model assets: final trained YOLO files, a processed/audited dataset, held-out
accuracy, actual Llama execution on the Pi, severity policy, and hardware
commissioning results. Do not represent these as complete until those files
and records exist.

Official challenge information: https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html
