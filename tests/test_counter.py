from flowsense.counter import TrackingCounter


def test_counts_once_per_track_lane():
    c = TrackingCounter()
    assert c.update([(1, "kota"), (1, "kota"), (2, "kota")]) == {"kota": 2}
    assert c.update([(2, "kota")]) == {"kota": 2}


def test_track_crosses_two_lanes():
    c = TrackingCounter()
    c.update([(1, "kota"), (1, "ploso")])
    assert c.snapshot() == {"kota": 1, "ploso": 1}


def test_ignores_no_lane():
    c = TrackingCounter()
    assert c.update([(1, None)]) == {}


def test_reset_clears_state():
    c = TrackingCounter()
    c.update([(1, "kota")])
    c.reset()
    assert c.snapshot() == {}
    assert c.update([(1, "kota")]) == {"kota": 1}
