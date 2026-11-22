# Published PCB defect-detection benchmarks

**Purpose:** literature comparison for the PCB inspection prototype. Every score in this document is a publisher-reported result from a separate model and evaluation. These are **not measurements from this project**, are not a validation of the model currently deployed by this repository, and must not be copied into the project-accuracy fields.

## Comparable published results

The closest public datasets in the reviewed papers are DeepPCB and PKU-Market-PCB. Both contain multiple PCB defect classes, including open-circuit and short-circuit defects; PKU-Market-PCB and the HRIPCB-derived data used in recent work also contain missing-hole labels.

| Published model / study | Evaluation dataset | Precision | Recall | mAP@0.50 | mAP@0.50:0.95 | Notes |
|---|---|---:|---:|---:|---:|---|
| YOLO-MBBi (Du et al., 2023) | DeepPCB | 98.7% | 97.5% | 99.0% | Not reported in the cited comparison table | Six classes; paper reports averages across three random train/validation/test divisions |
| PCB-MMF (Jin et al., 2026) | DeepPCB | 96.23% | 97.02% | 98.68% | 82.16% | 2.36 M parameters; paper reports 5.5 GFLOPs and 73.79 FPS |
| RT-DETR-L (Jin et al., 2026) | DeepPCB | 98.20% | 97.66% | 98.74% | 82.34% | 32.0 M parameters; paper reports 103.5 GFLOPs and 30.00 FPS |
| PCB-YOLO (Wang et al., 2026) | PKU-Market-PCB | 96.1% | 97.4% | 98.4% | 71.6% | 2.4 M parameters; 6.9 GFLOPs; paper reports 224 FPS |
| PCB-YOLO (Wang et al., 2026) | DeepPCB cross-dataset evaluation | Not reported in the cited summary | Not reported in the cited summary | 99.0% | 80.4% | Paper reports 196 FPS and per-class AP above 98.2%; this is a separate cross-dataset experiment |

### Dataset and evaluation context

**YOLO-MBBi — DeepPCB.** Du et al. describe DeepPCB as 1,500 defect images with corresponding defect-free reference images. They report a 1,200/150/150 train/validation/test division and average the metrics from three random divisions. The DeepPCB test-set comparison table reports YOLO-MBBi precision 0.987, recall
0.975, mAP@0.50 0.990 and 69.5 FPS. Its per-class tables report:

| DeepPCB source class | Mapping to project class | Precision | Recall | AP@0.50 |
|---|---|---:|---:|---:|
| open | open_circuit | 98.4% | 98.3% | 99.4% |
| short | short_circuit | 99.3% | 94.7% | 98.8% |
| pin-hole | Not mapped | 99.4% | 98.8% | 99.5% |
| mouse bite | Not mapped | 98.9% | 97.3% | 99.1% |
| spur | Not mapped | 96.4% | 97.7% | 98.9% |
| copper | Not mapped | 99.3% | 96.0% | 98.3% |

The source `pin-hole` annotation is not a verified equivalent of this
project's `missing_hole` definition. Do not use the pin-hole score as a
missing-hole result.

**PCB-MMF and RT-DETR-L — DeepPCB.** Jin et al. describe 1,500 paired defect/reference images and six annotations: open, short, mouse bite, spur, copper and pin-hole. The authors split the image pairs 7:2:1 into training, validation and test sets. Table 5 reports the precision, recall, mAP@0.50, mAP@0.75 and mAP@0.50:0.95 values listed above. These models were evaluated by the paper's authors, not on this project's Raspberry Pi station.

**PCB-YOLO — PKU-Market-PCB.** Wang et al. describe 1,386 images and six classes: missing hole, mouse bite, open circuit, short circuit, spurious copper and spur. Their split is 1,109 training, 138 validation and 139 test images. They report 96.1% precision, 97.4% recall, 98.4% mAP@0.50, 71.6% mAP@0.50:0.95 and 224 FPS. The reported FPS is from the authors' experimental setup, not a Raspberry Pi 5 measurement.

**PCB-YOLO — DeepPCB cross-dataset evaluation.** The same study reports 99.0% mAP@0.50 and 80.4% mAP@0.50:0.95 on DeepPCB, compared with 94.0% and 65.4% for its YOLOv8n baseline. It reports 196 FPS on this test. The paper says all six defect categories exceeded 98.2% AP under PCB-YOLO, with short-defect AP at 98.2%.

## The pretrained detector currently used by the Pi provisioner

The current one-command provisioner downloads the six-class YOLOv8s checkpoint published by Sulojan Rajkumar. Its model-card results, on the publisher's stated 70-image / 286-box test set, are:

| Metric | Publisher-reported result |
|---|---:|
| Precision | 97.2% |
| Recall | 91.2% |
| mAP@0.50 | 94.1% |
| mAP@0.50:0.95 | 50.3% |
| Inference time | 18.4 ms/image in the publisher's test environment |

Per-class mAP on the same publisher-reported test set is:

| Source class | Application mapping | mAP@0.50 | mAP@0.50:0.95 |
|---|---|---:|---:|
| missing_hole | missing_hole | 99.5% | 65.7% |
| mouse_bite | Ignored | 92.2% | 51.2% |
| open_circuit | open_circuit | 99.2% | 53.8% |
| short | short_circuit | 97.5% | 50.2% |
| spur | Ignored | 90.4% | 44.8% |
| spurious_copper | Ignored | 86.1% | 36.2% |

The six source classes are `missing_hole`, `mouse_bite`, `open_circuit`, `short`, `spur` and `spurious_copper`. This repository's deployment sidecar maps only `missing_hole`, `open_circuit` and `short` to the application's three classes. The author-reported figures above are for the original six-class checkpoint and its own evaluation, not a measured result after this project's export, class filtering, ONNX decoding or Raspberry Pi deployment.

Source model: https://huggingface.co/Sulojan/pcb-defect-yolov8s

## Why these figures are not the project's detection accuracy

1. **Different model weights.** The studies evaluate their own trained architectures and checkpoints. This repository does not contain a project-trained three-class checkpoint.
2. **Different datasets and image distributions.** Public, synthetic or laboratory PCB images do not reproduce this station's camera, lens, lighting, conveyor vibration, board materials or defect appearance.
3. **Class-name similarity is not annotation equivalence.** DeepPCB's `pin-hole` class must not automatically be treated as a missing drill hole at a known expected location. Class definitions must be reconciled before training or scoring.
4. **Different splits and possible image correlation.** The cited papers describe image-level random splits in some experiments. This repository requires the project to keep all views and crops from a physical board/capture group in one split. Published values may therefore have a different generalization difficulty.
5. **Different score definitions and operating points.** Precision and recall depend on the evaluator's confidence threshold and matching rules. mAP integrates the precision-recall curve at a stated IoU threshold; mAP@0.50:0.95 is stricter than mAP@0.50.
6. **FPS is not portable.** It depends on the device, runtime, precision, image size, batch size, preprocessing and whether post-processing is included. None of the quoted FPS values is a measurement of this project's Pi 5 pipeline.

## Project-measured accuracy status

| Required project evidence | Current status |
|---|---|
| Project dataset import manifest with verified labels and licences | Not supplied in this repository |
| Processed train/validation/test data and audit | Not present |
| Team-trained three-class checkpoint | Not present |
| Held-out board-level predictions | Not present |
| Project precision / recall / per-class F1 / macro-F1 | Not measured |
| Project mAP@0.50 / mAP@0.50:0.95 | Not measured |
| Confusion matrix and false-positive / false-negative review | Not measured |
| ONNX-versus-source-checkpoint prediction parity | Not measured |

Do not replace any of these fields with the literature values above. Once the project's labeled dataset and checkpoint are available, run:

```bash
python pcb_engine_kit/train_export.py validate \
  --data /path/to/processed/pcb3/data.yaml \
  --weights /path/to/team_best.pt \
  --size 640 --device 0 \
  --report-out docs/results/project_test_metrics.json
```

Keep the dataset audit, group-split evidence, checkpoint SHA-256 and evaluator report with the submission. The report generator now records per-class test image/object support, per-class precision/recall/F1/AP, macro-F1 and the evaluation settings. A test split with a missing target class must be treated as incomplete.

## Use in the Bharat AI-SoC submission

The challenge rules state that entries must be the entrants' original work,
be solely owned by the entrants and must not violate third-party intellectual
property. This literature comparison is appropriate as related-work and
benchmark context; it is not evidence that this project trained the listed
models, owns their checkpoints or achieved their scores. Keep model/data
attribution and licence notices with any third-party baseline, and verify the
rights to the actual model weights and training data used in the submission.
The checkpoint currently fetched by the provisioner is declared MIT by its
model card, but the dataset terms still require separate verification.

Official challenge page: https://armbharatchallenge.com/

## Sources

1. Bowei Du, Fang Wan, Guangbo Lei, Li Xu, Chengzhi Xu and Ying Xiong, “YOLO-MBBi: PCB Surface Defect Detection Method Based on Enhanced YOLOv5,” *Electronics*, 12(13), 2821 (26 June 2023). https://doi.org/10.3390/electronics12132821
2. Lingxiao Jin, Yuqin Feng, Hao Yang and Shuxian Liu, “A multi-cognitive PCB defect detection model integrating Mamba,” *Scientific Reports*, 16, 19124 (25 April 2026). https://doi.org/10.1038/s41598-026-49734-2
3. Yuting Wang, Bingyang Guo, Liming Sun and Ruiyun Yu, “Toward Real-Time Industrial Small Object Inspection: Decoupled Attention and Multi-Scale Aggregation for PCB Defect Detection,” *Electronics*, 15(6), 1191 (12 March 2026). https://doi.org/10.3390/electronics15061191
4. Sulojan Rajkumar, YOLOv8s PCB defect detector model card and checkpoint: https://huggingface.co/Sulojan/pcb-defect-yolov8s. The author's training/evaluation source repository, including the reported precision, recall and inference-time results: https://github.com/Sulojan2027/PCB_Defect_Detect

**Reporting rule:** use the above only as *published literature benchmarks*. Only results generated from this project's verified held-out boards may be labelled *project results* or *our detection accuracy*.
