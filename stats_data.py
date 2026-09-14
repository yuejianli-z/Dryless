"""Read-only aggregation of saved blink-minute records.

An entry represents one *saved minute*, not verified active monitoring time.
No application configuration is imported and no history file is changed here.
Public date ranges include both start and end; bucket datetimes use exclusive
ends. Empty buckets have no total/average, whereas recorded zeroes remain zero.
"""

import math
import re
from datetime import date, datetime, time, timedelta


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z", re.ASCII)
_CLOCK = re.compile(r"([01]\d|2[0-3]):([0-5]\d)\Z", re.ASCII)
_DAY = timedelta(days=1)


def _clean_metadata(value):
    """Keep scalar export metadata; it never contributes to blink totals."""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (str, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return ""


def normalize_history(raw):
    """Return ``(days, skipped)`` for current or legacy JSON history objects.

    ``days`` maps date objects to clean records with their original one-based
    record_index. Repeated minute indices are independent saved observations.
    ``skipped`` counts invalid records; an invalid date discards/counts all of
    its entries, and a malformed/empty date group counts as one invalid item.
    An unrecognized top-level format raises ValueError for a visible load error.
    Missing/invalid clock times retain the record for day/week/month summaries.
    """
    if not isinstance(raw, dict):
        raise ValueError("History must be an object")
    if "days" in raw:
        source = raw["days"]
    elif "date" in raw and "history" in raw:
        source = {raw["date"]: raw["history"]} if isinstance(raw["date"], str) else None
    else:
        raise ValueError("History has no recognized records mapping")
    if not isinstance(source, dict):
        raise ValueError("History days must be a mapping")

    days, skipped = {}, 0
    for key, entries in source.items():
        try:
            if not isinstance(key, str) or not _DATE.fullmatch(key):
                raise ValueError("Invalid date key")
            current = date.fromisoformat(key)
        except ValueError:
            skipped += max(1, len(entries)) if isinstance(entries, list) else 1
            continue
        if not isinstance(entries, list):
            skipped += 1
            continue
        records = []
        for index, entry in enumerate(entries, 1):
            value = entry.get("blinks") if isinstance(entry, dict) else None
            valid = isinstance(value, int) and not isinstance(value, bool) and value >= 0
            if isinstance(value, float):
                valid = math.isfinite(value) and value >= 0 and value.is_integer()
            if not valid:
                skipped += 1
                continue
            clock = entry.get("time", "")
            records.append({
                "record_index": index,
                "minute": _clean_metadata(entry.get("minute", "")),
                "time": clock if isinstance(clock, str) else "",
                "blinks": int(value),
            })
        days[current] = records
    return dict(sorted(days.items())), skipped


def _validate_range(start, end):
    if type(start) is not date or type(end) is not date:
        raise ValueError("Range endpoints must be date objects")
    if start > end:
        raise ValueError("Range start must not follow its end")
    if end == date.max:
        raise ValueError("Range end must allow an exclusive following day")


def choose_grain(start, end):
    """Choose a readable default based on the inclusive number of days."""
    _validate_range(start, end)
    count = (end - start).days + 1
    if count == 1:
        return "hour"
    if count <= 45:
        return "day"
    if count <= 210:
        return "week"
    return "month"


def _period_date(current, grain):
    if grain == "week":
        return current - timedelta(days=current.weekday())
    if grain == "month":
        return current.replace(day=1)
    return current


def _period_after(current, grain):
    if grain == "month":
        if current.month == 12:
            return date(current.year + 1, 1, 1)
        return current.replace(month=current.month + 1)
    return current + timedelta(days=7 if grain == "week" else 1)


def _new_point(start, end, natural_start, partial, calendar_days):
    return {"start": start, "end": end, "period_start": natural_start,
            "partial": partial, "minutes": 0, "total": None,
            "average": None, "recorded_days": 0,
            "calendar_days": calendar_days}


def aggregate_periods(days, start, end, grain):
    """Return ``(points, unplaced_count)`` without inventing missing history.

    start/end are inclusive dates. Each output start/end is clipped to that
    selection; period_start is the natural calendar boundary (Monday/month 1).
    ``partial`` flags clipping, independent of how much history was recorded.
    Hour view requires a single day and excludes entries without strict HH:MM
    timestamps, reporting their count. All other views retain those entries.
    """
    _validate_range(start, end)
    if grain not in {"hour", "day", "week", "month"}:
        raise ValueError("Unknown aggregation grain")
    if grain == "hour" and start != end:
        raise ValueError("Hour aggregation requires a single selected day")
    points, lookup = [], {}
    if grain == "hour":
        midnight = datetime.combine(start, time.min)
        for hour in range(24):
            beginning = midnight + timedelta(hours=hour)
            point = _new_point(beginning, beginning + timedelta(hours=1), beginning, False, 1)
            points.append(point)
            lookup[hour] = point
    else:
        exclusive_end = end + _DAY
        current = _period_date(start, grain)
        while current <= end:
            try:
                following = _period_after(current, grain)
            except (ValueError, OverflowError):
                # The requested end is representable even if a final natural
                # month/week boundary would extend beyond datetime's domain.
                following = date.max
            visible_start = max(current, start)
            visible_end = min(following, exclusive_end)
            point = _new_point(datetime.combine(visible_start, time.min),
                               datetime.combine(visible_end, time.min),
                               datetime.combine(current, time.min),
                               visible_start != current or visible_end != following,
                               (visible_end - visible_start).days)
            points.append(point)
            lookup[current] = point
            current = following

    unplaced = 0
    recorded_dates = {}
    for current, records in days.items():
        if current < start or current > end:
            continue
        for record in records:
            if grain == "hour":
                clock = record.get("time", "")
                match = _CLOCK.fullmatch(clock) if isinstance(clock, str) else None
                if match is None:
                    unplaced += 1
                    continue
                key = int(match.group(1))
            else:
                key = _period_date(current, grain)
            point = lookup[key]
            point["minutes"] += 1
            point["total"] = (point["total"] or 0) + record["blinks"]
            recorded_dates.setdefault(key, set()).add(current)
    for key, point in lookup.items():
        if point["minutes"]:
            point["average"] = point["total"] / point["minutes"]
            point["recorded_days"] = len(recorded_dates[key])
    return points, unplaced
