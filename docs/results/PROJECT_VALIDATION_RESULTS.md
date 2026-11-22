# Project model validation results

## Current status: no verified accuracy result included

This repository does not publish a numerical accuracy result for the three-class PCB defect detector.

A previously supplied screenshot could not be linked to an identified model checkpoint, training-provenance record, dataset version, board-group split manifest, validation sample counts or raw evaluator output. Its numerical values have therefore been excluded from the submission-facing project results. They are not attributed to the detector implementation documented in this repository.

The current machine-readable record is `project_validation_metrics.json` and correctly reports `NOT_PROVIDED` with null metric fields. The separate held-out test record is `project_test_metrics.json`; it is also `NOT_PROVIDED`.

Do not report precision, recall, F1, mAP, false-positive rate, false-negative rate or overall detection accuracy as an achieved project result until the exact checkpoint and audited test dataset are available and the evaluation can be reproduced. Do not substitute values from another PCB detector, paper, hardware benchmark or model package.

## What is present

The repository contains source code for:
- manifest-driven dataset import and provenance auditing;
- random-initialization detector training using an Ultralytics architecture YAML with `pretrained=False`;
- held-out test evaluation;
- ONNX export and checkpoint-to-ONNX prediction-parity checking.

The presence of these tools demonstrates software implementation work. It does not mean that a training run, export or evaluation has been completed.
