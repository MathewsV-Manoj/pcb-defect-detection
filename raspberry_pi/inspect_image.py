#!/usr/bin/env python3
"""One-image/one-frame YOLOv8 ONNX inference for the 3-class PCB detector."""
from __future__ import annotations
import argparse, json, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort

CLASS_NAMES = ["missing_hole", "open_circuit", "short_circuit"]
SIZE = 640

def letterbox(image, size=SIZE):
    h, w = image.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    dw, dh = size - nw, size - nh
    left, right = int(round(dw / 2 - 0.1)), int(round(dw / 2 + 0.1))
    top, bottom = int(round(dh / 2 - 0.1)), int(round(dh / 2 + 0.1))
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                cv2.BORDER_CONSTANT, value=(114,114,114))
    return padded, scale, (left, top)

def decode(output, original_shape, scale, pad, conf=0.25, iou=0.45):
    pred = np.squeeze(np.asarray(output))
    if pred.ndim != 2:
        raise RuntimeError(f"Unexpected YOLO output rank/shape: {pred.shape}")
    if pred.shape[0] == 7:
        pred = pred.T
    elif pred.shape[1] != 7:
        raise RuntimeError(f"Expected 7 values per anchor (4 boxes + 3 classes), got {pred.shape}")
    if not np.isfinite(pred).all():
        raise RuntimeError("ONNX output contains NaN/Inf")
    xywh = pred[:, :4]
    class_scores = pred[:, 4:7]
    class_ids = class_scores.argmax(axis=1)
    scores = class_scores.max(axis=1)
    keep = scores >= conf
    xywh, scores, class_ids = xywh[keep], scores[keep], class_ids[keep]
    if not len(scores):
        return []
    boxes = [[int(cx-bw/2), int(cy-bh/2), int(bw), int(bh)] for cx,cy,bw,bh in xywh]
    indices = cv2.dnn.NMSBoxes(boxes, scores.tolist(), conf, iou)
    if indices is None or len(indices) == 0:
        return []
    indices = np.asarray(indices).reshape(-1)
    h, w = original_shape
    px, py = pad
    found = []
    for i in indices:
        cx,cy,bw,bh = xywh[i]
        x1 = float(np.clip((cx-bw/2-px)/scale, 0, w-1))
        y1 = float(np.clip((cy-bh/2-py)/scale, 0, h-1))
        x2 = float(np.clip((cx+bw/2-px)/scale, 0, w-1))
        y2 = float(np.clip((cy+bh/2-py)/scale, 0, h-1))
        cid = int(class_ids[i])
        found.append({"class_id":cid, "class_name":CLASS_NAMES[cid],
                      "confidence":float(scores[i]),
                      "bbox_xyxy":[round(x1,2),round(y1,2),round(x2,2),round(y2,2)]})
    return found

def read_frame(args):
    if args.source:
        frame = cv2.imread(args.source)
        if frame is None: raise RuntimeError(f"Cannot read {args.source}")
        return frame, "IMAGE_INFERENCE"
    if args.picamera2:
        try: from picamera2 import Picamera2
        except ImportError as exc: raise RuntimeError("Install python3-picamera2 from Raspberry Pi OS") from exc
        cam = Picamera2()
        cam.configure(cam.create_still_configuration(main={"format":"RGB888","size":(1280,960)}))
        cam.start(); time.sleep(1); rgb = cam.capture_array(); cam.stop()
        if rgb is None: raise RuntimeError("No frame from Picamera2")
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), "LIVE"
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened(): raise RuntimeError(f"Cannot open camera index {args.camera}")
    ok, frame = cap.read(); cap.release()
    if not ok or frame is None: raise RuntimeError("Camera returned no frame")
    return frame, "LIVE"

def main():
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--source")
    src.add_argument("--camera", type=int)
    src.add_argument("--picamera2", action="store_true")
    p.add_argument("--weights", default="models/best.onnx")
    p.add_argument("--board-id")
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.45)
    p.add_argument("--output", default="inspection_result.json")
    p.add_argument("--annotated", default="inspection_annotated.jpg")
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    if not Path(args.weights).is_file(): p.error(f"Model missing: {args.weights}")
    if not (0 <= args.conf <= 1 and 0 <= args.iou <= 1): p.error("conf/iou must be in [0,1]")
    try:
        image, source_type = read_frame(args)
        session = ort.InferenceSession(args.weights, providers=["CPUExecutionProvider"])
        inp = session.get_inputs()
        if len(inp) != 1: raise RuntimeError("Expected one ONNX input")
        meta = inp[0]
        if len(meta.shape) != 4: raise RuntimeError(f"Expected rank-4 input, got {meta.shape}")
        if meta.shape[1] not in (3, "3", None): raise RuntimeError(f"Expected NCHW input [1,3,640,640], got {meta.shape}")
        padded, scale, pad = letterbox(image)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        tensor = (rgb.astype(np.float32)/255.0).transpose(2,0,1)[None]
        t0 = time.perf_counter()
        outputs = session.run(None, {meta.name:tensor})
        latency = (time.perf_counter()-t0)*1000
        if not outputs: raise RuntimeError("ONNX returned no output")
        detections = decode(outputs[0], image.shape[:2], scale, pad, args.conf, args.iou)
        now = datetime.now(timezone.utc)
        board_id = args.board_id or f"PCB-{now.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
        event = {
            "record_id":f"{board_id}-{uuid.uuid4().hex[:8]}",
            "board_id":board_id, "timestamp":now.isoformat(),
            "decision":"REVIEW" if detections else "NO_TARGET_DEFECT_DETECTED",
            "source":source_type, "model_file":Path(args.weights).name,
            "model_class_order":CLASS_NAMES, "input_size":[SIZE,SIZE],
            "confidence_threshold":args.conf, "nms_iou_threshold":args.iou,
            "inference_latency_ms":round(latency,2), "detections":detections,
            "advisory":None,
            "note":"No target defect detected is not proof of a defect-free PCB."
        }
        for d in detections:
            x1,y1,x2,y2 = map(int,d["bbox_xyxy"])
            cv2.rectangle(image,(x1,y1),(x2,y2),(0,80,255),2)
            cv2.putText(image,f"{d['class_name']} {d['confidence']:.2f}",
                        (x1,max(20,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,80,255),1)
        cv2.imwrite(args.annotated,image)
        Path(args.output).write_text(json.dumps(event,indent=2)+"\n",encoding="utf-8")
        if args.publish:
            from firebase_client import publish_event
            publish_event(event)
        print(json.dumps(event,indent=2))
        print(f"Annotated image: {args.annotated}; event: {args.output}")
        return 0
    except Exception as exc:
        print(f"Inspection failed: {exc}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
