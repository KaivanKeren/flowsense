from flowsense.detector import summarize_frame, track_summary


class FakeBox:
    def __init__(self, cls, conf, xyxy, tid=None):
        self.cls = [cls]
        self.conf = [conf]
        self.xyxy = [xyxy]
        self.id = None if tid is None else [tid]


class FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


def _results(boxes):
    return [FakeResult(boxes)]


def test_summarize_counts_vehicles_only():
    lanes = {"kota": [(0, 0), (500, 0), (500, 500), (0, 500)]}
    boxes = [
        FakeBox(2, 0.9, [10, 10, 50, 90]),    # car -> in lane
        FakeBox(3, 0.4, [60, 10, 80, 80]),    # motorcycle -> in lane
        FakeBox(0, 0.9, [100, 100, 120, 120]),  # person -> ignored
    ]
    s = summarize_frame(_results(boxes), lanes, min_conf=0.35)
    assert s["total_vehicles"] == 2
    assert s["per_lane"] == {"kota": 2}
    assert s["vehicles"][0]["type"] == "car"


def test_summarize_filters_low_conf():
    s = summarize_frame(_results([FakeBox(2, 0.2, [10, 10, 50, 90])]), {}, min_conf=0.35)
    assert s["total_vehicles"] == 0


def test_summarize_unknown_lane_is_none():
    lanes = {"kota": [(0, 0), (100, 0), (100, 100), (0, 100)]}
    s = summarize_frame(_results([FakeBox(2, 0.9, [500, 500, 550, 590])]), lanes, min_conf=0.35)
    assert s["total_vehicles"] == 1
    assert s["vehicles"][0]["lane"] is None
    assert s["per_lane"] == {"kota": 0}


def test_track_summary_emits_pairs():
    lanes = {"kota": [(0, 0), (500, 0), (500, 500), (0, 500)]}
    boxes = [
        FakeBox(2, 0.9, [10, 10, 50, 90], tid=1),
        FakeBox(3, 0.5, [200, 10, 220, 80], tid=2),
        FakeBox(2, 0.9, [500, 500, 550, 590], tid=3),  # outside lanes -> lane None
    ]
    dets, pairs = track_summary(_results(boxes), lanes, min_conf=0.35)
    assert pairs == [(1, "kota"), (2, "kota"), (3, None)]
    assert dets[0]["track_id"] == 1
    assert dets[2]["lane"] is None
