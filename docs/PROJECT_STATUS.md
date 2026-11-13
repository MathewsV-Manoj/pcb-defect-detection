# Implementation overview

## Built inspection workflow

The project brings together the PCB inspection station, camera-based image acquisition, OpenCV preprocessing, YOLO-based defect localization, edge-side inspection-event generation, Firebase publication and a browser dashboard.

The inspection flow is:

1. Position a PCB at the inspection station and acquire an image.
2. Prepare the image with OpenCV.
3. Run the configured YOLO detector on the edge-computing device.
4. Decode class scores and bounding boxes and map them to the original PCB image.
5. Generate an annotated image and structured inspection record.
6. Pass structured findings to the optional operator-advisory interface.
7. Publish the event to Firebase Realtime Database.
8. Display the latest state and inspection history in the dashboard.

## Repository implementation

| Area | Repository component | Role |
|---|---|---|
| Edge inference | `raspberry_pi/inspect_image.py` | Image, USB-camera and CSI-camera inference using ONNX Runtime |
| Event publication | `raspberry_pi/firebase_client.py` | Direct REST publication to Firebase |
| Dataset engineering | `pcb_engine_kit/dataset.py` | Annotation conversion, validation and dataset preparation |
| Detector development | `pcb_engine_kit/train_export.py` | YOLO training, validation and TFLite export |
| Image queue processing | `pcb_engine_kit/engine.py` | TFLite folder-worker, annotated outputs and result records |
| Reference comparison | `pcb_engine_kit/make_reference.py`, `engine.py` | Reference image setup and ORB/homography alignment |
| Dashboard | `dashboard/index.html` | Live Firebase overview and inspection history |
| Advisory interface | `llm_advisory/prompt.py` | Builds an advisory prompt from structured YOLO findings |
| Event contract | `schemas/` | Standardized inspection-event structure |
| Firebase configuration | `firebase/` | Example database rules |
| Demonstration | `demo_video/` | Upload location and guide for the project video |

## Model and dataset release information

The detector is used through a model file and a matching class map. The Raspberry Pi ONNX application expects a compatible three-class detector at `models/best.onnx`. The exact checkpoint, exported model metadata, training dataset and evaluation report should be versioned together for a reproducible release.

The supplied training/export utility and the Pi inference handoff contain different class-order conventions. Check the final checkpoint's class metadata and the corresponding deployment decoder before packaging a model release. The relevant engineering note is `pcb_engine_kit/CLASS_ORDER_CONFLICT.md`.

The auxiliary `pcb_engine_kit/optional_unet/pcb_ultra_resatt_unet.pth` file is a separate five-channel ResAttention U-Net trace-extraction checkpoint. It is not the three-class YOLO defect detector.

## Verification

The included dependency-free contract tests cover atomic image submission and rejection of unsafe ZIP extraction paths. The model and application evaluation process is documented in the root README and the training and deployment guides. Record measured detection metrics and Raspberry Pi 5 benchmarks with the exact model and test configuration used.
