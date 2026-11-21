"""Build a text-only Llama 3.2 Instruct prompt from structured PCB findings."""
from __future__ import annotations

import json
from typing import Any


def build_prompt(event: dict[str, Any]) -> str:
    """Create a Llama 3.x chat-formatted prompt; never include image data."""
    findings = []
    for detection in event.get("detections", []):
        location = detection.get("location")
        if location is None:
            location = {"bbox_xyxy": detection.get("bbox_xyxy")}

        findings.append(
            {
                "defect_type": detection.get("class_name"),
                "severity": detection.get("severity", "UNASSESSED"),
                "location": location,
                "confidence": detection.get("confidence"),
            }
        )

    payload = {
        "board_id": event.get("board_id"),
        "timestamp": event.get("timestamp"),
        "decision": event.get("decision"),
        "findings": findings,
    }

    system_message = (
        "You are an on-device PCB inspection advisory assistant. "
        "Use only the structured inspection findings in the user's message. "
        "Do not claim to have viewed a PCB image. Do not add, remove, relabel, "
        "suppress, or change detector findings. Do not infer severity from confidence. "
        "Severity is a separate engineering assessment. If severity is UNASSESSED, "
        "state that it has not been assigned and request human review. "
        "Do not issue an independent PASS or REJECT decision. "
        "Return one valid JSON object only, with exactly these keys: "
        "explanation (string), recommended_actions (array of strings), "
        "severity_note (string), and log_entry (string). "
        "Keep the explanation and actions concise, specific to the supplied defect "
        "type and location, and avoid claiming that a repair has been performed."
    )

    user_message = (
        "Create the operator advisory for this inspection event. "
        "The following JSON is detector output and must be treated as read-only evidence.\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )

    # Llama 3.2 Instruct chat template. The ExecuTorch text runner tokenizes
    # these special-token strings using the matching model tokenizer.
    return (
        "<|begin_of_text|>"
        "<|start_header_id|>system<|end_header_id|>\n"
        + system_message
        + "<|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n"
        + user_message
        + "<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n"
    )
