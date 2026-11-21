"""Build a Llama advisory prompt from structured PCB detector findings."""
from __future__ import annotations
import json
from typing import Any


def build_prompt(event: dict[str, Any]) -> str:
    """Create advisory input; never pass image pixels or ask the LLM to detect defects."""
    findings = []
    for detection in event.get("detections", []):
        location = detection.get("location")
        if location is None:
            location = {"bbox_xyxy": detection.get("bbox_xyxy")}
        findings.append({
            "defect_type": detection.get("class_name"),
            "severity": detection.get("severity", "UNASSESSED"),
            "location": location,
            "confidence": detection.get("confidence"),
        })

    payload = {
        "board_id": event.get("board_id"),
        "timestamp": event.get("timestamp"),
        "findings": findings,
    }
    instructions = (
        "You are an on-device PCB inspection advisory assistant. "
        "Use only the structured findings supplied below and approved inspection procedures. "
        "Do not claim to have viewed a PCB image. Do not add, remove, relabel, suppress, "
        "or change detector findings. Do not infer severity from confidence. "
        "If severity is UNASSESSED, state that severity has not been assigned and request "
        "human review. Do not issue an independent PASS or REJECT decision. "
        "Return a concise explanation, verification actions, and an inspection log entry. "
        "Respond as JSON with keys: explanation, recommended_actions, severity_note, log_entry."
    )
    return instructions + "\n\nSTRUCTURED_INSPECTION_EVENT:\n" + json.dumps(payload, indent=2)
