"""Stats screen with KPIs, history charts, and eye-care tips."""
from datetime import date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import theme as T
from i18n import t
from widgets import Card, SectionLabel, DailyKChart, HabitCalendar
import history_store


def _fnt(size, weight=400):
    f = QFont(T.FONT_UI)
    f.setFamilies([T.FONT_UI] + T.FONT_FB)
    f.setPixelSize(int(size))
    m = {400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
         600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold}
    f.setWeight(m.get(weight, QFont.Weight.Normal))
    return f


def QColor_rgba(hex_, alpha):
    """兼容简单 rgba 字符串，不依赖 QColor 实例。"""
    h = hex_.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _compute_kpis(data: list) -> dict:
    """从每日统计列表计算 KPI，数据不足时返回空值占位。"""
    if not data:
        return {"streak": 0, "avg7": None, "total": 0, "best_health": None}

    streak = 0
    for d in reversed(data):
        if d["health"] >= 60:
            streak += 1
        else:
            break

    last7 = [d for d in data if d["date"] >= date.today() - timedelta(days=6)]
    avg7 = sum(d["avg"] for d in last7) / len(last7) if last7 else None

    total = sum(d["total"] for d in data)
    best_health = max(d["health"] for d in data)
    return {"streak": streak, "avg7": avg7, "total": total, "best_health": best_health}


class _KpiMini(Card):
    def __init__(self, label, val, unit, color=None):
        super().__init__(padding=(12, 12, 15, 12))
        lay = self.layout()
        self._lbl = SectionLabel(label)
        lay.addWidget(self._lbl)
        lay.addSpacing(3)
        row = QHBoxLayout()
        row.setSpacing(3)
        self._v = QLabel(val)
        self._v.setFont(_fnt(22, 700))
        self._v.setStyleSheet(f"color:{color or T.C_TEXT}; background:transparent; border:none;")
        row.addWidget(self._v)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet(f"color:{T.C_TEXT2}; font-size:11px; background:transparent; border:none;")
            row.addWidget(u, alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)
        lay.addLayout(row)

    def setValue(self, val: str, color: str | None = None):
        self._v.setText(val)
        if color:
            self._v.setStyleSheet(
                f"color:{color}; background:transparent; border:none;")

    def setLabel(self, text):
        self._lbl.setText(text)


class StatsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # KPI 4 列
        kpi = QHBoxLayout()
        kpi.setSpacing(10)
        self._kpi_streak = _KpiMini(t("kpi_streak"), "—", t("unit_days"))
        self._kpi_avg7   = _KpiMini(t("kpi_avg7"),   "—", t("unit_per_min"))
        self._kpi_total  = _KpiMini(t("kpi_total"),  "—", t("unit_wan"))
        self._kpi_best   = _KpiMini(t("kpi_best"),   "—", t("unit_pct"))
        for w in (self._kpi_streak, self._kpi_avg7, self._kpi_total, self._kpi_best):
            kpi.addWidget(w, 1)
        root.addLayout(kpi)

        # K 线卡
        kcard = Card(padding=(16, 16, 18, 16))
        klay = kcard.layout()
        krow = QHBoxLayout()
        kt = QVBoxLayout()
        kt.setSpacing(2)
        t_obj = QLabel(t("kchart_title"))
        t_obj.setFont(_fnt(13, 600))
        t_obj.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        kt.addWidget(t_obj)
        s_obj = QLabel(t("kchart_sub"))
        s_obj.setStyleSheet(f"color:{T.C_TEXT3}; font-size:11px; background:transparent; border:none;")
        kt.addWidget(s_obj)
        self._kchart_title_lbl = t_obj
        self._kchart_sub_lbl = s_obj
        krow.addLayout(kt)
        krow.addStretch(1)
        self._k_leg_labels = []
        for lb, col in [(t("legend_healthy"), T.BRAND), (t("legend_low"), T.WARN), (t("legend_high"), "#5B8FC9")]:
            box = QHBoxLayout()
            box.setSpacing(5)
            sw = QFrame()
            sw.setFixedSize(14, 2)
            sw.setStyleSheet(f"background:{col}; border:none;")
            box.addWidget(sw)
            lbl = QLabel(lb)
            lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10px; background:transparent; border:none;")
            box.addWidget(lbl)
            self._k_leg_labels.append(lbl)
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setLayout(box)
            krow.addWidget(w)
            krow.addSpacing(6)
        klay.addLayout(krow)
        klay.addSpacing(10)
        self._kchart = DailyKChart()
        self._kchart.setMinimumHeight(200)
        klay.addWidget(self._kchart)

        self._empty_k = QLabel(t("no_data"))
        self._empty_k.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_k.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:12px; background:transparent; border:none;")
        self._empty_k.setMinimumHeight(200)
        klay.addWidget(self._empty_k)
        root.addWidget(kcard)

        # 底部：热力图 + 建议
        bot = QHBoxLayout()
        bot.setSpacing(12)

        heatmap = Card(padding=(14, 14, 16, 14))
        hlay = heatmap.layout()
        self._heatmap_title_lbl = QLabel(t("heatmap_title"))
        self._heatmap_title_lbl.setFont(_fnt(13, 600))
        self._heatmap_title_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        hlay.addWidget(self._heatmap_title_lbl)
        self._heatmap_sub_lbl = QLabel(t("heatmap_sub"))
        self._heatmap_sub_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10.5px; background:transparent; border:none;")
        hlay.addWidget(self._heatmap_sub_lbl)
        hlay.addSpacing(10)
        self._hcal = HabitCalendar()
        hlay.addWidget(self._hcal)
        hlay.addSpacing(8)

        legend = QHBoxLayout()
        legend.setSpacing(8)
        self._legend_low_health_lbl = QLabel(t("legend_low_health"))
        self._legend_low_health_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10px; background:transparent; border:none;")
        legend.addWidget(self._legend_low_health_lbl)
        swatches = [
            QColor_rgba(T.DANGER, 0.40),
            QColor_rgba(T.WARN, 0.40),
            QColor_rgba(T.BRAND, 0.27),
            QColor_rgba(T.BRAND, 0.53),
            QColor_rgba(T.BRAND, 0.80),
        ]
        for c in swatches:
            sw = QFrame()
            sw.setFixedSize(14, 14)
            sw.setStyleSheet(f"background:{c}; border-radius:2px;")
            legend.addWidget(sw)
        self._legend_hi_lbl = QLabel(t("legend_hi"))
        self._legend_hi_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:10px; background:transparent; border:none;")
        legend.addWidget(self._legend_hi_lbl)
        legend.addStretch(1)
        hlay.addLayout(legend)
        bot.addWidget(heatmap, 1)

        tips = Card(padding=(14, 14, 16, 14))
        tlay = tips.layout()
        self._tips_title_lbl = QLabel(t("tips_title"))
        self._tips_title_lbl.setFont(_fnt(13, 600))
        self._tips_title_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        tlay.addWidget(self._tips_title_lbl)
        tlay.addSpacing(8)
        self._tip_labels = []
        for icon, title_key, desc_key, accent in [
            ("👁", "tip1_title", "tip1_desc", T.BRAND),
            ("💧", "tip2_title", "tip2_desc", "#5B8FC9"),
            ("🌙", "tip3_title", "tip3_desc", T.WARN),
            ("📋", "tip4_title", "tip4_desc", T.C_TEXT3),
        ]:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{T.C_BG}; border:1px solid {T.C_BORDER};"
                f"border-radius:10px;}}"
            )
            cl = QHBoxLayout(card)
            cl.setContentsMargins(10, 9, 10, 9)
            cl.setSpacing(10)
            ic = QLabel(icon)
            ic.setFixedSize(28, 28)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet(
                f"background:{T.rgba(accent, 0.12)}; border-radius:8px;"
                f"font-size:14px; border:none;"
            )
            cl.addWidget(ic)
            txt = QVBoxLayout()
            txt.setSpacing(1)
            wt = QLabel(t(title_key))
            wt.setStyleSheet(
                f"color:{T.C_TEXT}; font-size:11px; font-weight:600;"
                f"background:transparent; border:none;")
            txt.addWidget(wt)
            wd = QLabel(t(desc_key))
            wd.setStyleSheet(
                f"color:{T.C_TEXT2}; font-size:10px;"
                f"background:transparent; border:none;")
            wd.setWordWrap(True)
            txt.addWidget(wd)
            self._tip_labels.append((wt, wd, title_key, desc_key))
            cl.addLayout(txt, 1)
            tlay.addWidget(card)
            tlay.addSpacing(5)
        tips.setFixedWidth(260)
        bot.addWidget(tips)
        root.addLayout(bot)

        root.addStretch(1)

        # 首次加载真实数据
        self._refresh()

    def _refresh(self):
        """从 history_store 读取真实数据并刷新所有控件。"""
        data = history_store.load_daily_stats(30)
        kpis = _compute_kpis(data)

        # KPI
        streak = kpis["streak"]
        self._kpi_streak.setValue(
            str(streak),
            color=T.BRAND if streak else T.WARN,
        )
        if kpis["avg7"] is not None:
            avg7 = kpis["avg7"]
            self._kpi_avg7.setValue(
                f"{avg7:.1f}",
                color=T.BRAND if 15 <= avg7 <= 20 else T.WARN,
            )
        else:
            self._kpi_avg7.setValue("—")

        total = kpis["total"]
        self._kpi_total.setValue(f"{total/10000:.1f}" if total else "—")

        best = kpis["best_health"]
        self._kpi_best.setValue(f"{best}%" if best is not None else "—",
                                color=T.BRAND if best else None)

        # K 线图 / 空状态
        if data:
            self._kchart.setData(data)
            self._kchart.setVisible(True)
            self._empty_k.setVisible(False)
            self._hcal.setData([d["health"] for d in data])
        else:
            self._kchart.setVisible(False)
            self._empty_k.setVisible(True)
            self._hcal.setData([])

    def update_stats(self):
        """每分钟结束后由 ui.py 调用，刷新统计页。"""
        self._refresh()

    def retranslate(self):
        self._kpi_streak.setLabel(t("kpi_streak"))
        self._kpi_avg7.setLabel(t("kpi_avg7"))
        self._kpi_total.setLabel(t("kpi_total"))
        self._kpi_best.setLabel(t("kpi_best"))
        self._kchart_title_lbl.setText(t("kchart_title"))
        self._kchart_sub_lbl.setText(t("kchart_sub"))
        for lbl, key in zip(self._k_leg_labels, ["legend_healthy", "legend_low", "legend_high"]):
            lbl.setText(t(key))
        self._empty_k.setText(t("no_data"))
        self._heatmap_title_lbl.setText(t("heatmap_title"))
        self._heatmap_sub_lbl.setText(t("heatmap_sub"))
        self._legend_low_health_lbl.setText(t("legend_low_health"))
        self._legend_hi_lbl.setText(t("legend_hi"))
        self._tips_title_lbl.setText(t("tips_title"))
        for wt, wd, title_key, desc_key in self._tip_labels:
            wt.setText(t(title_key))
            wd.setText(t(desc_key))
