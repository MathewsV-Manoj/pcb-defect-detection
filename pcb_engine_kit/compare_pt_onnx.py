"""Compare one audited project checkpoint with its matching ONNX export."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda item: int(item))]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    return []


def box_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def match_detections(reference: list[dict[str, Any]], candidate: list[dict[str, Any]],
                     minimum_iou: float) -> dict[str, Any]:
    pairs = []
    for ref_index, ref in enumerate(reference):
        for candidate_index, current in enumerate(candidate):
            if ref["class_id"] == current["class_id"]:
                overlap = box_iou(ref["xyxy"], current["xyxy"])
                if overlap >= minimum_iou:
                    pairs.append((overlap, ref_index, candidate_index))
    pairs.sort(reverse=True)
    used_ref: set[int] = set()
    used_candidate: set[int] = set()
    matched = []
    for overlap, ref_index, candidate_index in pairs:
        if ref_index in used_ref or candidate_index in used_candidate:
            continue
        used_ref.add(ref_index)
        used_candidate.add(candidate_index)
        ref, current = reference[ref_index], candidate[candidate_index]
        matched.append({
            "reference_index": ref_index,
            "candidate_index": candidate_index,
            "class_id": ref["class_id"],
            "iou": overlap,
            "confidence_abs_diff": abs(ref["confidence"] - current["confidence"]),
            "max_coordinate_abs_diff_px": max(
                abs(left - right) for left, right in zip(ref["xyxy"], current["xyxy"])
            ),
        })
    return {
        "matched_count": len(matched),
        "reference_count": len(reference),
        "candidate_count": len(candidate),
        "unmatched_reference_count": len(reference) - len(used_ref),
        "unmatched_candidate_count": len(candidate) - len(used_candidate),
        "matched": matched,
    }


def detections_from_result(result: Any) -> list[dict[str, Any]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []
    coordinates = boxes.xyxy.detach().cpu().tolist()
    confidences = boxes.conf.detach().cpu().tolist()
    class_ids = boxes.cls.detach().cpu().tolist()
    output = []
    for xyxy, confidence, class_id in zip(coordinates, confidences, class_ids):
        output.append({
            "xyxy": [float(value) for value in xyxy],
            "confidence": float(confidence),
            "class_id": int(class_id),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, help="Audited project best.pt checkpoint")
    parser.add_argument("--onnx", required=True, help="ONNX export from that exact checkpoint")
    parser.add_argument("--data", required=True, help="Matching processed data.yaml")
    parser.add_argument("--images-dir", required=True, help="Held-out test images only")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--nms-iou", type=float, default=0.45)
    parser.add_argument("--minimum-box-iou", type=float, default=0.98)
    parser.add_argument("--maximum-confidence-difference", type=float, default=0.02)
    parser.add_argument("--maximum-coordinate-difference-px", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum image count; 0 means all")
    parser.add_argument("--report-out", default="docs/results/project_onnx_parity.json")
    parser.add_argument("--mark-verified", action="store_true",
                        help="Set the ONNX sidecar parity flag only if every checked image passes")
    args = parser.parse_args()

    if args.image_size < 32 or args.image_size % 32:
        parser.error("--image-size must be at least 32 and divisible by 32")
    if not (0.0 <= args.confidence < 1.0):
        parser.error("--confidence must be in [0, 1)")
    if not (0.0 < args.nms_iou <= 1.0 and 0.0 < args.minimum_box_iou <= 1.0):
        parser.error("IoU thresholds must be in (0, 1]")
    if args.maximum_confidence_difference < 0 or args.maximum_coordinate_difference_px < 0:
        parser.error("Difference tolerances cannot be negative")
    if args.limit < 0:
        parser.error("--limit cannot be negative")

    import yaml
    from ultralytics import YOLO

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    onnx_path = Path(args.onnx).expanduser().resolve()
    data_path = Path(args.data).expanduser().resolve()
    images_dir = Path(args.images_dir).expanduser().resolve()
    sidecar_path = onnx_path.with_suffix(".onnx.json")
    provenance_path = checkpoint.parent.parent / "project_training_provenance.json"
    data_audit_path = data_path.parent / "audit.json"

    for required in (checkpoint, onnx_path, data_path, images_dir, sidecar_path, provenance_path, data_audit_path):
        if not required.exists():
            raise FileNotFoundError(f"Required parity input is missing: {required}")
    if not images_dir.is_dir():
        raise NotADirectoryError(f"Test image directory is not a directory: {images_dir}")

    checkpoint_hash = sha256_file(checkpoint)
    onnx_hash = sha256_file(onnx_path)
    data_hash = sha256_file(data_path)
    audit_hash = sha256_file(data_audit_path)
    provenance_hash = sha256_file(provenance_path)
    metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    dataset_audit = json.loads(data_audit_path.read_text(encoding="utf-8"))
    data_config = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    class_order = ordered_names(data_config.get("names") if isinstance(data_config, dict) else None)

    provenance_checks = {
        "onnx_hash_matches_sidecar": metadata.get("sha256") == onnx_hash,
        "checkpoint_hash_matches_onnx_sidecar": metadata.get("checkpoint_sha256") == checkpoint_hash,
        "dataset_yaml_hash_matches_onnx_sidecar": metadata.get("dataset_yaml_sha256") == data_hash,
        "dataset_audit_hash_matches_onnx_sidecar": metadata.get("dataset_audit_sha256") == audit_hash,
        "training_provenance_hash_matches_onnx_sidecar": metadata.get("training_provenance_sha256") == provenance_hash,
        "project_training_provenance_declared": provenance.get("provenance_status") == "VERIFIED_PROJECT_TRAINING",
        "random_initialization_declared": provenance.get("initialization_method") == "random_initialization_from_yolo_yaml",
        "pretrained_weights_not_used": provenance.get("pretrained_weights_used") is False,
        "dataset_import_audit_release_ready": dataset_audit.get("release_ready") is True,
        "dataset_and_metadata_class_order_match": class_order == CLASS_ORDER and metadata.get("class_order") == CLASS_ORDER,
    }
    failed_provenance = [key for key, passed in provenance_checks.items() if not passed]
    if failed_provenance:
        raise RuntimeError("Parity inputs failed provenance checks: " + ", ".join(failed_provenance))

    images = sorted(
        image for image in images_dir.rglob("*")
        if image.is_file() and image.suffix.lower() in SUPPORTED_IMAGES
    )
    if args.limit:
        images = images[:args.limit]
    if not images:
        raise ValueError(f"No supported test images found under {images_dir}")

    checkpoint_model = YOLO(str(checkpoint))
    onnx_model = YOLO(str(onnx_path))
    if ordered_names(checkpoint_model.names) != CLASS_ORDER or ordered_names(onnx_model.names) != CLASS_ORDER:
        raise RuntimeError("Checkpoint or ONNX class order differs from the project contract")

    image_results = []
    all_pairs = []
    for image_path in images:
        reference_results = checkpoint_model.predict(
            source=str(image_path), imgsz=args.image_size, conf=args.confidence,
            iou=args.nms_iou, device="cpu", verbose=False,
        )
        candidate_results = onnx_model.predict(
            source=str(image_path), imgsz=args.image_size, conf=args.confidence,
            iou=args.nms_iou, device="cpu", verbose=False,
        )
        if len(reference_results) != 1 or len(candidate_results) != 1:
            raise RuntimeError(f"Expected one prediction result per image: {image_path}")
        reference = detections_from_result(reference_results[0])
        candidate = detections_from_result(candidate_results[0])
        matching = match_detections(reference, candidate, args.minimum_box_iou)
        matched = matching["matched"]
        max_confidence_diff = max((item["confidence_abs_diff"] for item in matched), default=0.0)
        max_coordinate_diff = max((item["max_coordinate_abs_diff_px"] for item in matched), default=0.0)
        passed = (
            matching["unmatched_reference_count"] == 0
            and matching["unmatched_candidate_count"] == 0
            and max_confidence_diff <= args.maximum_confidence_difference
            and max_coordinate_diff <= args.maximum_coordinate_difference_px
        )
        image_entry = {
            "image_relative_to_test_dir": image_path.relative_to(images_dir).as_posix(),
            "image_sha256": sha256_file(image_path),
            "parity_pass": passed,
            **{key: value for key, value in matching.items() if key != "matched"},
            "maximum_confidence_abs_diff": max_confidence_diff,
            "maximum_coordinate_abs_diff_px": max_coordinate_diff,
            "mean_matched_iou": (
                sum(item["iou"] for item in matched) / len(matched) if matched else None
            ),
        }
        image_results.append(image_entry)
        all_pairs.extend(matched)

    report = {
        "schema_version": 1,
        "measurement_type": "project_checkpoint_vs_onnx_prediction_parity",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["parity_pass"] for item in image_results) else "FAIL",
        "image_count": len(image_results),
        "model": {
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": checkpoint_hash,
            "onnx_path": str(onnx_path),
            "onnx_sha256": onnx_hash,
            "onnx_sidecar_path": str(sidecar_path),
            "training_provenance_sha256": provenance_hash,
            "dataset_yaml_sha256": data_hash,
            "dataset_audit_sha256": audit_hash,
            "class_order": CLASS_ORDER,
        },
        "evaluation_settings": {
            "image_size": args.image_size,
            "confidence_threshold": args.confidence,
            "nms_iou": args.nms_iou,
            "minimum_box_iou": args.minimum_box_iou,
            "maximum_confidence_difference": args.maximum_confidence_difference,
            "maximum_coordinate_difference_px": args.maximum_coordinate_difference_px,
            "execution_provider": "CPU for both checkpoint and ONNX predictions",
        },
        "provenance_checks": provenance_checks,
        "total_matched_detections": len(all_pairs),
        "mean_matched_iou": (
            sum(item["iou"] for item in all_pairs) / len(all_pairs) if all_pairs else None
        ),
        "maximum_matched_confidence_abs_diff": (
            max((item["confidence_abs_diff"] for item in all_pairs), default=0.0)
        ),
        "maximum_matched_coordinate_abs_diff_px": (
            max((item["max_coordinate_abs_diff_px"] for item in all_pairs), default=0.0)
        ),
        "images": image_results,
        "limitations": [
            "This checks prediction parity only on the supplied test images and configured thresholds; it does not measure defect-detection accuracy.",
            "A parity pass does not prove that test annotations are correct or that the dataset is representative.",
            "Both models run on CPU using the Ultralytics prediction interface; this is not a Raspberry Pi runtime benchmark.",
            "Detection matching uses class identity and bounding-box IoU; boxes below the configured threshold are counted as unmatched.",
        ],
    }
    report_path = Path(args.report_out).expanduser()
    if not report_path.is_absolute():
        report_path = Path(__file__).resolve().parents[1] / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_bytes = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    report_path.write_bytes(report_bytes)
    report_hash = hashlib.sha256(report_bytes).hexdigest()

    if args.mark_verified and report["status"] == "PASS":
        metadata["prediction_parity_verified"] = True
        metadata["prediction_parity_report_path"] = str(report_path)
        metadata["prediction_parity_report_sha256"] = report_hash
        sidecar_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        report["sidecar_marked_verified"] = True
    elif args.mark_verified:
        report["sidecar_marked_verified"] = False
        report["sidecar_marking_note"] = "Parity failed; the ONNX sidecar was not marked verified."

    print(json.dumps({
        "status": report["status"],
        "image_count": report["image_count"],
        "total_matched_detections": report["total_matched_detections"],
        "report_path": str(report_path),
        "report_sha256": report_hash,
        "sidecar_marked_verified": report.get("sidecar_marked_verified", False),
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
