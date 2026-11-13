# Datasets and provenance

No original training dataset archive or processed YOLO dataset was present in the accessible project files when this repository was assembled. This folder contains provenance templates, not images or labels.

## Sources mentioned in project records
- DeepPCB: https://github.com/tangsanli5201/DeepPCB
- Tiny-Defect-Detection-for-PCB: https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB
- Project discussion also mentioned Mendeley Mixed PCB Defect Dataset v4. Its exact version, URL, annotation mapping and terms must be verified against the training run.

These are source candidates mentioned across different planning records, not proof that all were used in the final checkpoint. Confirm the final `data.yaml`, training log/args, download records and class mapping. DeepPCB's `pin-hole` label must not be relabelled as `missing_hole` without annotation-level evidence.

## Redistribution checklist
1. Read the current dataset license/terms.
2. Confirm redistribution of images and converted labels is permitted.
3. Record source, version/date, attribution and archive SHA-256.
4. Keep project camera images separate and obtain permission from contributors.
5. If redistribution is not allowed, publish source links and a reproducible download/import recipe instead.

Large datasets should use Git LFS or an approved dataset host where permitted. The repository ignores raw/processed data folders by default; only manifests and provenance docs belong in the initial commit.
