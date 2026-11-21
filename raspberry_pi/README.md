# Raspberry Pi 5 inspection station

The Raspberry Pi 5 is the edge-computing controller for the conveyor-based inspection station. The physical station includes a conveyor, an IR presence sensor, an inspection camera and an externally powered LED strip.

## Station sequence

1. The conveyor transports the PCB into the inspection point.
2. The IR sensor detects board arrival.
3. The GPIO station controller switches the external illumination driver on.
4. After the configured illumination-settle interval, the controller starts a one-frame camera inspection.
5. The ONNX inference process preprocesses the image, runs YOLO inference, saves an annotated image and serializes an inspection event.
6. The illumination driver is switched off after the inspection process exits.

The station controller supports a USB/UVC camera or a CSI camera through Picamera2. Its GPIO numbers, sensor polarity and illumination-driver polarity are environment-configured to match the assembled wiring. The script does not control the conveyor motor or the emergency-stop circuit.

## Vision inference

`inspect_image.py` is the base Raspberry Pi CPU path and uses ONNX Runtime with `CPUExecutionProvider`. It supports a still image, one frame from a USB camera or one frame from a CSI camera.

The deployment class map is:

| ID | Class |
|---:|---|
| 0 | missing_hole |
| 1 | open_circuit |
| 2 | short_circuit |

The matching model file is expected at `models/best.onnx`. The model binary is a separate release artifact; no trained detector binary is included in this source checkout.

## GPIO station controller

`station_controller.py` listens for the IR sensor's active transition and initiates one inspection per board-arrival event. The following environment variables bind the code to the actual station wiring:

| Variable | Meaning |
|---|---|
| `PCB_IR_GPIO` | BCM pin connected to the IR sensor's digital output |
| `PCB_IR_ACTIVE_LOW` | `true` when a low level represents board detection |
| `PCB_IR_PULL_UP` | `on`, `off` or `floating` input configuration |
| `PCB_LED_DRIVER_GPIO` | BCM pin that switches the external LED driver |
| `PCB_LED_DRIVER_ACTIVE_LOW` | Driver input polarity |
| `PCB_CAMERA_MODE` | `usb` or `picamera2` |
| `PCB_CAMERA_INDEX` | USB camera index when `PCB_CAMERA_MODE=usb` |
| `PCB_MODEL_PATH` | ONNX model path |
| `PCB_ILLUMINATION_SETTLE_SECONDS` | Delay between enabling illumination and capture |
| `PCB_TRIGGER_COOLDOWN_SECONDS` | Minimum interval between accepted triggers |
| `PCB_FIREBASE_PUBLISH` | `true` to publish events using configured Firebase credentials |

The LED strip must use an external MOSFET/relay driver and its own suitable power supply. The Raspberry Pi GPIO pin is a logic-level control signal only. The IR output must be compatible with 3.3 V GPIO; higher-voltage outputs require appropriate level shifting. The actual pin assignments and interface polarity are installation-specific and are not hard-coded.

## Runtime separation

- **Vision:** ONNX Runtime on the Pi ARM CPU. HailoRT on a Hailo NPU / AI HAT+ / AI HAT+ 2 is an optional vision acceleration path.
- **Advisory:** Llama through ExecuTorch on the Pi ARM CPU. It receives structured detection findings and remains independent of the vision runtime.

The controller records an IR-triggered source status and illumination state in the inspection event. Severity is set to `UNASSESSED` unless a board-specific severity policy is supplied; confidence is never substituted for severity.
