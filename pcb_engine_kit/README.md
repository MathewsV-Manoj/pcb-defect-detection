# Supplementary PCB dataset and inference utilities

This directory contains supporting source utilities for dataset conversion, local annotation, YOLO training/export, queued-image processing, reference-board comparison and contract tests.

The primary Raspberry Pi 5 application path is maintained in `raspberry_pi/`. The deployment class-ID contract is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The dataset converter, training exporter and TFLite worker use this same class order. DeepPCB open-circuit and short-circuit annotations are mapped explicitly to the corresponding project IDs. A DeepPCB pin-hole label is not treated as a missing-hole label.

The folder-worker is a supplementary TFLite path and is separate from the root ONNX Runtime station controller. It is not a Hailo deployment. The optional ResAttention U-Net trace-extraction experiment is separate from the three-class defect detector.
