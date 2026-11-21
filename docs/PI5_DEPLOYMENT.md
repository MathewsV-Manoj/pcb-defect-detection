# Raspberry Pi 5 station service and deployment

## Service architecture

`raspberry_pi/station_controller.py` runs the IR state machine, camera capture, Pi-hosted HTTP service and operator-triggered inference launch. The operator opens the web page from a laptop browser using the Raspberry Pi's IP address. The website and its API are served by the Pi.

The operator button sends a command to the Pi; image processing and both model pipelines run locally on the Pi.

## Physical operating sequence

1. At station startup, hold a hand in front of the IR sensor for approximately three seconds.
2. The station enters a latched armed state.
3. Release the sensor and place the PCB on the conveyor.
4. The conveyor transports the PCB to the camera position.
5. The next active transition on the IR input identifies the board at the camera position.
6. The station enables the external LED driver, waits for the configured settle time and captures a frame.
7. The Pi serves the captured frame to the browser for visual verification.
8. The operator clicks **Run inspection on Raspberry Pi**.
9. The browser sends `POST /api/run-inspection`; the Pi processes the stored image and returns the result to the dashboard.

The sensor is configured with a three-second hold event. A short activation that ends before the hold interval does not arm the station. After a successful hold, release is required before the next IR activation can be treated as PCB arrival. The armed state persists after each completed inspection, so subsequent boards do not require another hand-hold. Restarting the station controller resets the arming state.

## Runtime components

| Component | Implementation |
|---|---|
| IR arming and board-position state | gpiozero `Button` with a three-second hold event |
| Illumination | gpiozero output controlling an external LED driver |
| Camera capture | OpenCV UVC capture or Picamera2 CSI capture |
| Pi-hosted website and API | Python standard-library `ThreadingHTTPServer` |
| Preprocessing | OpenCV letterbox, BGR-to-RGB conversion, float32 normalization, NCHW |
| Base vision runtime | YOLOv8 Nano through ONNX Runtime CPU |
| Optional vision acceleration | HailoRT on Hailo NPU / AI HAT+ / AI HAT+ 2 |
| Advisory runtime | Llama 3.2 Instruct through ExecuTorch on Pi ARM CPU |
| Event log | Local JSON and annotated image |
| Optional synchronization | Firebase Realtime Database |

Hailo is a vision accelerator option only. The Llama advisory remains a separate ExecuTorch pipeline on the Pi ARM CPU.

## Operator API

| Method and path | Function |
|---|---|
| `GET /` | Serve `dashboard/index.html` |
| `GET /api/health` | Return service health |
| `GET /api/status` | Return arming, IR, illumination, capture and inspection state |
| `GET /api/capture.jpg` | Serve the saved raw capture |
| `GET /api/annotated.jpg` | Serve the annotated result after inference |
| `GET /api/history` | Return recent local inspection events |
| `POST /api/run-inspection` | Launch the inspection coordinator on the captured frame |

The API is served from the same origin as the dashboard, so the browser can call it without a separate backend or CORS configuration. The station service is intended for a trusted private network and must not be port-forwarded or exposed directly to the public internet.

## Image preprocessing

The current YOLO contract uses a three-channel 640 × 640 RGB input. OpenCV letterboxes and pads the frame, converts BGR to RGB, normalizes float32 values to `[0,1]` and arranges the input as NCHW. The inference code does not perform grayscale conversion or a separate handcrafted line-continuity/edge-detection pass. The learned YOLO model localizes the configured defect classes from the three-channel image.

## Installation

On 64-bit Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero

git clone https://github.com/MathewsV-Manoj/pcb-defect-detection.git
cd pcb-defect-detection

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt

cp raspberry_pi/.env.example raspberry_pi/.env
nano raspberry_pi/.env
```

Set the actual BCM GPIO values, sensor and driver polarity, camera mode, detector path and ExecuTorch model/tokenizer paths in the environment file. The LED strip must be supplied through its external driver and a suitable power source. The IR output must be electrically compatible with the Pi's 3.3 V GPIO interface.

Load the station environment and launch the service:

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

From the laptop browser on the same trusted LAN, open:

```text
http://<RASPBERRY_PI_IP>:8080/
```

The Pi address can be read on the device with `hostname -I`.

## Vision and advisory execution

After the operator command, the station service invokes `raspberry_pi/run_inspection.py` with the captured image path. The coordinator runs:

1. OpenCV image preprocessing and YOLOv8 Nano ONNX inference.
2. Detection decoding, class mapping, bounding-box remapping and annotation.
3. Structured event creation and local JSON storage.
4. `llm_advisory/run_executorch.py` with the text-only findings prompt.
5. Advisory and runtime telemetry insertion into the event.
6. Optional Firebase publication when enabled.

The complete run requires `models/best.onnx`, an ExecuTorch Llama `.pte` model and its matching tokenizer. If the advisory assets are absent or the runner fails, the UI reports that the vision result is available but the required advisory did not complete. A vision-only commissioning run is not the full submission workflow.

## Local records and optional Firebase

The raw captured frame, annotated frame, event JSON and advisory JSON are stored under the configured `PCB_OUTPUT_DIR`. The dashboard reads current status and history from the Pi station API. Firebase synchronization can be enabled after configuring its URL and authentication; it is not required for the laptop-to-Pi run button and it does not perform inference.

## Performance measurement

Vision and advisory metrics are measured independently on the Raspberry Pi 5:

| Vision | Advisory |
|---|---|
| Per-class precision, recall and F1 | Time to first token |
| FPS and per-image inference latency | Tokens per second |
| IR trigger to event latency | Total response time |
| Peak RAM, power and temperature | Peak RAM, power and temperature |
| Capture/inference reliability | Response validity and consistency |

Each measurement is tied to the Pi RAM configuration, OS, runtime versions, model hashes, input size, dataset version and held-out split.
