# Dataset provenance and selection

The model target is PCB inspection with three defect classes: `open_circuit`, `short_circuit` and `missing_hole`. Dataset choice is therefore evaluated by image domain, annotation meaning, class compatibility and capture conditions.

## Committee-listed reference datasets

| Dataset | Image domain | Published contents | Role in this project |
|---|---|---|---|
| [MVTec AD](https://www.mvtec.com/company/research/datasets/mvtec-ad) | Industrial objects and textures | Anomaly-detection images across 15 object and texture categories | General anomaly-detection reference; it does not supply the project's three PCB labels |
| [NEU Surface Defect / NEU-DET](https://faculty.neu.edu.cn/songkc/en/zdylm/263265) | Hot-rolled steel strip | 1,800 grayscale images, six steel-surface defect categories, with NEU-DET bounding-box annotations | Surface-inspection reference; its steel labels are not PCB defect labels |
| [KolektorSDD](https://www.vicos.si/resources/kolektorsdd/) | Electrical commutator surfaces | 399 grayscale images, including defective and non-defective examples, with fine or box annotation releases | Industrial surface-defect reference; it is not a PCB dataset |

KolektorSDD is distributed under CC BY-NC-SA 4.0 on the dataset owner's page. Use is non-commercial under that licence; commercial use requires contacting the dataset owner. The MVTec and NEU datasets are governed by their respective provider terms. No third-party dataset is redistributed in this repository.

## PCB-specific data sources

| Dataset | Source | Annotation consideration |
|---|---|---|
| DeepPCB | [Project repository](https://github.com/tangsanli5201/DeepPCB) | Inspect upstream class IDs and label semantics before mapping to the project's classes |
| Tiny-Defect-Detection-for-PCB | [Project repository](https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB) | Verify each source label and annotation convention before conversion |
| Project camera captures | Assembled inspection station | Captures the actual camera, lens, LED illumination and PCB appearance used by the inspection setup |

A source annotation is not automatically mapped to a project class based on its name alone. In particular, a `pin_hole` or hole-related source label is not assumed to mean `missing_hole` until its annotation semantics are reviewed.

## Provenance and evaluation policy

`SOURCE_MANIFEST.csv` records the source URL, domain, reuse terms and relationship to the PCB task. The `training_use_status` field distinguishes a dataset reference from a source verified in the exact training run.

A dataset is described as training data only when its use is supported by the corresponding training configuration, annotation mapping and split records. Board-aware splitting keeps images from the same physical PCB or capture group within one split, reducing leakage between training and evaluation.

Raw and processed dataset archives are not included in this repository. Each model release is associated with its dataset version, annotation map, split manifest and source checksums.
