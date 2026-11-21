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
        self.assertIn("['missing_hole','open_circuit','short_circuit']", exporter)
        self.assertIn("['missing_hole','open_circuit','short_circuit']", worker)

    def test_event_schema_and_example_have_required_finding_fields(self):
        schema = json.loads((ROOT / "schemas" / "inspection-event.schema.json").read_text(encoding="utf-8"))
        example = json.loads((ROOT / "schemas" / "example-event.json").read_text(encoding="utf-8"))
        finding = schema["properties"]["detections"]["items"]
        self.assertTrue({"class_name", "confidence", "bbox_xyxy", "severity", "location"}.issubset(
            set(finding["required"])
        ))
        self.assertIn("station", schema["properties"])
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

    def test_dashboard_exposes_station_and_review_fields_without_demo_tools(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        for marker in ("id=\"irStatus\"", "id=\"ledStatus\"", "<th>SEVERITY</th>", "<th>LOCATION</th>"):
            self.assertIn(marker, html)
        for stale in ('id="service"', 'id="intro"', "applySimulation", "PASTE_"):
            self.assertNotIn(stale, html)

    def test_station_controller_invokes_complete_inspection_coordinator(self):
        controller = (ROOT / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        coordinator = (ROOT / "raspberry_pi" / "run_inspection.py").read_text(encoding="utf-8")
        self.assertIn('run_inspection.py', controller)
        self.assertIn('run_executorch.py', coordinator)
        self.assertIn('publish_event(event)', coordinator)


if __name__ == "__main__":
    unittest.main()
