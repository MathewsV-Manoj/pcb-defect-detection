import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

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
        worker = (ROOT / "pcb_engine_kit" / "engine.py").read_text(encoding="utf-8")
        self.assertIn("NAMES=['missing_hole','open_circuit','short_circuit']", converter)
        self.assertIn('CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]', exporter)
        self.assertIn('CLASS_ORDER = ["missing_hole", "open_circuit", "short_circuit"]', worker)

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
        self.assertIn("for cid in range(len(CLASS_NAMES)):", source)
        self.assertIn("positions = np.flatnonzero(class_ids == cid)", source)
        self.assertIn("class_boxes = [boxes[int(position)] for position in positions]", source)
        self.assertNotIn("NMSBoxes(boxes, scores.tolist()", source)
        self.assertIn("len(session.get_outputs()) != 1", source)

    def test_exporter_produces_pi_onnx_and_supplementary_tflite(self):
        exporter = (ROOT / "pcb_engine_kit" / "train_export.py").read_text(encoding="utf-8")
        self.assertIn('"export-onnx"', exporter)
        self.assertIn('"export-tflite"', exporter)
        self.assertIn('format="onnx"', exporter)
        self.assertIn('nms=False', exporter)
        self.assertIn('"best.onnx"', exporter)
        self.assertIn('"detector.tflite"', exporter)

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
        self.assertIn('self.capture_path = None', controller)
        self.assertIn('result=None', controller)
        self.assertIn('"COMPLETE"', controller)


if __name__ == "__main__":
    unittest.main()
