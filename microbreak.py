"""Camera-presence microbreak timing, independent of blink detection."""
PRESENCE_SECONDS = 25 * 60
PROMPT_SECONDS = 30
ABSENCE_RESET_SECONDS = 20
TRACKING_GRACE_SECONDS = 5


class MicrobreakController:
    def __init__(self):
        self.last_time = None
        self.previous_face = False
        self.presence = 0.0
        self.absent_since = None
        self.prompt_until = None

    def update(self, face, now, paused=False):
        was_active = self.prompt_until is not None
        dt = 0 if self.last_time is None else max(0, now - self.last_time)
        if paused or dt > TRACKING_GRACE_SECONDS:
            self.presence = 0.0
            self.prompt_until = None
            self.absent_since = None
            self.previous_face = False
            dt = 0
        if not face:
            if self.absent_since is None:
                self.absent_since = self.last_time if self.previous_face else now
            absence = now - self.absent_since
            if absence > TRACKING_GRACE_SECONDS:
                self.presence = 0.0
            if absence >= ABSENCE_RESET_SECONDS:
                self.prompt_until = None
        else:
            if self.absent_since is not None and now - self.absent_since > TRACKING_GRACE_SECONDS:
                self.presence = 0.0
            self.absent_since = None
            if self.previous_face and self.prompt_until is None and not paused:
                self.presence += dt
        if self.prompt_until is not None and now >= self.prompt_until:
            self.prompt_until = None
        ended = was_active and self.prompt_until is None
        if ended:
            self.presence = 0.0
        started = False
        if not paused and face and not ended and self.prompt_until is None and self.presence >= PRESENCE_SECONDS:
            self.prompt_until = now + PROMPT_SECONDS
            self.presence = 0.0
            started = True
        self.last_time = now
        self.previous_face = bool(face) and not paused
        return dict(active=self.prompt_until is not None, started=started, ended=ended,
                    presence_seconds=self.presence,
                    remaining_seconds=max(0, (self.prompt_until or now) - now))
