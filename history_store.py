"""
Blink history persistence and aggregation helpers.

Storage format (`blink_data.json`):
{
  "days": {
    "2024-06-01": [{"minute": 0, "blinks": 12, "time": "09:00"}, ...],
    ...
  }
}

Public API:
  append_minute(blinks, minute, time_str)
  load_daily_stats(n=30)
  today_minutes()
"""

import json
import os
from datetime import date, timedelta

_DATA_FILE = os.path.join(os.path.expanduser("~"), ".blink_reminder", "blink_data.json")

_HEALTHY_MIN = 15.0
_HEALTHY_MAX = 20.0


def _load_raw() -> dict:
    if not os.path.exists(_DATA_FILE):
        return {"days": {}}
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "days" not in data:
            # 兼容旧格式（backend.py 写的单日格式）
            if "date" in data and "history" in data:
                return {"days": {data["date"]: data["history"]}}
            return {"days": {}}
        return data
    except Exception as e:
        print(f"[history_store] Failed to read history: {e}")
        return {"days": {}}


def _save_raw(raw: dict):
    try:
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[history_store] Failed to write history: {e}")


def append_minute(blinks: int, minute: int, time_str: str):
    """追加一条分钟记录到今日数据并持久化。"""
    raw = _load_raw()
    today = date.today().isoformat()
    day_list = raw["days"].setdefault(today, [])
    day_list.append({"minute": minute, "blinks": blinks, "time": time_str})
    _save_raw(raw)


def today_minutes() -> list:
    """返回今日原始分钟列表。"""
    raw = _load_raw()
    return raw["days"].get(date.today().isoformat(), [])


def _day_stats(records: list, d: date) -> dict | None:
    """把一天的分钟记录聚合成统计字典，无数据返回 None。"""
    if not records:
        return None
    rates = []
    for r in records:
        mins = r.get("blinks", 0)
        if mins > 0:
            rates.append(float(mins))
    if not rates:
        return None
    avg = sum(rates) / len(rates)
    mn = min(rates)
    mx = max(rates)
    total = sum(int(r.get("blinks", 0)) for r in records)
    health = int(max(0, min(100, (1 - abs(avg - (_HEALTHY_MIN + _HEALTHY_MAX) / 2) / 8) * 100)))
    return {
        "date": d, "avg": avg, "min": mn, "max": mx,
        "total": total, "health": health,
        "_minutes": rates,   # 供堆叠面积图精确拆层
    }


def today_hourly() -> list[tuple[str, float]]:
    """
    返回今日各整点小时的眨眼频率均值，格式 [(hour_label, avg_rate), ...]。
    只返回有数据的小时，空小时跳过。
    """
    records = today_minutes()
    buckets: dict[int, list[float]] = {}
    for r in records:
        t = r.get("time", "")
        try:
            hour = int(t.split(":")[0])
        except (ValueError, IndexError):
            continue
        rate = float(r.get("blinks", 0))
        if rate > 0:
            buckets.setdefault(hour, []).append(rate)
    result = []
    for hour in sorted(buckets):
        rates = buckets[hour]
        avg = sum(rates) / len(rates)
        result.append((str(hour), avg))
    return result


def load_daily_stats(n: int = 30) -> list:
    """
    返回最近 n 天有数据的统计列表，最新一天在末尾。
    只返回有实际数据的天，不补假数据。
    """
    raw = _load_raw()
    today = date.today()
    result = []
    for i in range(n - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        records = raw["days"].get(key, [])
        stats = _day_stats(records, d)
        if stats:
            result.append(stats)
    return result
