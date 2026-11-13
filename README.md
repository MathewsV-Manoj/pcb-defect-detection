
# Intelligent PCB Defect Inspection and Edge Quality Monitoring

**An edge-AI vision system for automated printed circuit board inspection, designed around YOLOv8 Nano and Raspberry Pi deployment.**

PCB manufacturing quality depends on identifying visual defects before a board advances to the next production stage. This project develops an integrated inspection workflow that combines computer vision, edge inference, structured inspection records, optional AI-assisted operator guidance and a real-time monitoring dashboard.

The detector is designed for three target defect categories:

- **Open circuit:** an unintended discontinuity in a conductive track.
- **Short circuit:** an unintended conductive bridge between separate tracks.
- **Missing hole:** an absent or defective hole at an expected PCB location.

The intended system places image acquisition and inference close to the inspection hardware, with **Raspberry Pi 5** as the edge-computing target. YOLOv8 Nano performs visual defect localization. The resulting inspection record can be sent to Firebase Realtime Database and displayed through a single-page operator dashboard. A separate Llama-family advisory component is planned to explain structured detector findings for an operator.

The project connects machine learning, embedded systems, computer vision, edge deployment, IoT data flow and operator-facing software in one PCB inspection workflow.

---

## 1. Project objectives

1. Detect and localize selected PCB defects using a vision-based object detector.
2. Build a reproducible dataset workflow for annotation conversion, class verification and board-aware data splitting.
3. Train and evaluate a lightweight YOLOv8 Nano detector.
4. Prepare inference and image-acquisition software for Raspberry Pi deployment.
5. Generate traceable inspection records containing board ID, timestamp, defect class, confidence and bounding-box coordinates.
6. Provide optional LLM-generated explanations based on structured YOLO findings.
7. Publish inspection records through Firebase and present them through a responsive dashboard.
8. Evaluate both detection quality and edge-device performance using measurable criteria.

## 2. System architecture

The architecture separates three responsibilities: visual detection, operator explanation and information presentation. YOLO is the only component responsible for visual defect localization. The optional Llama-family model receives structured YOLO results and generates advisory text; it is not used to inspect pixels or create detections.

    PCB / Inspection Camera
              |
              v
    Image Acquisition and Validation
             OpenCV
              |
              v
       YOLOv8 Nano Detector
   Open Circuit / Short Circuit / Missing Hole
              |
              v
     Structured Inspection Record
     Board ID + Timestamp + Class
       Confidence + Bounding Box
              |
       +------+------+
       |             |
       v             v
  Llama Advisory   Inspection Log
  (optional)       and Image Record
       |             |
       +------+------+
              |
              v
    Firebase Realtime Database
              |
              v
    Single-Page Operator Dashboard

**Data flow:** the edge application captures or receives a PCB image, performs preprocessing and inference, creates a structured inspection event, and publishes it directly to Firebase. Firebase provides data storage and real-time transport; it does not execute YOLO or Llama. The HTML dashboard subscribes to database updates. This architecture does not require a separate Flask or Node.js web backend.

## 3. Vision model and defect classes

The intended vision model is **YOLOv8 Nano**, selected as a lightweight object-detection architecture for evaluation on an edge-computing platform.

| Target class | Inspection objective |
|---|---|
| open_circuit | Localize a visible break in a conductive track |
| short_circuit | Localize an unintended bridge between conductive paths |
| missing_hole | Localize a missing or defective hole at an expected PCB location |

The output of the detector is a list of findings. Each finding contains a class identifier, class name, confidence score and bounding-box coordinates in the original image frame.

The model interface is defined by more than the checkpoint filename. Class IDs, class names, preprocessing, input dimensions, output tensor layout, confidence filtering and non-maximum suppression must remain consistent across training, export, edge inference and dashboard presentation. The repository includes a model release manifest and a class-order verification record for this purpose.

## 4. Dataset engineering and training workflow

The supplied training kit provides utilities for converting and preparing annotated PCB images. The dataset importer supports YOLO, Pascal VOC and DeepPCB annotation formats and produces a consistent YOLO dataset layout.

The dataset workflow includes:

- Source dataset inventory and original class-name verification.
- Annotation conversion into YOLO label format.
- Image readability, bounding-box range and label validation.
- Duplicate-image checks.
- Train, validation and test split assignment by physical-board or capture group.
- Dataset audit output for reviewing split composition and class coverage.
- A local OpenCV annotation tool for project-specific images.

Board-aware splitting is important because related crops or images from the same physical board should not be distributed across training and evaluation splits. The dataset source manifest is maintained at SOURCES_MANIFEST in the datasets folder. For a release, record the exact source, version, annotation mapping, license/terms, split and archive checksum used by the selected checkpoint.

### Example training and validation

The training utility supports YOLO training, test-split validation and INT8 TFLite export. The following commands illustrate the workflow and parameters; the final report should reproduce the exact arguments recorded in the selected training run.

    python train_export.py train --data data/pcb/data.yaml --size 640 --batch 4 --epochs 100 --device 0

    python train_export.py validate --data data/pcb/data.yaml --weights runs/pcb/weights/best.pt --size 640 --device 0

For a final evaluation, retain the training arguments, dataset YAML, class list, checkpoint hash, package versions, evaluation split, confusion matrix, precision-recall curves and representative prediction images.

## 5. Raspberry Pi edge deployment

**Raspberry Pi 5 is the target edge-computing platform.** The deployment design keeps image processing and detector inference on the device. The initial ONNX path uses ONNX Runtime with CPU execution.

The repository contains two documented deployment implementations:

| Deployment implementation | Runtime and purpose |
|---|---|
| Raspberry Pi 5 integration path | ONNX Runtime CPU for image or one-frame camera inference |
| Supplied folder-worker kit | TFLite Runtime for queued image processing and result-file generation |

The Pi 5 handoff specifies a 640 × 640 RGB model input and describes an expected raw YOLO ONNX output shape of approximately [1, 7, 8400]. The actual model graph is inspected before release so that image preprocessing, output decoding, confidence filtering and non-maximum suppression match the exported checkpoint.

The Pi-oriented software includes:

- OpenCV image loading and preprocessing.
- One-frame capture from a USB/UVC camera or Raspberry Pi CSI camera through Picamera2.
- ONNX Runtime CPU inference.
- YOLO output decoding and bounding-box mapping to the original image.
- Annotated image generation and JSON inspection-event creation.
- Optional direct Firebase publishing.

The folder-worker implementation additionally supports atomic image submission, an incoming/processing/results/archive/failed directory structure, sequential processing and reference-board comparison.

## 6. Reference-assisted inspection

The supplied engine includes an optional reference-board workflow. A known-good PCB image can be used to define expected component regions. The engine aligns an inspection image with the reference using ORB features and homography, then compares the configured regions.

Region differences are presented as **review candidates** for operator verification. These candidates are kept distinct from trained YOLO defect detections. This provides an additional inspection aid when component presence or placement is relevant to the board revision.

## 7. AI-assisted operator advisory

The planned Llama-family advisory stage is an explanation component that receives structured YOLO findings. Its input can include board ID, timestamp, defect class, confidence, bounding-box coordinates and approved inspection procedures.

The advisory can explain why a finding was raised and suggest a verification step. It does not replace the detector, inspect the original PCB pixels, alter YOLO class labels or independently issue a pass decision. ExecuTorch is the planned deployment route, subject to model, tokenizer, quantization and Raspberry Pi runtime compatibility evaluation.

## 8. Firebase and operator dashboard

The operator interface is a static HTML dashboard connected to Firebase Realtime Database.

### Dashboard capabilities

- Inspection overview and board/session counts.
- Latest board result and detected defect details.
- Defect-category distribution.
- Optional operator-advisory display.
- Camera and device status fields.
- Inspection history and CSV export.
- Distinction between live inspection records, image-based tests and simulated demonstration records.

### Data structure

The edge application publishes completed inspection records under:

    /inspections/{record_id}
    /live

A record includes board ID, timestamp, source, decision/status, model identifier, inference latency, detections and optional advisory text. Each detection includes class, confidence and bounding-box coordinates.

Firebase Authentication and restrictive Realtime Database security rules should be used. Authentication tokens and service-account credentials must remain outside public browser code and source control.

## 9. Evaluation methodology

The evaluation plan covers model accuracy, edge-device performance and end-to-end inspection behaviour.

### A. Detection performance

| Metric / evidence | Evaluation purpose |
|---|---|
| Per-class precision | Correctness of predicted defect labels |
| Per-class recall | Ability to identify annotated defects |
| mAP@50 | Detection performance at IoU 0.50 |
| mAP@50–95 | Detection performance across IoU thresholds |
| Confusion matrix | Class confusion and missed detections |
| Precision-recall curves | Confidence-threshold behaviour |
| Visual prediction review | Bounding-box placement and small-defect localization |
| Unseen PCB images | Generalization beyond training examples |

Report metrics against the exact checkpoint and held-out split that produced them. Include good boards and defective boards, representative defect sizes, multiple capture conditions and sample false-positive/false-negative reviews.

### B. Raspberry Pi 5 performance

| Measurement | Evaluation purpose |
|---|---|
| Mean and median inference latency | Typical detector execution time |
| p95 inference latency | Slow-case execution time |
| Throughput / FPS | Processing capacity |
| Peak RAM usage | Edge memory footprint |
| CPU temperature | Thermal behaviour under sustained use |
| Sustained-run reliability | Stability over repeated inspections |
| Prediction parity | Agreement between reference and exported model |

Laptop GPU timings must not be reported as Raspberry Pi results. Capture edge metrics on the actual Pi 5 using the exact model, runtime, input resolution and camera pipeline.

### C. Application and hardware evaluation

Evaluate image acquisition, inference completion, correct class-name display, bounding-box alignment, board/event IDs, Firebase publication, dashboard refresh, annotated-image storage, error handling and inspection-history export. For the physical inspection stage, evaluate camera triggering, conveyor timing, repeatable PCB positioning and safe motor stopping.

The supplied source kit includes two dependency-free contract tests for atomic image submission and rejection of unsafe ZIP extraction paths. Both pass in the current development environment.

## 10. Repository structure

    pcb-defect-detection/
    ├── raspberry_pi/
    │   ├── inspect_image.py
    │   ├── firebase_client.py
    │   ├── requirements.txt
    │   └── README.md
    ├── pcb_engine_kit/
    │   ├── dataset.py
    │   ├── label.py
    │   ├── train_export.py
    │   ├── engine.py
    │   ├── evaluate_pi.py
    │   ├── make_reference.py
    │   ├── submit.py
    │   ├── safe_extract.py
    │   ├── GUI_ARCHITECTURE.md
    │   ├── TRAINING_AND_DEPLOYMENT.md
    │   └── optional_unet/
    ├── dashboard/
    │   └── index.html
    ├── models/
    │   ├── class_names.txt
    │   └── release_manifest.json
    ├── datasets/
    │   └── SOURCE_MANIFEST.csv
    ├── training/
    ├── llm_advisory/
    ├── schemas/
    ├── firebase/
    └── docs/

## 11. Setup and execution

### Raspberry Pi 5

Use a 64-bit Raspberry Pi OS installation.

    sudo apt update
    sudo apt install -y python3-venv python3-pip python3-opencv

    git clone https://github.com/MathewsV-Manoj/pcb-defect-detection.git
    cd pcb-defect-detection

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r raspberry_pi/requirements.txt

Place the verified three-class ONNX model at models/best.onnx.

Image inference:

    python raspberry_pi/inspect_image.py --source /path/to/pcb_image.jpg --weights models/best.onnx

USB camera, one-frame capture:

    python raspberry_pi/inspect_image.py --camera 0 --weights models/best.onnx

CSI camera, one-frame capture:

    python raspberry_pi/inspect_image.py --picamera2 --weights models/best.onnx

### Training workstation

The supplied training and export kit is intended for an Ubuntu workstation. Follow the detailed instructions in:

- pcb_engine_kit/README.md
- pcb_engine_kit/TRAINING_AND_DEPLOYMENT.md
- pcb_engine_kit/GUI_ARCHITECTURE.md

Keep the training environment separate from the Raspberry Pi runtime environment.

## 12. Development snapshot

The mechanical conveyor assembly has been developed. Software integration and system-level evaluation are being carried out as distinct engineering stages.

| Project area | Repository implementation |
|---|---|
| Dataset engineering | Importer, annotation utility, manifest and audit workflow |
| Detector development | YOLO training, validation and export scripts |
| Edge inference | ONNX Runtime Pi scaffold and TFLite folder-worker implementation |
| Reference inspection | Reference-region creation and alignment/comparison logic |
| Operator application | Firebase-connected HTML dashboard |
| Data exchange | Inspection-event schema and direct Firebase publisher |
| Advisory AI | Structured-data prompt interface for Llama/ExecuTorch integration |
| Verification | Contract tests, model release manifest and Pi evaluation utility |

The supplied ZIP contains an auxiliary ResAttention U-Net checkpoint named pcb_ultra_resatt_unet.pth. This checkpoint is for PCB trace extraction and is separate from the three-class YOLO defect detector. Its source code and checksum are documented under pcb_engine_kit/optional_unet/.

The training kit provides the scripts required to prepare data and train/export the defect detector. Add selected model weights, dataset images/labels and evaluation reports as versioned project release artifacts after verifying their identity, class mapping and redistribution terms.

## 13. Engineering contribution

This project integrates several engineering disciplines into one PCB inspection workflow:

- **Computer vision:** visual defect localization using object detection.
- **Dataset engineering:** annotation conversion, validation and board-aware data splitting.
- **Edge AI:** deployment-oriented inference on Raspberry Pi hardware.
- **Embedded integration:** camera acquisition and inspection-system interfaces.
- **AI-assisted operation:** structured LLM explanations separated from visual detection.
- **IoT and data engineering:** Firebase-based event publication and real-time dashboard updates.
- **Performance evaluation:** model metrics combined with edge-device and system-level measurements.

The objective is to move beyond isolated model predictions toward a traceable inspection process connecting the physical inspection environment, edge inference, operator feedback and stored inspection evidence.

---

## Project information

**Repository:** https://github.com/MathewsV-Manoj/pcb-defect-detection  
**Application target:** Raspberry Pi 5  
**Vision model target:** YOLOv8 Nano  
**Target classes:** Open Circuit, Short Circuit, Missing Hole  
**Data platform:** Firebase Realtime Database  
**Dashboard:** HTML, CSS and JavaScript  
**Advisory AI target:** Llama-family model with ExecuTorch evaluation
