# PCB dataset and YOLO training tools

This folder contains the dataset importer, annotation utility and YOLO training/ONNX export scripts used to prepare the detector deployed by the Raspberry Pi station.

The deployment class order is fixed:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

## Prepare the dataset

Copy `datasets/import_manifest.example.csv` to `datasets/import_manifest.csv` and enter the real image and annotation paths. The manifest contains one row per image.

| Column | Meaning |
|---|---|
| `image` | Source image path, relative to the CSV |
| `label` | Annotation path, relative to the CSV |
| `format` | `yolo`, `voc` or `deeppcb` |
| `split` | `train`, `val` or `test` |
| `group` | Physical board/design/capture group |

Keep images from the same PCB or capture group in one split. The importer checks files, class IDs, bounding boxes, exact duplicate image hashes and group/split consistency. It writes `data.yaml` and `audit.json` into a new output folder.

```bash
cd pcb_engine_kit
cp ../datasets/import_manifest.example.csv ../datasets/import_manifest.csv
# Replace every example path and group in the CSV.
python dataset.py ../datasets/import_manifest.csv ../datasets/processed/pcb3
```

The importer checks the class mapping. DeepPCB open/short labels are mapped only after checking the source annotation convention. Its `pin-hole` category is not treated as `missing_hole`.

## Train and validate

Install the training dependencies in a separate environment:

```bash
python -m pip install -r requirements-train.txt
```

Train the detector:

```bash
python train_export.py train \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights yolov8n.pt \
  --size 640 --epochs 100 --batch 4 --device 0
```

The script validates the class names in the dataset YAML before training and prints the exact `best.pt` path after training. Use that printed path for the next steps; do not assume a run-directory name.

Run held-out test evaluation:

```bash
python train_export.py validate \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights <EXACT_BEST_PT_PATH> \
  --size 640 --device 0
```

Keep the checkpoint, data YAML, import manifest, generated audit, training arguments and test output together. Do not report metrics from a different checkpoint or split.

## Export the Raspberry Pi ONNX model

The station expects a raw YOLO ONNX model without NMS embedded in the graph:

```bash
python -m pip install -r requirements-export.txt
python train_export.py export-onnx \
  --weights <EXACT_BEST_PT_PATH> \
  --size 640 --out deployment
```

This writes `best.onnx` and `best.onnx.json`. Copy both into the repository's `models/` folder on the Pi. The metadata records the class order, image preprocessing contract and ONNX SHA-256. Export completion does not mean the model has been validated on the Pi.

## Annotation and utility scripts

- `label.py` — draw and save YOLO bounding boxes with OpenCV.
- `safe_extract.py` — extract a dataset ZIP after checking for path traversal, symlinks and oversized archives.
- `test_contracts.py` — dependency-light checks for archive extraction and dataset-import contracts.
