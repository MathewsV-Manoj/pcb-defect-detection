# Submission checklist and evaluation

This file lists what needs to be included in the submission and how the station should be tested. Use the checkboxes only after the corresponding evidence has been collected.

## What the submission should contain

| Item | Evidence to include | Current source status |
|---|---|---|
| Pi station software | Controller, API, camera capture and inspection coordinator | In repository |
| Operator page | Pi-hosted dashboard and browser-to-Pi request | In repository |
| Vision model | Final three-class checkpoint, ONNX file, hash and class map | Model files not included |
| Llama advisory | ExecuTorch .pte, matching tokenizer and runtime version | Model files not included |
| Dataset | Source list, import manifest, board-level split and label mapping | Templates and source list included; full dataset absent |
| Physical test | Video and completed Pi commissioning record | Needs recording on the station |
| Performance results | ONNX benchmark, end-to-end timing and Llama timing | No Pi measurements included |
| Technical report | Station sequence, model details, tests and measured results | Report included; add results after testing |

## Station acceptance test

Run this sequence on the actual Pi with the final model files installed.

| Test | Pass condition | Evidence |
|---|---|---|
| Initial arming | A continuous three-second hand presence arms the station | Status response or short video |
| Short IR activation | Releasing before three seconds does not arm it | Status response |
| Armed state | After release, the station remains armed | Status response |
| Board trigger | The next IR activation starts a single capture | Capture file and event log |
| Illumination | LED driver turns on during capture and then turns off | Video or measured signal |
| Image preview | Browser displays the most recent capture | Browser recording |
| Operator command | Run button starts processing on the Pi | API response and log |
| Vision result | An event and annotated image are written | JSON and image |
| Advisory result | A valid four-field response is displayed | Event JSON |
| Next board | A second board is captured without re-arming | Two consecutive event records |

Repeat the board cycle at least 20 times. Record the number of attempts, successful captures, missed triggers, duplicate triggers, unreadable images and failed runs.

The sensor reports presence at its trigger point; it does not measure exact image alignment. Confirm that the board is in the camera field through mechanical setup and the saved preview.

The detailed test sheet is in [PI5_COMMISSIONING.md](PI5_COMMISSIONING.md).

## Detection evaluation

Use a held-out set of boards or board groups. Images from one physical PCB or capture session must not be divided across training and test splits.

Report, at minimum:

- precision, recall and F1 for each of the three classes;
- the confusion matrix;
- false positives and missed defects;
- mAP@50 and mAP@50–95;
- sample predictions on boards that were not used for training.

The results must be generated from the final checkpoint and the exact test split listed in the release record. Do not reuse the older six-class DeepPCB baseline figures as three-class model results.

## Raspberry Pi runtime

Run raspberry_pi/benchmark_onnx.py on a folder of representative held-out images. Keep its JSON output with the model hash and Pi configuration.

The script measures image preprocessing, ONNX inference and detector post-processing. It reports per-image latency percentiles, sequential FPS, peak process RSS and thermal readings.

It does not measure:
- sensor-to-capture time;
- camera-to-browser transfer time;
- the complete inspection time including Llama;
- electrical power;
- detection accuracy.

Measure those separately. Use an external power meter for power. Record the start/end conditions and measurement method.

## Llama runtime

For the exact .pte model and tokenizer installed on the Pi, record:
- model and tokenizer hashes;
- ExecuTorch revision and build options;
- time to first token;
- tokens generated and tokens per second;
- total response time;
- peak process memory;
- whether the output passed the four-field JSON check.

Also check that the advisory does not introduce, remove or change a detector result.

## Severity

The current detector leaves severity as UNASSESSED. Do not assign LOW, MEDIUM or HIGH until the project has a board-specific rule based on defect type, physical extent and board function. Confidence is not a severity score.

## Demonstration video

The video should be recorded on the actual station. It should show the initial three-second hold, release, PCB loading, conveyor movement, IR trigger, LED capture, laptop preview, operator run button, Pi-side processing and the returned result. Do not use a simulated dashboard result as evidence of live hardware operation.

A shot list is kept in demo_video/README.md.

## Reproducibility record

For every reported result, save:

- Pi model and RAM configuration;
- operating system and kernel;
- Python, OpenCV, ONNX Runtime and ExecuTorch versions;
- model hashes and class order;
- tokenizer identity;
- dataset version and held-out split;
- image size and detector thresholds;
- number of images and repeated station cycles;
- measurement method, including any external instrument.

Only include values that were measured on the stated hardware. Workstation measurements must be labelled as workstation measurements.
