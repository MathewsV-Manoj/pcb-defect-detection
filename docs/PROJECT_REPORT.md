# PCB inspection station
## Project report

## 1. Project overview

This project develops a conveyor-fed inspection station for printed circuit boards. A Raspberry Pi 5 controls the capture sequence and runs the image-processing software. The target is to identify three visible defect types:

- open circuit;
- short circuit;
- missing hole.

The operator uses a laptop browser to view the captured image and start an inspection. The browser does not run the detector. It sends a request to the Raspberry Pi, which processes the saved image and returns the result.

The physical assembly includes a conveyor, IR presence sensor, camera, LED strip and external LED driver. The software repository contains the station controller, Pi-hosted web page, ONNX inference path, inspection coordinator, advisory runner and event schema.

## 2. Station sequence

The IR sensor is used in two stages. At the beginning of a session, the operator holds a hand in front of it for about three seconds. When the hand is removed, the controller remains armed. The next sensor activation is treated as a board-presence trigger. The station does not require the hand-hold sequence again for each board; the armed state is cleared when the controller restarts.

When the board reaches the trigger point, the Pi switches on the LED driver, waits for the configured settling interval and captures one frame. The frame is saved locally. The Pi then serves the image to the operator's browser.

The IR sensor is a binary presence detector. It does not calculate the PCB's exact position in the image. The camera view must be aligned through the mechanical placement of the conveyor, sensor and camera.

## 3. Operator website and API

The website is served directly by raspberry_pi/station_controller.py from dashboard/index.html. The operator opens the Pi's IP address and port from a laptop on the same private network.

| Route | Use |
|---|---|
| GET / | Load the operator page |
| GET /api/health | Check whether the service responds |
| GET /api/status | Read sensor, capture and inspection state |
| GET /api/capture.jpg | View the raw captured frame |
| GET /api/annotated.jpg | View the detector output after processing |
| GET /api/history | Read recent local inspection events |
| POST /api/run-inspection | Ask the Pi to process the captured frame |

The operator checks the raw image before running the detector. After the run button is pressed, the Pi starts the inspection coordinator. The page polls the Pi for state changes and displays the saved result.

The HTTP service is intended for a trusted local network. It should not be exposed directly to the public internet.

## 4. Image preparation

The ONNX detector expects one RGB image with dimensions 640 × 640. The current preprocessing in raspberry_pi/inspect_image.py is:

1. read the saved frame with OpenCV;
2. resize it while keeping its aspect ratio;
3. pad the remaining area to 640 × 640;
4. convert BGR to RGB;
5. convert to float32 and divide by 255;
6. arrange the array as NCHW with shape [1, 3, 640, 640].

The detector uses a three-channel image. The current implementation does not convert the image to grayscale or run a separate hand-written trace-continuity detector.

## 5. Vision model and class mapping

The base application uses YOLOv8 Nano exported to ONNX and executed through ONNX Runtime on the Raspberry Pi CPU. The class order used by the application and training tools is:

| Class ID | Class name |
|---:|---|
| 0 | missing_hole |
| 1 | open_circuit |
| 2 | short_circuit |

The detector output contains box coordinates and class scores. The Pi applies a confidence threshold and non-maximum suppression separately for each class. It maps the retained boxes back to the original image, draws them on an annotated copy and stores their coordinates and confidence in the event record.

The class mapping must match the training data. DeepPCB open-circuit and short-circuit labels can be mapped after checking the source label convention. A source label such as pin_hole is not automatically treated as missing_hole; its meaning must be checked first. The project import manifest records the image, label format, board group and train/validation/test split for each image.

## 6. Llama advisory

The Llama process is separate from the vision model. The Pi sends it the structured event fields: board ID, timestamp, defect type, confidence, severity and location. It does not send an image or image path.

The requested response contains four fields: an explanation, recommended operator actions, a severity note and a log entry. The runner checks that the response is valid JSON with the required field types.

The advisory is intended to help the operator review a detector result. It does not add or remove detections, change the detector's class, assign severity from confidence or make an independent PASS/REJECT decision.

The source uses ExecuTorch's text-only TextLLMRunner Python binding. The .pte model and matching tokenizer must be supplied separately and must be built for the Pi's ARM64 environment. The ExecuTorch Python runner API is experimental, so the installed binding, model and tokenizer need to be checked together on the target device.

## 7. Inspection record

Each inspection event stores:

- a record ID and board ID;
- timestamp and image source;
- model filename and class order;
- confidence and NMS thresholds;
- detector latency;
- a list of detections;
- station information;
- the advisory result, when available;
- Firebase synchronization status, when publication is enabled.

Each detection includes its class ID, class name, confidence, box coordinates, severity and normalized centre location.

The current detector sets severity to UNASSESSED. A board-specific severity rule has not been configured. The software therefore leaves severity for human review rather than assigning a value without evidence.

A decision of NO_TARGET_DEFECT_DETECTED means that the detector did not find any of the three configured classes in that frame. It does not prove that the entire PCB is defect-free.

## 8. Local records and Firebase

The Pi stores the captured image, annotated image and event JSON in the configured output directory. The dashboard reads recent records from the Pi.

Firebase Realtime Database is an optional copy of the inspection record. The Pi publishes the completed event to /inspections/{record_id} and updates /live. Firebase is not used for image inference or advisory generation. The station can be used locally without Firebase.

## 9. Testing and evaluation

The repository includes automated tests for the station state transitions, event schema, class order, dashboard script syntax, Llama prompt boundary, advisory JSON format, dataset importer and supplementary folder-worker utilities. GitHub Actions runs these tests and compiles the Python source.

Those checks run in a software environment; they do not exercise the GPIO pins, camera, LED driver or model binaries on the Raspberry Pi. The following measurements are still required on the target setup:

| Area | What to record |
|---|---|
| Detection | Per-class precision, recall, F1, confusion matrix and mAP at the stated IoU thresholds |
| Capture and station | IR trigger-to-capture time, capture success rate and repeat-cycle reliability |
| Vision runtime | Per-image latency, sustained FPS, peak RAM and CPU temperature |
| Llama runtime | Time to first token, tokens per second, total response time and peak RAM |
| Electrical | Power measured with an external meter under idle, capture and inference load |
| Operator use | Correct frame preview, clear run acknowledgement and successful result display |

The test split must contain boards or capture groups that were not used for training. Views of the same physical PCB should not be spread across the training and test splits.

Every reported metric should be accompanied by the model hash, data split, input size, thresholds, runtime versions and Raspberry Pi configuration. A workstation result should not be reported as a Pi measurement.

## 10. Current project files and remaining release items

The repository contains the application source, dashboard, event schema, dataset utilities, model export script and software tests.

The final trained three-class YOLO checkpoint and ONNX file, the ExecuTorch model and tokenizer, the complete processed dataset and target-device measurements are not included in this source checkout. The physical components have been assembled, but the complete capture-to-result cycle still needs reliable validation on the Raspberry Pi with the release models installed.

The demonstration video also needs to be recorded on the physical station. The demo_video/ folder contains the shot list for that recording.

Source repository: https://github.com/MathewsV-Manoj/pcb-defect-detection
