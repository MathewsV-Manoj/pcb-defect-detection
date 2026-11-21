# PCB inspection station
## Technical project report

## 1. Project overview

This project develops a conveyor-fed optical inspection station for printed circuit boards. A Raspberry Pi 5 controls image capture and runs the inspection software locally. The system is designed to identify three visible defect classes: open circuit, short circuit and missing hole.

The physical station uses a conveyor, an IR presence sensor, a camera and an LED strip driven through an external LED driver. The operator uses a laptop browser on the same local network to review the captured frame and request inspection. The detector and advisory run on the Raspberry Pi; the browser presents results and does not perform inference.

## 2. Physical station sequence

At the beginning of a session, the operator holds a hand in front of the IR sensor for approximately three seconds and releases it. The controller remains armed until it is restarted.

A PCB then travels on the conveyor. When the board activates the IR sensor at the camera trigger point, the Raspberry Pi switches on the LED driver, waits for the configured settling interval and captures a frame. The frame is saved locally and made available to the operator page.

The IR sensor is a binary presence detector. It does not calculate the exact PCB position in the camera image. That relationship depends on the mechanical placement of the conveyor, sensor and camera.

## 3. Operator interface and software workflow

The operator opens the Pi-hosted page from a laptop on the same private network. The operator checks the latest captured image and presses **Run inspection on Raspberry Pi**.

The page sends a same-origin request to `POST /api/run-inspection`. The Pi then:

1. reads the captured frame;
2. applies OpenCV letterboxing and BGR-to-RGB conversion;
3. scales pixel values to float32 in the [0, 1] range and arranges the input as NCHW;
4. runs the YOLOv8 Nano ONNX detector using ONNX Runtime on the Pi CPU;
5. applies confidence filtering and class-wise non-maximum suppression;
6. maps the retained boxes back to original image coordinates;
7. saves an annotated image and structured inspection-event JSON;
8. sends the structured event, not the image, to the ExecuTorch text runner for the operator advisory;
9. displays the detector result, annotated image and advisory on the browser page.

The Pi keeps local inspection records. When Firebase synchronization is configured, the completed event is copied to Realtime Database paths `/inspections/{record_id}` and `/live`. Firebase carries records; it does not execute the detector or the advisory model.

## 4. Vision model and class mapping

The deployment class order is fixed across the annotator, dataset importer, YOLO checkpoint, ONNX export, event schema and Raspberry Pi decoder.

| Class ID | Class name | Visual target |
|---:|---|---|
| 0 | `missing_hole` | An absent or visibly defective hole at an expected board location |
| 1 | `open_circuit` | A visible break or discontinuity in a conductive track |
| 2 | `short_circuit` | An unintended bridge between separate conductive paths |

The ONNX input contract is one 640 × 640 RGB image, float32 normalized to [0, 1], with shape `[1, 3, 640, 640]`. Letterboxing preserves the source aspect ratio. The Pi decoder expects raw YOLO output for four box coordinates and three class scores, without embedded NMS.

Source annotation names are checked before conversion. DeepPCB open/short annotations can be mapped only after checking their original class IDs. Its `pin-hole` annotation is not treated as a missing drill hole. A different dataset's class name is not sufficient evidence that its label has the same physical meaning.

The current repository has the dataset importer and training/export scripts, but its source checkout does not include the final processed dataset or trained model binaries. Therefore, the final training run, held-out metrics and ONNX parity have not been established by the repository itself.

## 5. Inspection event and operator advisory

Each inspection event includes a record ID, board ID, timestamp, source type, model filename and class order, thresholds, inference latency, detections and station information. Each detection stores a class ID/name, confidence, bounding box and image-relative location.

The vision model is responsible for visual defect localization. The Llama advisory receives the structured event as text only. It does not receive the PCB image and is instructed not to add, remove, relabel or suppress detector findings. It produces an explanation, recommended operator checks, a severity note and a log entry.

The advisory code uses ExecuTorch's text-only `TextLLMRunner`. Llama and ExecuTorch are required technologies for the Bharat AI-SoC Challenge. The repository contains the prompt builder and runner source, but the exported ExecuTorch `.pte` model and matching tokenizer are not included. The required on-device advisory therefore remains an outstanding release item until the actual model/tokenizer are supplied and tested on the Pi.

The detector currently sets severity to `UNASSESSED`. No board-specific severity policy has been validated. Confidence is a detector score, not a severity measure, and is not used to invent a severity label.

A decision of `NO_TARGET_DEFECT_DETECTED` means the detector did not find one of the three configured classes in the captured frame. It is not a declaration that the entire PCB is defect-free.

## 6. Local records and Firebase synchronization

The Pi stores the captured image, annotated image and event JSON in its configured output directory. The dashboard reads recent history from the Pi service.

The Firebase client copies completed inspection records to Realtime Database when configured. It is a data-synchronization path; it is not required for local image capture or local model inference. Firebase credentials must not be committed to the public repository.

## 7. Testing and evaluation

The repository includes automated software checks for the class-order contract, event schema, station state transitions, advisory prompt boundary, advisory response format, dashboard script syntax, dataset importer and safe dataset archive extraction. GitHub Actions runs the software checks.

These checks do not exercise the physical GPIO wiring, camera, LED driver, final YOLO weights, ExecuTorch model or sustained Raspberry Pi operation. The following evidence is still required before a complete technical claim can be made:

| Area | Evidence required |
|---|---|
| Detection quality | Per-class precision, recall and F1; confusion matrix; mAP@50 and mAP@50–95; false positives and missed defects on a held-out board-level test split |
| Model provenance | Exact checkpoint path and hash, dataset version, split manifest, class map, image size and thresholds |
| Export correctness | ONNX model hash, input/output contract and prediction comparison against the source checkpoint |
| Station operation | Verified GPIO pin mapping, camera capture, illumination timing, repeated trigger tests and complete operator workflow |
| Edge performance | Pi-side inference latency percentiles, throughput, RAM and temperature, measured on the stated Pi configuration |
| Advisory operation | Llama model/tokenizer identity and hashes, ExecuTorch version/build, valid output and on-device latency |
| Application reliability | Repeated capture-to-result tests, local record integrity and Firebase synchronization result when enabled |

Do not report workstation measurements as Raspberry Pi measurements. Do not claim a performance threshold unless it has been measured using the stated hardware and method.

## 8. Current release status

The repository includes the source implementation, dashboard, event schema, dataset preparation and training source, deployment instructions, tests and a demonstration MP4 file.

The final YOLO `best.pt` and `best.onnx`, model metadata generated from the final export, Llama `.pte` model, matching tokenizer, processed dataset/audit, held-out evaluation output and completed Pi commissioning record are not present in this source checkout. The committed MP4 file must be reviewed to confirm that it shows the actual live station sequence required by the submission.

The source-only repository is not yet a complete runnable release. These missing artifacts and validations are listed in [Submission readiness](SUBMISSION_READINESS.md).

Source repository: https://github.com/MathewsV-Manoj/pcb-defect-detection
