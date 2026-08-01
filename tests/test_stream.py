import numpy as np
import pytest

from flowsense.stream import ReconnectingStream


def test_open_failure_raises(monkeypatch):
    class FakeCap:
        def __init__(self, url):
            self.url = url

        def isOpened(self):
            return False

        def release(self):
            pass

    monkeypatch.setattr("flowsense.stream.cv2.VideoCapture", FakeCap)
    s = ReconnectingStream("http://x")
    with pytest.raises(RuntimeError, match="Could not open stream"):
        s.open()


def test_stream_reconnects_and_recovers(monkeypatch):
    calls = {"n": 0}

    class FakeCap:
        def __init__(self, url):
            calls["n"] += 1
            self.fails = 0 if calls["n"] >= 3 else 1
            self.frame = np.zeros((10, 10, 3), dtype=np.uint8)

        def isOpened(self):
            return True

        def read(self):
            if self.fails > 0:
                self.fails -= 1
                return False, None
            return True, self.frame

        def release(self):
            pass

    monkeypatch.setattr("flowsense.stream.cv2.VideoCapture", FakeCap)
    s = ReconnectingStream("http://x", max_reconnects=5, backoff=0.0)
    ok, frame = s.read()
    assert ok is True
    assert frame is not None
    assert calls["n"] == 3


def test_stream_gives_up_after_max_reconnects(monkeypatch):
    calls = {"n": 0}

    class FakeCap:
        def __init__(self, url):
            calls["n"] += 1

        def isOpened(self):
            return True

        def read(self):
            return False, None

        def release(self):
            pass

    monkeypatch.setattr("flowsense.stream.cv2.VideoCapture", FakeCap)
    s = ReconnectingStream("http://x", max_reconnects=2, backoff=0.0)
    ok, frame = s.read()
    assert ok is False
    assert frame is None
    assert calls["n"] == 3  # initial open + 2 reconnects
