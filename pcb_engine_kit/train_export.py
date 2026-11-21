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
UPSTREAM_BASELINE_CLASS_ORDER = [
    "missing_hole", "mouse_bite", "open_circuit", "short", "spur", "spurious_copper"
]
UPSTREAM_BASELINE_CLASS_MAP = {
    "missing_hole": "missing_hole",
    "open_circuit": "open_circuit",
    "short": "short_circuit",
}


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


def export_upstream_baseline_onnx(model: YOLO, out: Path, size: int) -> Path:
    """Export the attributed six-class Sulojan YOLOv8s baseline for Pi inference."""
    source_names = ordered_names(model.names)
    if source_names != UPSTREAM_BASELINE_CLASS_ORDER:
        raise RuntimeError(
            "This baseline exporter expects the Sulojan six-class order "
            f"{UPSTREAM_BASELINE_CLASS_ORDER!r}, got {source_names!r}"
        )
    result = Path(
        model.export(
            format="onnx", imgsz=size, opset=17, simplify=False,
            dynamic=False, batch=1, nms=False, device="cpu",
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
        "architecture": "YOLOv8s",
        "origin": {
            "publisher": "Sulojan Rajkumar",
            "model_repository": "https://huggingface.co/Sulojan/pcb-defect-yolov8s",
            "source_code": "https://github.com/Sulojan2027/PCB_Defect_Detect",
            "upstream_file": "best.pt",
            "upstream_file_sha256": "1acd655ce93a474f0ed00958ddd1079afb46c74868f916af6187bf63dad5bb3d",
            "license_declared_by_model_repository": "MIT",
            "upstream_model_metrics_document": "docs/PCB_UPSTREAM_BASELINE.md",
        },
        "class_order": source_names,
        "target_class_order": CLASS_ORDER,
        "target_class_map": UPSTREAM_BASELINE_CLASS_MAP,
        "ignored_source_classes": ["mouse_bite", "spur", "spurious_copper"],
        "input_size": [size, size],
        "input": {
            "color_order": "RGB", "layout": "NCHW", "dtype": "float32",
            "normalization": "0_to_1", "resize": "letterbox",
        },
        "output_contract": "raw_yolov8_xywh_6_class_scores_no_nms",
        "sha256": digest,
        "validated_on_pi": False,
        "warning": "Upstream model metrics are not this team's evaluation. Evaluate the project checkpoint on its own held-out boards.",
    }
    (out / "best.onnx.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["train", "validate", "export-onnx", "export-upstream-onnx"])
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
        source_names = ordered_names(model.names)
        if source_names not in (CLASS_ORDER, UPSTREAM_BASELINE_CLASS_ORDER):
            raise RuntimeError(
                "Training initial checkpoint must use either the deployment three-class "
                "order or the documented six-class PCB baseline order; "
                f"got {source_names!r}"
            )
        if source_names == UPSTREAM_BASELINE_CLASS_ORDER:
            print(
                "Transfer-learning initialization: Sulojan Rajkumar's six-class "
                "YOLOv8s PCB checkpoint. Ultralytics will adapt the detection head "
                "to the supplied three-class dataset. The resulting checkpoint "
                "must be evaluated as a new project model."
            )
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
    if args.mode == "export-upstream-onnx":
        out = Path(args.out).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        onnx_path = export_upstream_baseline_onnx(model, out, args.size)
        print(f"Attributed six-class baseline ONNX export: {onnx_path}")
        print("The Pi decoder maps only missing_hole, open_circuit and short to the configured three-class output.")
        return 0
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
