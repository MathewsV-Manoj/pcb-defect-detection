"""Train, validate and export PCB YOLO models for Pi ONNX and TFLite runtimes."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ultralytics import YOLO

CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def check_class_order(model: YOLO) -> None:
    names: Any = model.names
    if isinstance(names, dict):
        ordered = [names[index] for index in sorted(names)]
    else:
        ordered = list(names)
    if ordered != CLASS_ORDER:
        raise RuntimeError(
            f"Checkpoint class order {ordered!r} does not match deployment order {CLASS_ORDER!r}"
        )


def export_onnx(model: YOLO, out: Path, size: int) -> Path:
    result = Path(
        model.export(
            format="onnx",
            imgsz=size,
            opset=17,
            simplify=False,
            dynamic=False,
            batch=1,
            nms=False,
            device="cpu",
        )
    )
    if not result.is_file():
        raise RuntimeError(f"Ultralytics did not return a readable ONNX model path: {result}")
    destination = out / "best.onnx"
    if result.resolve() != destination.resolve():
        shutil.copy2(result, destination)
    metadata = {
        "format": "onnx",
        "architecture": "YOLOv8",
        "class_order": CLASS_ORDER,
        "input_size": [size, size],
        "preprocessing": [
            "letterbox",
            "BGR_TO_RGB",
            "float32_normalize_0_1",
            "NCHW",
        ],
        "output_contract": "raw_yolov8_xywh_3_class_scores_no_nms",
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "validated_on_pi": False,
    }
    (out / "best.onnx.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def export_tflite(model: YOLO, out: Path, data: str, size: int) -> Path:
    result = Path(
        model.export(
            format="tflite",
            int8=True,
            data=data,
            imgsz=size,
            batch=1,
            nms=False,
            device="cpu",
        )
    )
    candidates = []
    if result.is_file() and "full_integer_quant" in result.name:
        candidates = [result]
    elif result.is_dir():
        candidates = list(result.rglob("*full_integer_quant.tflite"))
    else:
        candidates = list(result.parent.rglob("*full_integer_quant.tflite"))

    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one full-integer TFLite artifact from this export; "
            f"found {len(candidates)} candidates: {candidates}"
        )

    destination = out / "detector.tflite"
    if candidates[0].resolve() != destination.resolve():
        shutil.copy2(candidates[0], destination)

    metadata = {
        "schema_version": 1,
        "classes": CLASS_ORDER,
        "input": "RGB_0_1_letterbox_114",
        "box_units": "normalized",
        "output": "yolov8_raw_xywh_class_scores",
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "validated": False,
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["train", "validate", "export", "export-onnx", "export-tflite"],
    )
    parser.add_argument("--data", help="YOLO dataset YAML")
    parser.add_argument("--weights", default="yolov8n.pt", help="Checkpoint or base YOLO weights")
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0")
    parser.add_argument("--out", default="deployment")
    args = parser.parse_args()

    if args.size < 32 or args.size % 32:
        parser.error("--size must be at least 32 and divisible by 32")
    if args.mode in {"train", "validate", "export", "export-tflite"} and not args.data:
        parser.error(f"--data is required for mode {args.mode}")

    model = YOLO(args.weights)
    if args.mode == "train":
        model.train(
            data=args.data,
            imgsz=args.size,
            epochs=args.epochs,
            batch=args.batch,
            device=args.device,
            workers=2,
            seed=42,
            patience=20,
            project="runs",
            name="pcb",
            amp=True,
            mosaic=0.0,
            mixup=0.0,
        )
        return 0

    if args.mode == "validate":
        check_class_order(model)
        model.val(data=args.data, split="test", imgsz=args.size, device=args.device, plots=True)
        return 0

    check_class_order(model)
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    if args.mode in {"export", "export-onnx"}:
        onnx_path = export_onnx(model, out, args.size)
        print(f"ONNX export: {onnx_path}")
    if args.mode in {"export", "export-tflite"}:
        tflite_path = export_tflite(model, out, args.data or "", args.size)
        print(f"TFLite export: {tflite_path}")

    print("Export metadata is marked unvalidated until parity and target-device camera tests pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
