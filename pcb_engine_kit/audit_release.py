"""Create portable dataset and checkpoint provenance audit reports for a candidate release."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def dataset_audit(data_value: str | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "audit_type": "project_dataset_release_audit",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NOT_PROVIDED",
        "structure_checks": {},
        "provenance_checks": {},
        "blockers": [],
        "limitations": [
            "Rights and label-review statuses are team declarations, not independent legal or scientific verification.",
            "The script cannot determine whether a bounding box semantically represents the intended physical defect.",
            "A valid group split depends on the team assigning the same stable group ID to all views/crops of the same board or capture session.",
        ],
    }
    if not data_value:
        report["blockers"].append("No --data argument was supplied.")
        return report
    data_path = Path(data_value).expanduser().resolve()
    if not data_path.is_file():
        report["blockers"].append(f"Dataset YAML not found: {data_path}")
        return report

    report["dataset_yaml_path"] = str(data_path)
    report["dataset_yaml_sha256"] = sha256_file(data_path)
    try:
        config = yaml.safe_load(data_path.read_text(encoding="utf-8"))
        names = config.get("names") if isinstance(config, dict) else None
        if isinstance(names, dict):
            class_order = [str(names[key]) for key in sorted(names, key=lambda item: int(item))]
        elif isinstance(names, (list, tuple)):
            class_order = [str(name) for name in names]
        else:
            class_order = []
        audit_path = data_path.parent / "audit.json"
        report["dataset_import_audit_path"] = str(audit_path)
        if not audit_path.is_file():
            report["blockers"].append(f"Generated dataset audit is missing: {audit_path}")
            report["status"] = "INCOMPLETE"
            return report
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        report["dataset_import_audit_sha256"] = sha256_file(audit_path)

        structure_checks = {
            "class_order_matches_deployment": class_order == CLASS_ORDER and audit.get("class_order") == CLASS_ORDER,
            "importer_structure_status_valid": audit.get("structure_status") == "VALID",
            "data_yaml_hash_matches_import_audit": audit.get("data_yaml_sha256") == sha256_file(data_path),
            "all_splits_have_images": all(int(audit.get("image_counts", {}).get(split, 0)) > 0 for split in ("train", "val", "test")),
            "all_classes_present_in_each_split": all(
                all(int(count) > 0 for count in audit.get("box_counts", {}).get(split, {}).values())
                and set(audit.get("box_counts", {}).get(split, {}).keys()) == set(CLASS_ORDER)
                for split in ("train", "val", "test")
            ),
            "group_split_map_present": isinstance(audit.get("groups_by_split"), dict),
        }
        group_lists = audit.get("groups_by_split", {})
        flattened_groups = [group for split in ("train", "val", "test") for group in group_lists.get(split, [])]
        structure_checks["groups_are_unique_across_splits"] = len(flattened_groups) == len(set(flattened_groups))

        records = audit.get("records", [])
        file_checks = []
        for record in records:
            for field, hash_field in (("processed_image", "processed_image_sha256"),
                                      ("processed_label", "processed_label_sha256")):
                candidate = (data_path.parent / str(record.get(field, ""))).resolve()
                exists = candidate.is_file() and data_path.parent in candidate.parents
                hash_matches = exists and sha256_file(candidate) == record.get(hash_field)
                file_checks.append(bool(hash_matches))
        structure_checks["processed_file_hashes_match"] = bool(records) and all(file_checks)
        report["structure_checks"] = structure_checks

        manifest_path_value = audit.get("import_manifest_path")
        manifest_path = Path(manifest_path_value).expanduser() if manifest_path_value else None
        manifest_exists = bool(manifest_path and manifest_path.is_file())
        manifest_hash_matches = bool(
            manifest_exists and sha256_file(manifest_path) == audit.get("import_manifest_sha256")
        )
        provenance_checks = {
            "import_manifest_available": manifest_exists,
            "import_manifest_hash_matches": manifest_hash_matches,
            "importer_provenance_status_complete": audit.get("provenance_status") == "COMPLETE_AS_DECLARED",
            "no_provenance_issues_recorded": not audit.get("provenance_issues"),
            "all_rows_declare_source_identity_and_url": bool(records) and all(
                record.get("source_name") and record.get("source_url") for record in records
            ),
            "all_rows_declare_rights_review": bool(records) and all(
                record.get("rights_review_status", "").upper() == "CONFIRMED_BY_TEAM"
                for record in records
            ),
            "all_rows_declare_annotation_review": bool(records) and all(
                record.get("annotation_review_status", "").upper() == "REVIEWED_BY_TEAM"
                for record in records
            ),
        }
        report["provenance_checks"] = provenance_checks
        all_structure = all(structure_checks.values())
        all_provenance = all(provenance_checks.values())
        report["status"] = "VERIFIED" if all_structure and all_provenance else "INCOMPLETE"
        report["release_ready"] = bool(all_structure and all_provenance and audit.get("release_ready"))
        report["image_counts"] = audit.get("image_counts")
        report["box_counts"] = audit.get("box_counts")
        report["group_counts"] = audit.get("group_counts")
        report["source_names"] = audit.get("source_names")
        report["blockers"] = [
            f"Structure check failed: {name}" for name, passed in structure_checks.items() if not passed
        ] + [
            f"Provenance check failed: {name}" for name, passed in provenance_checks.items() if not passed
        ]
        if not audit.get("release_ready"):
            report["blockers"].append("The importer did not mark the dataset release-ready; inspect missing class coverage and provenance issues.")
    except Exception as exc:
        report["status"] = "ERROR"
        report["blockers"].append(f"Dataset audit could not be completed: {type(exc).__name__}: {exc}")
    return report


def checkpoint_audit(checkpoint_value: str | None, data_report: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "audit_type": "project_checkpoint_provenance_audit",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NOT_PROVIDED",
        "checks": {},
        "blockers": [],
        "limitations": [
            "The sidecar is a provenance record generated by the training script; it is not a cryptographic proof of who operated the machine.",
            "A matching SHA-256 proves byte identity, not model quality or correctness of annotations.",
            "The team must confirm that the training command was actually run by its members and that no unrecorded weights were used.",
        ],
    }
    if not checkpoint_value:
        report["blockers"].append("No --checkpoint argument was supplied.")
        return report
    checkpoint = Path(checkpoint_value).expanduser().resolve()
    if not checkpoint.is_file():
        report["blockers"].append(f"Checkpoint not found: {checkpoint}")
        report["status"] = "INCOMPLETE"
        return report
    provenance_path = checkpoint.parent.parent / "project_training_provenance.json"
    report["checkpoint_path"] = str(checkpoint)
    report["checkpoint_sha256"] = sha256_file(checkpoint)
    report["checkpoint_size_bytes"] = checkpoint.stat().st_size
    report["training_provenance_path"] = str(provenance_path)
    if not provenance_path.is_file():
        report["blockers"].append(f"Training provenance sidecar not found: {provenance_path}")
        report["status"] = "INCOMPLETE"
        return report
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        checks = {
            "sidecar_declares_project_training": provenance.get("provenance_status") == "VERIFIED_PROJECT_TRAINING",
            "random_initialization_declared": provenance.get("initialization_method") == "random_initialization_from_yolo_yaml",
            "pretrained_weights_not_used": provenance.get("pretrained_weights_used") is False,
            "checkpoint_sha256_matches": provenance.get("checkpoint_sha256") == report["checkpoint_sha256"],
            "class_order_matches": provenance.get("class_order") == CLASS_ORDER,
            "dataset_yaml_sha_matches_current_audit": provenance.get("dataset_yaml_sha256") == data_report.get("dataset_yaml_sha256"),
            "dataset_audit_sha_matches_current_audit": provenance.get("dataset_audit_sha256") == data_report.get("dataset_import_audit_sha256"),
            "dataset_audit_verified": data_report.get("status") == "VERIFIED" and data_report.get("release_ready") is True,
        }
        report["checks"] = checks
        report["training_provenance_sha256"] = sha256_file(provenance_path)
        report["initialization_method"] = provenance.get("initialization_method")
        report["pretrained_weights_used"] = provenance.get("pretrained_weights_used")
        report["class_order"] = provenance.get("class_order")
        report["dataset_yaml_sha256"] = provenance.get("dataset_yaml_sha256")
        report["dataset_audit_sha256"] = provenance.get("dataset_audit_sha256")
        report["status"] = "VERIFIED_PROJECT_TRAINING" if all(checks.values()) else "UNVERIFIED"
        report["release_ready"] = all(checks.values())
        report["blockers"] = [f"Checkpoint check failed: {name}" for name, passed in checks.items() if not passed]
    except Exception as exc:
        report["status"] = "ERROR"
        report["blockers"].append(f"Checkpoint audit could not be completed: {type(exc).__name__}: {exc}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="Processed dataset data.yaml; omit to record NOT_PROVIDED")
    parser.add_argument("--checkpoint", help="Project-trained best.pt; omit to record NOT_PROVIDED")
    parser.add_argument("--output-dir", default="docs/results", help="Directory for portable JSON audit reports")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    data_report = dataset_audit(args.data)
    checkpoint_report = checkpoint_audit(args.checkpoint, data_report)
    combined = {
        "schema_version": 1,
        "audit_type": "project_release_provenance_audit",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_status": data_report["status"],
        "checkpoint_status": checkpoint_report["status"],
        "release_ready": data_report.get("release_ready") is True and checkpoint_report.get("release_ready") is True,
        "rule": "No model or metric may be presented as a project result unless the checkpoint and dataset audits pass and the result is reproduced from the matching run.",
    }
    write_json(output_dir / "project_dataset_audit.json", data_report)
    write_json(output_dir / "project_checkpoint_audit.json", checkpoint_report)
    write_json(output_dir / "project_release_audit.json", combined)
    print(json.dumps(combined, indent=2))
    print(f"Dataset audit: {output_dir / 'project_dataset_audit.json'}")
    print(f"Checkpoint audit: {output_dir / 'project_checkpoint_audit.json'}")
    print(f"Combined audit: {output_dir / 'project_release_audit.json'}")
    return 0 if combined["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
