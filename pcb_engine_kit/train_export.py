"""Train, validate and export the three-class PCB YOLO model for Raspberry Pi ONNX inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
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
    parser.add_argument("--report-out", default="docs/results/project_test_metrics.json",
                        help="JSON report destination for held-out test validation")
    parser.add_argument("--val-conf", type=float, default=0.001,
                        help="Minimum confidence used while building the test precision-recall curve")
    parser.add_argument("--val-iou", type=float, default=0.7,
                        help="IoU threshold used by validation NMS")
    args = parser.parse_args()

    if args.size < 32 or args.size % 32:
        parser.error("--size must be at least 32 and divisible by 32")

    if args.mode in {"train", "validate"}:
        if not args.data:
            parser.error(f"--data is required for mode {args.mode}")
    if not (0.0 <= args.val_conf < 1.0):
        parser.error("--val-conf must be in [0, 1)")
    if not (0.0 < args.val_iou <= 1.0):
        parser.error("--val-iou must be in (0, 1]")

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
        metrics = model.val(
            data=args.data,
            split="test",
            imgsz=args.size,
            device=args.device,
            conf=args.val_conf,
            iou=args.val_iou,
            plots=True,
            verbose=True,
        )
        box = metrics.box

        def floats(value):
            if hasattr(value, "tolist"):
                value = value.tolist()
            if isinstance(value, (list, tuple)):
                return [float(item) for item in value]
            return []

        precision_values = floats(getattr(box, "p", []))
        recall_values = floats(getattr(box, "r", []))
        f1_values = floats(getattr(box, "f1", []))
        map50_values = floats(getattr(box, "ap50", []))
        map_values = floats(getattr(box, "ap", []))
        class_indices = [int(item) for item in floats(getattr(box, "ap_class_index", []))]
        class_to_slot = {class_id: slot for slot, class_id in enumerate(class_indices)}
        target_counts = floats(getattr(metrics, "nt_per_class", []))
        target_image_counts = floats(getattr(metrics, "nt_per_image", []))
        per_class = []
        for class_id, class_name in enumerate(CLASS_ORDER):
            slot = class_to_slot.get(class_id)
            precision = precision_values[slot] if slot is not None and slot < len(precision_values) else None
            recall = recall_values[slot] if slot is not None and slot < len(recall_values) else None
            class_map50 = map50_values[slot] if slot is not None and slot < len(map50_values) else None
            class_map = map_values[slot] if slot is not None and slot < len(map_values) else None
            f1 = f1_values[slot] if slot is not None and slot < len(f1_values) else None
            per_class.append({
                "class_id": class_id,
                "class_name": class_name,
                "test_ground_truth_images": (
                    int(target_image_counts[class_id])
                    if class_id < len(target_image_counts) else None
                ),
                "test_ground_truth_instances": (
                    int(target_counts[class_id]) if class_id < len(target_counts) else None
                ),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "map50": class_map50,
                "map50_95": class_map,
            })

        def scalar(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        checkpoint_path = Path(args.weights).expanduser().resolve()
        dataset_path = Path(args.data).expanduser().resolve()
        checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        mean_precision = scalar(box.mp)
        mean_recall = scalar(box.mr)
        class_f1_values = [item["f1"] for item in per_class if item["f1"] is not None]
        macro_f1 = (
            sum(class_f1_values) / len(class_f1_values) if class_f1_values else None
        )
        harmonic_macro_pr = (
            2 * mean_precision * mean_recall / (mean_precision + mean_recall)
            if mean_precision is not None and mean_recall is not None
            and mean_precision + mean_recall > 0 else None
        )
        classes_without_test_annotations = [
            item["class_name"] for item in per_class
            if item["test_ground_truth_instances"] == 0
        ]
        audit_path = dataset_path.parent / "audit.json"
        dataset_audit = None
        dataset_audit_sha = None
        if audit_path.is_file():
            audit_bytes = audit_path.read_bytes()
            dataset_audit_sha = hashlib.sha256(audit_bytes).hexdigest()
            audit_data = json.loads(audit_bytes.decode("utf-8"))
            group_splits = audit_data.get("groups", {})
            dataset_audit = {
                "audit_file": str(audit_path),
                "audit_sha256": dataset_audit_sha,
                "image_counts": audit_data.get("image_counts"),
                "box_counts": audit_data.get("box_counts"),
                "group_counts": {
                    split: sum(1 for value in group_splits.values() if value == split)
                    for split in ("train", "val", "test")
                } if isinstance(group_splits, dict) else None,
            }
        report = {
            "schema_version": 1,
            "measurement_type": "project_held_out_test_accuracy",
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": {
                "checkpoint": str(checkpoint_path),
                "checkpoint_sha256": checkpoint_sha,
                "class_order": CLASS_ORDER,
                "input_size": args.size,
            },
            "dataset": {
                "yaml": str(dataset_path),
                "yaml_sha256": dataset_sha,
                "split": "test",
                "group_split_policy": "Keep each physical PCB/design/capture group within exactly one split.",
                "audit": dataset_audit,
            },
            "evaluation_settings": {
                "image_size": args.size,
                "minimum_confidence_for_precision_recall_curve": args.val_conf,
                "nms_iou": args.val_iou,
                "precision_recall_operating_point": "Shared confidence selected at the maximum smoothed mean-F1 point of the test precision-recall curves by the pinned Ultralytics evaluator.",
            },
            "test_set_coverage": {
                "ground_truth_instances_per_class": {
                    item["class_name"]: {
                        "images": item["test_ground_truth_images"],
                        "instances": item["test_ground_truth_instances"],
                    } for item in per_class
                },
                "classes_without_test_annotations": classes_without_test_annotations,
                "all_three_classes_have_test_annotations": (
                    len(classes_without_test_annotations) == 0
                    and all(item["test_ground_truth_instances"] is not None for item in per_class)
                    and all(item["test_ground_truth_images"] is not None for item in per_class)
                ),
                "warning": (
                    "Per-class metrics and macro averages are incomplete when a class has no test annotations."
                    if classes_without_test_annotations else None
                ),
            },
            "overall": {
                "precision": mean_precision,
                "recall": mean_recall,
                "f1": macro_f1,
                "f1_definition": "Unweighted arithmetic mean of the reported per-class F1 values at the evaluator shared operating point.",
                "harmonic_mean_of_macro_precision_recall": harmonic_macro_pr,
                "map50": scalar(box.map50),
                "map50_95": scalar(box.map),
            },
            "per_class": per_class,
            "inference_speed_ms_per_image": {
                key: scalar(value) for key, value in getattr(metrics, "speed", {}).items()
            },
            "ultralytics_results_dict": {
                str(key): scalar(value) for key, value in metrics.results_dict.items()
            },
            "ultralytics_run_directory": str(getattr(metrics, "save_dir", "")),
            "notes": [
                "Metrics are generated by this command from the supplied checkpoint and dataset test split.",
                "Do not report these values as project results until the checkpoint, labels, group split and held-out test set have been independently audited.",
                "Precision, recall and F1 use the evaluator operating point stated in evaluation_settings; mAP integrates precision over the confidence curve.",
                "The dataset audit is included when pcb_engine_kit/dataset.py generated audit.json beside data.yaml.",
                "A missing test class makes the test report incomplete for that class; inspect test_set_coverage before interpreting macro scores.",
                "The upstream pretrained model-card metrics are not substituted into this report.",
            ],
        }
        report_path = Path(args.report_out).expanduser()
        if not report_path.is_absolute():
            report_path = Path(__file__).resolve().parents[1] / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Test evaluation completed. Machine-readable report: {report_path}")
        print(json.dumps(report["overall"], indent=2))
        return 0

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    onnx_path = export_onnx(model, out, args.size)
    print(f"ONNX export: {onnx_path}")
    print("Export metadata remains unvalidated until held-out parity and target-Pi tests pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
