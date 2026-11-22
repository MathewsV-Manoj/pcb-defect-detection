# PCB inspection station
## Technical project report

## 1. Project overview

This project develops a conveyor-fed optical inspection station for printed circuit boards. A Raspberry Pi 5 controls image capture and runs the inspection software locally. The system is designed to identify three visible defect classes: open circuit, short circuit and missing hole.

The physical station uses a conveyor, an IR presence sensor, a camera and an LED strip driven through an external LED driver. The operator uses a laptop browser on the same local network to review the captured frame and request inspection. The detector and advisory are configured to run on the Raspberry Pi CPU; the browser presents results and does not perform inference.

## 2. Physical station sequence

At the beginning of a session, the operator holds a hand in front of the IR sensor for approximately three seconds and releases it. The controller remains armed until it is restarted.

A PCB then travels on the conveyor. When the board activates the IR sensor at the camera trigger point, the Raspberry Pi switches on the LED driver, waits for the configured settling interval and captures a frame. The frame is saved locally and made available to the operator page.

The IR sensor is a binary presence detector. It does not calculate the exact PCB position in the camera image. That relationship depends on the mechanical placement of the conveyor, sensor and camera.

### Local inference and offline operation

The production inference path is on-device. OpenCV preprocessing and YOLO inference execute on the Raspberry Pi 5 using ONNX Runtime's CPU execution provider. The text-only Llama 3.2 1B Instruct SpinQuant model is invoked through the ExecuTorch C++ `llama_main` runner on the Pi CPU. The dashboard is static HTML/JavaScript served by the Pi; the browser is a remote display/control client on the private LAN and does not run model inference. The Llama prompt contains the structured event, not the PCB image.

The default `PCB_FIREBASE_PUBLISH=false` setting keeps the event history local. Firebase, when deliberately enabled, is only an optional HTTPS record-replication destination. It is not on the inference path. The model and runtime assets must first be downloaded/built and copied to the Pi; after provisioning, the inference path is designed to run without internet access. Offline operation has not been recorded as a passed hardware test until the final Pi completes an inspection with WAN disconnected and the operator browser still connected on the local LAN. See [Local execution and performance record](LOCAL_EXECUTION_AND_PERFORMANCE.md).

## 3. Operator interface and software workflow

The operator opens the Pi-hosted page from a laptop on the same private network. The operator checks the latest captured image and presses **Run inspection on Raspberry Pi**.

The page sends a same-origin request to `POST /api/run-inspection`. The Pi then:

1. reads the captured frame;
2. applies OpenCV letterboxing and BGR-to-RGB conversion;
3. scales pixel values to float32 in the [0, 1] range and arranges the input as NCHW;
4. runs the configured YOLO ONNX detector using ONNX Runtime with the CPU execution provider on the Pi CPU;
5. applies confidence filtering and class-wise non-maximum suppression;
6. maps the retained boxes back to original image coordinates;
7. saves an annotated image and structured inspection-event JSON;
8. sends the structured event, not the image, to the ExecuTorch text runner for the operator advisory;
9. displays the detector result, annotated image and advisory on the browser page.

The Pi keeps local inspection records. Firebase synchronization is disabled by default. When explicitly enabled, the completed event is copied to Realtime Database paths `/inspections/{record_id}` and `/live`. Firebase carries records only; it does not execute the detector or the advisory model.

## 4. Vision model and class mapping

The deployment class order is fixed across the annotator, dataset importer, YOLO checkpoint, ONNX export, event schema and Raspberry Pi decoder.

| Class ID | Class name | Visual target |
|---:|---|---|
| 0 | `missing_hole` | An absent or visibly defective hole at an expected board location |
| 1 | `open_circuit` | A visible break or discontinuity in a conductive track |
| 2 | `short_circuit` | An unintended bridge between separate conductive paths |

The configured YOLO ONNX input contract is one 640 × 640 RGB image, float32 normalized to [0, 1], with shape `[1, 3, 640, 640]`. Letterboxing preserves the source aspect ratio. For a three-class project checkpoint, the Pi decoder expects raw YOLO output for four box coordinates and three class scores, without embedded NMS. The separately documented six-class YOLOv8s baseline is decoded using its sidecar class metadata and maps only the three target classes.

Source annotation names are checked before conversion. DeepPCB open/short annotations can be mapped only after checking their original class IDs. Its `pin-hole` annotation is not treated as a missing drill hole. A different dataset's class name is not sufficient evidence that its label has the same physical meaning.

The project team has supplied a screenshot reporting validation metrics, recorded in §4.3, [PROJECT_VALIDATION_RESULTS.md](results/PROJECT_VALIDATION_RESULTS.md) and [published_pcb_benchmarks.json](results/published_pcb_benchmarks.json). The processed dataset, checkpoint, split manifest and raw evaluator output are not yet committed. The screenshot can therefore be cited as a reported validation result, but it does not establish independently reproducible metrics, held-out test performance, ONNX parity or Raspberry Pi performance.

## 4.1 Public pretrained baseline

An additional pretrained PCB model is referenced as a transfer-learning and
deployment baseline: Sulojan Rajkumar's YOLOv8s checkpoint published on
Hugging Face. The model card declares an MIT license. Its source repository
describes training on the Kaggle `akhatova/pcb-defects` dataset with six
classes. The source checkpoint and its published SHA-256 are recorded in
`models/pretrained/` and `models/release_manifest.json`.

The original author reports a held-out test split of 70 images and 286
bounding boxes, with precision 0.972, recall 0.912, mAP@50 0.941,
mAP@50–95 0.503 and 18.4 ms/image in the author's test environment. Per-class
mAP@50 is 0.995 for `missing_hole`, 0.992 for `open_circuit` and 0.975 for
`short`. These figures belong to the original publisher's test setup and
are cited as external baseline results, not as measurements obtained by this
project or its Raspberry Pi station.

The checkpoint has six classes. The Pi's ONNX sidecar maps `missing_hole`,
`open_circuit` and `short` to the project's three event classes and ignores
the other source classes. The original source class order and mapping are
preserved in each inspection event. A separate training mode permits this
checkpoint to initialize training on the project's own three-class dataset;
metrics from any resulting checkpoint must be generated on the project's
own held-out board groups.

See [PCB upstream baseline](PCB_UPSTREAM_BASELINE.md) for model provenance,
license declaration, checkpoint checksum, dataset and source links, detailed
metrics and exact download/export commands.

## 4.2 Published research comparison

Several independent PCB-defect studies provide reference points on public
datasets. On DeepPCB, YOLO-MBBi reports 98.7% precision, 97.5% recall and
99.0% mAP@0.50; PCB-MMF reports 96.23% precision, 97.02% recall, 98.68%
mAP@0.50 and 82.16% mAP@0.50:0.95; RT-DETR-L reports 98.20% precision,
97.66% recall, 98.74% mAP@0.50 and 82.34% mAP@0.50:0.95. On
PKU-Market-PCB, PCB-YOLO reports 96.1% precision, 97.4% recall, 98.4%
mAP@0.50 and 71.6% mAP@0.50:0.95. PCB-YOLO's separate DeepPCB experiment
reports 99.0% mAP@0.50 and 80.4% mAP@0.50:0.95.

These are results from the cited papers' own trained models, datasets and
evaluation environments. They demonstrate the performance reported in the
literature, not accuracy achieved by this project. Dataset class definitions,
splits, imaging conditions, evaluator settings and target hardware differ;
the FPS figures in those papers are not Raspberry Pi 5 measurements. Full
provenance, dataset details and source links are recorded in
[EXTERNAL_PCB_BENCHMARKS.md](EXTERNAL_PCB_BENCHMARKS.md), with the values also
stored in [published_pcb_benchmarks.json](results/published_pcb_benchmarks.json).

## 4.3 Project validation results reported by the team

The team supplied a screenshot of the training-results page showing the following validation metrics:

| Metric | Validation result |
|---|---:|
| Precision | 98.3% |
| Recall | 98.4% |
| mAP@0.50 | 98.9% |
| mAP@0.50:0.95 | 62.5% |

| Defect class | Precision | Recall | mAP@0.50 |
|---|---:|---:|---:|
| Missing Hole | 97.8% | 98.2% | 98.5% |
| Open Circuit | 99.1% | 99.6% | 99.5% |
| Short Circuit | 97.9% | 97.6% | 98.8% |

These values are recorded as **reported validation metrics**, not independent test-set results. The screenshot does not identify the dataset/version, validation sample count, checkpoint hash, image size, evaluation thresholds or raw evaluator output. The original screenshot filename and SHA-256 are listed in [PROJECT_VALIDATION_RESULTS.md](results/PROJECT_VALIDATION_RESULTS.md). Those details should be archived with the run before the metrics are treated as fully reproducible. No Raspberry Pi 5 latency, FPS or deployment accuracy is implied by this training-results screenshot.

The difference between mAP@0.50 (98.9%) and mAP@0.50:0.95 (62.5%) should remain visible in the report. The latter averages performance across stricter intersection-over-union thresholds and is a more demanding indicator of bounding-box localisation quality.

## 5. Inspection event and operator advisory

Each inspection event includes a record ID, board ID, timestamp, source type, model filename and class order, thresholds, inference latency, detections and station information. Each detection stores a class ID/name, confidence, bounding box and image-relative location.

The vision model is responsible for visual defect localization. The Llama advisory receives the structured event as text only. It does not receive the PCB image and is instructed not to add, remove, relabel or suppress detector findings. It produces an explanation, recommended operator checks, a severity note and a log entry.

The advisory is configured for Llama 3.2 1B Instruct SpinQuant INT4/EO8 using ExecuTorch's text-only C++ `llama_main` runner on the Raspberry Pi 5 CPU. The repository includes a pinned Hugging Face model downloader, local SHA-256 manifest generation, the pinned ExecuTorch Pi 5 runner build script (Pi-native build or x86_64 cross-build with the target Pi root filesystem) and an integration entry point called by the production inspection coordinator. The PTE weights and matching tokenizer are downloaded locally under the upstream Llama 3.2 license and are not committed to Git. The default station configuration requires the advisory (`PCB_LLAMA_REQUIRED=true`); it is not treated as an optional cloud feature.

The Llama prompt contains only the structured event fields and detection summaries. It does not contain the image or image path. The generated response must be a four-field JSON object and is validated before it is displayed. The advisory cannot alter detector findings, issue an independent PASS/REJECT decision or control the conveyor or illumination. A human operator remains responsible for the quality disposition.

The deployment recipe and integration source are committed, but the actual PTE/tokenizer download, compiled runner installation and live inference on the team's Raspberry Pi must still be evidenced in the commissioning record. Do not claim target-device Llama execution until the smoke test and complete station cycle are recorded.

The detector now applies a configurable provisional type-based screening policy from `models/severity_policy.json`: `missing_hole` is MEDIUM, while `open_circuit` and `short_circuit` are HIGH. The policy records a rationale for each class and explicitly states that board-specific validation/approval is still required. It is an initial review-priority rule, not a board-specific electrical risk assessment or safety certification. Unknown classes fall back to UNASSESSED. Confidence is a detector score and is never used to assign severity.

A decision of `NO_TARGET_DEFECT_DETECTED` means the detector did not find one of the three configured classes in the captured frame. It is not a declaration that the entire PCB is defect-free.

## 6. Local records and Firebase synchronization

The Pi stores the captured image, annotated image and event JSON in its configured output directory. The dashboard reads recent history from the Pi service.

The Firebase client copies completed inspection records to Realtime Database when configured. It is a data-synchronization path; it is not required for local image capture or local model inference. Firebase credentials must not be committed to the public repository.

## 7. Testing and evaluation

The repository includes automated software checks for the class-order contract, event schema, station state transitions, advisory prompt boundary, advisory response format, dashboard script syntax, dataset importer and safe dataset archive extraction. A Pi-side detector benchmark and a still-image vision-plus-Llama pipeline benchmark are also committed.

These checks do not exercise the physical GPIO wiring, camera, LED driver, final YOLO weights, downloaded Llama package, compiled ExecuTorch runtime or sustained Raspberry Pi operation. The following evidence is still required before a complete technical claim can be made:

| Area | Evidence required |
|---|---|
| Detection quality | Per-class precision, recall and F1; confusion matrix; mAP@50 and mAP@50–95; false positives and missed defects on a held-out board-level test split |
| Model provenance | Exact checkpoint path and hash, dataset version, split manifest, class map, image size and thresholds |
| Export correctness | ONNX model hash, input/output contract and prediction comparison against the source checkpoint |
| Station operation | Verified GPIO pin mapping, camera capture, illumination timing, repeated trigger tests and complete operator workflow |
| Edge performance | Pi-side inference latency percentiles, throughput, RAM and temperature, measured on the stated Pi configuration |
| Advisory operation | Downloaded Llama model/tokenizer identity and hashes, ExecuTorch version/build, valid output and measured on-device response time |
| Application reliability | Repeated capture-to-result tests, local record integrity and Firebase synchronization result when enabled |

Do not report workstation measurements as Raspberry Pi measurements. Do not claim a performance threshold unless it has been measured using the stated hardware and method.

## 8. Current release status

The repository includes the source implementation, dashboard, event schema, dataset preparation and training source, deployment instructions, tests and a demonstration MP4 file.

The final YOLO binaries and the generated deployment bundle are installed locally by `scripts/provision_pi5.sh` rather than committed to the source checkout. The processed project dataset/audit, held-out evaluation output and completed Pi commissioning record are still not present in this source checkout. The pinned Llama downloader and ExecuTorch Pi 5 build route are present, but the licensed PTE/tokenizer and compiled runner are local deployment assets, not tracked Git files. Their installation and target smoke test must be recorded on the actual Pi. The project team confirms that the demonstration MP4 is complete. The MP4 is present in the repository; the evaluator should be given the repository link or a shareable public/unlisted URL if required.

The source-only repository is not yet a complete runnable release. These missing artifacts and validations are listed in [Submission readiness](SUBMISSION_READINESS.md).

Source repository: https://github.com/MathewsV-Manoj/pcb-defect-detection
