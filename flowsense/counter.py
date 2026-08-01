"""Unique per-track, per-lane crossing counting."""
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class TrackingCounter:
    """Counts each tracked vehicle once per lane it crosses."""

    def __init__(self):
        self.crossings: Dict[str, int] = defaultdict(int)
        self._seen = set()

    def update(self, tracked_dets: List[Tuple[int, Optional[str]]]) -> Dict[str, int]:
        for track_id, lane in tracked_dets:
            if lane is None:
                continue
            key = (track_id, lane)
            if key not in self._seen:
                self._seen.add(key)
                self.crossings[lane] += 1
        return self.snapshot()

    def snapshot(self) -> Dict[str, int]:
        return dict(self.crossings)

    def reset(self):
        self.crossings = defaultdict(int)
        self._seen = set()
