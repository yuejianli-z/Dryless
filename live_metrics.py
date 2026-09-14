"""Monotonic, exposure-weighted blink windows shared by live and minute views."""
from collections import deque
from dataclasses import dataclass
import math

WINDOW_SECONDS = 60.0
MIN_VALID_SECONDS = 30.0
MAX_SAMPLE_GAP = 1.0


def frequency(blinks, valid_seconds):
    return blinks * 60.0 / valid_seconds if valid_seconds >= MIN_VALID_SECONDS else None


@dataclass(frozen=True)
class Minute:
    index: int
    blinks: int
    valid_seconds: float


class BlinkWindows:
    """Rolling (now-60, now] events and fixed [start, end) minute buckets.

    Only intervals with two valid endpoints, at most one second apart, count
    as exposure. Missing tracking is never treated as a recorded zero.
    """
    def __init__(self, start):
        self.start = float(start)
        self.previous = None
        self.previous_valid = False
        self.events = deque()
        self.spans = deque()
        self.buckets = {}
        self.next_minute = 0

    def sample(self, now, valid, blinked):
        now = float(now)
        if not math.isfinite(now) or now < self.start or (self.previous is not None and now < self.previous):
            raise ValueError('Samples must have finite, monotonic times')
        continuous = (self.previous is not None and valid and self.previous_valid
                      and 0 < now-self.previous <= MAX_SAMPLE_GAP)
        if continuous:
            begin = self.previous
            self.spans.append((begin, now))
            while begin < now:
                index = int((begin-self.start)//60)
                end = min(now, self.start+(index+1)*60)
                bucket = self.buckets.setdefault(index, [0, 0.0])
                bucket[1] += end-begin
                begin = end
        if continuous and blinked:
            self.events.append(now)
            index = int((now-self.start)//60)
            self.buckets.setdefault(index, [0, 0.0])[0] += 1
        completed = []
        current = int((now-self.start)//60)
        while self.next_minute < current:
            count, exposure = self.buckets.pop(self.next_minute, [0, 0.0])
            completed.append(Minute(self.next_minute, count, min(60., exposure)))
            self.next_minute += 1
        self.previous, self.previous_valid = now, bool(valid)
        cutoff = now-WINDOW_SECONDS
        while self.events and self.events[0] <= cutoff:
            self.events.popleft()
        while self.spans and self.spans[0][1] <= cutoff:
            self.spans.popleft()
        exposure = min(60., sum(end-max(begin, cutoff) for begin, end in self.spans))
        return {
            'rate': frequency(len(self.events), exposure),
            'valid_seconds': exposure,
            'blinks': len(self.events),
            'completed': completed,
        }
