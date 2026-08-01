import json

from flowsense.lanes import lane_from_detection, load_rois, point_in_poly

SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]


def test_point_in_poly():
    assert point_in_poly((50, 50), SQUARE)
    assert not point_in_poly((200, 200), SQUARE)


def test_point_on_edge_counts_as_inside():
    assert point_in_poly((0, 50), SQUARE)


def test_lane_from_detection():
    lanes = {
        "kota": [(0, 0), (100, 0), (100, 100), (0, 100)],
        "ploso": [(200, 0), (300, 0), (300, 100), (200, 100)],
    }
    assert lane_from_detection([10, 20, 30, 40], lanes) == "kota"
    assert lane_from_detection([250, 20, 270, 90], lanes) == "ploso"
    assert lane_from_detection([500, 20, 520, 90], lanes) is None


def test_load_rois_missing_file(tmp_path):
    assert load_rois(tmp_path / "nope.json", "30") == {}


def test_load_rois_unknown_camera(tmp_path):
    p = tmp_path / "rois.json"
    p.write_text(json.dumps({"30": {"kota": [[0, 0], [1, 0], [1, 1]]}}), encoding="utf-8")
    assert load_rois(p, "99") == {}


def test_load_rois_known_camera(tmp_path):
    p = tmp_path / "rois.json"
    p.write_text(json.dumps({"30": {"kota": [[0, 0], [1, 0], [1, 1]]}}), encoding="utf-8")
    assert load_rois(p, "30") == {"kota": [[0, 0], [1, 0], [1, 1]]}
