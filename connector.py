"""
FlowSense connector - local edge detection for Kudus CCTV.

Reads an HLS feed, runs YOLOv11, maps detections into per-lane ROIs,
and emits tiny metadata JSON (kilobytes, not video). Safe to run on
any PC that can reach the stream.

Usage:
    python connector.py --camera "Simpang DPRD Arah Kota"
    python connector.py --camera-id 30
    python connector.py --url <direct m3u8 url> --out data/test.jsonl
    python connector.py --snapshot-only  # grab one frame + run detect
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
ROIS_PATH = BASE_DIR / "config" / "rois.json"
DEFAULT_OUT = BASE_DIR / "data"

API_URL = "https://kudussehat.kuduskab.go.id/api/get-cctv"
API_KEY = "sdsi72392knqw2hhuhsi21380sdisidSHSIAbA12bhsjk23Sndj"

# YOLO COCO classes that count as vehicles
VEHICLE_CLASSES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

DEFAULT_MODEL = "yolo11n.pt"


def fetch_cameras():
    r = requests.get(API_URL, headers={"X-SDC": API_KEY}, timeout=25)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"API failed: {data}")
    return data["camera"]


def find_camera(cameras, name=None, cam_id=None):
    if cam_id is not None:
        for c in cameras:
            if str(c["id"]) == str(cam_id):
                return c
        raise RuntimeError(f"No camera with id={cam_id}")
    if name:
        low = name.lower()
        for c in cameras:
            if low in c.get("nama", "").lower():
                return c
        raise RuntimeError(f"No camera matching name={name!r}")
    raise RuntimeError("Provide --camera, --camera-id, or --url")


def load_rois(camera_key):
    if not ROIS_PATH.exists():
        return {}
    rois = json.loads(ROIS_PATH.read_text(encoding="utf-8"))
    return rois.get(camera_key, {})


def point_in_poly(pt, poly):
    return cv2.pointPolygonTest(np.array(poly, np.int32), pt, False) >= 0


def lane_from_detection(det, lanes):
    """Map a detection to the lane whose polygon contains its ground point."""
    bx1, by1, bx2, by2 = det["bbox"]
    ground = ((bx1 + bx2) / 2.0, by2)  # bottom-center = where vehicle touches road
    for lane_name, poly in lanes.items():
        if point_in_poly(ground, poly):
            return lane_name
    return None


def summarize_frame(results, lanes):
    """Build a compact JSON metadata record from YOLO results."""
    counts = {name: 0 for name in lanes}
    vehicles = []
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if cls not in VEHICLE_CLASSES:
                continue
            conf = float(box.conf[0])
            if conf < 0.35:
                continue
            bbox = [float(x) for x in box.xyxy[0].tolist()]
            det = {"bbox": bbox, "cls": cls, "type": VEHICLE_CLASSES[cls], "conf": conf}
            lane = lane_from_detection(det, lanes)
            det["lane"] = lane
            vehicles.append(det)
            if lane:
                counts[lane] += 1
    return {
        "total_vehicles": len(vehicles),
        "per_lane": counts,
        "vehicles": vehicles,
    }


def open_stream(url):
    # Prefer OpenCV's ffmpeg backend for HLS. Falls back to an image URL.
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open stream: {url}")
    return cap


def annotate(frame, lanes, summary):
    for name, poly in lanes.items():
        pts = np.array(poly, np.int32).reshape(-1, 1, 2)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        cx = int(np.mean([p[0] for p in poly]))
        cy = int(np.mean([p[1] for p in poly]))
        cv2.putText(frame, f"{name}: {summary['per_lane'].get(name, 0)}",
                    (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame


def main():
    ap = argparse.ArgumentParser(description="FlowSense edge connector")
    ap.add_argument("--camera", help="camera name substring, e.g. 'Simpang DPRD Arah Kota'")
    ap.add_argument("--camera-id", help="camera id from the API")
    ap.add_argument("--url", help="direct m3u8 url (bypasses the camera API)")
    ap.add_argument("--out", help="output .jsonl file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--interval", type=float, default=2.0,
                    help="seconds between metadata records")
    ap.add_argument("--snapshot-only", action="store_true",
                    help="detect on one frame then exit (used for calibration)")
    ap.add_argument("--show", action="store_true", help="display annotated frames")
    ap.add_argument("--skip-detect", action="store_true",
                    help="just read frames (test stream before installing model)")
    args = ap.parse_args()

    # Resolve camera + stream
    if args.url:
        cam = {"id": "custom", "nama": "custom", "url": args.url}
        stream_url = args.url
    else:
        cameras = fetch_cameras()
        cam = find_camera(cameras, name=args.camera, cam_id=args.camera_id)
        stream_url = cam["url"]
    camera_key = str(cam["id"])

    print(f"[flowsense] camera {cam.get('id')} '{cam.get('nama', '')}'")
    print(f"[flowsense] stream {stream_url}")
    print(f"[flowsense] model  {args.model}")

    # Lane ROIs (draw once with calibrate.py)
    lanes = load_rois(camera_key)
    if not lanes:
        print(f"[flowsense] WARNING: no lane ROIs for camera {camera_key}. "
              "Run: python calibrate.py --camera-id <id>")
        lanes = {}

    # Model
    model_path = args.model
    if not os.path.exists(model_path) and (BASE_DIR / model_path).exists():
        model_path = str(BASE_DIR / model_path)
    model = YOLO(model_path) if not args.skip_detect else None
    if model is not None:
        print(f"[flowsense] yolov11 loaded ({args.model})")

    cap = open_stream(stream_url)
    out_path = args.out or (DEFAULT_OUT / f"connector_{camera_key}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    frame_idx = 0
    last_emit = 0.0
    with open(out_path, "a", encoding="utf-8") as f:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("[flowsense] stream read failed, retrying in 3s...")
                time.sleep(3)
                cap.release()
                cap = open_stream(stream_url)
                continue

            frame_idx += 1
            now = time.time()

            if args.skip_detect:
                if frame_idx % 30 == 0:
                    print(f"[flowsense] reading stream OK (frame {frame_idx})")
                continue

            summary = {}
            if model is not None:
                results = model(frame, verbose=False)
                summary = summarize_frame(results, lanes)

            if now - last_emit >= args.interval:
                record = {
                    "ts": int(now),
                    "camera_id": cam["id"],
                    "camera": cam.get("nama", ""),
                    "total_vehicles": summary.get("total_vehicles", 0),
                    "per_lane": summary.get("per_lane", {}),
                }
                f.write(json.dumps(record, separators=(",", ":")) + "\n")
                f.flush()
                last_emit = now
                print(json.dumps(record))

            if args.show and model is not None:
                view = annotate(frame.copy(), lanes, summary)
                cv2.imshow("flowsense", view)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if args.snapshot_only:
                break

    cap.release()
    if args.show:
        cv2.destroyAllWindows()
    print(f"[flowsense] done. metadata -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
