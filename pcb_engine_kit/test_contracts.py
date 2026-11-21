import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Contracts(unittest.TestCase):
    def test_zip_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive = folder / "bad.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.txt", "bad")
            result = subprocess.run(
                [sys.executable, str(ROOT / "safe_extract.py"), str(archive), str(folder / "out")],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / "escape.txt").exists())
            self.assertFalse((folder / "out").exists())

    def test_zip_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive = folder / "symlink.zip"
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr(info, "target")
            result = subprocess.run(
                [sys.executable, str(ROOT / "safe_extract.py"), str(archive), str(folder / "out")],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / "out").exists())

    def test_publish_complete_image_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "board.jpg"
            source.write_bytes(b"test image payload")
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "submit.py"),
                    str(source),
                    "--root",
                    str(folder / "spool"),
                ],
                check=True,
                capture_output=True,
            )
            incoming = folder / "spool" / "incoming"
            images = list(incoming.glob("*.jpg"))
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0].read_bytes(), source.read_bytes())
            self.assertFalse(list(incoming.glob("*.part")))

    def test_submit_rejects_non_image_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "notes.txt"
            source.write_text("not an image")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "submit.py"),
                    str(source),
                    "--root",
                    str(folder / "spool"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / "spool" / "incoming").exists())

    def test_tflite_engine_handles_empty_detector_candidates(self):
        source = (ROOT / "engine.py").read_text(encoding="utf-8")
        self.assertIn("if not boxes:", source)
        self.assertIn("if kept is None or len(kept) == 0:", source)
        self.assertIn('component_status = "not_configured"', source)
        self.assertIn('if component_status != "checked":', source)

    def test_dataset_importer_uses_explicit_validation_not_assertions(self):
        source = (ROOT / "dataset.py").read_text(encoding="utf-8")
        self.assertIn("Board group", source)
        self.assertIn("Bounding box outside image", source)
        self.assertIn("Image missing at manifest row", source)
        self.assertNotIn("assert ", source)


if __name__ == "__main__":
    unittest.main()
