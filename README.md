# PCB inspection station — project software and evidence

A three-class PCB visual-inspection project for **missing hole**, **open circuit** and **short circuit** screening. This repository contains the application source, Raspberry Pi-targeted station controller, browser dashboard, YOLO training/export tools, Llama advisory integration and evidence/audit templates.

The repository is a **software and deployment source checkout**, not a verified release of the trained model or the complete physical station. The current checkout does not contain the processed training dataset, a project-trained checkpoint, a completed dataset/checkpoint audit, or target-device commissioning results. Those absences are recorded below rather than filled with assumed values.

## What the source implements

| Area | Present in repository | Verification status |
|---|---|---|
| Three-class detector contract | Class order, OpenCV preprocessing, ONNX decoder and training/export source | Source present; trained model artifact absent |
| Dataset tools | Importer, annotation helper, board-group split checks and provenance audit | Tools present; actual dataset and completed import manifest absent |
| Operator dashboard | Pi-served browser dashboard and inspection API | Source present; target-device workflow not evidenced |
| Edge inference | ONNX Runtime CPU path targeted at Raspberry Pi 5 | Deployment code present; no target smoke-test record |
| Advisory | Text-only Llama 3.2 1B Instruct integration through ExecuTorch | Third-party foundation model; model files and target test absent |
| Station controller | IR trigger, camera and LED-driver control source | Source present; physical wiring and full cycle not verified |
| Demo | MP4 file in demo_video/ | File present; content review still required |

The IR input is a presence trigger, not an image-position sensor. The source workflow does not claim precision positioning from the IR sensor. The browser is an operator interface; detector/advisory execution is designed for the Pi. Firebase event replication is optional and disabled by default in the example configuration.

## Detector ownership and initialization

The project training utility accepts a YOLO architecture YAML and explicitly trains with pretrained weights disabled. It rejects .pt initial checkpoints. This is intended to prevent a third-party PCB detector checkpoint from being presented as a model trained by this team.

The project-trained detector is **not currently included** in this repository. The Pi provisioner refuses to proceed without a project ONNX file and matching provenance sidecar. Ultralytics/PyTorch, OpenCV and ONNX Runtime are third-party software dependencies; the YOLO architecture and framework are not claimed as original inventions.

The Llama 3.2 1B Instruct model is also third-party. It is used only to turn structured detector findings into an operator advisory. It is not trained by the project team, does not receive the PCB image, and does not alter detector output.

## Dataset preparation, training and evaluation

The raw and processed training data are not included. Complete the import manifest with actual image and label paths, source links, permission review, annotation review and stable PCB/capture group IDs. Keep every image from the same physical board/design/capture group in a single split.

See:
- datasets/README.md — dataset source and audit requirements
- pcb_engine_kit/README.md — importer, random-initialized training, held-out test evaluation and export
- docs/results/project_dataset_audit.json — current dataset status
- docs/results/project_checkpoint_audit.json — current checkpoint status
- docs/results/project_release_audit.json — combined status

Example development workflow:

```bash
python -m pip install -r pcb_engine_kit/requirements-train.txt
python pcb_engine_kit/dataset.py datasets/import_manifest.csv datasets/processed/pcb3
python pcb_engine_kit/audit_release.py --data datasets/processed/pcb3/data.yaml --output-dir docs/results

python pcb_engine_kit/train_export.py train \
  --data datasets/processed/pcb3/data.yaml \
  --model-yaml yolov8n.yaml --size 640 --epochs 100 --batch 4 --device 0
```

Use the exact best.pt path printed by training for validation, export and audit. Do not use a validation score from one checkpoint to describe another checkpoint.

## Raspberry Pi deployment

Prepare and audit the project-trained ONNX detector on the development machine, then copy both deployment/best.onnx and deployment/best.onnx.json into models/ on the Raspberry Pi. The sidecar must bind the ONNX SHA-256 to the dataset audit and training-provenance hashes.

Then, on the documented Raspberry Pi 5 target, run:

```bash
bash scripts/provision_pi5.sh
bash scripts/run_station_pi5.sh
```

The provisioner no longer downloads a third-party PCB detector. It verifies the project detector metadata before installing the runtime and provisioning the separately licensed Llama/ExecuTorch advisory. It does not verify GPIO wiring or prove that the physical station works. Follow docs/PI5_COMMISSIONING.md.

## Project validation screenshot — not an independent test

A team-supplied screenshot reports the following validation metrics:

| Metric | Screenshot-reported value |
|---|---:|
| Precision | 98.3% |
| Recall | 98.4% |
| mAP@0.50 | 98.9% |
| mAP@0.50:0.95 | 62.5% |

These values are transcribed from the screenshot only. The screenshot does not identify the checkpoint, dataset version, sample counts, evaluator settings or raw output. They have not been reproduced from the current training pipeline and must not be described as held-out test accuracy, Pi performance or independently verified results. Per-class values and source-image hashes are in docs/results/PROJECT_VALIDATION_RESULTS.md and docs/results/project_validation_metrics.json.

**No numerical performance results from other PCB models, research papers, hardware benchmarks or Llama deployments are included as project results.** There is no independent test-set score or project Pi runtime measurement in the current checkout.

## Scope and release blockers

A valid final release still needs the actual project dataset and completed import audit, a random-initialized project checkpoint and provenance file, matching ONNX export, held-out test metrics, prediction-parity check, Pi runtime smoke test, physical commissioning record, offline test evidence and human review of the demo video. The severity policy remains provisional and requires board/QA approval.

The repository cannot independently prove that every custom source line was written by a named team member. Team members must review and confirm their contributions, identify any AI-assisted or reused code according to challenge rules, and preserve third-party notices and licences. The source does not claim sole authorship of external libraries, the YOLO architecture, ExecuTorch or Llama.

## Team

- **Mathews V Manoj** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Jordan Noby Eralil** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Deon Lukose Shince** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science

## Main documentation

- docs/PROJECT_REPORT.md
- docs/SUBMISSION_READINESS.md
- docs/DELIVERABLES_AND_EVALUATION.md
- docs/PHASE1_SUBMISSION_CHECKLIST.md
- docs/LOCAL_EXECUTION_AND_PERFORMANCE.md
- docs/PI5_DEPLOYMENT.md
- docs/PI5_COMMISSIONING.md
