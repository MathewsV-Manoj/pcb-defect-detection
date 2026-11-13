# PCB engine: Ubuntu training and Raspberry Pi deployment

## Read first

This is a development kit, not a trained or validated fault detector. No training dataset or trained fault-detection weights are included. The existing U-Net checkpoint is a trace extractor, not a fault detector. All training and conversion happen locally. The Pi runs the exported detector and optional reference comparison.

The implemented baseline uses RGB directly for three trained classes: `open_circuit`, `short_circuit`, `missing_hole`. Missing components use registered reference regions and produce **review candidates**, not definitive missing-component classifications. This preserves information discarded by the existing trace extractor and establishes a measurable CPU baseline. The existing U-Net is supplied as an optional laptop diagnostic. A distilled student and a fully integrated dual-model pipeline have not been implemented or trained in this kit.

No frame rate or accuracy is guaranteed. The software has not been run on your Ubuntu laptop or Pi. Python source compilation and dependency-free contract tests are reported in `VERIFICATION.md`. Model execution, export, alignment, GUI labeling, and performance need hardware testing.

## 1. Hardware and software

- Ubuntu 22.04 x86_64 with Python 3.10 is the intended training/export environment.
- An NVIDIA GPU with 8 GB VRAM and 16–32 GB system RAM is a useful starting point. Smaller batches can fit smaller GPUs.
- Use a 64-bit Raspberry Pi OS Bookworm installation with Python 3.11 for the Pi instructions below.
- Provide cooling and a stable power supply. Record Pi RAM capacity before setting a memory target.
- Use the same camera view, board scale, focus and lighting for data collection and inspection.

Extract `PCB_ENGINE_KIT.zip`, open a terminal inside `pcb_engine_kit`, and run:

```bash
sudo apt update
sudo apt install python3-venv python3-pip libgl1 libglib2.0-0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-train.txt
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

The GPU must have a compatible NVIDIA driver. If CUDA reports false, resolve the driver/PyTorch compatibility using the official PyTorch installer before GPU training. `--device cpu` works for functional checks but may be slow. Do not install arbitrary CUDA packages until the GPU and driver are identified.

This kit deliberately pins Ultralytics 8.3.161 to use its legacy TFLite export path. Do not replace it with the latest version without updating and retesting export and decoding: current Ultralytics uses a different LiteRT export interface. Export dependency pins are a proposed environment, not an executed lockfile. Save `pip freeze` after successful installation and conversion.

## 2. Get and organize data

Use these original project sources; datasets are not redistributed in this ZIP:

- DeepPCB: https://github.com/tangsanli5201/DeepPCB . Supports initial opens/shorts experiments. Its `pin-hole` class is **not** missing drill hole. The project describes research-only usage; inspect its terms before your intended use.
- PCB defect dataset and download links: https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB . Includes missing-hole examples. Follow the repository's current download instructions, inspect the annotation names and terms, and use the VOC importer if its downloaded annotations are Pascal VOC XML.
- Your own camera images: necessary to measure transfer to populated boards. Include multiple good boards and real defects. Public bare-board datasets do not establish accuracy on populated boards.

Download archives from the owners' links in your browser. There is no guessed or embedded third-party mirror. Extract ZIP downloads with:

```bash
python safe_extract.py /path/to/dataset.zip data/raw_public
```

Use a new destination. Other archive types should be extracted with Ubuntu's archive manager. Keep originals unchanged. The extraction helper rejects traversal paths, symlinks and archives declaring more than 20 GiB of uncompressed data; it is not intended for hostile archives.

Start with an inventory of actual samples per class. Do not begin a four-fault deployment with only open/short labels. Keep a separate folder of real camera test images. Synthetic gaps, bridges or absent components can supplement training, but cannot substitute for real held-out defects. Do not count rotated or cropped versions as independent boards.

## 3. Label your images locally

Put JPG/PNG files in a folder, then run:

```bash
python label.py data/my_boards
```

Keys: `1` open circuit, `2` short circuit, `3` missing hole; `r` draws a box; `u` undoes the last box; `s` saves and advances; `q` quits. Select boxes with the mouse and confirm with Enter. Each image gets a sibling YOLO `.txt` file. Saving no boxes means the image was reviewed and contains none of the three target faults. Existing labels are loaded. Keep intentionally unpopulated component sites out of defect labels.

Class IDs in label files are 0, 1, 2 respectively. Draw boxes around the visible defect and enough nearby structure to identify it. For a missing hole, mark the expected hole site using a known-good image or design information. Verify each label manually.

Do not label missing components with this three-class annotator. They are configured using reference regions in step 7. A learned component detector would require a separate dataset and training stage.

## 4. Build explicit training, validation and test splits

Copy `manifest.example.csv` to `manifest.csv` and replace every example row. Paths are relative to the manifest. Each row needs:

| Column | Meaning |
|---|---|
| image | Original inspected image, not the good template |
| label | Its annotation file; empty file only for a reviewed negative |
| format | `yolo`, `voc`, or `deeppcb` |
| group | Physical board/design/capture group shared by related images |
| split | `train`, `val`, or `test` |

Use roughly 70/15/15 by board group as an initial split, adjusting to keep every target class represented. Assign every image from the same physical board and its derived crops to one split. Hold out board designs if you need generalization to new designs. Preserve DeepPCB's official split for comparable public results; do not blindly resplit related crops.

`dataset.py` maps DeepPCB classes 1 and 2 only; class 6 is ignored rather than relabeled. VOC names recognized are `open`, `open_circuit`, `short`, `short_circuit`, `missing_hole`. Inspect all source labels first; extend the alias map deliberately if spelling differs. Other defect types are ignored for this three-class task.

```bash
python dataset.py manifest.csv data/pcb
```

The output directory must not already exist. Review `data/pcb/audit.json`, open examples from all splits, and verify bounding boxes. Fix the manifest/source labels and build into a new directory if import fails. The importer checks bounds, group overlap and exact duplicate image files. It cannot detect every visually duplicated or related image; group assignment requires human review.

## 5. Train and assess

```bash
python train_export.py train --data data/pcb/data.yaml --size 640 --batch 4 --epochs 100 --device 0
python train_export.py validate --data data/pcb/data.yaml --weights runs/pcb/weights/best.pt --size 640 --device 0
```

The first run downloads pretrained `yolov8n.pt` unless supplied locally. Run-directory numbering may change on repeated runs; use the actual `best.pt`. Training creates logs and validation plots. Choose confidence thresholds on validation data; assess the final selected model once on held-out test data.

Measure per-class recall, precision, false alarms per good board and minimum visible fault size. Inspect missed tiny defects. The code letterboxes the entire image; it does **not** implement tiling. Supply consistently cropped inspection images if a full board resized to 640 loses defects. For large boards, treat tiling with overlap and coordinate merging as a subsequent required extension, with additional Pi latency.

Train a 320 or 416 candidate only if the smallest required defects remain visible. Resolution is fixed during export. Do not assume an arbitrarily resized 640 model has equivalent accuracy. Train and benchmark candidate resolutions separately.

## 6. Export and transfer

Use the same activated Ubuntu environment:

```bash
python -m pip install -r requirements-export.txt
python train_export.py export --data data/pcb/data.yaml --weights runs/pcb/weights/best.pt --size 640 --out deployment
python -m pip freeze > deployment/environment.txt
```

Calibration uses the dataset supplied via `--data`; its validation images must represent actual camera inputs, including small structures and lighting variation. Never use generic COCO images to calibrate this PCB model. The exporter may download converter assets. Review installation/conversion errors rather than silently switching runtime versions.

`deployment` contains `detector.tflite` and `metadata.json`. The export wrapper expects one full-integer artifact. If it finds multiple old exports, identify the current one explicitly rather than selecting arbitrarily. The engine checks the model hash, class order and raw output shape.

Before approval, compare original and exported predictions on the same validation images: class, box location, confidence and especially small-gap recall. Check the raw TFLite output uses normalized xywh boxes with three class scores and no embedded NMS, as required by this decoder. Validate input/output quantization and inspect the graph for unsupported/floating-point fallback operators. If export changes this contract, update the decoder and tests together. A `.tflite` suffix alone is not proof of efficient INT8 execution.

Leave `metadata.json`'s `validated` false until these checks and actual camera validation pass. Setting it true is a human release decision; it is not a substitute for testing. Low confidence detections are not guarantees of good boards.

Copy the kit's Python files, `config.json`, and `deployment/` to the Pi. No PyTorch or Ultralytics is needed on the Pi. Copy reference profiles too.

## 7. Configure component references

On the Ubuntu laptop, use a clean photograph of the correct, fully populated board revision:

```bash
python make_reference.py data/good_board.jpg references/board_A_rev1
```

Select tight rectangles around installed components. Rename region IDs in `profile.json` to the real component designators, such as R12 or U3. Exclude intentionally empty footprints. The reference is resized to at most 1200 pixels and boxes are recorded in that coordinate system.

Set `reference_profile` in `config.json` to the profile's path. Current engine configuration supports **one board design/revision per worker**. Board identification is not implemented; do not mix revisions in its input folder.

The engine aligns using ORB and homography, then compares each region's grayscale appearance. A region difference can be caused by a missing, shifted or wrong component, lighting or alignment. It is reported as `missing_component_candidate`, with `confidence: null` and a separate `similarity` score. This score is not a calibrated fault probability. Thresholds begin at 0.8 and require tuning on good and faulty captures. Alignment gates are basic; repeated PCB patterns can still produce wrong matches. Validate manually with known displacements and partial views before relying on it.

This stage never automatically declares a missing component confirmed. The GUI must support operator review. A reliable automatic missing-component decision requires validated presence/absence classification or stronger reference tests and a measured false-alarm rate.

## 8. Run on Raspberry Pi 4

For 64-bit Bookworm/Python 3.11, inside the copied kit:

```bash
sudo apt update
sudo apt install python3-venv python3-opencv
python3 -m venv --system-site-packages .venv-pi
source .venv-pi/bin/activate
python -m pip install -r requirements-pi.txt
python engine.py --config config.json
```

These package versions target that specific OS/Python combination. If no ARM64 wheel exists for your interpreter, use the specified Python environment or validate an alternative LiteRT runtime; do not install the full training stack on the Pi as a workaround.

Default root: `~/Desktop/PCBInspection`. The engine creates incoming, processing, results, archive and failed directories. Model/profile paths in config are relative to the launch directory; use absolute paths for a desktop shortcut or service.

Publish a complete image from a second terminal:

```bash
source .venv-pi/bin/activate
python submit.py /path/to/inspection.jpg
```

Use this helper or the GUI's atomic publication protocol. Directly copying a large file into incoming with a final `.jpg` name may cause inspection before copying completes.

## 9. Interpret and qualify results

- `faulty`: the trained detector found at least one target fault above threshold. Treat results as provisional until the model has been validated.
- `not_faulty`: no detector fault; component reference was checked with no candidate; detector metadata is validated. Means no configured visible defect was found, not proof of electrical function.
- `review_required`: no detector fault, but a component candidate, missing reference, alignment failure, or unvalidated model prevents a pass.
- `error`: unreadable image or processing exception. Never show green/pass.

An annotated image is written before its JSON completion record. Each box is in original image pixel coordinates. Detector confidence is a model score, not a guaranteed probability. Source images are retained in archive; errors go to failed. Files consume disk over time: define retention and check free space before unattended operation. There is no automatic deletion in the kit.

One worker processes images sequentially with two inference threads by default. Try 1, 2 and 4 threads. Record p50/p95 latency, peak resident RAM, temperature and missed faults across a sustained session. JSON `inference_ms` includes detection/reference work but excludes file queue time and final output encoding. Measure complete submit-to-JSON latency separately. If arrivals exceed processing speed, the disk queue grows.

The restart path requeues files left in processing. There is a small crash window after archiving but before JSON publication; an operator can resubmit an archived input without a result. Exactly-once delivery and automatic disk-full recovery are not provided. Keep a visible heartbeat/process status in the GUI.

Run detector evaluation on copied held-out YOLO images/labels:

```bash
python evaluate_pi.py deployment data/pcb/images/test data/pcb/labels/test --threads 2 --out pi_metrics.json
```

This reports precision/recall at IoU 0.5, false alarms on negative images, detector latency percentiles and Linux peak process RAM. It does not report mAP or validate component comparison. Compare the same images against the original model and inspect disagreements before deployment.

## 10. Existing U-Net

`optional_unet/run_pcb_ultra.py` is copied from your supplied documentation, and the supplied checkpoint is included unchanged. It can generate trace maps locally for diagnostics. Its closing operation may hide gaps, and its output removes hole/component evidence. It is intentionally not invoked by the RGB detector, whose train/deploy inputs must match.

```bash
python -m pip install scikit-image
cd optional_unet
python run_pcb_ultra.py /path/to/board.jpg
cd ..
```

The checkpoint is user-supplied; load only weights you trust. Optional U-Net conversion instructions are in its README. No accuracy claim from the supplied documentation has been independently verified.

## Handoff checklist

- Send the GUI developer `GUI_ARCHITECTURE.md` and an actual JSON/image result pair.
- Record class order, model hash, preprocessing, resolution, confidence threshold and board reference revision.
- Test faulty, clean, missing-component candidate, bad alignment and corrupt image cases.
- Test Pi memory and latency before calling the engine smooth or production ready.
- Verify software/dataset licenses before redistribution or commercial use; Ultralytics has licensing requirements.

References: https://docs.ultralytics.com/modes/export/ ; https://docs.ultralytics.com/guides/raspberry-pi/ ; https://github.com/ultralytics/ultralytics/blob/main/docs/en/integrations/tflite.md