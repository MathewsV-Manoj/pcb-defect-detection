# Raspberry Pi 5 inspection station

The Raspberry Pi 5 is the edge-computing controller for the conveyor-based inspection station. The physical station includes a conveyor, an IR presence sensor, an inspection camera and an externally powered LED strip.

## Station sequence

1. The conveyor transports the PCB into the inspection point.
2. The IR sensor detects board arrival.
3. The GPIO station controller switches the external illumination driver on.
4. After the configured illumination-settle interval, the controller launches the integrated inspection coordinator.
5. The coordinator invokes the ONNX vision process, saves an annotated image and structured event, runs the text-only Llama/ExecuTorch advisory, appends advisory telemetry and then optionally publishes the completed event.
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

## Complete inspection orchestration

The station controller launches `run_inspection.py`, which sequences the vision and advisory components:

1. Run `inspect_image.py` with the captured camera frame.
2. Read the local JSON event containing type, severity, location and confidence.
3. Run `llm_advisory/run_executorch.py` with text-only structured findings.
4. Append advisory text and runtime telemetry to the same event record.
5. Publish the completed event to Firebase when event synchronization is enabled.

The Llama model and matching tokenizer are configured through `PCB_LLAMA_MODEL_PATH` and `PCB_LLAMA_TOKENIZER_PATH`. The complete station workflow requires both assets. `PCB_LLAMA_REQUIRED=false` is reserved for vision-only hardware commissioning; it is not the full selection-architecture mode.

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
