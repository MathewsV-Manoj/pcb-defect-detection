import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseAuditToolTests(unittest.TestCase):
    def test_missing_inputs_are_reported_as_blockers_not_as_a_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "results"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "pcb_engine_kit" / "audit_release.py"),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
            dataset = json.loads((output_dir / "project_dataset_audit.json").read_text(encoding="utf-8"))
            checkpoint = json.loads((output_dir / "project_checkpoint_audit.json").read_text(encoding="utf-8"))
            release = json.loads((output_dir / "project_release_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(dataset["status"], "NOT_PROVIDED")
            self.assertEqual(checkpoint["status"], "NOT_PROVIDED")
            self.assertFalse(release["release_ready"])
            self.assertEqual(release["evidence_status"]["held_out_test_metrics"], "NOT_PROVIDED")
            self.assertEqual(release["evidence_status"]["onnx_prediction_parity"], "NOT_PROVIDED")
            self.assertEqual(release["evidence_status"]["pi_runtime_smoke_test"], "NOT_RUN")
            self.assertEqual(release["evidence_status"]["physical_station_commissioning"], "NOT_VERIFIED")
            self.assertEqual(release["evidence_status"]["offline_operation"], "NOT_VERIFIED")
            self.assertEqual(release["evidence_status"]["demo_video_content_review"], "NOT_CONFIRMED")
            self.assertEqual(release["evidence_status"]["source_authorship_review"], "TEAM_ATTESTATION_REQUIRED")
            self.assertTrue(release["evidence_blockers"])


if __name__ == "__main__":
    unittest.main()
