# Raspberry Pi 5 deployment and runtime

## Platform

The edge application targets 64-bit Raspberry Pi OS on Raspberry Pi 5. The physical inspection line supplies PCB transport, IR arrival sensing, camera acquisition and external LED illumination.

The base execution profile uses the Pi ARM CPU for both vision and advisory workloads:

| Workload | Runtime | Processor |
|---|---|---|
| Image preprocessing | OpenCV | Raspberry Pi 5 CPU |
| Vision inference | ONNX Runtime | Raspberry Pi 5 ARM CPU |
| Advisory reasoning | Llama 3.2 Instruct 1B/3B through ExecuTorch | Raspberry Pi 5 ARM CPU |
| Local inspection log | JSON | Raspberry Pi 5 storage |
| Optional event synchronization | Firebase Realtime Database | Network data service, not an inference runtime |

A Hailo NPU with HailoRT and AI HAT+ / AI HAT+ 2 is an optional alternative for the vision model only. It does not replace the ExecuTorch Llama advisory. The current station source implements ONNX Runtime CPU inference.

## Hardware interface

The IR sensor is a digital input. The station controller accepts a configurable BCM GPIO, input polarity and pull-up mode. The LED-control output switches an external driver for the separately powered LED strip.

| Environment variable | Function |
|---|---|
| `PCB_IR_GPIO` | BCM GPIO connected to the IR sensor output |
| `PCB_IR_ACTIVE_LOW` | IR active-level polarity |
| `PCB_IR_PULL_UP` | GPIO pull-up mode |
| `PCB_LED_DRIVER_GPIO` | BCM GPIO controlling the external LED driver |
| `PCB_LED_DRIVER_ACTIVE_LOW` | LED-driver input polarity |
| `PCB_CAMERA_MODE` | `usb` or `picamera2` |
| `PCB_CAMERA_INDEX` | USB camera index |
| `PCB_MODEL_PATH` | ONNX detector path |
| `PCB_ILLUMINATION_SETTLE_SECONDS` | Delay between enabling the light and image capture |
| `PCB_TRIGGER_COOLDOWN_SECONDS` | Debounce / minimum interval between accepted board triggers |
| `PCB_CONFIDENCE_THRESHOLD` | Detector confidence threshold |
| `PCB_NMS_IOU_THRESHOLD` | Non-maximum-suppression IoU threshold |
| `PCB_LLAMA_MODEL_PATH` | ExecuTorch Llama `.pte` model path |
| `PCB_LLAMA_TOKENIZER_PATH` | Matching tokenizer binary path |
| `PCB_LLAMA_REQUIRED` | Complete pipeline requirement flag; defaults to true |
| `PCB_FIREBASE_PUBLISH` | Optional completed-event synchronization |
| `PCB_OUTPUT_DIR` | Local inspection event and image directory |

The LED strip is powered through its external driver and suitable supply; the Raspberry Pi GPIO is a logic-level control output. The IR sensor output is electrically compatible with the Pi's 3.3 V GPIO interface. Actual BCM assignments and signal polarities are installation-specific.

## Software sequence

`station_controller.py` listens for the IR arrival transition. Each accepted event enables illumination, waits for the configured settle interval and launches `run_inspection.py`. The station controller turns illumination off after the inspection process exits.

The inspection coordinator runs:

1. `inspect_image.py` for a still image, USB/UVC frame or CSI camera frame.
2. OpenCV preprocessing and YOLOv8 Nano inference through ONNX Runtime CPU.
3. Annotated-image generation and structured inspection-event JSON.
4. `llm_advisory/run_executorch.py` with a text-only prompt generated from the event.
5. Advisory text and runtime telemetry insertion into the event.
6. Optional Firebase publication of the completed event.

The complete inspection path requires the detector file, an ExecuTorch Llama `.pte` package and its matching tokenizer. The coordinator defaults to a required advisory. A vision-only commissioning run is a separate operating profile and does not represent the complete vision-plus-advisory path.

## Installation

The Python station environment uses Raspberry Pi OS packages for GPIO and camera access, together with the repository's runtime requirements.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero

git clone https://github.com/MathewsV-Manoj/pcb-defect-detection.git
cd pcb-defect-detection

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt
```

For CSI camera capture, the Raspberry Pi OS Picamera2 package is used. The station environment is configured from `raspberry_pi/.env.example`; the actual GPIO values, camera mode, model file and Llama assets are deployment-specific.

The configured environment is exported to the station process before launch. The station entry point is:

```bash
python raspberry_pi/station_controller.py
```

## Local event and synchronization model

Each accepted board trigger produces a local JSON record and annotated image under the configured output directory. The event stores the IR and illumination state recorded at capture, along with board ID, timestamp, model identity, inference latency and detection details.

Firebase is an optional synchronization layer:

- `/live` — latest station and inspection state.
- `/inspections/{record_id}` — retained inspection events.

The camera, vision model and advisory model run locally. Firebase does not receive camera frames for inference and is not used to run the Llama model.

## Performance measurement

Vision and advisory performance are measured independently on the Raspberry Pi 5.

| Vision measurement | Advisory measurement |
|---|---|
| Per-class precision, recall and F1 | Time to first token |
| FPS and per-image latency | Tokens per second |
| End-to-end trigger-to-record latency | Total response time |
| Peak RAM and power | Peak RAM and power |
| Sustained-run reliability | Response consistency and failure rate |

The measurement record includes the Pi memory configuration, operating system, ONNX Runtime / ExecuTorch versions, model hashes, input size, sample count and evaluation split. Workstation measurements are not represented as Pi 5 measurements.
