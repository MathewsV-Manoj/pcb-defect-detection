# Pretrained PCB defect model

This directory contains the downloader for a third-party MIT-licensed
YOLOv8s PCB defect checkpoint published by Sulojan Rajkumar.

- Checkpoint repository: https://huggingface.co/Sulojan/pcb-defect-yolov8s
- Source code and training details: https://github.com/Sulojan2027/PCB_Defect_Detect
- Published results and attribution: [docs/PCB_UPSTREAM_BASELINE.md](../../docs/PCB_UPSTREAM_BASELINE.md)

Fetch and hash-verify the weights with:

    python -m pip install "huggingface_hub>=0.30,<2"
    python models/pretrained/download_sulojan_pcb_yolov8s.py

The 22.5 MB checkpoint is stored locally under
\`sulojan_pcb_yolov8s/best.pt\` and is intentionally ignored by Git.
Keep \`model_manifest.json\` with the downloaded file when transferring it.

The upstream model has six classes. The ONNX exporter produces a metadata
sidecar that maps only \`missing_hole\`, \`open_circuit\` and \`short\` to the
application's three output classes. Do not label the upstream model or its
published benchmark as trained or measured by this project.
