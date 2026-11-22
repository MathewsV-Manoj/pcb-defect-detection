"""Train a project-owned three-class YOLO detector, evaluate it, and export ONNX."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
import ultralytics
from ultralytics import YOLO

CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ordered_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda item: int(item))]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    raise RuntimeError(f"Unsupported class-name structure: {type(names).__name__}")


def check_dataset_class_order(data_path: str | Path) -> dict[str, Any]:
    path = Path(data_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "names" not in data:
        raise RuntimeError(f"Dataset YAML must contain a names field: {path}")
    names = ordered_names(data["names"])
    if names != CLASS_ORDER:
        raise RuntimeError(f"Dataset class order {names!r} does not match {CLASS_ORDER!r}")
    audit_path = path.parent / "audit.json"
    if not audit_path.is_file():
        raise RuntimeError(
            f"Dataset audit is missing: {audit_path}. Rebuild the dataset with pcb_engine_kit/dataset.py."
        )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("structure_status") != "VALID":
        raise RuntimeError("Dataset structure audit is not VALID.")
    if audit.get("provenance_status") != "COMPLETE_AS_DECLARED":
        raise RuntimeError(
            "Dataset provenance is incomplete. Complete source, rights-review and annotation-review fields first."
        )
    if not audit.get("release_ready", False):
        raise RuntimeError(
            "Dataset audit is not release-ready. Ensure all three classes appear in train, val and test."
        )
    if audit.get("data_yaml_sha256") != sha256_file(path):
        raise RuntimeError("Dataset YAML hash does not match the audit.json record.")
    if audit.get("class_order") != CLASS_ORDER:
        raise RuntimeError("Dataset audit class order does not match the deployment contract.")
    return {"path": path, "sha256": sha256_file(path), "audit_path": audit_path,
            "audit": audit, "audit_sha256": sha256_file(audit_path)}


def checkpoint_provenance_path(checkpoint: Path) -> Path:
    # Expected layout: runs/pcb*/weights/best.pt and runs/pcb*/project_training_provenance.json.
    return checkpoint.parent.parent / "project_training_provenance.json"


def verify_project_checkpoint(checkpoint_value: str | Path, dataset: dict[str, Any]) -> tuple[Path, dict[str, Any], Path]:
    checkpoint = Path(checkpoint_value).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint does not exist: {checkpoint}")
    provenance_path = checkpoint_provenance_path(checkpoint)
    if not provenance_path.is_file():
        raise RuntimeError(
            f"Project training provenance is missing: {provenance_path}. "
            "A bare .pt file cannot be accepted as a verified project checkpoint."
        )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    checkpoint_sha = sha256_file(checkpoint)
    checks = {
        "provenance_status": provenance.get("provenance_status") == "VERIFIED_PROJECT_TRAINING",
        "pretrained_weights_used": provenance.get("pretrained_weights_used") is False,
        "initialization_method": provenance.get("initialization_method") == "random_initialization_from_yolo_yaml",
        "checkpoint_sha256": provenance.get("checkpoint_sha256") == checkpoint_sha,
        "dataset_yaml_sha256": provenance.get("dataset_yaml_sha256") == dataset["sha256"],
        "dataset_audit_sha256": provenance.get("dataset_audit_sha256") == dataset["audit_sha256"],
        "class_order": provenance.get("class_order") == CLASS_ORDER,
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Checkpoint provenance verification failed: " + ", ".join(failed))
    return checkpoint, provenance, provenance_path


def scalar(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def floats(value: Any) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return []


def export_onnx(model: YOLO, out: Path, size: int, checkpoint: Path,
                provenance_path: Path, provenance: dict[str, Any]) -> Path:
    names = ordered_names(model.names)
    if names != CLASS_ORDER:
        raise RuntimeError(f"Checkpoint class order {names!r} does not match {CLASS_ORDER!r}")
    result = Path(model.export(
        format="onnx", imgsz=size, opset=17, simplify=False,
        dynamic=False, batch=1, nms=False, device="cpu",
    ))
    if not result.is_file():
        raise RuntimeError(f"Ultralytics did not return a readable ONNX file: {result}")
    out.mkdir(parents=True, exist_ok=True)
    destination = out / "best.onnx"
    if result.resolve() != destination.resolve():
        destination.write_bytes(result.read_bytes())
    metadata = {
        "schema_version": 2,
        "format": "onnx",
        "architecture": "YOLOv8 Nano",
        "provenance_status": "VERIFIED_PROJECT_TRAINING",
        "initialization_method": provenance["initialization_method"],
        "pretrained_weights_used": False,
        "class_order": CLASS_ORDER,
        "input_size": [size, size],
        "input": {
            "color_order": "RGB", "layout": "NCHW", "dtype": "float32",
            "normalization": "0_to_1", "resize": "letterbox",
        },
        "output_contract": "raw_yolov8_xywh_3_class_scores_no_nms",
        "checkpoint_path_at_export": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "dataset_yaml_sha256": provenance["dataset_yaml_sha256"],
        "dataset_audit_sha256": provenance["dataset_audit_sha256"],
        "training_provenance_sha256": sha256_file(provenance_path),
        "sha256": sha256_file(destination),
        "validated_on_pi": False,
        "prediction_parity_verified": False,
    }
    (out / "best.onnx.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["train", "validate", "export-onnx"])
    parser.add_argument("--data", required=True, help="Audited YOLO dataset YAML")
    parser.add_argument("--model-yaml", default="yolov8n.yaml",
                        help="Ultralytics model architecture YAML; .pt weights are not accepted")
    parser.add_argument("--checkpoint", help="Exact project best.pt path (required for validate/export)")
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0")
    parser.add_argument("--out", default="deployment")
    parser.add_argument("--project", default="runs")
    parser.add_argument("--name", default="pcb")
    parser.add_argument("--report-out", default="docs/results/project_test_metrics.json")
    parser.add_argument("--val-conf", type=float, default=0.001)
    parser.add_argument("--val-iou", type=float, default=0.7)
    args = parser.parse_args()

    if args.size < 32 or args.size % 32:
        parser.error("--size must be at least 32 and divisible by 32")
    if not (0.0 <= args.val_conf < 1.0):
        parser.error("--val-conf must be in [0, 1)")
    if not (0.0 < args.val_iou <= 1.0):
        parser.error("--val-iou must be in (0, 1]")
    if args.mode in {"validate", "export-onnx"} and not args.checkpoint:
        parser.error(f"--checkpoint is required for mode {args.mode}")
    if args.mode == "train" and Path(args.model_yaml).suffix.lower() == ".pt":
        parser.error("Training must start from a model architecture YAML; pretrained .pt checkpoints are disabled.")

    dataset = check_dataset_class_order(args.data)

    if args.mode == "train":
        model = YOLO(args.model_yaml)
        model.train(
            data=str(dataset["path"]),
            imgsz=args.size,
            epochs=args.epochs,
            batch=args.batch,
            device=args.device,
            workers=2,
            seed=42,
            deterministic=True,
            patience=20,
            project=args.project,
            name=args.name,
            amp=True,
            mosaic=0.0,
            mixup=0.0,
            pretrained=False,
        )
        save_dir = Path(model.trainer.save_dir).resolve()
        checkpoint = save_dir / "weights" / "best.pt"
        if not checkpoint.is_file():
            raise RuntimeError(f"Training did not produce best.pt: {checkpoint}")
        trained = YOLO(str(checkpoint))
        if ordered_names(trained.names) != CLASS_ORDER:
            raise RuntimeError(f"Trained checkpoint class order {ordered_names(trained.names)!r} is invalid.")
        audit = dataset["audit"]
        provenance = {
            "schema_version": 1,
            "provenance_status": "VERIFIED_PROJECT_TRAINING",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_model": True,
            "architecture_yaml": args.model_yaml,
            "initialization_method": "random_initialization_from_yolo_yaml",
            "pretrained_weights_used": False,
            "class_order": CLASS_ORDER,
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": sha256_file(checkpoint),
            "dataset_yaml_path": str(dataset["path"]),
            "dataset_yaml_sha256": dataset["sha256"],
            "dataset_audit_path": str(dataset["audit_path"]),
            "dataset_audit_sha256": dataset["audit_sha256"],
            "import_manifest_path": audit.get("import_manifest_path"),
            "import_manifest_sha256": audit.get("import_manifest_sha256"),
            "training_configuration": {
                "image_size": args.size, "epochs": args.epochs, "batch": args.batch,
                "device": args.device, "seed": 42, "deterministic": True,
                "patience": 20, "mosaic": 0.0, "mixup": 0.0,
                "pretrained": False,
            },
            "software": {"ultralytics": ultralytics.__version__},
            "notes": [
                "The detector weights are initialized from the model architecture YAML; no pretrained .pt checkpoint was supplied.",
                "This record proves the declared local training run inputs and file hashes, not independent correctness of dataset labels or legal rights.",
                "Do not edit the dataset, checkpoint or this record after training; rerun training if any source changes.",
            ],
        }
        provenance_path = save_dir / "project_training_provenance.json"
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "training_status": "COMPLETED",
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": provenance["checkpoint_sha256"],
            "provenance": str(provenance_path),
        }, indent=2))
        return 0

    checkpoint, provenance, provenance_path = verify_project_checkpoint(args.checkpoint, dataset)
    model = YOLO(str(checkpoint))
    if ordered_names(model.names) != CLASS_ORDER:
        raise RuntimeError(f"Checkpoint class order {ordered_names(model.names)!r} is invalid.")

    if args.mode == "export-onnx":
        onnx_path = export_onnx(model, Path(args.out).expanduser().resolve(), args.size,
                                checkpoint, provenance_path, provenance)
        print(f"Project-trained ONNX export: {onnx_path}")
        print("Export is not evidence of prediction parity or target-device validation.")
        return 0

    metrics = model.val(
        data=str(dataset["path"]), split="test", imgsz=args.size,
        device=args.device, conf=args.val_conf, iou=args.val_iou,
        plots=True, verbose=True,
    )
    box = metrics.box
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
        per_class.append({
            "class_id": class_id, "class_name": class_name,
            "test_ground_truth_images": int(target_image_counts[class_id]) if class_id < len(target_image_counts) else None,
            "test_ground_truth_instances": int(target_counts[class_id]) if class_id < len(target_counts) else None,
            "precision": precision_values[slot] if slot is not None and slot < len(precision_values) else None,
            "recall": recall_values[slot] if slot is not None and slot < len(recall_values) else None,
            "f1": f1_values[slot] if slot is not None and slot < len(f1_values) else None,
            "map50": map50_values[slot] if slot is not None and slot < len(map50_values) else None,
            "map50_95": map_values[slot] if slot is not None and slot < len(map_values) else None,
        })
    classes_without_test_annotations = [
        item["class_name"] for item in per_class if item["test_ground_truth_instances"] in (None, 0)
    ]
    class_f1_values = [item["f1"] for item in per_class if item["f1"] is not None]
    mean_precision = scalar(box.mp)
    mean_recall = scalar(box.mr)
    macro_f1 = sum(class_f1_values) / len(class_f1_values) if len(class_f1_values) == len(CLASS_ORDER) else None
    report = {
        "schema_version": 1,
        "measurement_type": "project_held_out_test_accuracy",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "result_status": "COMPLETE" if not classes_without_test_annotations else "INCOMPLETE_TEST_CLASS_COVERAGE",
        "model": {
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": sha256_file(checkpoint),
            "training_provenance_path": str(provenance_path),
            "training_provenance_sha256": sha256_file(provenance_path),
            "initialization_method": provenance["initialization_method"],
            "pretrained_weights_used": False,
            "class_order": CLASS_ORDER,
            "image_size": args.size,
        },
        "dataset": {
            "yaml_path": str(dataset["path"]), "yaml_sha256": dataset["sha256"],
            "audit_path": str(dataset["audit_path"]), "audit_sha256": dataset["audit_sha256"],
            "import_manifest_sha256": dataset["audit"].get("import_manifest_sha256"),
            "evaluation_split": "test",
            "board_grouped_split": True,
        },
        "evaluation_settings": {
            "minimum_confidence_for_precision_recall_curve": args.val_conf,
            "nms_iou": args.val_iou,
            "operating_point": "Ultralytics shared confidence selected at maximum smoothed mean F1.",
        },
        "test_set_coverage": {
            "ground_truth_instances_per_class": {
                item["class_name"]: {"images": item["test_ground_truth_images"], "instances": item["test_ground_truth_instances"]}
                for item in per_class
            },
            "classes_without_test_annotations": classes_without_test_annotations,
        },
        "overall": {
            "precision": mean_precision, "recall": mean_recall,
            "macro_f1": macro_f1, "map50": scalar(box.map50), "map50_95": scalar(box.map),
        },
        "per_class": per_class,
        "inference_speed_ms_per_image": {key: scalar(value) for key, value in getattr(metrics, "speed", {}).items()},
        "ultralytics_run_directory": str(getattr(metrics, "save_dir", "")),
        "limitations": [
            "Metrics apply only to this checkpoint and this held-out test split.",
            "Board-group independence depends on truthful and consistent group IDs in the import manifest.",
            "The audit records team-declared rights and annotation review; it does not independently establish legal rights or label correctness.",
            "Do not copy values from published models or external hardware benchmarks into this report.",
        ],
    }
    report_path = Path(args.report_out).expanduser()
    if not report_path.is_absolute():
        report_path = Path(__file__).resolve().parents[1] / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Project held-out test report: {report_path}")
    print(json.dumps(report["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
