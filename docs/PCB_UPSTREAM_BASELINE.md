# Third-party PCB YOLOv8s baseline: source, metrics and deployment mapping

This repository records an externally published checkpoint as a **credited
pretrained baseline**. It is not a model trained by the current project team.
The upstream metric values below belong to the original author's held-out
test split; they are not measurements of this repository's Raspberry Pi
station or camera setup.

## Selected checkpoint

| Field | Value |
|---|---|
| Model | YOLOv8s PCB defect detector |
| Publisher/author | Sulojan Rajkumar |
| Hugging Face repository | https://huggingface.co/Sulojan/pcb-defect-yolov8s |
| Source-code repository | https://github.com/Sulojan2027/PCB_Defect_Detect |
| Artifact | \`best.pt\`, 22.5 MB |
| Upstream model-file commit | \`c6d4b68\` |
| Published SHA-256 | \`1acd655ce93a474f0ed00958ddd1079afb46c74868f916af6187bf63dad5bb3d\` |
| Model-card license declaration | MIT |
| Dataset reported by author | Kaggle \`akhatova/pcb-defects\` |
| Class order | \`missing_hole, mouse_bite, open_circuit, short, spur, spurious_copper\` |
| Input | 640 × 640 |

The model card identifies the six classes, training setup, test split and
license. The companion source repository names the author and provides its
training/evaluation workflow.

## Author-reported held-out results

The upstream author reports the following results on a 70-image / 286-box
test split. The original training description reports 554 training images,
69 validation images and 70 test images, grouped from 10 PCB board designs.

| Metric | Upstream author's result |
|---|---:|
| Precision | 0.972 |
| Recall | 0.912 |
| mAP@0.50 | 0.941 |
| mAP@0.50:0.95 | 0.503 |
| Inference | 18.4 ms/image (author-reported test environment) |
| Best checkpoint | Epoch 116 |

Per-class mAP:

| Source class | mAP@0.50 | mAP@0.50:0.95 |
|---|---:|---:|
| missing_hole | 0.995 | 0.657 |
| mouse_bite | 0.922 | 0.512 |
| open_circuit | 0.992 | 0.538 |
| short | 0.975 | 0.502 |
| spur | 0.904 | 0.448 |
| spurious_copper | 0.861 | 0.362 |

The model card states 693 images from 10 board designs, an 80/10/10 split
with seed 42, YOLOv8s at 640 × 640, 180 training epochs and AdamW. Its
reported held-out test set contains 70 images and 286 boxes. These details
are included so that the source metrics are not confused with a different
dataset split or a measurement from this project.

## Mapping into the current three-class application

The published checkpoint has six outputs. The current inspection-event
schema has three classes. The sidecar created by the baseline exporter maps:

| Upstream output | Application output |
|---|---|
| missing_hole | missing_hole |
| open_circuit | open_circuit |
| short | short_circuit |
| mouse_bite | ignored |
| spur | ignored |
| spurious_copper | ignored |

This uses the author's class names; it does not reinterpret DeepPCB's
\`pin-hole\` label as \`missing_hole\`. The Pi decoder reads the ONNX sidecar,
validates the number of output channels and runs NMS only for the three
mapped application classes. Original six-class order and mapping are kept
in the inspection event for traceability.

## Fetch the exact upstream checkpoint

From the repository root:

    python -m pip install "huggingface_hub>=0.30,<2"
    python models/pretrained/download_sulojan_pcb_yolov8s.py

The downloader verifies the published SHA-256 before retaining the file.
It writes a local \`model_manifest.json\`. Large model files are ignored by
Git and are not copied into this repository.

## Export the six-class ONNX baseline for Raspberry Pi

Install the training/export dependencies from \`pcb_engine_kit/\`, then run
from the repository root:

    python -m pip install -r pcb_engine_kit/requirements-train.txt
    python models/pretrained/download_sulojan_pcb_yolov8s.py
    python pcb_engine_kit/train_export.py export-upstream-onnx \
      --weights models/pretrained/sulojan_pcb_yolov8s/best.pt \
      --size 640 \
      --out deployment_upstream

Copy the generated \`deployment_upstream/best.onnx\` and
\`deployment_upstream/best.onnx.json\` to the Pi as
\`models/best.onnx\` and \`models/best.onnx.json\`. The Pi inference and
benchmark scripts will read the sidecar and apply the three-class mapping.

This is a direct use of a published pretrained model with the documented
mapping. It is **not** a claim that this team trained that six-class model
or reproduced its published test results.

## Fine-tune for the project's own three-class data

To create a team-trained checkpoint, use the same upstream model as the
initialization, but train on the project's own verified three-class dataset:

    python pcb_engine_kit/train_export.py train \
      --data datasets/processed/pcb3/data.yaml \
      --weights models/pretrained/sulojan_pcb_yolov8s/best.pt \
      --size 640 --epochs 100 --batch 4 --device 0

The training wrapper accepts only the documented six-class source checkpoint
or the project's canonical three-class checkpoint, checks the dataset class
order and verifies that the saved best checkpoint has the project's
three-class order. Validate that resulting checkpoint on held-out board
groups, export using \`export-onnx\`, and report those metrics separately.

## License and attribution

The Hugging Face model card declares MIT. The checkpoint remains attributed
to Sulojan Rajkumar and the source-code repository above. Retain the upstream
MIT notice/terms and verify any separate dataset terms before reusing the
training data. This project does not claim ownership of the upstream model,
its training run, or its published metrics.
