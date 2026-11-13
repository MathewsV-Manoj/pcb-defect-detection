# PCB inspection GUI handoff (from supplied kit)

## Folder-worker architecture
The worker in `engine.py` polls `~/Desktop/PCBInspection/incoming`, atomically moves each image to `processing`, runs the configured TFLite detector and optional registered-reference comparison, writes an annotated image under `results`, archives the original, then writes a completion JSON file. JSON written by atomic rename is the completion signal.

```text
GUI/camera -> atomic image publication -> incoming/
  -> engine claims file -> TFLite detector + optional reference comparison
  -> annotated JPG + result JSON -> archive / results / failed
```

## Directories
- `incoming`: GUI publishes completed PNG/JPG images.
- `processing`: worker claims image; GUI must not modify it.
- `results`: annotated JPG and completion JSON.
- `archive`: original successfully processed images.
- `failed`: unreadable or failed inputs.

Use `submit.py` to publish with a temporary `.part` filename and atomic rename. The GUI event loop should not run inference. Keep one worker process and monitor its heartbeat/logs.

## Result/status display
- `faulty`: red; show detector findings.
- `not_faulty`: no configured visible detections found, only when model metadata is marked validated and optional reference check is successful.
- `review_required`: amber; show unvalidated model/reference/alignment warnings and candidates.
- `error`: error; never show as PASS.

Reference-comparison events are `missing_component_candidate`, not a confirmed defect. Confidence is null; similarity is not a probability.

## Acceptance checks
Test duplicate original filenames, incomplete uploads, corrupt images, non-square images, unvalidated model metadata, missing references, alignment failure, restart recovery and sustained operation. Save operator decisions separately from detector evidence.

This folder-worker design and its TFLite Runtime are a separate path from the root Raspberry Pi 5 ONNX one-shot scaffold. Decide the target runtime only after testing the exact final model on the actual Pi 5.
