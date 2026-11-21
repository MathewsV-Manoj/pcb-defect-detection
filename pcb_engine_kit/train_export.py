"""Train, validate and export the three-class PCB YOLO model for Raspberry Pi ONNX inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from ultralytics import YOLO

CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def ordered_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda item: int(item))]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    raise RuntimeError(f"Unsupported class-name structure: {type(names).__name__}")


def check_dataset_class_order(data_path: str | Path) -> None:
    path = Path(data_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "names" not in data:
        raise RuntimeError(f"Dataset YAML must contain a names field: {path}")
    names = ordered_names(data["names"])
    if names != CLASS_ORDER:
        raise RuntimeError(
            f"Dataset class order {names!r} does not match deployment order {CLASS_ORDER!r}"
        )


def check_checkpoint_class_order(model: YOLO) -> None:
    names = ordered_names(model.names)
    if names != CLASS_ORDER:
        raise RuntimeError(
            f"Checkpoint class order {names!r} does not match deployment order {CLASS_ORDER!r}"
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

    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    metadata = {
        "format": "onnx",
        "architecture": "YOLOv8 Nano",
        "class_order": CLASS_ORDER,
        "input_size": [size, size],
        "input": {
            "color_order": "RGB",
            "layout": "NCHW",
            "dtype": "float32",
            "normalization": "0_to_1",
            "resize": "letterbox",
        },
        "output_contract": "raw_yolov8_xywh_3_class_scores_no_nms",
        "sha256": digest,
        "validated_on_pi": False,
    }
    (out / "best.onnx.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["train", "validate", "export-onnx"])
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

    if args.mode in {"train", "validate"}:
        if not args.data:
            parser.error(f"--data is required for mode {args.mode}")

    if args.mode == "train":
        check_dataset_class_order(args.data)
        model = YOLO(args.weights)
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
        save_dir = Path(model.trainer.save_dir).resolve()
        best_path = save_dir / "weights" / "best.pt"
        if not best_path.is_file():
            raise RuntimeError(f"Training completed without a best.pt checkpoint at {best_path}")
        trained = YOLO(str(best_path))
        check_checkpoint_class_order(trained)
        print(f"Training output directory: {save_dir}")
        print(f"Best checkpoint: {best_path}")
        return 0

    model = YOLO(args.weights)
    check_checkpoint_class_order(model)

    if args.mode == "validate":
        check_dataset_class_order(args.data)
        model.val(
            data=args.data,
            split="test",
            imgsz=args.size,
            device=args.device,
            plots=True,
        )
        print("Test evaluation completed. See the generated Ultralytics run directory and plots.")
        return 0

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    onnx_path = export_onnx(model, out, args.size)
    print(f"ONNX export: {onnx_path}")
    print("Export metadata remains unvalidated until held-out parity and target-Pi tests pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
