import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llm_advisory"))
from prompt import build_prompt


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


if __name__ == "__main__":
    unittest.main()
