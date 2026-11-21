# PCB dataset and model development utilities

This package contains the source utilities for PCB dataset preparation, annotation, YOLO training and validation, deployment export, queued TFLite inference and reference-board comparison.

The primary Raspberry Pi 5 station uses the ONNX Runtime CPU inference application in `raspberry_pi/`. The canonical class order is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

## Dataset preparation

`dataset.py` converts supported YOLO, Pascal VOC and DeepPCB annotations into a canonical YOLO dataset. Its CSV manifest requires the following fields:

| Field | Meaning |
|---|---|
| `image` | Image path relative to the manifest directory |
| `label` | Annotation path relative to the manifest directory |
| `format` | `yolo`, `voc` or `deeppcb` |
| `split` | `train`, `val` or `test` |
| `group` | Board/capture group identifier |

Rows from the same board group must remain in a single split. Duplicate image content is rejected by SHA-256. The converter validates image readability and bounding-box ranges and writes `data.yaml` and `audit.json`.

The image-import manifest is separate from `datasets/SOURCE_MANIFEST.csv`, which records dataset provenance. Start from `datasets/import_manifest.example.csv`, then replace the example image and label paths with the actual local files:

```bash
cp ../datasets/import_manifest.example.csv ../datasets/import_manifest.csv
# Edit import_manifest.csv so every row points to an existing image and label.

cd pcb_engine_kit
python dataset.py ../datasets/import_manifest.csv ../datasets/processed/pcb3
```

The provenance manifest is not accepted as the dataset-import CSV. Source datasets and redistribution permissions remain governed by their original providers. DeepPCB open- and short-circuit annotations are mapped explicitly. A DeepPCB pin-hole annotation is not treated as a missing-hole annotation.

## Train and validate the three-class detector

```bash
cd pcb_engine_kit

python train_export.py train \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights yolov8n.pt \
  --size 640 --epochs 100 --batch 4 --device 0

python train_export.py validate \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights runs/pcb/weights/best.pt \
  --size 640 --device 0
```

The training configuration uses the canonical class order, a fixed seed, board-group-aware split and YOLO training/validation routines. Preserve the checkpoint, data YAML, split manifest, training arguments, evaluation plots and model hash together.

## Export for the Raspberry Pi ONNX station

The base Raspberry Pi station uses `models/best.onnx`. Export the trained checkpoint with the raw YOLO output contract (embedded NMS disabled):

```bash
python train_export.py export-onnx \
  --weights runs/pcb/weights/best.pt \
  --size 640 --out deployment
```

The export produces:

- `deployment/best.onnx` — raw YOLO ONNX detector for the Raspberry Pi CPU path.
- `deployment/best.onnx.json` — class order, input size, preprocessing contract and SHA-256 identity.

Copy the verified ONNX file to `models/best.onnx` on the Raspberry Pi deployment. The metadata file should be retained with the model release. The repository intentionally does not contain unverified model weights.

The Pi inference contract is three-channel RGB, letterbox/pad to 640 × 640, float32 normalization to [0, 1], NCHW input and a raw YOLO output with four box values plus three class scores.

## Export the supplementary TFLite folder-worker model

The queued-image worker uses a separate TFLite runtime and metadata contract. Export an INT8 model with representative calibration data:

```bash
python train_export.py export-tflite \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights runs/pcb/weights/best.pt \
  --size 640 --out deployment_tflite
```

The exporter writes `detector.tflite` and `metadata.json`. Its metadata is marked unvalidated until model parity and real-camera tests have passed. This TFLite path is separate from the Pi station's ONNX Runtime inference path.

The combined `export` mode writes both formats.

## Local annotation and reference-board checking

- `label.py` is the OpenCV bounding-box annotator; hotkeys are 1 = missing hole, 2 = open circuit, 3 = short circuit, R = draw, U = undo, S = save, Q = quit.
- `make_reference.py` creates a known-good reference image and selected regions for ORB/homography-based review.
- `engine.py` is a single-worker TFLite folder processor with incoming, processing, results, archive and failed queues.
- `evaluate_pi.py` measures exported-model detector timing and thresholded IoU matching. Its output is a basic detector evaluation report, not a COCO mAP calculation.

## Safety and reproducibility

`safe_extract.py` rejects ZIP path traversal, symlinks and oversized archives. `submit.py` atomically moves a complete input image into the folder-worker queue.

Do not report model performance until it is measured on a held-out board-level test split. A valid release includes the model hash, class map, data provenance, runtime version, preprocessing contract, validation results and target-device measurements.
