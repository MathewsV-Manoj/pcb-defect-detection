import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class DatasetUtilityContracts(unittest.TestCase):
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

    def test_dataset_importer_uses_explicit_validation_not_assertions(self):
        source = (ROOT / "dataset.py").read_text(encoding="utf-8")
        self.assertIn("Board group", source)
        self.assertIn("Bounding box outside image", source)
        self.assertIn("Image missing at manifest row", source)
        self.assertNotIn("assert ", source)


if __name__ == "__main__":
    unittest.main()
