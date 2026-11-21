import json
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llm_advisory"))
from prompt import build_prompt
from run_executorch import parse_advisory_json, validate_advisory


class AdvisoryPromptContractTests(unittest.TestCase):
    def test_prompt_contains_structured_findings(self):
        event = {
            "board_id": "PCB-TEST-01",
            "timestamp": "2026-11-21T10:00:00+05:30",
            "detections": [
                {
                    "class_name": "open_circuit",
                    "confidence": 0.82,
                    "severity": "UNASSESSED",
                    "location": {
                        "bbox_xyxy": [10, 20, 50, 80],
                        "center_normalized": [0.25, 0.5],
                    },
                }
            ],
        }
        prompt = build_prompt(event)
        self.assertIn("open_circuit", prompt)
        self.assertIn("UNASSESSED", prompt)
        self.assertIn("center_normalized", prompt)
        self.assertIn("Do not infer severity from confidence", prompt)

    def test_prompt_does_not_include_image_payload(self):
        event = {
            "board_id": "PCB-TEST-02",
            "detections": [],
            "image": "private-frame-payload",
            "image_path": "/tmp/private-frame.jpg",
        }
        prompt = build_prompt(event)
        self.assertNotIn("private-frame-payload", prompt)
        self.assertNotIn("/tmp/private-frame.jpg", prompt)
        self.assertNotIn('"image"', prompt)
        self.assertNotIn('"image_path"', prompt)

    def test_advisory_response_parser_accepts_valid_json_and_fenced_json(self):
        value = {
            "explanation": "A conductive track discontinuity was detected.",
            "recommended_actions": ["Inspect the localized track region."],
            "severity_note": "Severity is unassessed; request human review.",
            "log_entry": "PCB-TEST-04: open circuit finding requires review.",
        }
        raw = json.dumps(value)
        self.assertEqual(validate_advisory(parse_advisory_json(raw)), value)
        self.assertEqual(validate_advisory(parse_advisory_json("```json" + chr(10) + raw + chr(10) + "```")), value)

    def test_advisory_response_rejects_missing_or_wrongly_typed_fields(self):
        with self.assertRaises(RuntimeError):
            validate_advisory({"explanation": "Only a partial response"})
        with self.assertRaises(RuntimeError):
            validate_advisory({
                "explanation": "Finding.",
                "recommended_actions": "Not a list",
                "severity_note": "Review.",
                "log_entry": "Logged.",
            })

    def test_prompt_uses_llama_3_instruct_roles_and_read_only_evidence(self):
        prompt = build_prompt({"board_id": "PCB-TEST-03", "detections": []})
        self.assertTrue(prompt.startswith("<|begin_of_text|>"))
        self.assertIn("<|start_header_id|>system<|end_header_id|>", prompt)
        self.assertIn("<|start_header_id|>user<|end_header_id|>", prompt)
        self.assertTrue(prompt.endswith("<|start_header_id|>assistant<|end_header_id|>\n"))
        self.assertIn("read-only evidence", prompt)


if __name__ == "__main__":
    unittest.main()
