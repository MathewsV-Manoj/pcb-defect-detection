"""Build an advisory prompt from structured YOLO findings; no model weights included."""
from __future__ import annotations
import json
from typing import Any

def build_prompt(event: dict[str, Any]) -> str:
    safe = {
        "board_id": event.get("board_id"),
        "detections": [
            {"class_name": d.get("class_name"), "confidence": d.get("confidence"),
             "bbox_xyxy": d.get("bbox_xyxy")}
            for d in event.get("detections", [])
        ],
    }
    return (
        "You are an inspection support assistant. Use only the structured "
        "YOLO findings below and approved inspection procedures. Do not claim "
        "to have viewed an image. Do not add, remove, relabel or modify "
        "detector findings. Do not issue a PASS/REJECT decision. Give a brief "
        "operator verification suggestion.\n\n" + json.dumps(safe, indent=2)
    )
