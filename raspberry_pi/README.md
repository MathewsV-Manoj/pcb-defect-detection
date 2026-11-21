# Raspberry Pi 5 station software

The station controller provides the IR arming state machine, board-position capture trigger, illumination control, Pi-hosted web/API service and operator-triggered inspection launch.

## Operating sequence

1. Hold a hand in front of the IR sensor for approximately three seconds.
2. The station arms and waits for the sensor to be released.
3. Place the PCB on the conveyor; the belt transports it towards the camera.
4. The next IR activation identifies the PCB at the camera position.
5. The Pi enables the external LED driver, waits for the illumination settle time and captures a frame.
6. The image is saved locally and served to the laptop browser.
7. The operator clicks **Run inspection on Raspberry Pi**.
8. The browser sends `POST /api/run-inspection`; the Pi executes vision and advisory processing using the saved frame.

## Processing sequence

The station controller captures the board image before inference. The inspection coordinator then performs OpenCV preprocessing, YOLO ONNX inference, detection decoding and annotation, structured event creation, text-only Llama/ExecuTorch advisory generation and optional Firebase publication.

The current OpenCV detector preprocessing is letterbox resize/padding, BGR-to-RGB conversion, float32 normalization to `[0,1]` and NCHW tensor creation. The three-channel YOLO path does not use grayscale conversion or a separate handcrafted trace-detection algorithm.

## Camera and GPIO configuration

`station_controller.py` uses gpiozero for IR sensing and the external illumination-driver control. GPIO assignments and polarities are environment-configured.

| Variable | Purpose |
|---|---|
| `PCB_IR_GPIO` | IR sensor BCM input |
| `PCB_IR_ACTIVE_LOW` | IR active polarity |
| `PCB_IR_PULL_UP` | IR input pull-up setting |
| `PCB_LED_DRIVER_GPIO` | External LED driver BCM output |
| `PCB_LED_DRIVER_ACTIVE_LOW` | Driver input polarity |
| `PCB_CAMERA_MODE` | `usb` or `picamera2` |
| `PCB_CAMERA_INDEX` | USB camera index |
| `PCB_MODEL_PATH` | ONNX detector file |
| `PCB_ILLUMINATION_SETTLE_SECONDS` | Delay before capture |
| `PCB_OUTPUT_DIR` | Local capture, event and annotated-image directory |
| `PCB_LLAMA_MODEL_PATH` | ExecuTorch `.pte` path |
| `PCB_LLAMA_TOKENIZER_PATH` | Matching tokenizer path |
| `PCB_FIREBASE_PUBLISH` | Optional completed-event synchronization |

The LED strip uses an external driver and power supply. The Pi GPIO provides only the control signal. The IR electrical output must be compatible with 3.3 V GPIO.

## Inspection software

| File | Responsibility |
|---|---|
| `station_controller.py` | IR arming, position trigger, illumination, camera frame capture and HTTP service |
| `inspect_image.py` | OpenCV preprocessing, YOLO ONNX inference, localization and event creation |
| `run_inspection.py` | Sequences vision, ExecuTorch advisory, event update and optional synchronization |
| `firebase_client.py` | Publishes completed event records to Firebase |

The required Llama advisory uses ExecuTorch on the Raspberry Pi ARM CPU. The `.pte` model and matching tokenizer are separate deployment artifacts. The optional HailoRT path applies to vision acceleration only and is not part of this ONNX base implementation.
