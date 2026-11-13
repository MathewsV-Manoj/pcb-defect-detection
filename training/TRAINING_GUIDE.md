# Training and evaluation protocol

## Intended detector
YOLOv8 Nano, three classes, input 640. Raspberry Pi 5 handoff class order:
```text
0 missing_hole
1 open_circuit
2 short_circuit
```

Do not retrain merely to populate a repository. First locate and verify the final run under `runs/pcb3/`. The earlier `runs/pcb/` model was six-class and is not the target model.

## Reproduction template
On the training workstation, using the recorded Ultralytics version:
```bash
yolo detect train model=yolov8n.pt data=/absolute/path/to/data.yaml imgsz=640 epochs=100 batch=4 project=runs name=pcb3
```
This is a template, not a claim that these exact parameters produced the checkpoint referenced by the handoff. Preserve the original `args.yaml` and `results.csv`.

## Evaluation
```bash
yolo detect val model=runs/pcb3/weights/best.pt data=/absolute/path/to/data.yaml imgsz=640 split=test
```
Save per-class precision, recall, mAP@50, mAP@50–95, confusion matrix, PR curves and sample predictions. Select thresholds on validation data; use the held-out test split for final reporting.

## ONNX export
```bash
yolo export model=runs/pcb3/weights/best.pt format=onnx imgsz=640 simplify=True
```
Verify ONNX inputs/outputs and compare PyTorch/ONNX predictions on the same images. A successful export is not proof of a correct decoder.

## Model release record
Record checkpoint and ONNX SHA-256, dataset version, `data.yaml`, class order, image size, thresholds, package versions, evaluation split and export command in `models/release_manifest.json`. No accuracy or runtime numbers are hard-coded here.
