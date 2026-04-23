"""Monitor screen."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import config
import theme as T
import history_store
from i18n import t
from widgets import (
    Card, SectionLabel, RateRing, HealthGauge, CameraView,
    TrendChart, HourlyBars,
)


def _fnt(size, weight=400):
    f = QFont(T.FONT_UI)
    f.setFamilies([T.FONT_UI] + T.FONT_FB)
    f.setPixelSize(int(size))
    weight_map = {
        400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
        600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold,
    }
    f.setWeight(weight_map.get(weight, QFont.Weight.Normal))
    return f


def _fmt_session(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


class _Kpi(Card):
    def __init__(self, label, val, unit, color=None):
        super().__init__(padding=(13, 13, 16, 13))
        self._color = color or T.C_TEXT
        lay = self.layout()
        self._lbl = SectionLabel(label)
        lay.addWidget(self._lbl)
        lay.addSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(3)
        self._val = QLabel(val)
        self._val.setFont(_fnt(22, 700))
        self._val.setStyleSheet(f"color:{self._color}; background:transparent; border:none;")
        row.addWidget(self._val)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet(f"color:{T.C_TEXT2}; font-size:11px; background:transparent; border:none;")
            row.addWidget(u, alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)
        lay.addLayout(row)

    def setValue(self, v):
        self._val.setText(str(v))

    def setColor(self, c):
        self._color = c
        self._val.setStyleSheet(f"color:{c}; background:transparent; border:none;")

    def setLabel(self, text):
        self._lbl.setText(text)


class _AlertTile(QFrame):
    def __init__(self, label, color, sec):
        super().__init__()
        self._color = color
        bg = T.rgba(color, 0.06)
        border = T.rgba(color, 0.30)
        self.setStyleSheet(
            f"QFrame{{background:{bg}; "
            f"border:1px solid {border}; border-radius:8px;}}"
        )
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 8, 6, 8)
        v.setSpacing(2)
        lb = QLabel(label)
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setStyleSheet(
            f"color:{color}; font-size:10px; font-weight:600; border:none; background:transparent;"
        )
        v.addWidget(lb)
        self._cnt = QLabel("0")
        self._cnt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cnt.setFont(_fnt(20, 700))
        self._cnt.setStyleSheet(
            f"color:{T.C_TEXT3}; border:none; background:transparent;"
        )
        v.addWidget(self._cnt)
        s = QLabel(sec)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:9px; border:none; background:transparent;"
        )
        v.addWidget(s)

    def setCount(self, n: int, active: bool = False):
        self._cnt.setText(str(n))
        if n > 0 or active:
            self._cnt.setStyleSheet(
                f"color:{self._color}; border:none; background:transparent;"
            )
        else:
            self._cnt.setStyleSheet(
                f"color:{T.C_TEXT3}; border:none; background:transparent;"
            )


class MonitorScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alert_counts = [0, 0, 0, 0]

        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setHorizontalSpacing(14)
        root.setVerticalSpacing(12)
        root.setColumnStretch(0, 0)
        root.setColumnStretch(1, 1)

        # ── 左列 ─────────────────────────────
        left = QWidget(self)
        left.setFixedWidth(320)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        self.camera = CameraView()
        self.camera.setFixedSize(320, 240)
        lv.addWidget(self.camera)

        # 实时状态卡
        status = Card(padding=(14, 14, 16, 14))
        slay = status.layout()

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self._realtime_lbl = SectionLabel(t("realtime_status"))
        top_row.addWidget(self._realtime_lbl)
        top_row.addStretch(1)
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color:{T.BRAND}; font-size:11px; background:transparent; border:none;")
        self._status_lbl = QLabel(t("normal_blink"))
        self._status_lbl.setStyleSheet(
            f"color:{T.BRAND}; font-size:11px; font-weight:600; background:transparent; border:none;")
        top_row.addWidget(self._status_dot)
        top_row.addWidget(self._status_lbl)
        slay.addLayout(top_row)
        slay.addSpacing(12)

        rr = QHBoxLayout()
        rr.setSpacing(16)
        self.rate_ring = RateRing()
        rr.addWidget(self.rate_ring)
        rright = QVBoxLayout()
        rright.setSpacing(2)
        self._since_lbl = QLabel(t("since_last_blink"))
        self._since_lbl.setStyleSheet(f"color:{T.C_TEXT2}; font-size:11px; background:transparent; border:none;")
        rright.addWidget(self._since_lbl)
        self._secs_lbl = QLabel("0.0")
        self._secs_lbl.setFont(_fnt(26, 700))
        self._secs_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        rright.addWidget(self._secs_lbl)
        self._thresh_lbl = QLabel(t("threshold_fmt", v=config.NO_BLINK_ALERT_SEC))
        self._thresh_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10px; background:transparent; border:none;")
        rright.addWidget(self._thresh_lbl)
        rr.addLayout(rright, 1)
        slay.addLayout(rr)
        slay.addSpacing(10)

        # 4段进度
        lvl_lay = QVBoxLayout()
        lvl_lay.setSpacing(3)
        self._level_bars = []
        row_bars = QHBoxLayout()
        row_bars.setSpacing(3)
        for _i in range(4):
            b = QFrame()
            b.setFixedHeight(3)
            b.setStyleSheet("background:#EDE9E2; border-radius:2px;")
            row_bars.addWidget(b, 1)
            self._level_bars.append(b)
        lvl_lay.addLayout(row_bars)
        row_lbls = QHBoxLayout()
        row_lbls.setSpacing(3)
        for info in T.alert_levels():
            lb = QLabel(info["sec"])
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setStyleSheet(f"color:{T.C_TEXT3}; font-size:9px; background:transparent; border:none;")
            row_lbls.addWidget(lb, 1)
        lvl_lay.addLayout(row_lbls)
        slay.addLayout(lvl_lay)
        slay.addSpacing(10)

        # 开合度
        eye = QFrame()
        eye.setStyleSheet(f"background:{T.C_BG}; border-radius:7px;")
        ev = QVBoxLayout(eye)
        ev.setContentsMargins(11, 8, 11, 10)
        ev.setSpacing(4)
        er = QHBoxLayout()
        self._eye_openness_lbl = QLabel(t("eye_openness"))
        self._eye_openness_lbl.setStyleSheet(f"color:{T.C_TEXT2}; font-size:10.5px; background:transparent; border:none;")
        er.addWidget(self._eye_openness_lbl)
        er.addStretch(1)
        self._eye_state_lbl = QLabel(t("eye_open"))
        self._eye_state_lbl.setStyleSheet(
            f"color:{T.BRAND}; font-size:10.5px; font-weight:600; background:transparent; border:none;")
        er.addWidget(self._eye_state_lbl)
        ev.addLayout(er)

        self._eye_track = QFrame()
        self._eye_track.setFixedHeight(3)
        self._eye_track.setStyleSheet(
            f"background:{T.C_BORDER}; border-radius:2px;"
        )
        self._eye_fill = QFrame(self._eye_track)
        self._eye_fill.setGeometry(0, 0, 100, 3)
        self._eye_fill.setStyleSheet(
            f"background:{T.BRAND}; border-radius:2px;"
        )
        ev.addWidget(self._eye_track)
        slay.addWidget(eye)

        lv.addWidget(status)

        # 健康评分卡
        hcard = Card(padding=(14, 14, 16, 14))
        hlay = hcard.layout()
        hrow = QHBoxLayout()
        hrow.setSpacing(16)
        self.gauge = HealthGauge()
        hrow.addWidget(self.gauge)
        hmid = QVBoxLayout()
        hmid.setSpacing(4)
        self._habit_lbl = QLabel(t("habit_good"))
        self._habit_lbl.setStyleSheet(
            f"color:{T.BRAND}; font-size:12px; font-weight:600; background:transparent; border:none;")
        hmid.addWidget(self._habit_lbl)
        self._habit_sub = QLabel(t("habit_sub", rate="—"))
        self._habit_sub.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10px; background:transparent; border:none;")
        hmid.addWidget(self._habit_sub)
        hrow.addLayout(hmid, 1)
        hlay.addLayout(hrow)
        lv.addWidget(hcard)

        lv.addStretch(1)
        root.addWidget(left, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)

        # ── 右列 ─────────────────────────────
        right = QWidget(self)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_today = _Kpi(t("kpi_today"), "—", t("unit_times"))
        self._kpi_rate = _Kpi(t("kpi_rate"), "—", t("unit_per_min"), color=T.BRAND)
        self._kpi_session = _Kpi(t("kpi_session"), "—", "")
        for k in (self._kpi_today, self._kpi_rate, self._kpi_session):
            kpi_row.addWidget(k, 1)
        rv.addLayout(kpi_row)

        trend_card = Card(padding=(16, 15, 16, 15))
        tlay = trend_card.layout()
        trow = QHBoxLayout()
        ttitle = QVBoxLayout()
        ttitle.setSpacing(1)
        self._trend_title_lbl = QLabel(t("trend_title"))
        self._trend_title_lbl.setFont(_fnt(13, 600))
        self._trend_title_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        ttitle.addWidget(self._trend_title_lbl)
        self._trend_sub_lbl = QLabel(t("trend_sub"))
        self._trend_sub_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10.5px; background:transparent; border:none;")
        ttitle.addWidget(self._trend_sub_lbl)
        trow.addLayout(ttitle)
        trow.addStretch(1)
        leg = QHBoxLayout()
        leg.setSpacing(12)
        self._leg_labels = []
        for lb, kind in [(t("legend_rate"), "line"), (t("legend_health"), "box")]:
            c = QHBoxLayout()
            c.setSpacing(4)
            sw = QFrame()
            if kind == "line":
                sw.setFixedSize(14, 2)
                sw.setStyleSheet(f"background:{T.BRAND}; border:none;")
            else:
                sw.setFixedSize(10, 8)
                sw.setStyleSheet(
                    "background:transparent;"
                    "border:1.5px solid rgba(74,158,128,160);"
                )
            c.addWidget(sw)
            l = QLabel(lb)
            l.setStyleSheet(f"color:{T.C_TEXT3}; font-size:9.5px; background:transparent; border:none;")
            c.addWidget(l)
            self._leg_labels.append(l)
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setLayout(c)
            leg.addWidget(w)
        trow.addLayout(leg)
        tlay.addLayout(trow)
        tlay.addSpacing(10)
        self.trend = TrendChart()
        self.trend.setMinimumHeight(140)
        tlay.addWidget(self.trend)
        rv.addWidget(trend_card)

        hourly_card = Card(padding=(14, 14, 16, 14))
        hclay = hourly_card.layout()
        hhrow = QHBoxLayout()
        htitle = QVBoxLayout()
        htitle.setSpacing(1)
        self._hourly_title_lbl = QLabel(t("hourly_title"))
        self._hourly_title_lbl.setFont(_fnt(13, 600))
        self._hourly_title_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        htitle.addWidget(self._hourly_title_lbl)
        self._hourly_sub_lbl = QLabel(t("hourly_sub"))
        self._hourly_sub_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10.5px; background:transparent; border:none;")
        htitle.addWidget(self._hourly_sub_lbl)
        hhrow.addLayout(htitle)
        hhrow.addStretch(1)
        hclay.addLayout(hhrow)
        hclay.addSpacing(10)
        self.hourly = HourlyBars()
        self.hourly.setMinimumHeight(64)
        hclay.addWidget(self.hourly)
        rv.addWidget(hourly_card)

        alerts_card = Card(padding=(13, 13, 16, 14))
        aclay = alerts_card.layout()
        self._alerts_today_lbl = SectionLabel(t("alerts_today"))
        aclay.addWidget(self._alerts_today_lbl)
        aclay.addSpacing(8)
        arow = QHBoxLayout()
        arow.setSpacing(8)
        self._alert_tiles = []
        for info in T.alert_levels():
            tile = _AlertTile(info["label"], info["c"], info["sec"])
            self._alert_tiles.append(tile)
            arow.addWidget(tile, 1)
        aclay.addLayout(arow)
        rv.addWidget(alerts_card)

        rv.addStretch(1)
        root.addWidget(right, 0, 1, alignment=Qt.AlignmentFlag.AlignTop)

    # ── 事件 ────────────────────────────────
    def on_alert_triggered(self, level: int):
        if 0 <= level < 4:
            self._alert_counts[level] += 1
            self._alert_tiles[level].setCount(self._alert_counts[level], True)

    def update_state(self, s: dict):
        level = s["alert_level"]
        if level >= 0:
            info = T.alert_levels()[level]
            self._status_dot.setStyleSheet(f"color:{info['c']}; font-size:11px; background:transparent; border:none;")
            self._status_lbl.setStyleSheet(
                f"color:{info['c']}; font-size:11px; font-weight:600; background:transparent; border:none;")
            self._status_lbl.setText(info["label"])
            self._secs_lbl.setStyleSheet(f"color:{info['c']}; background:transparent; border:none;")
        else:
            self._status_dot.setStyleSheet(f"color:{T.BRAND}; font-size:11px; background:transparent; border:none;")
            self._status_lbl.setStyleSheet(
                f"color:{T.BRAND}; font-size:11px; font-weight:600; background:transparent; border:none;")
            self._status_lbl.setText(t("normal_blink"))
            self._secs_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")

        self._secs_lbl.setText(f"{s['no_blink']:.1f}")
        self._thresh_lbl.setText(t("threshold_fmt", v=config.NO_BLINK_ALERT_SEC))

        for i, b in enumerate(self._level_bars):
            if level >= i:
                c = T.ALERT_LEVELS[i]["c"]  # color only, no translation needed
                b.setStyleSheet(f"background:{c}; border-radius:2px;")
            else:
                b.setStyleSheet("background:#EDE9E2; border-radius:2px;")

        if s["eye_open"]:
            self._eye_state_lbl.setText(t("eye_open"))
            self._eye_state_lbl.setStyleSheet(
                f"color:{T.BRAND}; font-size:10.5px; font-weight:600; background:transparent; border:none;")
            self._eye_fill.setStyleSheet(f"background:{T.BRAND}; border-radius:2px;")
        else:
            self._eye_state_lbl.setText(t("eye_closed"))
            self._eye_state_lbl.setStyleSheet(
                f"color:{T.DANGER}; font-size:10.5px; font-weight:600; background:transparent; border:none;")
            self._eye_fill.setStyleSheet(f"background:{T.DANGER}; border-radius:2px;")

        # 用真实 ratio 驱动进度条宽度（ratio=1.0 为基线，clamp 到 0~1）
        ratio = s.get("eye_ratio")
        if ratio is not None:
            pct = max(0.02, min(1.0, ratio))
        else:
            pct = 0.75 if s["eye_open"] else 0.05
        track_w = max(40, self._eye_track.width())
        self._eye_fill.setGeometry(0, 0, max(4, int(track_w * pct)), 3)

        self.rate_ring.setRate(s["rate"], level)

        self._kpi_today.setValue(f"{s['total']:,}")
        self._kpi_rate.setValue(f"{s['rate']:.1f}")
        self._kpi_session.setValue(_fmt_session(s["session_sec"]))
        if 15 <= s["rate"] <= 20:
            self._kpi_rate.setColor(T.BRAND)
        else:
            self._kpi_rate.setColor(T.WARN)

        score = int(max(18, min(100, round(100 - abs(s["rate"] - 17.5) * 4.5))))
        self.gauge.setScore(score)
        if score >= 80:
            self._habit_lbl.setText(t("habit_good"))
            self._habit_lbl.setStyleSheet(
                f"color:{T.BRAND}; font-size:12px; font-weight:600; background:transparent; border:none;")
        elif score >= 60:
            self._habit_lbl.setText(t("habit_low"))
            self._habit_lbl.setStyleSheet(
                f"color:{T.WARN}; font-size:12px; font-weight:600; background:transparent; border:none;")
        else:
            self._habit_lbl.setText(t("habit_bad"))
            self._habit_lbl.setStyleSheet(
                f"color:{T.DANGER}; font-size:12px; font-weight:600; background:transparent; border:none;")
        self._habit_sub.setText(t("habit_sub", rate=f"{s['rate']:.1f}"))

        hist = list(s.get("minute_history") or [])
        self.trend.setData(hist)

        # 按小时柱状图：从 history_store 读今日真实数据
        bars = history_store.today_hourly()
        self.hourly.setData(bars)

    def retranslate(self):
        self._realtime_lbl.setText(t("realtime_status"))
        self._status_lbl.setText(t("normal_blink"))
        self._since_lbl.setText(t("since_last_blink"))
        self._thresh_lbl.setText(t("threshold_fmt", v=config.NO_BLINK_ALERT_SEC))
        self._eye_openness_lbl.setText(t("eye_openness"))
        self._kpi_today.setLabel(t("kpi_today"))
        self._kpi_rate.setLabel(t("kpi_rate"))
        self._kpi_session.setLabel(t("kpi_session"))
        self._trend_title_lbl.setText(t("trend_title"))
        self._trend_sub_lbl.setText(t("trend_sub"))
        for lbl, key in zip(self._leg_labels, ["legend_rate", "legend_health"]):
            lbl.setText(t(key))
        self._hourly_title_lbl.setText(t("hourly_title"))
        self._hourly_sub_lbl.setText(t("hourly_sub"))
        self._alerts_today_lbl.setText(t("alerts_today"))
