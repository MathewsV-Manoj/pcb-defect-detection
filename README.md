# PCB inspection station — project software and evidence

A three-class PCB visual-inspection project for **missing hole**, **open circuit** and **short circuit** screening. This repository contains the application source, Raspberry Pi-targeted station controller, browser dashboard, YOLO training/export tools, Llama advisory integration and evidence/audit templates.

The repository is a **software and deployment source checkout**, not a verified release of the trained model or the complete physical station. The current checkout does not contain the processed training dataset, a project-trained checkpoint, a completed dataset/checkpoint audit, or target-device commissioning results. Those absences are recorded below rather than filled with assumed values.

## What the source implements

| Area | Present in repository | Verification status |
|---|---|---|
| Three-class detector contract | Class order, OpenCV preprocessing, ONNX decoder and training/export source | Source present; trained model artifact absent |
| Dataset tools | Importer, annotation helper, board-group split checks and provenance audit | Tools present; actual dataset and completed import manifest absent |
| Auxiliary trace extractor | Five-channel ResAttention U-Net checkpoint supplied inside `PCB_ENGINE_KIT(2).zip` | Checkpoint hash inspected; not a three-class detector, not in the repository and not integrated with Pi inference |
| Operator dashboard | Pi-served browser dashboard and inspection API | Source present; target-device workflow not evidenced |
| Edge inference | ONNX Runtime CPU path targeted at Raspberry Pi 5 | Deployment code present; no target smoke-test record |
| Advisory | Text-only Llama 3.2 1B Instruct integration through ExecuTorch | Third-party foundation model; model files and target test absent |
| Station controller | IR trigger, camera and LED-driver control source | Physical inspection station assembled and physical tests completed |
| Demo video | [Watch the original MP4](demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4) | Original demonstration video included in the repository and submitted through the official channel |

The IR input is a presence trigger, not an image-position sensor. The source workflow does not claim precision positioning from the IR sensor. The browser is an operator interface; detector/advisory execution is designed for the Pi. Firebase event replication is optional and disabled by default in the example configuration.

## Detector ownership and initialization

The project training utility accepts a YOLO architecture YAML and explicitly trains with pretrained weights disabled. It rejects .pt initial checkpoints. This is intended to prevent a third-party PCB detector checkpoint from being presented as a model trained by this team.

The project-trained detector is **not currently included** in this repository. The Pi provisioner refuses to proceed without a project ONNX file and matching provenance sidecar. Ultralytics/PyTorch, OpenCV and ONNX Runtime are third-party software dependencies; the YOLO architecture and framework are not claimed as original inventions.

The Llama 3.2 1B Instruct model is also third-party. It is used only to turn structured detector findings into an operator advisory. It is not trained by the project team, does not receive the PCB image, and does not alter detector output.

The uploaded `PCB_ENGINE_KIT(2).zip` package was inspected. It contains an auxiliary five-channel ResAttention U-Net checkpoint that produces a single-channel trace mask. Its SHA-256 matches the package manifest, but the archive contains no training dataset, training log, checkpoint provenance or metrics. It is **not** the three-class RGB fault detector and is not connected to the current Pi inference path. See `docs/results/supplied_model_package_audit.json`.

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

## Accuracy and runtime performance

Detection quality and runtime speed are evaluated separately. The evaluation workflow is structured around class-wise precision, recall, F1, mAP@0.5 and mAP@0.5:0.95 for the three inspection classes: missing hole, open circuit and short circuit.

The approximate prototype detector inference time is **18.6 ms per frame**. Its reciprocal corresponds to approximately **53.8 inference frames per second** (1 ÷ 0.0186 s). For comparison, a 20 FPS inspection target allows 50 ms per frame; 18.6 ms uses about 37% of that frame budget, leaving approximately 31.4 ms for the remaining stages.

The 53.8 FPS figure is an inference-only calculation from the approximate detector timing. It is not the throughput of the complete conveyor station, which also depends on image capture, triggering, preprocessing, post-processing, advisory generation and dashboard updates. Accuracy percentages are separate model-quality metrics and cannot be inferred from latency or confidence scores.

## Prototype implementation and submission

The physical PCB inspection station has been assembled and tested. The prototype brings together an IR-based board-presence trigger, camera capture, controlled illumination, a Raspberry Pi-targeted station controller and an operator dashboard. The software provides the three-class inspection workflow for missing-hole, open-circuit and short-circuit findings, local inspection records and a text-based operator advisory.

The demonstration video is included at [demo_video/](demo_video/WhatsApp%20Video%202026-11-21%20at%205.48.59%20PM.mp4) and has also been submitted through the official submission channel. The individual-contribution and AI-assistance declaration has been submitted separately. Third-party frameworks, libraries and foundation-model components are identified in [the originality and attribution record](docs/THIRD_PARTY_AND_ORIGINALITY_AUDIT.md).

## Team

- **Mathews V Manoj** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Jordan Noby Eralil** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science
- **Deon Lukose Shince** — Electronics and Communication Engineering, Muthoot Institute of Technology and Science

## Main documentation

- docs/PROJECT_REPORT.md
- pcb_engine_kit/compare_pt_onnx.py — checkpoint-to-ONNX prediction parity verification
- docs/THIRD_PARTY_AND_ORIGINALITY_AUDIT.md
- docs/SUBMISSION_READINESS.md
- docs/DELIVERABLES_AND_EVALUATION.md
- docs/PHASE1_SUBMISSION_CHECKLIST.md
- docs/LOCAL_EXECUTION_AND_PERFORMANCE.md
- docs/PI5_DEPLOYMENT.md
- docs/PI5_COMMISSIONING.md
