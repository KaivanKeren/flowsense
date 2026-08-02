"""Lane ROI loading and ground-point mapping."""
import json
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def load_rois(rois_path, camera_key: str) -> dict:
    path = Path(rois_path)
    if not path.exists():
        return {}
    rois = json.loads(path.read_text(encoding="utf-8"))
    return rois.get(camera_key, {})


def point_in_poly(pt, poly) -> bool:
    if not poly or len(poly) < 3:
        return False
    return cv2.pointPolygonTest(np.array(poly, np.int32), pt, False) >= 0


def lane_from_detection(bbox, lanes) -> Optional[str]:
    """Map a detection to the lane containing its ground point (bbox bottom-center)."""
    bx1, _, bx2, by2 = bbox
    ground = ((bx1 + bx2) / 2.0, by2)
    for lane_name, poly in lanes.items():
        if point_in_poly(ground, poly):
            return lane_name
    return None
