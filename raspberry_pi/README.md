# Raspberry Pi station software

The Raspberry Pi runs the IR state machine, LED driver output, camera capture, OpenCV/ONNX inspection process, ExecuTorch advisory coordinator and the operator web page. The operator opens the page from a laptop on the same trusted private network.

## Station operation

At the beginning of a session, the operator holds a hand in front of the IR sensor for about three seconds and then releases it. The station stays armed. When the next PCB reaches the sensor trigger point, the controller turns on the LED driver and captures one frame.

The Pi saves the frame and serves it to the browser. The operator checks the image and presses **Run inspection on Raspberry Pi**. The Pi runs the detector, writes an annotated image and event JSON, then sends structured findings to the text-only Llama advisory runner through ExecuTorch.

The armed state remains set after an inspection, so the next board does not need another hand-hold. Restarting the controller clears the armed state.

The IR sensor reports presence at its trigger point. It does not measure the board's exact position in the camera image; that is set by the mechanical layout.

## Configuration

The controller reads these values from the process environment. See `.env.example` for the full list.

| Variable | Use |
|---|---|
| `PCB_IR_GPIO` | IR sensor BCM input |
| `PCB_IR_ACTIVE_LOW` | IR sensor active polarity |
| `PCB_IR_PULL_UP` | IR input pull-up setting |
| `PCB_LED_DRIVER_GPIO` | External LED driver BCM output |
| `PCB_LED_DRIVER_ACTIVE_LOW` | LED driver input polarity |
| `PCB_CAMERA_MODE` | `usb` or `picamera2` |
| `PCB_CAMERA_INDEX` | USB camera index |
| `PCB_MODEL_PATH` | ONNX detector path |
| `PCB_CONFIDENCE_THRESHOLD` | Detector confidence threshold |
| `PCB_NMS_IOU_THRESHOLD` | NMS IoU threshold |
| `PCB_ILLUMINATION_SETTLE_SECONDS` | Delay between LED activation and capture |
| `PCB_OUTPUT_DIR` | Local capture and event directory |
| `PCB_LLAMA_MODEL_PATH` | ExecuTorch `.pte` model |
| `PCB_LLAMA_TOKENIZER_PATH` | Matching tokenizer |
| `PCB_FIREBASE_PUBLISH` | Enable event synchronization |

The station controller does not read the `.env` file itself. Export it into the shell before starting the controller:

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

## Source files

| File | Responsibility |
|---|---|
| `station_controller.py` | IR state, illumination, camera capture and Pi HTTP service |
| `inspect_image.py` | OpenCV preparation, ONNX inference, NMS and event creation |
| `run_inspection.py` | Vision inference, ExecuTorch advisory and configured Firebase synchronization |
| `benchmark_onnx.py` | Measures Pi-side ONNX detector runtime |
| `firebase_client.py` | Copies completed events to Firebase Realtime Database |

The deployed vision path is ONNX Runtime on the Raspberry Pi CPU. Firebase synchronization copies event data; it does not run either model.
