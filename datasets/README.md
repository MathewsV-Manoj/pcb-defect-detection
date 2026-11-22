# PCB dataset provenance and split audit

The detector's fixed class order is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

**No training dataset is included in this repository.** The sample CSV is a template only. Do not describe DeepPCB, PKU-Market-PCB, Kaggle data, or any other public dataset as used by this project unless its actual files and annotations appear in the completed import manifest and have been reviewed.

## Import manifest

Copy `import_manifest.example.csv` to `import_manifest.csv` and replace every example row and placeholder with the actual file, source and review information. The manifest contains one row per image.

| Column | Required meaning |
|---|---|
| `split` | `train`, `val` or `test` |
| `group` | Stable physical-board/design/capture-session group ID |
| `image`, `label` | Paths relative to the manifest CSV |
| `format` | `yolo`, `voc` or `deeppcb` |
| `source_name`, `source_url` | Actual origin of the image |
| `license_or_permission` | Exact licence or permission basis; do not guess |
| `rights_review_status` | Set to `CONFIRMED_BY_TEAM` only after the team checks the terms |
| `annotation_review_status` | Set to `REVIEWED_BY_TEAM` only after a person reviews the class and box |

A `PENDING` review status is intentionally not release-ready. The audit records team declarations; it does not independently verify licensing or annotation correctness.

Keep every view, crop, augmentation source, or repeated capture from the same physical board/design/capture group in one split. Do not split near-duplicate views across training, validation and test. Each of the three splits must include all three target classes before the dataset is considered release-ready. Include good-board images with correctly empty label files where appropriate.

## Build the processed dataset

Install the tools in a separate training environment, then run:

```bash
python -m pip install -r pcb_engine_kit/requirements-train.txt
python pcb_engine_kit/dataset.py datasets/import_manifest.csv datasets/processed/pcb3
```

The importer checks required metadata, readable images, annotation format, class IDs, normalized YOLO coordinates, bounding-box bounds, duplicate image hashes and group/split consistency. It writes:

- `data.yaml` — dataset class and split contract;
- `audit.json` — import-manifest hash, source/label hashes, class counts, group mapping, declared rights/annotation review and structural audit.

The data and audit are generated from the actual input files. Never edit the audit to force a pass. Correct the manifest or source files and rebuild into a new output directory.

## Audit the release inputs

```bash
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --output-dir docs/results
```

When the project-trained checkpoint exists, add its exact path:

```bash
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

The audit creates `project_dataset_audit.json`, `project_checkpoint_audit.json` and `project_release_audit.json`. A missing dataset/checkpoint is recorded as `NOT_PROVIDED` or `INCOMPLETE`; missing artefacts are never treated as a pass.

## Dataset source register

`SOURCE_MANIFEST.csv` is a source register, not proof that a dataset was used. It lists possible origins and review requirements. Actual use is determined only by the completed import manifest and the hashes in the generated audit.
