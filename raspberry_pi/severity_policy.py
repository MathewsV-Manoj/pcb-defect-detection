"""Configurable, transparent defect-type severity screening policy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "models" / "severity_policy.json"
ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "UNASSESSED"}
EXPECTED_CLASSES = {"missing_hole", "open_circuit", "short_circuit"}


def load_severity_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the policy used by the detector event writer."""
    policy_path = Path(path).expanduser() if path else DEFAULT_POLICY_PATH
    if not policy_path.is_absolute():
        policy_path = (ROOT / policy_path).resolve()
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load severity policy {policy_path}: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported severity policy format: {policy_path}")
    rules = policy.get("rules")
    fallback = policy.get("fallback")
    if not isinstance(rules, dict) or not isinstance(fallback, dict):
        raise RuntimeError("Severity policy must contain rules and fallback objects")
    for class_name, rule in rules.items():
        if class_name not in EXPECTED_CLASSES or not isinstance(rule, dict):
            raise RuntimeError(f"Unknown or malformed severity rule: {class_name}")
        if rule.get("severity") not in ALLOWED_SEVERITIES:
            raise RuntimeError(f"Invalid severity value for {class_name}: {rule.get('severity')}")
        if not isinstance(rule.get("basis"), str) or not rule["basis"].strip():
            raise RuntimeError(f"Severity rule for {class_name} must include a non-empty basis")
    if fallback.get("severity") not in ALLOWED_SEVERITIES:
        raise RuntimeError("Severity policy fallback has an invalid severity")
    if not isinstance(fallback.get("basis"), str) or not fallback["basis"].strip():
        raise RuntimeError("Severity policy fallback must include a non-empty basis")
    policy["_path"] = str(policy_path)
    return policy


def classify_severity(
    class_name: str, policy: dict[str, Any]
) -> tuple[str, str]:
    """Return configured severity and its rationale; never infer from confidence."""
    rule = policy.get("rules", {}).get(class_name)
    if not isinstance(rule, dict):
        rule = policy["fallback"]
    return str(rule["severity"]), str(rule["basis"])
