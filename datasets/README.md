# PCB dataset notes

The detector is trained for three classes: `missing_hole`, `open_circuit` and `short_circuit`. A label name from another dataset is not sufficient evidence that it describes the same physical defect. Inspect the upstream annotation definitions before mapping it.

## Dataset sources recorded for this project

| Source | Relevance | Check before use |
|---|---|---|
| [DeepPCB](https://github.com/tangsanli5201/DeepPCB) | PCB images with open/short annotations | Confirm source class IDs and box convention. Its `pin-hole` label is not automatically `missing_hole`. |
| [Tiny-Defect-Detection-for-PCB](https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB) | PCB small-defect examples including hole-related samples | Verify annotation names, physical meaning, format and licence. |
| Project camera captures | Images from the inspection station | Label consistently and group by physical board/capture session. |

`SOURCE_MANIFEST.csv` records source URLs, reuse notes and whether use in the final training run has been verified. This repository does not contain third-party dataset archives.

## Import manifest and split

Copy `import_manifest.example.csv` and list each actual image and annotation file. Each row requires:

- image path;
- label path;
- annotation format (`yolo`, `voc` or `deeppcb`);
- split (`train`, `val` or `test`);
- group ID for the physical board or capture session.

Keep every view and derived crop from the same board/capture group in one split. The processed dataset is not stored in this repository. Preserve the completed import manifest, generated `data.yaml` and `audit.json` with the trained checkpoint and its evaluation results.
