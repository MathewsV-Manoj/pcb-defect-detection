"""Single-worker TFLite folder engine. Model contract: raw YOLOv8, 3 classes, normalized xywh."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class Detector:
    def __init__(self, folder: str | Path, threads: int = 2):
        folder = Path(folder).expanduser().resolve()
        if threads < 1:
            raise ValueError("threads must be at least 1")
        metadata_path = folder / "metadata.json"
        model_path = folder / "detector.tflite"
        if not metadata_path.is_file() or not model_path.is_file():
            raise FileNotFoundError(f"TFLite model folder must contain metadata.json and detector.tflite: {folder}")

        self.meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        if self.meta.get("classes") != CLASS_ORDER:
            raise ValueError(
                f"TFLite class order {self.meta.get('classes')!r} does not match {CLASS_ORDER!r}"
            )
        if self.meta.get("box_units") != "normalized":
            raise ValueError("TFLite metadata box_units must be 'normalized'")
        expected_hash = self.meta.get("sha256")
        actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if not expected_hash or actual_hash != expected_hash:
            raise ValueError("TFLite model SHA-256 does not match metadata.json")

        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            try:
                from tensorflow.lite import Interpreter
            except ImportError as exc:
                raise RuntimeError("Install tflite-runtime or TensorFlow Lite to run the folder worker") from exc

        self.runner = Interpreter(model_path=str(model_path), num_threads=threads)
        self.runner.allocate_tensors()
        inputs = self.runner.get_input_details()
        outputs = self.runner.get_output_details()
        if len(inputs) != 1:
            raise RuntimeError(f"Expected one TFLite input tensor, found {len(inputs)}")
        if len(outputs) != 1:
            raise RuntimeError(f"Expected one raw YOLO output tensor, found {len(outputs)}")

        self.input_detail = inputs[0]
        self.output_detail = outputs[0]
        shape = list(map(int, self.input_detail["shape"]))
        if len(shape) != 4 or shape[0] != 1 or shape[3] != 3:
            raise RuntimeError(f"Expected TFLite NHWC input [1,H,W,3], got {shape}")
        self.height, self.width = shape[1], shape[2]
        if self.height <= 0 or self.width <= 0:
            raise RuntimeError(f"Invalid TFLite input dimensions: {shape}")

    def detect(self, image: np.ndarray, threshold: float) -> list[dict[str, Any]]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("confidence threshold must be between 0 and 1")
        height, width = image.shape[:2]
        scale = min(self.width / width, self.height / height)
        resized_width = round(width * scale)
        resized_height = round(height * scale)
        left = (self.width - resized_width) // 2
        top = (self.height - resized_height) // 2

        canvas = np.full((self.height, self.width, 3), 114, dtype=np.uint8)
        canvas[top:top + resized_height, left:left + resized_width] = cv2.resize(
            image, (resized_width, resized_height)
        )
        tensor = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32)[None] / 255.0

        input_dtype = self.input_detail["dtype"]
        if np.issubdtype(input_dtype, np.integer):
            scale_q, zero_point = self.input_detail.get("quantization", (0.0, 0))
            if scale_q <= 0:
                raise RuntimeError("Quantized TFLite input has an invalid quantization scale")
            limits = np.iinfo(input_dtype)
            tensor = np.clip(
                np.rint(tensor / scale_q + zero_point), limits.min, limits.max
            )

        self.runner.set_tensor(self.input_detail["index"], tensor.astype(input_dtype))
        self.runner.invoke()
        output = self.runner.get_tensor(self.output_detail["index"])

        output_dtype = output.dtype
        if np.issubdtype(output_dtype, np.integer):
            scale_q, zero_point = self.output_detail.get("quantization", (0.0, 0))
            if scale_q <= 0:
                raise RuntimeError("Quantized TFLite output has an invalid quantization scale")
            output = (output.astype(np.float32) - zero_point) * scale_q

        predictions = np.asarray(output)
        if predictions.ndim != 3 or predictions.shape[0] != 1:
            raise RuntimeError(f"Expected TFLite output shape [1,7,N] or [1,N,7], got {predictions.shape}")
        predictions = predictions[0]
        if predictions.shape[0] == 7:
            predictions = predictions.T
        elif predictions.shape[1] != 7:
            raise RuntimeError(f"Expected seven values per YOLO anchor, got {predictions.shape}")
        if not np.isfinite(predictions).all():
            raise RuntimeError("TFLite model output contains NaN or infinity")

        result: list[dict[str, Any]] = []
        for class_id, class_name in enumerate(CLASS_ORDER):
            rows = predictions[predictions[:, 4 + class_id] >= threshold]
            boxes: list[list[float]] = []
            scores: list[float] = []
            for row in rows:
                center_x, center_y, box_width, box_height = (
                    row[:4] * [self.width, self.height, self.width, self.height]
                )
                x1 = float(np.clip((center_x - box_width / 2 - left) / scale, 0, width))
                y1 = float(np.clip((center_y - box_height / 2 - top) / scale, 0, height))
                x2 = float(np.clip((center_x + box_width / 2 - left) / scale, 0, width))
                y2 = float(np.clip((center_y + box_height / 2 - top) / scale, 0, height))
                if x2 > x1 and y2 > y1:
                    boxes.append([x1, y1, x2 - x1, y2 - y1])
                    scores.append(float(row[4 + class_id]))

            # OpenCV may return None or an empty tuple when a class has no candidates.
            if not boxes:
                continue
            kept = cv2.dnn.NMSBoxes(boxes, scores, threshold, 0.45)
            if kept is None or len(kept) == 0:
                continue

            for index in np.asarray(kept).reshape(-1):
                x, y, box_width, box_height = boxes[int(index)]
                result.append(
                    {
                        "class": class_name,
                        "box": [x, y, x + box_width, y + box_height],
                        "confidence": scores[int(index)],
                        "source": "detector",
                    }
                )
        return result


def reference_check(image: np.ndarray, profile_path: str | Path):
    profile_path = Path(profile_path).expanduser().resolve()
    if not profile_path.is_file():
        raise FileNotFoundError(f"Reference profile not found: {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    reference_path = (profile_path.parent / profile.get("reference", "")).resolve()
    if profile_path.parent not in reference_path.parents or not reference_path.is_file():
        raise ValueError("Reference image path must point to an existing file inside the profile folder")
    reference = cv2.imread(str(reference_path))
    if reference is None:
        raise ValueError(f"Cannot read reference image: {reference_path}")

    factor = min(1.0, 1200 / max(image.shape[:2]))
    small = cv2.resize(image, None, fx=factor, fy=factor) if factor < 1.0 else image.copy()
    orb = cv2.ORB_create(2000)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    reference_keypoints, reference_descriptors = orb.detectAndCompute(reference_gray, None)
    if descriptors is None or reference_descriptors is None:
        return [], "alignment_failed"

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(descriptors, reference_descriptors, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.7 * pair[1].distance]
    if len(good) < 15:
        return [], "alignment_failed"

    source_points = np.float32([keypoints[match.queryIdx].pt for match in good])
    destination_points = np.float32([reference_keypoints[match.trainIdx].pt for match in good])
    homography, mask = cv2.findHomography(source_points, destination_points, cv2.RANSAC, 3)
    if homography is None or mask is None or int(mask.sum()) < 12 or float(mask.mean()) < 0.5:
        return [], "alignment_failed"
    try:
        inverse_homography = np.linalg.inv(homography)
    except np.linalg.LinAlgError:
        return [], "alignment_failed"

    aligned = cv2.warpPerspective(gray, homography, (reference.shape[1], reference.shape[0]))
    valid = cv2.warpPerspective(
        np.ones(gray.shape, dtype=np.uint8),
        homography,
        (reference.shape[1], reference.shape[0]),
    )
    findings = []
    for region in profile.get("regions", []):
        if not isinstance(region, dict) or "box" not in region or len(region["box"]) != 4:
            return [], "invalid_reference_profile"
        x1, y1, x2, y2 = map(int, region["box"])
        if not (0 <= x1 < x2 <= reference.shape[1] and 0 <= y1 < y2 <= reference.shape[0]):
            return [], "invalid_reference_region"
        reference_roi = reference_gray[y1:y2, x1:x2]
        aligned_roi = aligned[y1:y2, x1:x2]
        valid_roi = valid[y1:y2, x1:x2]
        if reference_roi.size == 0 or not np.all(valid_roi):
            return [], "alignment_failed"

        similarity = (
            float(cv2.matchTemplate(aligned_roi, reference_roi, cv2.TM_CCOEFF_NORMED)[0, 0])
            if reference_roi.std() > 1 and aligned_roi.std() > 1
            else 0.0
        )
        if similarity < float(region.get("min_similarity", 0.8)):
            corners = np.float32([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]])
            corners = cv2.perspectiveTransform(corners, inverse_homography)[0] / factor
            box = [
                float(corners[:, 0].min()),
                float(corners[:, 1].min()),
                float(corners[:, 0].max()),
                float(corners[:, 1].max()),
            ]
            findings.append(
                {
                    "class": "missing_component_candidate",
                    "reference_id": region.get("id"),
                    "box": box,
                    "confidence": None,
                    "similarity": similarity,
                    "source": "reference",
                }
            )

    return findings, "review_required" if findings else "checked"


def inspect(detector: Detector, image: np.ndarray, config: dict[str, Any]):
    start = time.perf_counter()
    findings = detector.detect(image, float(config["confidence"]))
    notes = []
    component_status = "not_configured"
    reference_profile = config.get("reference_profile")
    if reference_profile:
        reference_findings, component_status = reference_check(image, reference_profile)
        findings += reference_findings
        if component_status != "checked":
            notes.append("components: " + component_status)

    if not detector.meta.get("validated"):
        notes.append("model_not_validated")
    status = (
        "faulty"
        if any(finding["source"] == "detector" for finding in findings)
        else "review_required" if notes or any(f["source"] == "reference" for f in findings)
        else "not_faulty"
    )
    return {
        "status": status,
        "detections": findings,
        "notes": notes,
        "inference_ms": round((time.perf_counter() - start) * 1000, 2),
        "image_size": [image.shape[1], image.shape[0]],
        "model_sha256": detector.meta["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.is_file():
        parser.error(f"Configuration file not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    required = {"root", "model_dir", "confidence"}
    missing = required.difference(config)
    if missing:
        parser.error(f"Configuration missing keys: {sorted(missing)}")
    confidence = float(config["confidence"])
    if not 0.0 <= confidence <= 1.0:
        parser.error("confidence must be between 0 and 1")

    cv2.setNumThreads(1)
    root = Path(config["root"]).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = (root / "engine.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError(f"Another folder-worker already owns {root / 'engine.lock'}")

    for name in ("incoming", "processing", "results", "archive", "failed"):
        (root / name).mkdir(exist_ok=True)
    detector = Detector(config["model_dir"], config.get("threads", 2))

    # Recover claimed images after an unclean previous worker exit.
    for old in (root / "processing").iterdir():
        if old.is_file():
            os.replace(old, root / "incoming" / old.name)

    print("Watching", root / "incoming", flush=True)
    while True:
        for source in sorted((root / "incoming").iterdir()):
            if not source.is_file() or source.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            job = uuid.uuid4().hex
            claimed = root / "processing" / (job + source.suffix.lower())
            os.replace(source, claimed)
            result = {
                "schema_version": 1,
                "job_id": job,
                "original_name": source.name,
                "created_unix": time.time(),
            }
            try:
                image = cv2.imread(str(claimed))
                if image is None:
                    raise ValueError("Unreadable image")
                result.update(inspect(detector, image, config))
                visualized = image.copy()
                for finding in result["detections"]:
                    x1, y1, x2, y2 = map(round, finding["box"])
                    confidence_value = finding["confidence"]
                    label = finding["class"] + (
                        f" {confidence_value:.2f}" if confidence_value is not None else " REVIEW"
                    )
                    cv2.rectangle(visualized, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(
                        visualized,
                        label,
                        (max(0, x1), max(20, y1)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1,
                    )
                cv2.putText(
                    visualized, result["status"], (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
                )
                image_path = root / "results" / (job + ".jpg")
                temporary_image = root / "results" / (job + ".tmp.jpg")
                if not cv2.imwrite(str(temporary_image), visualized):
                    raise OSError("Image write failed")
                os.replace(temporary_image, image_path)
                result["annotated_image"] = str(image_path)
                archive_path = root / "archive" / claimed.name
                os.replace(claimed, archive_path)
                result["original_image"] = str(archive_path)
            except Exception as exc:
                result.update(status="error", error=str(exc), detections=[])
                traceback.print_exc()
                if claimed.exists():
                    os.replace(claimed, root / "failed" / claimed.name)
            atomic_json(root / "results" / (job + ".json"), result)
        time.sleep(0.25)


if __name__ == "__main__":
    main()
