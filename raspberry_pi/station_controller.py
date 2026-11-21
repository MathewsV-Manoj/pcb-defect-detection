#!/usr/bin/env python3
"""Raspberry Pi station service: IR arm -> board capture -> operator-triggered inference.

The web dashboard is served by this process. The operator opens it from a laptop
on the same trusted LAN. The dashboard's Run Inspection button sends a request
back to this Raspberry Pi; inference is never executed in the browser.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
INSPECTION = ROOT / "raspberry_pi" / "run_inspection.py"
DASHBOARD = ROOT / "dashboard"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def required_gpio(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw.isdigit():
        raise RuntimeError(f"{name} must be set to the BCM GPIO number used by the actual wiring")
    pin = int(raw)
    if not 0 <= pin <= 27:
        raise RuntimeError(f"{name} must be a BCM GPIO in the range 0..27")
    return pin


class StationRuntime:
    """Thread-safe station state and inspection worker."""

    def __init__(self, illumination, camera_mode: str, camera_index: int,
                 model_path: str, output_dir: Path, settle: float,
                 confidence: str, iou: str, publish: bool):
        self.illumination = illumination
        self.camera_mode = camera_mode
        self.camera_index = camera_index
        self.model_path = model_path
        self.output_dir = output_dir
        self.settle = settle
        self.confidence = confidence
        self.iou = iou
        self.publish = publish
        self.lock = threading.RLock()
        self.capture_path: Path | None = None
        self.event_path: Path | None = None
        self.annotated_path: Path | None = None
        self.state = {
            "state": "WAITING_FOR_ARM",
            "message": "Hold your hand in front of the IR sensor for about 3 seconds to arm the station.",
            "armed": False,
            "busy": False,
            "board_id": None,
            "ir_sensor_status": "CLEAR",
            "illumination_status": "OFF",
            "camera_status": "READY",
            "capture_ready": False,
            "capture_time": None,
            "decision": None,
            "detections": [],
            "advisory": None,
            "inference_latency_ms": None,
            "error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def update(self, **changes) -> None:
        with self.lock:
            self.state.update(changes)
            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict:
        with self.lock:
            result = dict(self.state)
            result["capture_url"] = "/api/capture.jpg" if self.capture_path and self.capture_path.is_file() else None
            result["annotated_url"] = "/api/annotated.jpg" if self.annotated_path and self.annotated_path.is_file() else None
            return result

    def ir_pressed(self) -> None:
        """Arm once; subsequent sensor activations are PCB-at-camera triggers."""
        capture = False
        with self.lock:
            current = self.state["state"]
            self.state["ir_sensor_status"] = "DETECTED"

            if current == "WAITING_FOR_ARM" and not self.state["armed"]:
                self.state.update(
                    state="ARMING",
                    message="IR presence detected. Keep your hand in front of the sensor for 3 seconds.",
                    error=None,
                    capture_ready=False,
                )
            elif (
                self.state["armed"]
                and not self.state["busy"]
                and current in {
                    "WAITING_FOR_BOARD",
                    "COMPLETE",
                    "COMPLETE_SYNC_WARNING",
                    "VISION_COMPLETE_ADVISORY_INCOMPLETE",
                    "ERROR",
                }
            ):
                # Invalidate the previous board before starting the next capture.
                self.capture_path = None
                self.event_path = None
                self.annotated_path = None
                self.state.update(
                    state="CAPTURING",
                    busy=True,
                    message="PCB detected at the camera position. Illuminating and capturing the frame.",
                    board_id=None,
                    camera_status="CAPTURING",
                    capture_ready=False,
                    capture_time=None,
                    decision=None,
                    detections=[],
                    advisory=None,
                    inference_latency_ms=None,
                    result=None,
                    error=None,
                )
                capture = True

            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()

        if capture:
            threading.Thread(target=self._capture_worker, daemon=True).start()

    def ir_held(self) -> None:
        """Called by gpiozero after a continuous 3-second sensor activation."""
        with self.lock:
            if self.state["state"] != "ARMING":
                return
            self.state.update(
                state="ARMED_WAIT_RELEASE",
                armed=True,
                message="Station armed. Release the sensor, then place the PCB on the conveyor.",
            )
            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def ir_released(self) -> None:
        with self.lock:
            self.state["ir_sensor_status"] = "CLEAR"
            if self.state["state"] == "ARMED_WAIT_RELEASE":
                self.state.update(
                    state="WAITING_FOR_BOARD",
                    message="Station armed. The conveyor can bring the PCB to the camera position. Arming remains active for subsequent boards.",
                )
            elif self.state["state"] == "ARMING":
                self.state.update(
                    state="WAITING_FOR_ARM",
                    message="The sensor was released before 3 seconds. Hold your hand in front of it for about 3 seconds.",
                    armed=False,
                )
            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def _read_camera_frame(self):
        import cv2

        if self.camera_mode == "picamera2":
            try:
                from picamera2 import Picamera2
            except ImportError as exc:
                raise RuntimeError("Picamera2 is not installed for the selected CSI camera mode") from exc
            camera = Picamera2()
            try:
                camera.configure(camera.create_still_configuration(main={"format": "RGB888", "size": (1280, 960)}))
                camera.start()
                time.sleep(0.8)
                rgb = camera.capture_array()
                if rgb is None:
                    raise RuntimeError("CSI camera returned an empty frame")
                return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            finally:
                try:
                    camera.stop()
                finally:
                    camera.close()

        capture = cv2.VideoCapture(self.camera_index)
        try:
            if not capture.isOpened():
                raise RuntimeError(f"Cannot open USB camera index {self.camera_index}")
            # Discard an initial frame so automatic exposure can settle.
            capture.read()
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError("USB camera did not return an inspection frame")
            return frame
        finally:
            capture.release()

    def _capture_worker(self) -> None:
        now = datetime.now(timezone.utc)
        board_id = "PCB-" + now.strftime("%Y%m%dT%H%M%S-%f")
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", board_id)
        capture_path = self.output_dir / f"{safe_id}_capture.jpg"
        event_path = self.output_dir / f"{safe_id}.json"
        annotated_path = self.output_dir / f"{safe_id}_annotated.jpg"

        try:
            import cv2

            self.illumination.on()
            self.update(illumination_status="ON", camera_status="SETTLING")
            time.sleep(self.settle)
            self.update(camera_status="CAPTURING")
            frame = self._read_camera_frame()
            if not cv2.imwrite(str(capture_path), frame):
                raise RuntimeError(f"Could not save captured frame: {capture_path}")
            with self.lock:
                self.capture_path = capture_path
                self.event_path = event_path
                self.annotated_path = annotated_path
                self.state.update(
                    state="AWAITING_OPERATOR_RUN",
                    message="Frame captured. Review the image on this page, then run inspection on the Raspberry Pi.",
                    board_id=board_id,
                    camera_status="FRAME_READY",
                    capture_ready=True,
                    capture_time=datetime.now(timezone.utc).isoformat(),
                    decision=None,
                    detections=[],
                    advisory=None,
                    inference_latency_ms=None,
                    result=None,
                    busy=False,
                    illumination_status="OFF",
                )
                self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            self.update(
                state="ERROR",
                message="Image capture failed. Check camera, IR alignment and illumination hardware.",
                error=str(exc),
                camera_status="ERROR",
                capture_ready=False,
                result=None,
                busy=False,
                illumination_status="OFF",
            )
        finally:
            self.illumination.off()

    def start_inspection(self) -> tuple[bool, str]:
        with self.lock:
            if (
                self.state["state"] != "AWAITING_OPERATOR_RUN"
                or not self.capture_path
                or not self.capture_path.is_file()
            ):
                return False, "A captured PCB frame is not waiting for operator approval."
            if self.state["busy"]:
                return False, "An inspection is already running."
            self.state.update(
                state="RUNNING_INSPECTION",
                message="Inspection request received. The Raspberry Pi is running the vision and advisory pipelines.",
                busy=True,
                error=None,
            )
            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        threading.Thread(target=self._inspection_worker, daemon=True).start()
        return True, "Inspection started on the Raspberry Pi."

    def _inspection_worker(self) -> None:
        with self.lock:
            capture_path = self.capture_path
            event_path = self.event_path
            annotated_path = self.annotated_path
            board_id = self.state["board_id"]
        if not capture_path or not event_path or not annotated_path:
            self.update(state="ERROR", busy=False, error="Captured image paths are unavailable.")
            return

        model = Path(self.model_path).expanduser()
        if not model.is_absolute():
            model = ROOT / model
        env = os.environ.copy()
        env["PCB_STATION_CAPTURE"] = "1"
        env["PCB_IR_SENSOR_STATUS"] = "TRIGGERED"
        env["PCB_ILLUMINATION_STATUS"] = "ON_AT_CAPTURE"
        env["PCB_STATION_CAMERA_SOURCE"] = "picamera2" if self.camera_mode == "picamera2" else "usb_camera"

        command = [
            sys.executable, str(INSPECTION),
            "--source", str(capture_path),
            "--weights", str(model),
            "--board-id", str(board_id),
            "--conf", self.confidence,
            "--iou", self.iou,
            "--output", str(event_path),
            "--annotated", str(annotated_path),
        ]
        if self.publish:
            command.append("--publish")

        try:
            completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
            event = None
            if event_path.is_file():
                event = json.loads(event_path.read_text(encoding="utf-8"))
            if event is None:
                raise RuntimeError(
                    f"Inspection process exited with code {completed.returncode} without an event record."
                )

            advisory_runtime = event.get("advisory_runtime") or {}
            advisory_complete = advisory_runtime.get("status") == "COMPLETED"
            firebase_sync = event.get("firebase_sync") or {}

            if advisory_complete and completed.returncode == 0:
                state = "COMPLETE"
                message = "Vision inspection and on-device Llama advisory completed on the Raspberry Pi. The station remains armed for the next PCB."
                error = None
            elif advisory_complete and firebase_sync.get("status") == "FAILED":
                state = "COMPLETE_SYNC_WARNING"
                message = "Vision and Llama advisory completed. Firebase synchronization failed; the local inspection record is saved."
                error = firebase_sync.get("message")
            elif advisory_complete:
                state = "COMPLETE_SYNC_WARNING"
                message = "Vision and Llama advisory completed, but the inspection process reported an additional error."
                error = f"Inspection process returned code {completed.returncode}."
            else:
                state = "VISION_COMPLETE_ADVISORY_INCOMPLETE"
                message = "Vision result is available. The required ExecuTorch advisory did not complete."
                error = (event.get("advisory") or {}).get("message") if isinstance(event.get("advisory"), dict) else None

            self.update(
                state=state,
                message=message,
                busy=False,
                decision=event.get("decision"),
                detections=event.get("detections", []),
                advisory=event.get("advisory"),
                inference_latency_ms=event.get("inference_latency_ms"),
                result=event,
                error=error,
                camera_status="FRAME_PROCESSED",
            )
        except Exception as exc:
            self.update(
                state="ERROR",
                message="The Raspberry Pi could not complete the inspection request.",
                busy=False,
                error=str(exc),
            )

    def history(self) -> list[dict]:
        records = []
        for path in sorted(self.output_dir.glob("PCB-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.name.endswith("_advisory.json"):
                continue
            try:
                event = json.loads(path.read_text(encoding="utf-8"))
                records.append(event)
            except (OSError, json.JSONDecodeError):
                continue
            if len(records) >= 50:
                break
        return records


class StationHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_handler(runtime: StationRuntime):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PCBStation/1.0"

        def log_message(self, fmt, *args):
            print("[web] " + fmt % args, flush=True)

        def send_json(self, payload, status=200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_file(self, path: Path, content_type: str | None = None):
            if not path.is_file():
                self.send_json({"error": "Requested file is not available."}, 404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if path.suffix.lower() == ".html":
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
                )
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                return self.send_json({"ok": True, "service": "PCB Raspberry Pi station"})
            if path == "/api/status":
                return self.send_json(runtime.snapshot())
            if path == "/api/history":
                return self.send_json({"records": runtime.history()})
            if path == "/api/capture.jpg":
                with runtime.lock:
                    capture = runtime.capture_path
                return self.send_file(capture, "image/jpeg") if capture else self.send_json({"error": "No captured frame."}, 404)
            if path == "/api/annotated.jpg":
                with runtime.lock:
                    annotated = runtime.annotated_path
                return self.send_file(annotated, "image/jpeg") if annotated else self.send_json({"error": "No annotated image."}, 404)

            relative = "index.html" if path in {"", "/"} else unquote(path.lstrip("/"))
            target = (DASHBOARD / relative).resolve()
            root = DASHBOARD.resolve()
            if root not in target.parents and target != root:
                return self.send_json({"error": "Invalid path."}, 403)
            if not target.is_file():
                return self.send_json({"error": "Page not found."}, 404)
            import mimetypes
            return self.send_file(target, mimetypes.guess_type(target.name)[0] or "application/octet-stream")

        def do_POST(self):
            path = urlparse(self.path).path
            if path != "/api/run-inspection":
                return self.send_json({"error": "Unknown API endpoint."}, 404)

            # Consume the request body so a persistent HTTP connection remains usable.
            try:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                return self.send_json({"error": "Invalid Content-Length."}, 400)
            if content_length < 0 or content_length > 2048:
                self.close_connection = True
                return self.send_json({"error": "Request body is too large."}, 413)
            body = self.rfile.read(content_length) if content_length else b""
            if body:
                try:
                    json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self.send_json({"error": "Request body must be valid JSON."}, 400)

            # Reject cross-origin browser requests. The station UI calls this same-origin API.
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if origin and urlparse(origin).netloc.lower() != host.lower():
                return self.send_json({"error": "Cross-origin requests are not allowed."}, 403)

            ok, message = runtime.start_inspection()
            return self.send_json({"accepted": ok, "message": message}, 202 if ok else 409)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IR-triggered PCB station and Pi-hosted operator UI")
    parser.add_argument("--host", default=os.getenv("PCB_STATION_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PCB_STATION_PORT", "8080")))
    args = parser.parse_args()

    try:
        from gpiozero import Button, OutputDevice
    except ImportError:
        print("gpiozero is required on Raspberry Pi OS.", file=sys.stderr)
        return 2

    if not INSPECTION.is_file() or not (DASHBOARD / "index.html").is_file():
        print("Inspection coordinator or dashboard entry point is missing.", file=sys.stderr)
        return 2

    ir_pin = required_gpio("PCB_IR_GPIO")
    led_pin = required_gpio("PCB_LED_DRIVER_GPIO")
    if ir_pin == led_pin:
        raise RuntimeError("IR sensor and LED driver must use different GPIO pins")

    ir_active_low = env_bool("PCB_IR_ACTIVE_LOW", True)
    pull_setting = os.getenv("PCB_IR_PULL_UP", "off").strip().lower()
    pull_up = True if pull_setting == "on" else False if pull_setting == "off" else None
    led_active_high = not env_bool("PCB_LED_DRIVER_ACTIVE_LOW", False)

    camera_mode = os.getenv("PCB_CAMERA_MODE", "usb").strip().lower()
    if camera_mode not in {"usb", "picamera2"}:
        raise RuntimeError("PCB_CAMERA_MODE must be 'usb' or 'picamera2'")
    camera_index_text = os.getenv("PCB_CAMERA_INDEX", "0").strip()
    if camera_mode == "usb" and not camera_index_text.isdigit():
        raise RuntimeError("PCB_CAMERA_INDEX must be a non-negative integer")
    camera_index = int(camera_index_text) if camera_index_text.isdigit() else 0

    output_dir = Path(os.getenv("PCB_OUTPUT_DIR", "inspection_runs")).expanduser()
    output_dir = output_dir if output_dir.is_absolute() else ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    settle = float(os.getenv("PCB_ILLUMINATION_SETTLE_SECONDS", "0.35"))
    confidence = os.getenv("PCB_CONFIDENCE_THRESHOLD", "0.25")
    iou = os.getenv("PCB_NMS_IOU_THRESHOLD", "0.45")
    publish = env_bool("PCB_FIREBASE_PUBLISH", False)
    if settle < 0:
        raise RuntimeError("PCB_ILLUMINATION_SETTLE_SECONDS must be non-negative")

    illumination = OutputDevice(led_pin, active_high=led_active_high, initial_value=False)
    runtime = StationRuntime(
        illumination=illumination,
        camera_mode=camera_mode,
        camera_index=camera_index,
        model_path=os.getenv("PCB_MODEL_PATH", "models/best.onnx"),
        output_dir=output_dir,
        settle=settle,
        confidence=confidence,
        iou=iou,
        publish=publish,
    )

    sensor = Button(
        ir_pin,
        pull_up=pull_up,
        active_state=not ir_active_low,
        bounce_time=0.12,
        hold_time=3.0,
        hold_repeat=False,
    )
    sensor.when_pressed = runtime.ir_pressed
    sensor.when_held = runtime.ir_held
    sensor.when_released = runtime.ir_released
    illumination.off()

    server = StationHTTPServer((args.host, args.port), make_handler(runtime))
    print(f"[station] IR GPIO BCM {ir_pin}; LED driver GPIO BCM {led_pin}; camera={camera_mode}", flush=True)
    print("[station] At session start, hold hand in front of IR sensor for 3 seconds once, then release to arm the station.", flush=True)
    print(f"[station] Operator UI: http://<RASPBERRY_PI_IP>:{args.port}/", flush=True)
    print("[station] Use the dashboard's Run Inspection button after the captured frame is reviewed.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[station] Shutting down.", flush=True)
    finally:
        server.server_close()
        sensor.close()
        illumination.off()
        illumination.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Station controller failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
