# Project PCB detector validation results

**Result type:** Team-reported validation metrics  
**Source:** User-supplied screenshot titled "Training results"  
**Source image filename:** `image(20261122-041729).png`  
**Source image SHA-256:** `e3e0bcf601d66d29163757287bf646ec18d6967ebc594688a169893c8cb02b0c`  
**Source image dimensions:** 1093 × 740 pixels  
**Recorded on:** 22 November 2026

## Overall validation metrics

| Metric | Reported value |
|---|---:|
| Precision | **98.3%** |
| Recall | **98.4%** |
| mAP@0.50 | **98.9%** |
| mAP@0.50:0.95 | **62.5%** |

## Per-class validation metrics

| Defect | Precision | Recall | mAP@0.50 |
|---|---:|---:|---:|
| Missing Hole (`missing_hole`) | 97.8% | 98.2% | 98.5% |
| Open Circuit (`open_circuit`) | 99.1% | 99.6% | 99.5% |
| Short Circuit (`short_circuit`) | 97.9% | 97.6% | 98.8% |

## Interpretation and limits

These numbers are transcribed from the screenshot. They are **validation results**, not an independently held-out test result, not a Raspberry Pi 5 measurement, and not a measurement of the separately published YOLOv8s baseline unless the exact checkpoint identity confirms that relationship.

The screenshot does not show the dataset name/version, number of validation images or instances, board-level split manifest, model/checkpoint path or SHA-256, image size, confidence threshold, NMS IoU threshold, evaluator version, or raw evaluator output. Those fields are deliberately left unknown in the machine-readable record.

Before using these figures as reproducible experimental results, archive:
1. The exact `best.pt` checkpoint and its SHA-256.
2. The dataset version, source/licence records, import manifest and generated dataset audit.
3. The train/validation/test split manifest, with all images from one physical board/design/capture group confined to one split.
4. The raw validation log/report and evaluator version/settings.
5. The ONNX export and metadata, followed by source-checkpoint/ONNX prediction-parity checks.

A separate board-level held-out test set must be evaluated before reporting generalisation/test accuracy. Do not use the validation split as the final test split. Do not substitute published-paper metrics for project measurements.

## Machine-readable record

The same values are stored in [published_pcb_benchmarks.json](published_pcb_benchmarks.json), under `project_results`. External literature benchmarks are stored separately in the `benchmarks` array.
