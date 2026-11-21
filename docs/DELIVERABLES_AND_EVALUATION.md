# Deliverables and evaluation framework

## Submission deliverables

| Deliverable | Evidence |
|---|---|
| Source code | IR state machine, Pi HTTP service, camera capture, OpenCV/ONNX inference, inspection coordinator, ExecuTorch advisory runner, operator UI, event schema and tests |
| Application | Conveyor station with IR-guided board positioning, controlled LED illumination, camera capture and Raspberry Pi 5 edge-processing workflow |
| Demonstration video | IR arming, PCB loading and transport, camera-position confirmation, illumination/capture, browser preview, operator run command and Pi-side results |
| Technical report | Physical sequence, UI/API command flow, preprocessing, separate inference runtimes, event contract, dataset strategy and evaluation methodology |

## End-to-end acceptance sequence

| Stage | Expected behaviour/evidence |
|---|---|
| IR arming | At station startup, continuous hand presence for approximately three seconds arms the station once; the armed state persists across subsequent PCB cycles |
| Sensor release | Station enters the board-waiting state and remains armed until controller restart |
| PCB transport | PCB is placed on the conveyor and transported towards the imaging zone |
| Camera-position detection | The next IR activation identifies the PCB at the camera position |
| Illumination and capture | External LED strip turns on through its driver; camera frame is saved on the Pi |
| Browser preview | Laptop browser displays the image served by the Pi |
| Operator authorization | Run Inspection button sends a command to the Pi station API |
| Vision processing | Pi preprocesses the saved frame and runs the selected YOLO model |
| Advisory | Pi executes the structured Llama/ExecuTorch advisory on the Pi ARM CPU |
| Result return | UI displays decision, defect class, severity, location, confidence, annotated image and advisory |
| Record retention | Local event JSON and inspection history are available; Firebase sync is optional |

## Runtime profiles

| Workload | Base profile | Optional profile |
|---|---|---|
| Vision | YOLOv8 Nano through ONNX Runtime on Raspberry Pi 5 ARM CPU | HailoRT on Hailo NPU through AI HAT+ / AI HAT+ 2 |
| Advisory | Llama 3.2 Instruct 1B/3B through ExecuTorch on Raspberry Pi 5 ARM CPU | No alternate runtime replaces ExecuTorch in the required advisory architecture |

Hailo is an optional vision accelerator only. The Llama advisory remains a separate ExecuTorch process on the Pi ARM CPU.

## Image preprocessing and detection

The current ONNX model contract uses a three-channel 640 × 640 input. OpenCV letterboxes and pads the source image, converts BGR to RGB, normalizes float32 values to `[0,1]` and produces an NCHW tensor. The deployed detector path does not use grayscale conversion or a separate handcrafted trace-continuity algorithm. Defect localization is performed by the configured YOLO detector.

## Detection quality

| Metric | Evaluation |
|---|---|
| Per-class precision | Correct predictions among predictions of each defect class |
| Per-class recall | Detected ground-truth defects among annotated instances |
| Per-class F1 | Harmonic mean of per-class precision and recall |
| Confusion matrix | Correct and incorrect class assignments |
| False positives / false negatives | Normal regions falsely flagged and actual defects missed |
| Localization | Bounding-box alignment and small-defect localization |
| mAP@50 and mAP@50–95 | Detection performance at the stated IoU criteria |

Evaluation uses held-out boards or capture groups so views of the same physical PCB do not leak across train and test splits.

## Vision runtime measurements

- FPS and sustained throughput.
- Per-image inference latency.
- End-to-end latency from IR-triggered capture through the completed result.
- Peak RAM, device power and CPU temperature.
- Trigger, camera and inference reliability.

## Advisory runtime measurements

- Time to first token.
- Tokens per second.
- Total response time.
- Peak memory and power.
- JSON/output validity.
- Grounding in defect type, severity and location.
- Absence of new detections or independent PASS/REJECT claims.

## Operator experience

The operator workflow is evaluated for the reliability of the three-second arming sequence, board-position trigger, capture preview, clear Run command acknowledgement, result clarity, advisory usefulness and inspection-history traceability.

## Reproducibility

Each numeric result is accompanied by Raspberry Pi model and RAM configuration, operating system and runtime versions, vision and Llama model hashes, tokenizer identity, dataset version and held-out split, image size, detector thresholds and number of repeated measurements. Workstation measurements are not reported as Raspberry Pi results.

## Release evidence

The public source repository contains station/API source, dashboard, vision and advisory orchestration code, event schemas and automated software contract tests. The trained YOLO detector, ExecuTorch `.pte` model and matching tokenizer, complete processed PCB dataset and validated Pi 5 benchmark report are not packaged in the current source release. No numerical performance result is claimed without the corresponding release artifact and device measurement.
