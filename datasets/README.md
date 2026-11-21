# PCB dataset notes

The detector is trained for three classes: open circuit, short circuit and missing hole. When choosing images, check the source label definitions and the way the boards were photographed. A similarly named label from another dataset is not necessarily the same defect.

## PCB image sources

| Source | Why it may be useful | Check before using |
|---|---|---|
| [DeepPCB](https://github.com/tangsanli5201/DeepPCB) | PCB images with open- and short-circuit annotations | Confirm the original class IDs and box convention |
| [Tiny-Defect-Detection-for-PCB](https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB) | PCB-specific small-defect examples | Review the label names and annotation format |
| Project camera captures | Same camera, lens, LED and board appearance as the station | Label the target classes consistently and group images by physical board |

A source label such as pin_hole must not be converted to missing_hole unless its meaning has been checked.

## Other industrial datasets

These datasets are useful for understanding inspection methods, but their labels are not PCB labels:

| Dataset | Image domain | Possible use here |
|---|---|---|
| [MVTec AD](https://www.mvtec.com/company/research/datasets/mvtec-ad) | Industrial objects and textures | General anomaly-detection reference |
| [NEU-DET](https://faculty.neu.edu.cn/songkc/en/zdylm/263265) | Hot-rolled steel strip | Reference for surface-defect detection methods |
| [KolektorSDD](https://www.vicos.si/resources/kolektorsdd/) | Electrical commutator surfaces | Reference for small surface defects |

KolektorSDD is provided under CC BY-NC-SA 4.0. Its use is non-commercial under that licence; contact the dataset owner about commercial use. Check the current terms from each provider before downloading or redistributing any dataset. This repository does not contain third-party dataset archives.

## Import manifest and train/test split

SOURCE_MANIFEST.csv records dataset sources, URLs, reuse terms and whether use in the final training run has been verified.

The separate import manifest lists each image and its label file. Start with import_manifest.example.csv and replace the sample paths with the actual files. The importer requires:

- image path;
- label path;
- annotation format (yolo, voc or deeppcb);
- split (train, val or test);
- group ID for the physical board or capture session.

Keep images from the same board or capture group in one split. This avoids placing near-identical views of one board in both training and test data.

The processed dataset is not stored in this repository. Keep the manifest, annotation mapping, audit.json and source checksums with the checkpoint produced from that data.
