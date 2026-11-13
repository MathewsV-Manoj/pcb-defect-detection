# Checkpoint binary upload required

The supplied ZIP contains the U-Net checkpoint:
- filename: `pcb_ultra_resatt_unet.pth`
- size: 32,897,063 bytes
- SHA-256: `23107a1805c13e57f3bccace4aa20bd59e5b400468cb3c0b26f6dba0bce1426c`

It is an existing five-channel trace-extraction U-Net weight file, not the YOLO three-class PCB fault detector and not a GPT/Llama model.

The connected GitHub writing interface can create UTF-8 files but does not support transferring this local binary as a Git object or Git LFS asset. The binary therefore needs one manual upload:
1. Open the repository in GitHub.
2. Select `pcb_engine_kit/optional_unet`.
3. Choose **Add file → Upload files**.
4. Upload `pcb_ultra_resatt_unet.pth` from the extracted ZIP.
5. Commit, then verify SHA-256 locally:
   `sha256sum pcb_ultra_resatt_unet.pth`

Do not rename it to `best.pt` or `best.onnx`. If you instead use Git LFS, track `*.pth` and push the object.
