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

        pi_source = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertIn('CLASS_NAMES = ["missing_hole", "open_circuit", "short_circuit"]', pi_source)

        converter = (ROOT / "pcb_engine_kit" / "dataset.py").read_text(encoding="utf-8")
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        self.assertIn("NAMES=['missing_hole','open_circuit','short_circuit']", converter)
        self.assertIn('CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]', exporter)

    def test_event_schema_and_example_have_required_finding_fields(self):
        schema = json.loads((ROOT / "schemas" / "inspection-event.schema.json").read_text(encoding="utf-8"))
        example = json.loads((ROOT / "schemas" / "example-event.json").read_text(encoding="utf-8"))
        finding = schema["properties"]["detections"]["items"]
        self.assertTrue({"class_name", "confidence", "bbox_xyxy", "severity", "location"}.issubset(
            set(finding["required"])
        ))
        self.assertIn("station", schema["properties"])
        self.assertIn("firebase_sync", schema["properties"])
        self.assertEqual(example["detections"][0]["severity"], "UNASSESSED")
        self.assertIn("center_normalized", example["detections"][0]["location"])

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

    def test_dashboard_distinguishes_pending_inspection_from_no_defect_result(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Inspection has not been run for this captured frame.", html)
        self.assertIn("No configured target defects detected in this frame.", html)
        self.assertIn('status.state==="RUNNING_INSPECTION"', html)

    def test_dashboard_javascript_references_existing_elements(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        declared = set(re.findall(r'\bid="([^"]+)"', html))
        referenced = set(re.findall(r'\$\("([^"]+)"\)', html))
        self.assertEqual(referenced - declared, set(), "Dashboard JavaScript references missing element IDs")

    def test_pi_onnx_benchmark_reports_runtime_only_and_model_identity(self):
        source = (ROOT / "raspberry_pi" / "benchmark_onnx.py").read_text(encoding="utf-8")
        self.assertIn('"measurement_type": "onnx_detector_runtime_only"', source)
        self.assertIn('"sha256": sha256_file(model_path)', source)
        self.assertIn('"total_p95"', source)
        self.assertIn('"power_watts": None', source)
        self.assertIn("It does not calculate precision, recall or mAP", source)

    def test_dashboard_exposes_station_and_review_fields_without_demo_tools(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        for marker in (
            'id="irStatus"', 'id="ledStatus"', 'id="captureArea"', 'id="runButton"',
            'id="annotatedImage"', "<th>SEVERITY</th>", "<th>LOCATION</th>", "/api/run-inspection",
        ):
            self.assertIn(marker, html)
        for stale in ('id="service"', 'id="intro"', "applySimulation", "PASTE_"):
            self.assertNotIn(stale, html)

    def test_station_controller_invokes_complete_inspection_coordinator(self):
        controller = (ROOT / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        coordinator = (ROOT / "raspberry_pi" / "run_inspection.py").read_text(encoding="utf-8")
        self.assertIn("run_inspection.py", controller)
        self.assertIn("run_executorch.py", coordinator)
        self.assertIn("publish_event(event)", coordinator)

    def test_onnx_detector_runs_nms_separately_for_each_class(self):
        source = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertIn("for source_id, source_name in enumerate(model_class_names):", source)
        self.assertIn("positions = np.flatnonzero(class_ids == source_id)", source)
        self.assertIn("target_name = target_class_map.get(source_name)", source)
        self.assertIn("class_boxes = [boxes[int(position)] for position in positions]", source)
        self.assertNotIn("NMSBoxes(boxes, scores.tolist()", source)
        self.assertIn("len(session.get_outputs()) != 1", source)

    def test_exporter_produces_only_pi_onnx_path(self):
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        self.assertIn('"export-onnx"', exporter)
        self.assertIn('format="onnx"', exporter)
        self.assertIn('nms=False', exporter)

    def test_release_manifest_contains_only_configured_deployment_path(self):
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["vision"]["runtime"], "ONNX Runtime CPU on Raspberry Pi 5")
        self.assertFalse(manifest["advisory"]["model_package_present"])
        self.assertTrue(manifest["advisory"]["required_for_challenge"])

    def test_text_only_llama_uses_text_llm_runner_and_chat_template(self):
        runner = (ROOT / "llm_advisory" / "run_executorch.py").read_text(encoding="utf-8")
        prompt = (ROOT / "llm_advisory" / "prompt.py").read_text(encoding="utf-8")
        self.assertIn("TextLLMRunner", runner)
        self.assertIn("runner.generate(prompt, config, token_callback, stats_callback)", runner)
        self.assertNotIn("MultimodalRunner", runner)
        self.assertIn("<|begin_of_text|>", prompt)
        self.assertIn("<|start_header_id|>assistant<|end_header_id|>", prompt)

    def test_station_api_reads_post_body_and_checks_browser_origin(self):
        controller = (ROOT / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        self.assertIn("self.rfile.read(content_length)", controller)
        self.assertIn("Cross-origin requests are not allowed", controller)
        self.assertIn("COMPLETE_SYNC_WARNING", controller)

    def test_station_image_and_result_are_reset_for_each_new_board(self):
        controller = (ROOT / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        self.assertIn("self.capture_path = None", controller)
        self.assertIn("result=None", controller)
        self.assertIn('"COMPLETE"', controller)


    def test_llama_model_and_execu_torch_pi5_deployment_are_pinned_and_required(self):
        downloader = (ROOT / "llm_advisory" / "download_model.py").read_text(encoding="utf-8")
        build = (ROOT / "llm_advisory" / "build_pi5_runner.sh").read_text(encoding="utf-8")
        runner = (ROOT / "llm_advisory" / "run_executorch.py").read_text(encoding="utf-8")
        coordinator = (ROOT / "raspberry_pi" / "run_inspection.py").read_text(encoding="utf-8")
        env_example = (ROOT / "raspberry_pi" / ".env.example").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET", downloader)
        self.assertIn("911221e0f49d3354cbd4697a9c09feee25cadec7", downloader)
        self.assertIn("Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte", downloader)
        self.assertIn("tokenizer.model", downloader)
        self.assertIn("setup-local-sysroot.sh", build)
        self.assertIn("985c1ceccc8bb8b6a32294f71aeb5d2f299562f7", build)
        self.assertIn('EXECUTORCH_SYSROOT:-/', build)
        self.assertIn("llama_main", build)
        self.assertIn("executorch_cpp_llama_main", runner)
        self.assertIn('"--prompt=', runner)
        self.assertIn('env_bool("PCB_LLAMA_REQUIRED", True)', coordinator)
        self.assertIn("PCB_LLAMA_REQUIRED=true", env_example)
        self.assertTrue(manifest["advisory"]["required_for_challenge"])
        self.assertTrue(manifest["advisory"]["deployment_recipe_present"])
        self.assertFalse(manifest["advisory"]["model_package_present"])
        self.assertIn("models/llama/*", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_attributed_pretrained_pcb_model_contract_and_class_mapping(self):
        downloader = (ROOT / "models" / "pretrained" / "download_sulojan_pcb_yolov8s.py").read_text(encoding="utf-8")
        provenance = (ROOT / "docs" / "PCB_UPSTREAM_BASELINE.md").read_text(encoding="utf-8")
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("Sulojan/pcb-defect-yolov8s", downloader)
        self.assertIn("1acd655ce93a474f0ed00958ddd1079afb46c74868f916af6187bf63dad5bb3d", downloader)
        self.assertIn("publisher", provenance.lower())
        self.assertIn("not a model trained by the current project team", provenance.lower())
        self.assertIn("export-upstream-onnx", exporter)
        self.assertIn('"short": "short_circuit"', exporter)
        self.assertIn("attribute_count = 4 + len(model_class_names)", detector)
        self.assertIn("source_model_class_order", detector)
        self.assertTrue(manifest["external_pretrained_baseline"]["metrics_are_upstream_not_project_results"])
        self.assertEqual(
            manifest["external_pretrained_baseline"]["target_mapping"],
            {"missing_hole": "missing_hole", "open_circuit": "open_circuit", "short": "short_circuit"},
        )

    def test_local_execution_claims_match_runtime_configuration(self):
        local_doc = (ROOT / "docs" / "LOCAL_EXECUTION_AND_PERFORMANCE.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        report = (ROOT / "docs" / "PROJECT_REPORT.md").read_text(encoding="utf-8")
        env_example = (ROOT / "raspberry_pi" / ".env.example").read_text(encoding="utf-8")
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        llama = (ROOT / "llm_advisory" / "run_executorch.py").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))

        self.assertIn('providers=["CPUExecutionProvider"]', detector)
        self.assertIn("executorch_cpp_llama_main", llama)
        self.assertIn("PCB_FIREBASE_PUBLISH=false", env_example)
        self.assertIn("cloud api", readme.lower())
        self.assertIn("Firebase synchronization is disabled by default", report)
        self.assertFalse(manifest["local_execution"]["remote_inference_api_configured"])
        self.assertFalse(manifest["local_execution"]["runtime_internet_required_for_inference"])
        self.assertFalse(manifest["local_execution"]["offline_validation_completed"])
        self.assertFalse(manifest["local_execution"]["firebase_record_sync"]["default_enabled"])

    def test_severity_policy_is_configured_and_provisional(self):
        policy = json.loads((ROOT / "models" / "severity_policy.json").read_text(encoding="utf-8"))
        detector = (ROOT / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertEqual(policy["status"], "PROVISIONAL_REQUIRES_BOARD_LEVEL_VALIDATION")
        self.assertEqual(policy["rules"]["missing_hole"]["severity"], "MEDIUM")
        self.assertEqual(policy["rules"]["open_circuit"]["severity"], "HIGH")
        self.assertEqual(policy["rules"]["short_circuit"]["severity"], "HIGH")
        self.assertIn("classify_severity(target_name, severity_policy)", detector)
        self.assertIn('"severity_policy": {', detector)

    def test_one_command_pi_provisioning_is_documented(self):
        provisioner = (ROOT / "scripts" / "provision_pi5.sh").read_text(encoding="utf-8")
        runtime_test = (ROOT / "scripts" / "validate_pi5_runtime.py").read_text(encoding="utf-8")
        launcher = (ROOT / "scripts" / "run_station_pi5.sh").read_text(encoding="utf-8")
        self.assertIn("download_sulojan_pcb_yolov8s.py", provisioner)
        self.assertIn("export-upstream-onnx", provisioner)
        self.assertIn("download_model.py", provisioner)
        self.assertIn("build_pi5_runner.sh", provisioner)
        self.assertIn("CPUExecutionProvider", runtime_test)
        self.assertIn("llama_main", runtime_test)
        self.assertIn("station_controller.py", launcher)

    def test_accuracy_report_uses_macro_f1_and_exposes_test_support(self):
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        self.assertIn('"f1": macro_f1', exporter)
        self.assertIn('"harmonic_mean_of_macro_precision_recall": harmonic_macro_pr', exporter)
        self.assertIn('"test_ground_truth_instances"', exporter)
        self.assertIn('"test_ground_truth_images"', exporter)
        self.assertIn('f1_values = floats(getattr(box, "f1", []))', exporter)
        self.assertIn('"classes_without_test_annotations"', exporter)
        self.assertIn('"minimum_confidence_for_precision_recall_curve": args.val_conf', exporter)
        self.assertIn('"nms_iou": args.val_iou', exporter)
        self.assertIn('"audit_sha256": dataset_audit_sha', exporter)
        self.assertNotIn('"f1": overall_f1', exporter)

    def test_pi_dependencies_cover_python_313_arm64_install_path(self):
        train = (ROOT / "pcb_engine_kit" / "requirements-train.txt").read_text(encoding="utf-8")
        export = (ROOT / "pcb_engine_kit" / "requirements-export.txt").read_text(encoding="utf-8")
        runtime = (ROOT / "raspberry_pi" / "requirements.txt").read_text(encoding="utf-8")
        provisioner = (ROOT / "scripts" / "provision_pi5.sh").read_text(encoding="utf-8")
        self.assertIn('numpy==1.26.4; python_version < "3.13"', train)
        self.assertIn('numpy==2.2.6; python_version >= "3.13"', train)
        self.assertIn('numpy>=2.0,<3; python_version >= "3.13"', runtime)
        self.assertIn("onnx==1.19.0", export)
        self.assertIn('"$PYTHON" -m pip check', provisioner)
        self.assertIn("import onnxruntime as ort", provisioner)
        self.assertIn('"CPUExecutionProvider" not in providers', provisioner)

    def test_published_pcb_benchmarks_are_cited_and_not_project_accuracy(self):
        document = (ROOT / "docs" / "EXTERNAL_PCB_BENCHMARKS.md").read_text(encoding="utf-8")
        data = json.loads((ROOT / "docs" / "results" / "published_pcb_benchmarks.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "models" / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertIn("not measurements from this project", document.lower())
        self.assertIn("DeepPCB", document)
        self.assertIn("PKU-Market-PCB", document)
        self.assertTrue(data["project_validation_metrics_reported"])
        self.assertFalse(data["project_test_accuracy_claimed"])
        mbbi = next(row for row in data["benchmarks"] if row["model"] == "YOLO-MBBi")
        self.assertEqual(mbbi["per_class"]["open"]["project_class_mapping"], "open_circuit")
        self.assertEqual(mbbi["per_class"]["short"]["project_class_mapping"], "short_circuit")
        self.assertEqual(mbbi["per_class"]["pin_hole"]["project_class_mapping"], "NOT_EQUIVALENT_TO_missing_hole")
        sulojan = next(row for row in data["benchmarks"] if row["authors"] == "Sulojan Rajkumar")
        self.assertEqual(sulojan["per_class"]["missing_hole"]["map50_percent"], 99.5)
        self.assertEqual(sulojan["per_class"]["short"]["project_class_mapping"], "short_circuit")
        project = data["project_results"]
        self.assertEqual(project["status"], "REPORTED_VALIDATION_SCREENSHOT_NOT_INDEPENDENT_TEST")
        self.assertEqual(project["evaluation_split"], "validation")
        self.assertEqual(project["precision_percent"], 98.3)
        self.assertEqual(project["recall_percent"], 98.4)
        self.assertEqual(project["map50_percent"], 98.9)
        self.assertEqual(project["map50_95_percent"], 62.5)
        self.assertEqual(project["per_class"]["missing_hole"]["map50_percent"], 98.5)
        self.assertEqual(project["per_class"]["open_circuit"]["map50_percent"], 99.5)
        self.assertEqual(project["per_class"]["short_circuit"]["map50_percent"], 98.8)
        self.assertIsNone(project["unavailable_run_metadata"]["checkpoint_sha256"])
        self.assertEqual(manifest["performance"]["external_pcb_benchmarks_document"], "docs/EXTERNAL_PCB_BENCHMARKS.md")
        self.assertTrue(manifest["performance"]["project_validation_metrics_present"])
        self.assertFalse(manifest["performance"]["project_test_accuracy_metrics_present"])
        self.assertFalse(manifest["performance"]["external_pcb_benchmarks_are_project_results"])
        vision_metrics = manifest["vision"]["metrics"]
        self.assertEqual(vision_metrics["split"], "validation")
        self.assertEqual(vision_metrics["map50_percent"], 98.9)
        self.assertEqual(vision_metrics["map50_95_percent"], 62.5)
        self.assertFalse(vision_metrics["independent_test_metrics_present"])
        self.assertFalse(vision_metrics["reproduced_from_raw_evaluator_output"])
        validation_note = (ROOT / "docs" / "results" / "PROJECT_VALIDATION_RESULTS.md").read_text(encoding="utf-8")
        self.assertIn("validation metrics", validation_note.lower())
        self.assertIn("not an independently held-out test result", validation_note.lower())
        self.assertIn("e3e0bcf601d66d29163757287bf646ec18d6967ebc594688a169893c8cb02b0c", data["project_results"]["validation_source_image"]["sha256"])
        checklist = (ROOT / "docs" / "PHASE1_SUBMISSION_CHECKLIST.md").read_text(encoding="utf-8")
        self.assertIn("23 November 2026", checklist)
        self.assertIn("original-work", checklist.lower())

    def test_external_benchmarks_are_explicitly_separate_from_project_measurements(self):
        reference = (ROOT / "docs" / "REFERENCE_BENCHMARKS.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "raspberry_pi" / "benchmark_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("not project results", reference.lower())
        self.assertIn("166.050 ms", reference)
        self.assertIn("14.5 tokens/s", reference)
        self.assertIn('"measurement_type": "still_image_vision_plus_executorch_advisory_pipeline"', pipeline)
        self.assertIn('"power_watts": None', pipeline)
        self.assertIn("physical camera", pipeline)


if __name__ == "__main__":
    unittest.main()
