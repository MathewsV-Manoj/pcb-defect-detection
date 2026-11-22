# PCB dataset provenance and split audit

The detector's fixed class order is:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

**No raw or processed training dataset is included in this repository. No external PCB dataset is currently confirmed as used.** The source register is intentionally header-only until the team has the exact dataset revision, files, source URL and licence/permission record. A source listed as a candidate is not evidence of use.

## Import manifest

Copy `import_manifest.example.csv` to `import_manifest.csv` and replace every example row and placeholder with the actual file, source and review information. The manifest contains one row per image.

| Column | Required meaning |
|---|---|
| `split` | `train`, `val` or `test` |
| `group` | Stable physical-board/design/capture-session group ID |
| `image`, `label` | Paths relative to the manifest CSV |
| `format` | `yolo` or `voc` |
| `source_name`, `source_url` | Actual origin of the image |
| `license_or_permission` | Exact licence or permission basis; do not guess |
| `rights_review_status` | Set to `CONFIRMED_BY_TEAM` only after the team checks the terms |
| `annotation_review_status` | Set to `REVIEWED_BY_TEAM` only after a person reviews the class and box |

The importer deliberately accepts only YOLO and Pascal VOC annotations. Annotations from other datasets must not be mapped into project classes by assuming numeric class IDs. Convert them to the canonical YOLO format only after the team has reviewed the source's exact class definitions and manually verified each mapping.

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

## Source register

`SOURCE_MANIFEST.csv` is intentionally header-only because no external dataset has been confirmed as used. Add one row per actual source only after inspecting the exact revision, class definitions, terms and redistribution permissions. The completed import manifest and its hashes determine which images entered the project dataset.
