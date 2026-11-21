# Project implementation record

## Physical station

The project includes a conveyor-based PCB inspection station with:
- IR sensor for PCB arrival detection.
- Camera for inspection image acquisition.
- External LED strip for controlled illumination.
- Raspberry Pi 5 as the edge-computing target.

The physical station and its operation are documented in the project demonstration video.

## Software architecture

| Component | Source location | Function |
|---|---|---|
| IR-triggered station acquisition | `raspberry_pi/station_controller.py` | Detect board arrival, control the illumination driver and initiate one-frame inspection |
| Vision inference | `raspberry_pi/inspect_image.py` | OpenCV preprocessing and YOLO ONNX CPU inference |
| Event publishing | `raspberry_pi/firebase_client.py` | Publish structured events to Firebase Realtime Database |
| Operator interface | `dashboard/index.html` | Present inspection result, advisory and history |
| Advisory prompt | `llm_advisory/prompt.py` | Build a text-only prompt from structured findings |
| Advisory runtime entry point | `llm_advisory/run_executorch.py` | Invoke the ExecuTorch LLM runner and capture response telemetry |
| Advisory boundary tests | `tests/test_advisory_contract.py` | Verify structured fields are included and image payloads are excluded |
| Event contract | `schemas/` | Define defect type, severity, location and confidence fields |

## Runtime architecture

The base vision path is ONNX Runtime on the Raspberry Pi 5 ARM CPU. A Hailo NPU and HailoRT through AI HAT+ / AI HAT+ 2 form an optional vision-acceleration path. The advisory path is separate: Llama 3.2 Instruct 1B/3B through ExecuTorch on the Pi ARM CPU.

## Evidence and release artifacts

The repository contains source for image inference, station-trigger handling, event publishing, prompt construction, the ExecuTorch runner entry point, dashboard presentation and advisory contract tests. The final YOLO detector binary, complete training dataset archive, ExecuTorch model package and target-device benchmark data are not bundled in the current source checkout. The model release manifest records the binary status; no unverified precision, recall, F1, FPS, latency, memory or power figures are stated.

## Hardware interface boundaries

IR and illumination GPIO assignments are configurable rather than hard-coded. The illumination output is intended to switch an external MOSFET/relay driver. It is not a power output for the LED strip. The station controller does not implement conveyor motor control or emergency-stop circuitry.
