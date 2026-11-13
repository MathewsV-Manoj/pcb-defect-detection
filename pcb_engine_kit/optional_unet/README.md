# Existing ResAttention U-Net trace extractor

The ZIP includes a PyTorch checkpoint named `pcb_ultra_resatt_unet.pth`, 32,897,063 bytes, SHA-256:

`23107a1805c13e57f3bccace4aa20bd59e5b400468cb3c0b26f6dba0bce1426c`

This model uses five-channel handcrafted image features and generates a trace/binary map. It is **not** a YOLO classifier/detector for `open_circuit`, `short_circuit`, and `missing_hole`. It is documented for laptop diagnostics only.

The original checkpoint binary still needs to be uploaded to this repository through GitHub's web interface (or Git LFS). The repository integration cannot directly transfer this binary through the available GitHub file-writing API. Upload it at:

`pcb_engine_kit/optional_unet/pcb_ultra_resatt_unet.pth`

After upload, verify that its SHA-256 matches the value above. Do not rename it as `best.pt` or `best.onnx`.

The script performs three inference passes and morphological closing; its outputs must not be used as trusted fault labels. The Pi deployment guide says not to put this large teacher model on the Pi before profiling and numerical validation.
