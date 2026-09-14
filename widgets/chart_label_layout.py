"""Deterministic mean-label placement without obscuring chart data."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, QSizeF


PLOT_MARGIN = 4.0
MEAN_GAP = 6.0
BUBBLE_CLEARANCE = 6.0
SEGMENT_CLEARANCE = 3.0


def _circle_hits_rect(rect: QRectF, center: QPointF, radius: float) -> bool:
    closest_x = max(rect.left(), min(center.x(), rect.right()))
    closest_y = max(rect.top(), min(center.y(), rect.bottom()))
    return ((closest_x - center.x()) ** 2 + (closest_y - center.y()) ** 2
            <= max(0.0, radius) ** 2)


def _segment_hits_rect(rect: QRectF, start: QPointF, end: QPointF) -> bool:
    """Liang-Barsky clipping; touching an edge counts as a collision."""
    dx, dy = end.x() - start.x(), end.y() - start.y()
    lower, upper = 0.0, 1.0
    for p, q in (
        (-dx, start.x() - rect.left()),
        (dx, rect.right() - start.x()),
        (-dy, start.y() - rect.top()),
        (dy, rect.bottom() - start.y()),
    ):
        if abs(p) < 1e-12:
            if q < 0.0:
                return False
            continue
        ratio = q / p
        if p < 0.0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return True


def place_mean_label(
    plot: QRectF,
    mean_y: float,
    size: QSizeF,
    bubbles: list[tuple[QPointF, float]],
    segments: list[tuple[QPointF, QPointF]],
    fallback: QRectF,
) -> tuple[QRectF, bool]:
    """Return a free in-plot label rectangle, or the caller's outside fallback.

    Anchor order is upper right, lower right, upper left, lower left,
    followed by a right-to-left scan of the two rows beside the mean.
    Bubble hit geometry includes the hover ring. The segment clearance is
    conservative at label corners so a stroke cannot touch the background.
    No data geometry is moved or modified by this function.
    """
    inner = plot.adjusted(PLOT_MARGIN, PLOT_MARGIN, -PLOT_MARGIN, -PLOT_MARGIN)
    width, height = size.width(), size.height()
    if (not math.isfinite(mean_y) or not math.isfinite(width)
            or not math.isfinite(height) or width <= 0.0 or height <= 0.0
            or inner.width() < width or inner.height() < height
            or mean_y < plot.top() or mean_y > plot.bottom()):
        return QRectF(fallback), True

    left, right = inner.left(), inner.right() - width
    above, below = mean_y - MEAN_GAP - height, mean_y + MEAN_GAP
    candidates = [(right, above), (right, below), (left, above), (left, below)]
    # At most 4 px between placements avoids skipping a narrow clear slot.
    steps = max(1, math.ceil((right - left) / 4.0))
    for index in range(1, steps):
        x = right - (right - left) * index / steps
        candidates.extend(((x, above), (x, below)))

    for x, y in candidates:
        rect = QRectF(x, y, width, height)
        if not inner.contains(rect):
            continue
        if any(_circle_hits_rect(rect, center, radius + BUBBLE_CLEARANCE)
               for center, radius in bubbles):
            continue
        buffered = rect.adjusted(-SEGMENT_CLEARANCE, -SEGMENT_CLEARANCE,
                                 SEGMENT_CLEARANCE, SEGMENT_CLEARANCE)
        if any(_segment_hits_rect(buffered, start, end) for start, end in segments):
            continue
        return rect, False
    return QRectF(fallback), True
