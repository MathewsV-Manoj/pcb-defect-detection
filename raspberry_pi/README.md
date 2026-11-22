# Raspberry Pi-targeted station software

This folder contains the station-controller, image inference, inspection coordinator, benchmark and optional Firebase record-synchronization source. The documented target is a Raspberry Pi 5. Source presence does not establish that the team's physical station has been commissioned or tested.

## Intended station sequence

The controller source describes an initial IR arming gesture, a later IR trigger, LED-driver activation, image capture and serving the captured frame to the operator dashboard. The operator reviews the frame and requests inspection. The Pi-side software runs the ONNX detector and sends structured findings to the text-only advisory runner.

The IR sensor reports presence at its trigger point; it does not measure exact board coordinates in the image. Mechanical alignment must be confirmed on the physical station. The controller does not claim to control conveyor speed/direction.

## Project model requirement

The inference path accepts the project's native three-class ONNX model only:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The ONNX sidecar is mandatory. It must match the model SHA-256, declare VERIFIED_PROJECT_TRAINING and random initialization from an architecture YAML, declare pretrained_weights_used=false, and contain the native class order. External six-class PCB detector mappings are not accepted.

Train, audit and export from the development machine using pcb_engine_kit/README.md before copying the model to models/best.onnx and models/best.onnx.json on the Pi.

## Advisory component

The advisory uses the third-party Llama 3.2 1B Instruct foundation model through ExecuTorch. It receives structured text findings only. It is not trained by the project team and must not be described as an original project model. See llm_advisory/README.md for upstream attribution and setup.

## Configuration

The controller reads settings from the process environment. See .env.example for the full list.

| Variable | Purpose |
|---|---|
| PCB_IR_GPIO | IR sensor BCM input |
| PCB_IR_ACTIVE_LOW | IR sensor active polarity |
| PCB_IR_PULL_UP | Input pull-up setting |
| PCB_LED_DRIVER_GPIO | External LED driver BCM output |
| PCB_LED_DRIVER_ACTIVE_LOW | Driver input polarity |
| PCB_CAMERA_MODE | usb or picamera2 |
| PCB_CAMERA_INDEX | USB camera index |
| PCB_MODEL_PATH | Project ONNX detector path |
| PCB_CONFIDENCE_THRESHOLD | Detector confidence threshold |
| PCB_NMS_IOU_THRESHOLD | NMS IoU threshold |
| PCB_ILLUMINATION_SETTLE_SECONDS | Delay from illumination to capture |
| PCB_OUTPUT_DIR | Local capture/event directory |
| PCB_LLAMA_MODEL_PATH | ExecuTorch PTE model |
| PCB_LLAMA_TOKENIZER_PATH | Matching tokenizer |
| PCB_LLAMA_RUNNER_PATH | ExecuTorch C++ runner |
| PCB_FIREBASE_PUBLISH | Optional event-record synchronization |

The station controller does not load a .env file itself. Export it before launching:

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

## Source map

| File | Responsibility |
|---|---|
| station_controller.py | IR state, illumination command, camera capture and HTTP service |
| inspect_image.py | Project ONNX provenance checks, OpenCV preprocessing, inference and event creation |
| run_inspection.py | Detector, text advisory and optional event synchronization |
| benchmark_onnx.py | Detector runtime measurements |
| benchmark_pipeline.py | Still-image vision-plus-advisory software measurements |
| firebase_client.py | Optional event-record replication |

The browser is a display/control client and does not run model inference. Firebase copies event data and does not run either model. Physical wiring, actual Pi execution, offline behaviour and performance remain unverified until their commissioning evidence is recorded.
