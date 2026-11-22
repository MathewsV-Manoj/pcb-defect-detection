# Vision and advisory model assets

The Raspberry Pi application expects the project-trained three-class YOLO ONNX detector at models/best.onnx and its required metadata sidecar at models/best.onnx.json.

The detector class order is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

The detector must be trained through pcb_engine_kit/train_export.py from a YOLO architecture YAML with pretrained=False. The CLI rejects .pt initial weights. The training run writes a project_training_provenance.json file; the ONNX sidecar records the checkpoint, dataset audit and training-provenance hashes.

The inference application rejects an ONNX file without the expected provenance declaration and matching SHA-256. The Pi provisioner also checks the model metadata before runtime setup.

The current repository does not include the primary three-class best.pt, best.onnx or their provenance files. The uploaded `PCB_ENGINE_KIT(2).zip` contains a separate five-channel ResAttention U-Net trace-mask checkpoint with one output channel. That checkpoint is not a defect classifier, is not integrated with the Pi runtime and has no training dataset/provenance/metrics in the supplied archive. Its checksum and architecture smoke check are recorded in docs/results/supplied_model_package_audit.json. See docs/results/project_checkpoint_audit.json for the still-open primary detector gate.

## Advisory model

The challenge advisory path uses the third-party Llama 3.2 1B Instruct foundation model through ExecuTorch. It is not trained by the project team. Model package, tokenizer and compiled runner are downloaded/built locally and are not stored in this source repository. See llm_advisory/README.md for attribution, license and build information.

models/release_manifest.json records which files are present and which tests have actually been completed.
