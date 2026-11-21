# Raspberry Pi 5 deployment

The inspection application runs on a 64-bit Raspberry Pi OS environment. The physical station connects a conveyor arrival sensor, camera and external LED illumination driver to the inspection workflow.

## Runtime components

| Component | Runtime |
|---|---|
| Station controller | Python and GPIO Zero |
| Camera capture and preprocessing | Picamera2 or OpenCV UVC capture |
| Vision detector | YOLOv8 Nano through ONNX Runtime CPU |
| Advisory model | Llama 3.2 Instruct 1B/3B through ExecuTorch LLM Runner |
| Event record | Local JSON inspection event |
| Optional record synchronization | Firebase Realtime Database |

The current source checkout implements the ONNX Runtime CPU vision path. HailoRT on a Hailo NPU / AI HAT+ / AI HAT+ 2 is a separate optional architecture path and is not included in the current deployment code.

## Station I/O

The IR sensor is configured as a digital input. Its BCM GPIO pin, active polarity and pull-up mode are set using the `PCB_IR_*` environment variables. The illumination GPIO switches an external MOSFET or relay driver. It does not directly supply power to the LED strip.

The IR output must be electrically compatible with the Raspberry Pi 3.3 V GPIO interface. Use level shifting or an appropriate interface circuit for higher-voltage sensor outputs. Actual pin assignments are installation-specific and are not assumed in the source.

The station controller initiates one inspection cycle when the IR sensor reports an arriving board. It coordinates the illumination-settle delay and camera capture. Conveyor motor control and emergency-stop circuitry are separate from this controller.

## Inspection coordinator

`raspberry_pi/station_controller.py` watches for the IR arrival transition and launches `raspberry_pi/run_inspection.py`.

The coordinator performs the following sequence:

1. Calls `raspberry_pi/inspect_image.py` for one camera frame.
2. Saves an annotated image and local structured event JSON.
3. Calls `llm_advisory/run_executorch.py` with text-only structured findings.
4. Appends the Llama advisory and response telemetry to the event record.
5. Publishes the completed event when Firebase publication is enabled.

The complete inspection path requires the YOLO ONNX model, an ExecuTorch Llama `.pte` file and its matching tokenizer binary.

## Configuration

The environment template is `raspberry_pi/.env.example`. It contains the station I/O, camera, model, advisory and Firebase settings. The actual BCM pin numbers, active polarities, camera mode and model paths are installation-specific.

Required station values:
- `PCB_IR_GPIO`
- `PCB_LED_DRIVER_GPIO`
- `PCB_LLAMA_MODEL_PATH`
- `PCB_LLAMA_TOKENIZER_PATH`

`PCB_LLAMA_REQUIRED=true` is the full committee architecture mode. Set it to false only for vision-only hardware commissioning; such a run is not a complete vision-plus-advisory inspection.

## Deployment artifacts

The source checkout does not bundle `models/best.onnx`, the ExecuTorch `.pte` model, tokenizer binary or a final processed PCB dataset archive. These artifacts must be matched to the class order recorded in `models/class_names.txt` and the inspection contract. Their hashes and validation records belong in the model release manifest.

## Performance evidence

Vision and advisory metrics are measured independently on the actual Raspberry Pi 5. Vision evidence includes precision, recall, F1, FPS, per-image latency, end-to-end latency, memory and power. Advisory evidence includes time to first token, tokens per second, total response time and peak memory. No laptop or workstation measurement is presented as a Raspberry Pi result.
