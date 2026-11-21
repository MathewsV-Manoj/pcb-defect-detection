# Phase 1 submission readiness

**Challenge:** Bharat AI-SoC Challenge 2026–27  
**Problem statement:** PS5 — Real-time industrial defect detection and quality-control assistant  
**Official Phase 1 deadline:** 23 November 2026  
**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection

## What is already in the repository

- Raspberry Pi station controller for the IR arming/capture sequence, illumination and camera.
- Pi-hosted operator page and same-origin inspection API.
- OpenCV preprocessing and three-class YOLOv8 ONNX inference source.
- Detection decoding, class-wise NMS, annotated-image creation and structured inspection events.
- Text-only Llama advisory prompt and ExecuTorch runner source.
- Local inspection history and Firebase Realtime Database synchronization code.
- Dataset import manifest template, source manifest, annotation utility, YOLO training/export source and software tests.
- Project report, deployment guide, workflow diagram and a committed MP4 demonstration file.

## Items preventing a complete submission-ready release

| Item | Current repository state | Required action/evidence |
|---|---|---|
| Final vision checkpoint | `models/best.pt` is absent | Provide the checkpoint from the verified three-class training run |
| Final ONNX detector | `models/best.onnx` is absent | Export from the same checkpoint, verify its hash and keep the generated metadata JSON |
| Dataset provenance | Source list and import template exist; processed dataset and audit are absent | Preserve the actual import manifest, board-level splits and generated audit for the final run |
| Detection evaluation | No final metrics or test predictions are committed | Add held-out per-class precision/recall/F1, confusion matrix, mAP@50, mAP@50–95 and representative errors |
| Llama model | No ExecuTorch `.pte` file is present | Supply the Llama-family model package used by the advisory runner |
| Matching tokenizer | Not present | Supply the tokenizer paired with that exact Llama model |
| ExecuTorch on Pi | Runner source exists; target build/runtime is not verified | Record ExecuTorch revision/build, verify imports and run the advisory on the actual Pi |
| Severity | Events use `UNASSESSED` | Define and validate the project's board-specific severity rule, or clearly report severity as not implemented |
| Pi commissioning | Pin mapping, capture/illumination verification and full-cycle test are not recorded | Complete the commissioning sheet with the actual hardware and test results |
| Runtime measurements | No Pi benchmark results are included | Measure detector latency/FPS/RAM/temperature and full capture-to-result time |
| Demo contents | MP4 file is present, but source review did not verify its scenes | Watch the committed video and confirm it shows the real station and actual output; upload it to a shareable link if the form requires one |
| Eligibility | README lists three members from Muthoot Institute of Technology and Science | Verify team leader, faculty mentor, college nomination and registration details against the official registration record |

## Important implementation boundaries

- The deployed vision path in this repository is YOLOv8 Nano exported to ONNX and run by ONNX Runtime on the Raspberry Pi 5 CPU.
- The image is processed on the Pi; the laptop browser only reviews the frame, requests inspection and displays the result.
- The Llama advisory receives structured detection results only. It does not inspect the image or change detector decisions.
- Firebase synchronization copies inspection events. It does not perform inference.
- The class order is fixed: `0 missing_hole`, `1 open_circuit`, `2 short_circuit`.
- No accuracy, latency, FPS, power or severity claim should be added without a measured record.

## Go/no-go

**Not yet ready for final Phase 1 submission as a complete working system.** The code, application source, report and video file are present, but the required on-device Llama/ExecuTorch package is missing. The trained YOLO files and target-device evidence are also missing from the repository, and severity remains unassessed. Complete the model handoff and Pi validation before representing the full system as operational.

Official challenge information: https://armbharatchallenge.com/
