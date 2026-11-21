import tempfile
import unittest
from pathlib import Path

from raspberry_pi.station_controller import StationRuntime


class DummyIllumination:
    def on(self):
        pass

    def off(self):
        pass


class StationWorkflowContractTests(unittest.TestCase):
    def make_runtime(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return StationRuntime(
            illumination=DummyIllumination(),
            camera_mode="usb",
            camera_index=0,
            model_path="models/best.onnx",
            output_dir=Path(temp.name),
            settle=0,
            confidence="0.25",
            iou="0.45",
            publish=False,
        )

    def test_hand_presence_arms_station_only_after_hold_callback(self):
        runtime = self.make_runtime()
        runtime.ir_pressed()
        self.assertEqual(runtime.snapshot()["state"], "ARMING")
        self.assertFalse(runtime.snapshot()["armed"])

        runtime.ir_held()
        self.assertEqual(runtime.snapshot()["state"], "ARMED_WAIT_RELEASE")
        self.assertTrue(runtime.snapshot()["armed"])

        runtime.ir_released()
        self.assertEqual(runtime.snapshot()["state"], "WAITING_FOR_BOARD")
        self.assertTrue(runtime.snapshot()["armed"])

    def test_short_sensor_activation_does_not_arm_station(self):
        runtime = self.make_runtime()
        runtime.ir_pressed()
        runtime.ir_released()
        self.assertEqual(runtime.snapshot()["state"], "WAITING_FOR_ARM")
        self.assertFalse(runtime.snapshot()["armed"])

    def test_run_command_is_rejected_until_capture_is_waiting_for_operator(self):
        runtime = self.make_runtime()
        accepted, message = runtime.start_inspection()
        self.assertFalse(accepted)
        self.assertIn("captured PCB frame", message)

    def test_controller_has_three_second_hold_and_pi_run_api(self):
        root = Path(__file__).resolve().parents[1]
        controller = (root / "raspberry_pi" / "station_controller.py").read_text(encoding="utf-8")
        dashboard = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn("hold_time=3.0", controller)
        self.assertIn("AWAITING_OPERATOR_RUN", controller)
        self.assertIn("/api/capture.jpg", controller)
        self.assertIn("/api/run-inspection", controller)
        self.assertIn('fetch("/api/run-inspection"', dashboard)
        self.assertIn("Run inspection on Raspberry Pi", dashboard)
        self.assertIn('id="annotatedImage"', dashboard)

    def test_detector_preprocessing_remains_three_channel_rgb(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "raspberry_pi" / "inspect_image.py").read_text(encoding="utf-8")
        self.assertIn("letterbox(image)", source)
        self.assertIn("cv2.COLOR_BGR2RGB", source)
        self.assertIn("rgb.astype(np.float32) / 255.0", source)
        self.assertNotIn("cv2.COLOR_BGR2GRAY", source)


if __name__ == "__main__":
    unittest.main()
