import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CLASSES = ["missing_hole", "open_circuit", "short_circuit"]


class SubmissionContractTests(unittest.TestCase):
    def test_canonical_class_order_is_shared(self):
        classes = (ROOT / "models" / "class_names.txt").read_text(encoding="utf-8")
        parsed = [line.split(maxsplit=1)[1] for line in classes.splitlines() if line.strip()]
        self.assertEqual(parsed, EXPECTED_CLASSES)
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        importer = (ROOT / "pcb_engine_kit" / "dataset.py").read_text(encoding="utf-8")
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        self.assertIn('CLASS_NAMES = ["missing_hole", "open_circuit", "short_circuit"]', detector)
        self.assertIn('NAMES = ["missing_hole", "open_circuit", "short_circuit"]', importer)
        self.assertIn('CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]', exporter)

    def test_event_schema_and_example_have_required_finding_fields(self):
        schema = json.loads((ROOT / "schemas" / "inspection-event.schema.json").read_text(encoding="utf-8"))
        example = json.loads((ROOT / "schemas" / "example-event.json").read_text(encoding="utf-8"))
        finding = schema["properties"]["detections"]["items"]
        self.assertTrue({"class_name", "confidence", "bbox_xyxy", "severity", "location"}.issubset(set(finding["required"])))
        self.assertIn("station", schema["properties"])
        self.assertIn("firebase_sync", schema["properties"])
        self.assertEqual(example["detections"][0]["severity"], "UNASSESSED")

    def test_architecture_diagram_is_valid_svg(self):
        ET.parse(ROOT / "docs" / "inspection_workflow.svg")

    def test_dashboard_module_javascript_syntax(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed in this test environment")
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        match = re.search(r'<script\s+type="module"\s*>(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match, "Dashboard module script was not found")
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8", delete=False) as handle:
            handle.write(match.group(1))
            script_path = Path(handle.name)
        try:
            checked = subprocess.run([node, "--check", str(script_path)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
        finally:
            script_path.unlink(missing_ok=True)

    def test_dashboard_references_existing_elements_and_no_simulation_tools(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        declared = set(re.findall(r'\bid="([^"]+)"', html))
        referenced = set(re.findall(r'\$\("([^"]+)"\)', html))
        self.assertEqual(referenced - declared, set())
        self.assertIn('id="runButton"', html)
        self.assertIn("/api/run-inspection", html)
        for stale in ('id="service"', 'id="intro"', "applySimulation", "PASTE_"):
            self.assertNotIn(stale, html)

    def test_station_controller_invokes_complete_inspection_coordinator(self):
        controller = (ROOT / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        coordinator = (ROOT / "raspberry_pi" / "run_inspection.py").read_text(encoding="utf-8")
        self.assertIn("run_inspection.py", controller)
        self.assertIn("run_executorch.py", coordinator)
        self.assertIn("publish_event(event)", coordinator)

    def test_random_initialization_and_checkpoint_provenance_are_required(self):
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertIn("pretrained=False", exporter)
        self.assertIn("random_initialization_from_yolo_yaml", exporter)
        self.assertIn("verify_project_checkpoint", exporter)
        self.assertIn("VERIFIED_PROJECT_TRAINING", exporter)
        self.assertIn("project_training_provenance.json", exporter)
        self.assertIn("ONNX model SHA-256 does not match", detector)
        self.assertIn("pretrained_weights_used", detector)

    def test_dataset_importer_records_sources_reviews_hashes_and_group_splits(self):
        importer = (ROOT / "pcb_engine_kit" / "dataset.py").read_text(encoding="utf-8")
        for marker in (
            "source_name", "source_url", "license_or_permission",
            "rights_review_status", "annotation_review_status",
            "import_manifest_sha256", "source_image_sha256",
            "source_label_sha256", "groups_by_split",
            "COMPLETE_AS_DECLARED", "Duplicate image content",
        ):
            self.assertIn(marker, importer)
        self.assertIn("group", (ROOT / "datasets" / "import_manifest.example.csv").read_text(encoding="utf-8").splitlines()[0])
        self.assertNotIn("parse_deeppcb", importer)
        self.assertNotIn('annotation_format == "deeppcb"', importer)

    def test_dataset_and_checkpoint_audits_do_not_claim_missing_artifacts(self):
        dataset = json.loads((ROOT / "docs" / "results" / "project_dataset_audit.json").read_text(encoding="utf-8"))
        checkpoint = json.loads((ROOT / "docs" / "results" / "project_checkpoint_audit.json").read_text(encoding="utf-8"))
        release = json.loads((ROOT / "docs" / "results" / "project_release_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(dataset["status"], "NOT_PROVIDED")
        self.assertFalse(dataset["release_ready"])
        self.assertEqual(checkpoint["status"], "NOT_PROVIDED")
        self.assertFalse(checkpoint["release_ready"])
        self.assertFalse(release["release_ready"])
        audit_tool = (ROOT / "pcb_engine_kit" / "audit_release.py").read_text(encoding="utf-8")
        self.assertIn("checkpoint_sha256_matches", audit_tool)
        self.assertIn("original_source_image_and_label_hashes_match", audit_tool)
        self.assertIn("project_training_provenance.json", audit_tool)

    def test_project_validation_values_are_screenshot_only(self):
        metrics = json.loads((ROOT / "docs" / "results" / "project_validation_metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics["status"], "UNVERIFIED_VALIDATION_RESULT")
        self.assertEqual(metrics["overall_metrics_percent"]["precision"], 98.3)
        self.assertEqual(metrics["overall_metrics_percent"]["recall"], 98.4)
        self.assertEqual(metrics["overall_metrics_percent"]["map50"], 98.9)
        self.assertEqual(metrics["overall_metrics_percent"]["map50_95"], 62.5)
        self.assertFalse(metrics["independent_test_metrics_present"])
        self.assertFalse(metrics["checkpoint_dataset_provenance_complete"])
        self.assertEqual(
            metrics["source_evidence"]["original_sha256"],
            "e3e0bcf601d66d29163757287bf646ec18d6967ebc594688a169893c8cb02b0c",
        )

    def test_no_external_pcb_detector_or_external_benchmark_values_remain(self):
        provisioner = (ROOT / "scripts" / "provision_pi5.sh").read_text(encoding="utf-8")
        self.assertNotIn("download_sulojan_pcb_yolov8s.py", provisioner)
        self.assertNotIn("export-upstream-onnx", provisioner)
        dataset_importer = (ROOT / "pcb_engine_kit" / "dataset.py").read_text(encoding="utf-8")
        self.assertNotIn("parse_deeppcb", dataset_importer)
        self.assertIn("VERIFIED_PROJECT_TRAINING", provisioner)
        for path in (
            "docs/EXTERNAL_PCB_BENCHMARKS.md",
            "docs/REFERENCE_BENCHMARKS.md",
            "docs/PCB_UPSTREAM_BASELINE.md",
            "docs/results/published_pcb_benchmarks.json",
            "models/pretrained/download_sulojan_pcb_yolov8s.py",
            "models/pretrained/README.md",
        ):
            self.assertFalse((ROOT / path).exists(), path)
        performance_doc = (ROOT / "docs" / "LOCAL_EXECUTION_AND_PERFORMANCE.md").read_text(encoding="utf-8")
        self.assertNotIn("166.050 ms", performance_doc)
        self.assertNotIn("14.5 tokens/s", performance_doc)

    def test_release_manifest_is_truthful_about_artifact_status(self):
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["vision"]["checkpoint"]["present_in_repository"])
        self.assertFalse(manifest["vision"]["onnx"]["present_in_repository"])
        self.assertFalse(manifest["dataset"]["release_ready"])
        self.assertEqual(manifest["dataset"]["audit_status"], "NOT_PROVIDED")
        self.assertFalse(manifest["vision"]["external_pcb_detector_weights_used_by_current_provisioner"])
        self.assertFalse(manifest["advisory"]["trained_by_project_team"])
        self.assertFalse(manifest["hardware_and_application"]["offline_test_verified"])

    def test_pi_provisioning_requires_a_project_onnx_artifact(self):
        provisioner = (ROOT / "scripts" / "provision_pi5.sh").read_text(encoding="utf-8")
        runtime_test = (ROOT / "scripts" / "validate_pi5_runtime.py").read_text(encoding="utf-8")
        self.assertIn("models/best.onnx", provisioner)
        self.assertIn("models/best.onnx.json", provisioner)
        self.assertIn("dataset_audit_sha256", provisioner)
        self.assertIn("llama_main", runtime_test)
        self.assertIn("CPUExecutionProvider", runtime_test)

    def test_llama_is_disclosed_as_a_third_party_text_only_advisory(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        report = (ROOT / "docs" / "PROJECT_REPORT.md").read_text(encoding="utf-8").lower()
        runner = (ROOT / "llm_advisory" / "run_executorch.py").read_text(encoding="utf-8")
        self.assertIn("third-party foundation model", readme)
        self.assertIn("not trained by the project team", report)
        self.assertIn("TextLLMRunner", runner)
        self.assertNotIn("MultimodalRunner", runner)

    def test_onnx_parity_verifier_is_limited_to_full_held_out_test_split(self):
        parity = (ROOT / "pcb_engine_kit" / "compare_pt_onnx.py").read_text(encoding="utf-8")
        report = json.loads((ROOT / "docs" / "results" / "project_onnx_parity.json").read_text(encoding="utf-8"))
        self.assertIn("expected_test_dir", parity)
        self.assertIn("--mark-verified requires the full held-out test split", parity)
        self.assertIn("checkpoint_hash_matches_onnx_sidecar", parity)
        self.assertIn("dataset_audit_hash_matches_onnx_sidecar", parity)
        self.assertIn("prediction_parity_verified", parity)
        self.assertEqual(report["status"], "NOT_PROVIDED")

    def test_severity_policy_is_configured_and_provisional(self):
        policy = json.loads((ROOT / "models" / "severity_policy.json").read_text(encoding="utf-8"))
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertEqual(policy["status"], "PROVISIONAL_REQUIRES_BOARD_LEVEL_VALIDATION")
        self.assertIn("classify_severity(target_name, severity_policy)", detector)

    def test_pi_benchmarks_do_not_claim_accuracy_or_power(self):
        source = (ROOT / "raspberry_pi" / "benchmark_onnx.py").read_text(encoding="utf-8")
        self.assertIn('"measurement_type": "onnx_detector_runtime_only"', source)
        self.assertIn('"sha256": sha256_file(model_path)', source)
        self.assertIn('"power_watts": None', source)
        self.assertIn("It does not calculate precision, recall or mAP", source)


if __name__ == "__main__":
    unittest.main()
