# Dataset and model tools

The scripts in this folder are used to prepare PCB images, train the detector and export models. The main station software is in raspberry_pi/. It uses ONNX Runtime. The folder-worker in engine.py is a separate TFLite utility.

The detector class order is fixed:

~~~text
0 missing_hole
1 open_circuit
2 short_circuit
~~~

## Prepare the dataset

Make a copy of datasets/import_manifest.example.csv and edit the image and label paths. The file has one row per image.

| Column | What to enter |
|---|---|
| image | Image path, relative to the CSV |
| label | Label file path, relative to the CSV |
| format | yolo, voc or deepPCB |
| split | train, val or test |
| group | Board or capture-session ID |

Keep images of the same board in one split. The importer checks the image files, label files, class IDs, bounding boxes and duplicate image hashes. It writes data.yaml and audit.json into a new output folder.

The source list in datasets/SOURCE_MANIFEST.csv is not the image import manifest. It only records where datasets came from and their reuse terms.

~~~bash
cd pcb_engine_kit
cp ../datasets/import_manifest.example.csv ../datasets/import_manifest.csv
# Edit import_manifest.csv with the real paths and board groups.
python dataset.py ../datasets/import_manifest.csv ../datasets/processed/pcb3
~~~

For DeepPCB, the importer maps the configured open-circuit and short-circuit IDs. It does not assume that a pin-hole label means missing_hole. Check the source annotation definitions before adding that class.

## Train and validate

Install the training packages in a separate training environment:

~~~bash
python -m pip install -r requirements-train.txt
~~~

Train the detector:

~~~bash
python train_export.py train \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights yolov8n.pt \
  --size 640 --epochs 100 --batch 4 --device 0
~~~

Run validation on the test split:

~~~bash
python train_export.py validate \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights runs/pcb/weights/best.pt \
  --size 640 --device 0
~~~

Keep the checkpoint, dataset YAML, import manifest, audit, training arguments and test output together. Do not report scores from a different checkpoint or a different test split.

## Export the Raspberry Pi model

The station expects a raw YOLO ONNX model without NMS embedded in the graph:

~~~bash
python train_export.py export-onnx \
  --weights runs/pcb/weights/best.pt \
  --size 640 --out deployment
~~~

This writes best.onnx and best.onnx.json. Copy both into the models folder on the Pi. The JSON file records the class order, input format and model SHA-256. The export has not been validated on the Pi just because this command completed.

## Export the TFLite folder-worker model

engine.py uses TFLite and is not called by the main station controller.

~~~bash
python train_export.py export-tflite \
  --data ../datasets/processed/pcb3/data.yaml \
  --weights runs/pcb/weights/best.pt \
  --size 640 --out deployment_tflite
~~~

This writes detector.tflite and metadata.json. Run the worker and check the output on the target device before relying on it.

## Other scripts

- label.py — draw and save YOLO bounding boxes with OpenCV.
- make_reference.py — select regions from a known-good board for the optional ORB/homography comparison.
- submit.py — copy a complete image into the TFLite worker's incoming folder using an atomic rename.
- safe_extract.py — extract a dataset ZIP after checking for path traversal, symlinks and oversized archives.
- evaluate_pi.py — basic TFLite detector timing and IoU matching. It does not calculate COCO mAP.
- test_contracts.py — tests for the ZIP extractor and image queue.

A model release should include the checkpoint, model hash, class map, dataset source list, board-level split, validation output and Pi measurements. Do not add numerical performance claims until they have been measured on the stated test set and device.
