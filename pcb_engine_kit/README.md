# PCB detector training, evaluation and export pipeline

This folder contains the dataset importer, annotation utility, training/evaluation script and release audit utility.

The deployment class order is fixed:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

## Dataset preparation

The repository does not include the team's raw or processed training dataset. Follow [the dataset provenance guide](../datasets/README.md), complete the real import manifest and rebuild the dataset:

```bash
python -m pip install -r pcb_engine_kit/requirements-train.txt
python pcb_engine_kit/dataset.py datasets/import_manifest.csv datasets/processed/pcb3
python pcb_engine_kit/audit_release.py --data datasets/processed/pcb3/data.yaml --output-dir docs/results
```

Training is blocked unless the generated audit has complete team-declared source/rights/annotation metadata and all three classes are represented in train, validation and test. The importer does not infer project class mappings from external dataset class IDs. Convert annotations only after manually checking the exact source class definitions.

## Train from an architecture YAML — no pretrained detector weights

The project training entry point accepts a model architecture YAML (default: `yolov8n.yaml`) and deliberately rejects `.pt` initial weights. The model is initialized without pretrained weights:

```bash
python pcb_engine_kit/train_export.py train \
  --data datasets/processed/pcb3/data.yaml \
  --model-yaml yolov8n.yaml \
  --size 640 --epochs 100 --batch 4 --device 0
```

The script prints the exact output checkpoint. It also writes `project_training_provenance.json` beside the run's `weights/best.pt`, recording the checkpoint SHA-256, dataset YAML/audit hashes, class order, training parameters, software version and the explicit random-initialization declaration.

This record ties the checkpoint bytes to the recorded training inputs. It is not proof of the operator's identity, legal rights, annotation correctness or generalization. The project team must truthfully confirm that the documented run was actually performed by its members.

## Evaluate the held-out test split

Use the exact checkpoint printed by the training command:

```bash
python pcb_engine_kit/train_export.py validate \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --size 640 --device 0 \
  --report-out docs/results/project_test_metrics.json
```

The validation command evaluates the `test` split, not train or validation. The machine-readable report includes checkpoint and dataset hashes, test support per class, per-class precision/recall/F1/AP and aggregate metrics. A test split without any one target class is incomplete and must not be presented as complete three-class evaluation.

## Export for the Raspberry Pi application

```bash
python pcb_engine_kit/train_export.py export-onnx \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --size 640 --out deployment
```

The exporter writes `best.onnx` and `best.onnx.json`. The metadata binds the ONNX file to the project checkpoint SHA-256, dataset audit and training-provenance hashes. Export success alone does not prove prediction parity or Raspberry Pi performance.

Run the parity checker against the exact held-out test split:

```bash
python pcb_engine_kit/compare_pt_onnx.py \
  --checkpoint runs/pcb/weights/best.pt \
  --onnx deployment/best.onnx \
  --data datasets/processed/pcb3/data.yaml \
  --images-dir datasets/processed/pcb3/images/test \
  --report-out docs/results/project_onnx_parity.json \
  --mark-verified
```

The tool checks the checkpoint, ONNX sidecar, training-provenance and dataset hashes before running both models with the same CPU settings. It matches predictions by class ID and bounding-box IoU, and checks confidence/coordinate differences. It requires the exact test folder named in `data.yaml`; `--mark-verified` is refused for a partial image sample. It updates the sidecar parity flag only when the full test directory passes. This is prediction parity, not detection accuracy or Pi performance.

## Portable release audit

```bash
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

Do not copy another author's PCB model or published benchmark into the project's model/result fields. External libraries and the Llama foundation model are third-party components and must remain attributed in the software/dependency disclosures.
