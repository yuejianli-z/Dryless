"""Saved blink history with a day/week/month bubble timeline."""
import csv
import json
import math
import os
import tempfile
from datetime import date, timedelta

from PyQt6.QtCore import QDate, QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QDateEdit, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

import config
import history_store
import theme as T
from stats_data import aggregate_periods, choose_grain, normalize_history
from widgets import Card
from widgets.selection_popup import StyledComboBox, StyledDateEdit
from widgets.soft_icon import SoftIcon
from widgets.time_bubble_chart import TimeBubbleChart


def _tr(zh, en):
    return zh if str(getattr(config, "LANGUAGE", "zh")).startswith("zh") else en


def _fnt(size, weight=400):
    font = T.ui_font()
    font.setFamilies([T.FONT_UI] + T.FONT_FB)
    font.setPixelSize(max(12, int(size)))
    font.setWeight({400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
                    600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold}[weight])
    return font


def _label(text="", size=T.TYPE_CAPTION, weight=400, color=None):
    label = QLabel(text)
    label.setFont(_fnt(size, weight))
    label.setStyleSheet(f"color:{color or T.C_TEXT};background:transparent;border:none;")
    return label


def _reserve_width(widget, *translations, padding=0):
    """Language changes replace text inside a slot sized for both translations."""
    width = max(widget.fontMetrics().horizontalAdvance(text) for text in translations) + padding
    widget.setFixedWidth(width)


def _duration(minutes):
    hours, mins = divmod(int(minutes), 60)
    if not hours:
        return _tr(f"{mins} 分钟", f"{mins} min")
    return _tr(f"{hours:,} 小时" + (f" {mins} 分" if mins else ""),
               f"{hours:,} h" + (f" {mins} m" if mins else ""))


def _read_history():
    source = getattr(history_store, "_DATA_FILE", None)
    if source is None:
        return history_store._load_raw()
    try:
        with open(source, "r", encoding="utf-8") as history:
            return json.load(history)
    except FileNotFoundError:
        return {"days": {}}


class _ComboBox(StyledComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(T.C_TEXT2), 1.4))
        x, y = self.width() - 13, self.height() / 2
        painter.drawLine(QPointF(x - 4, y - 2), QPointF(x, y + 2))
        painter.drawLine(QPointF(x, y + 2), QPointF(x + 4, y - 2))


class _ElidedLabel(QLabel):
    """A single-line status whose full message remains available on hover."""
    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self._update_text()

    def _update_text(self):
        text = getattr(self, "_full_text", "")
        super().setText(self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(0, self.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_text()


class _MetricNumberRow(QWidget):
    """Align mixed font sizes on their actual text baseline."""
    def __init__(self, labels):
        super().__init__()
        self._labels = labels
        self.setFixedHeight(35)
        for label in labels:
            label.setParent(self)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            label.show()

    def sizeHint(self):
        visible = [label for label in self._labels if not label.isHidden()]
        return QSize(sum(max(label.minimumWidth(), label.sizeHint().width()) for label in visible) + max(0, len(visible)-1)*4, 35)

    def place(self):
        visible = [label for label in self._labels if not label.isHidden()]
        baseline = self.height() - max((label.fontMetrics().descent() for label in visible), default=0)
        x = 0
        for label in visible:
            metrics = label.fontMetrics()
            width = max(label.minimumWidth(), label.sizeHint().width())
            label.setGeometry(x, baseline-metrics.ascent(), width, metrics.height())
            x += width + 4
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place()


class _Metric(Card):
    """One restrained metric: a label above numbers and smaller baseline units."""
    def __init__(self, icon_name):
        super().__init__(padding=(14, 8, 14, 8))
        self.setFixedHeight(80)
        self.setStyleSheet(
            f"QFrame#Card{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}")
        self.setMinimumWidth(145)
        self._title = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._title.setFixedHeight(20)
        self._value = _label("—", 27, 500)
        self._unit = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._secondary_value = _label(size=27, weight=500)
        self._secondary_unit = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        _reserve_width(self._secondary_unit, "分", "m")
        self._number_row = _MetricNumberRow((self._value, self._unit, self._secondary_value, self._secondary_unit))
        self._note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._note.hide()
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._icon = SoftIcon(icon_name, size=24, glyph_size=14)
        title_row.addWidget(self._icon)
        title_row.addWidget(self._title, 1)
        self.layout().addLayout(title_row)
        self.layout().addSpacing(3)
        self.layout().addWidget(self._number_row)
        self._number_row.setStyleSheet("background:transparent;border:none;")

    def set_content(self, title, value, note):
        self._title.setText(title)
        self._value.setText(value)
        self._note.setText(note)
        for label in (self._unit, self._secondary_value, self._secondary_unit):
            label.clear()
            label.hide()
        self.setToolTip(note)
        self.setAccessibleName(f"{title}: {value}. {note}")
        self._number_row.place()

    def set_unit(self, unit, translations=None):
        if translations:
            _reserve_width(self._unit, *translations)
        self._unit.setText(unit)
        self._unit.setVisible(bool(unit))
        self._number_row.place()

    def set_duration(self, minutes):
        hours, remainder = divmod(int(minutes), 60)
        self._value.setText(f"{hours:,}" if hours else str(remainder))
        self.set_unit(_tr("小时", "h") if hours else _tr("分钟", "min"), ("小时", "h") if hours else ("分钟", "min"))
        if hours and remainder:
            self._secondary_value.setText(str(remainder))
            self._secondary_unit.setText(_tr("分", "m"))
            self._secondary_value.show()
            self._secondary_unit.show()
        self.setAccessibleName(f"{self._title.text()}: {_duration(minutes)}. {self._note.text()}")
        self._number_row.place()


class StatsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._range = "30"
        self._grain = "auto"
        self._year = date.today().year
        self._start = date.today() - timedelta(days=29)
        self._end = date.today()
        self._synced_date_range = None
        self._days = {}
        self._points = []
        self._history = []
        self._skipped = 0
        self._load_error = False
        self._export_message = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.page_header = QWidget(self)
        self.page_header.setFixedHeight(36)
        header = QHBoxLayout(self.page_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        header.addWidget(SoftIcon("chart", size=26, glyph_size=15))
        self._title = _label(size=24, weight=600)
        self._title.setFixedHeight(36)
        header.addWidget(self._title, 1)
        self._export_button = self._button()
        _reserve_width(self._export_button, "导出 CSV", "Export CSV", padding=24)
        self._export_button.clicked.connect(self._export_csv)
        header.addWidget(self._export_button)
        self._range_label = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._range_label.setFixedHeight(20)
        root.addWidget(self._range_label)

        self._metrics_frame = QFrame()
        self._metrics_frame.setObjectName("StatsMetrics")
        self._metrics_frame.setStyleSheet(
            "QFrame#StatsMetrics{background:transparent;border:none;}")
        metrics = QHBoxLayout(self._metrics_frame)
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(10)
        self._metrics = [_Metric(name) for name in ("eye", "clock", "calendar", "activity")]
        for metric in self._metrics:
            metrics.addWidget(metric, 1)
        root.addWidget(self._metrics_frame)

        chart_card = Card(padding=(16, 16, 16, 16))
        chart_card.setObjectName("StatsChart")
        chart_card.setStyleSheet(
            f"QFrame#StatsChart{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}")
        controls = QHBoxLayout()
        controls.setSpacing(10)
        range_frame = QFrame()
        range_frame.setObjectName("HistoryRange")
        range_frame.setStyleSheet(f"QFrame#HistoryRange{{background:{T.C_SURFACE};border-radius:{T.R_SM}px;}}")
        ranges = QHBoxLayout(range_frame)
        ranges.setContentsMargins(3, 3, 3, 3)
        ranges.setSpacing(2)
        self._range_group = QButtonGroup(self)
        self._range_buttons = {}
        for key in ("30", "year", "all", "custom"):
            button = self._button()
            button.setCheckable(True)
            button.setFixedHeight(30)
            translations = {"30": ("近30天", "30 days"), "year": ("整年", "Year"),
                            "all": ("全部", "All time"), "custom": ("自定义", "Custom")}[key]
            _reserve_width(button, *translations, padding=24)
            button.setStyleSheet(
                f"QPushButton{{background:transparent;color:{T.C_TEXT2};border:1px solid transparent;"
                "border-radius:6px;padding:3px 10px;}"
                f"QPushButton:hover{{background:{T.C_BG};color:{T.C_TEXT};}}"
                f"QPushButton:checked{{background:{T.C_CARD};color:{T.C_TEXT};}}"
                f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}")
            button.clicked.connect(lambda checked=False, value=key: self._range_changed(value))
            self._range_group.addButton(button)
            self._range_buttons[key] = button
            ranges.addWidget(button)
        controls.addWidget(range_frame)
        self._year_combo = self._combo()
        self._year_combo.setFixedWidth(88)
        self._year_combo.currentIndexChanged.connect(self._year_changed)
        controls.addWidget(self._year_combo)
        controls.addStretch(1)
        self._grain_label = _label(color=T.C_TEXT2)
        self._grain_label.setFixedHeight(20)
        _reserve_width(self._grain_label, "气泡粒度", "Group by", padding=2)
        controls.addWidget(self._grain_label)
        self._grain_combo = self._combo()
        self._grain_combo.setFixedWidth(156)
        self._grain_combo.currentIndexChanged.connect(self._grain_changed)
        controls.addWidget(self._grain_combo)
        chart_card.layout().addLayout(controls)
        chart_card.layout().addSpacing(8)

        self._custom = QWidget()
        self._custom.setStyleSheet("background:transparent;border:none;")
        custom = QHBoxLayout(self._custom)
        custom.setContentsMargins(0, 0, 0, 0)
        custom.setSpacing(10)
        self._from_label = _label(color=T.C_TEXT2)
        self._from_label.setFixedHeight(20)
        _reserve_width(self._from_label, "从", "From", padding=2)
        custom.addWidget(self._from_label)
        self._start_edit = self._date_edit()
        self._end_edit = self._date_edit()
        custom.addWidget(self._start_edit)
        self._to_label = _label(color=T.C_TEXT2)
        self._to_label.setFixedHeight(20)
        _reserve_width(self._to_label, "至", "To", padding=2)
        custom.addWidget(self._to_label)
        custom.addWidget(self._end_edit)
        self._apply_button = self._button()
        _reserve_width(self._apply_button, "查看", "Apply", padding=24)
        self._apply_button.clicked.connect(self._apply_dates)
        custom.addWidget(self._apply_button)
        self._date_error = _label(color=T.WARN)
        self._date_error.setFixedHeight(20)
        _reserve_width(self._date_error, "开始日期需早于结束日期", "Start must precede end", padding=2)
        custom.addWidget(self._date_error)
        custom.addStretch(1)
        chart_card.layout().addWidget(self._custom)
        chart_card.layout().addSpacing(8)
        chart_heading = QHBoxLayout()
        chart_heading.setSpacing(10)
        self._back_button = self._button()
        _reserve_width(self._back_button, "← 返回", "← Back", padding=24)
        self._back_button.setMinimumHeight(26)
        self._back_button.clicked.connect(self._go_back)
        chart_heading.addWidget(self._back_button)
        self._chart_title = _label(size=T.TYPE_SECTION, weight=600)
        self._chart_title.setFixedHeight(24)
        self._chart_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        chart_heading.addWidget(self._chart_title, 1)
        self._chart_hint = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._chart_hint.setFixedHeight(20)
        _reserve_width(self._chart_hint, "每小时", "Hourly", "每天", "Daily", "每周", "Weekly", "每月", "Monthly", padding=2)
        self._chart_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        chart_heading.addWidget(self._chart_hint)
        self._help_button = self._button()
        self._help_button.setFixedSize(26, 26)
        self._help_button.setText("?")
        self._help_button.setStyleSheet(
            f"QPushButton{{color:{T.C_TEXT2};background:transparent;border:1px solid {T.C_BORDER};"
            "border-radius:8px;padding:0;}"
            f"QPushButton:hover{{background:{T.C_BG};color:{T.C_TEXT};}}")
        self._help_button.clicked.connect(self._show_chart_help)
        chart_heading.addWidget(self._help_button)
        chart_card.layout().addLayout(chart_heading)
        chart_card.layout().addSpacing(6)
        self._reference_note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._reference_note.setFixedHeight(20)
        self._reference_note.setWordWrap(False)
        self._reference_note.setToolTip('NEI: https://www.nei.nih.gov/eye-health-information/healthy-vision/nei-for-kids/visual-system')
        chart_card.layout().addWidget(self._reference_note)
        chart_card.layout().addSpacing(4)
        self._chart = TimeBubbleChart()
        self._chart.periodClicked.connect(self._drill)
        chart_card.layout().addWidget(self._chart, 1)
        self._empty = QWidget()
        self._empty.setStyleSheet("background:transparent;border:none;")
        empty = QVBoxLayout(self._empty)
        empty.setContentsMargins(20, 12, 20, 12)
        empty.setSpacing(10)
        self._empty.setMinimumHeight(160)
        empty.addStretch(1)
        self._empty_title = _label(size=15, weight=500)
        self._empty_title.setFixedHeight(24)
        self._empty_description = _label(color=T.C_TEXT2)
        self._empty_description.setFixedHeight(40)
        self._empty_description.setWordWrap(True)
        for label in (self._empty_title, self._empty_description):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.addWidget(label)
        empty.addStretch(1)
        chart_card.layout().addWidget(self._empty, 1)
        self._chart_note = _label(color=T.C_TEXT2)
        self._chart_note.setWordWrap(True)
        self._chart_note.hide()
        root.addWidget(chart_card, 1)

        self._explanation = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._explanation.setWordWrap(True)
        self._explanation.hide()
        self._status = _ElidedLabel()
        self._status.setFont(_fnt(12))
        self._status.setStyleSheet(f"color:{T.WARN};background:transparent;border:none;")
        self._status.setFixedHeight(18)
        self._status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        root.addWidget(self._status)
        self._refresh()

    def _button(self):
        button = QPushButton()
        button.setFont(_fnt(T.TYPE_CONTROL, 400))
        button.setFixedHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            f"QPushButton{{background:{T.C_CARD};color:{T.C_TEXT};border:1px solid {T.C_BORDER};"
            "border-radius:8px;padding:4px 10px;}"
            f"QPushButton:hover{{background:{T.C_BG};border-color:{T.CONTROL_BORDER};}}"
            f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}"
            f"QPushButton:disabled{{color:{T.C_TEXT3};background:{T.C_BG};}}")
        return button

    def _combo(self):
        combo = _ComboBox()
        combo.setFont(_fnt(T.TYPE_CONTROL))
        combo.setFixedHeight(32)
        combo.setStyleSheet(
            f"QComboBox{{background:{T.C_CARD};color:{T.C_TEXT};border:1px solid {T.C_BORDER};"
            "border-radius:8px;padding:4px 9px;}"
            "QComboBox::drop-down{border:none;width:23px;background:transparent;}"
            "QComboBox::down-arrow{image:none;}"
            f"QComboBox:focus{{border-color:{T.CONTROL_FOCUS};}}"
            f"QComboBox QAbstractItemView{{background:{T.C_CARD};color:{T.C_TEXT};"
            f"selection-background-color:{T.C_BG};selection-color:{T.C_TEXT};}}")
        return combo

    def _date_edit(self):
        edit = StyledDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy/MM/dd")
        edit.setFont(_fnt(T.TYPE_CONTROL))
        edit.setFixedWidth(132)
        edit.setFixedHeight(32)
        edit.setDateRange(QDate(1900, 1, 1), QDate.currentDate())
        edit.setStyleSheet(f"QDateEdit{{background:{T.C_CARD};border:1px solid {T.C_BORDER};"
                          "border-radius:8px;padding:4px 7px;}"
                          "QDateEdit::drop-down{border:none;width:22px;background:transparent;}")
        return edit

    def _resolve_range(self):
        today = date.today()
        if self._range == "30":
            self._start, self._end = today - timedelta(days=29), today
        elif self._range == "year":
            self._start = date(self._year, 1, 1)
            self._end = min(date(self._year, 12, 31), today)
        elif self._range == "all":
            eligible = [d for d, rows in self._days.items() if rows and d <= today]
            self._start = min(eligible) if eligible else today - timedelta(days=29)
            self._end = today

    def _snapshot(self):
        return self._range, self._grain, self._year, self._start, self._end

    def _range_changed(self, key):
        self._range, self._grain = key, "auto"
        self._history.clear()
        self._export_message = ""
        self._refresh()

    def _year_changed(self, index):
        year = self._year_combo.itemData(index)
        if year is not None:
            self._year = int(year)
            self._history.clear()
            self._resolve_range()
            self._render()

    def _grain_changed(self, index):
        grain = self._grain_combo.itemData(index)
        if grain is not None:
            self._grain = grain
            self._render()

    def _apply_dates(self):
        start, end = self._start_edit.date().toPyDate(), self._end_edit.date().toPyDate()
        if start > end:
            self._date_error.setText(_tr("开始日期需早于结束日期", "Start must precede end"))
            return
        self._start, self._end, self._grain = start, end, "auto"
        self._date_error.clear()
        self._history.clear()
        self._export_message = ""
        self._render()

    def _drill(self, point):
        if self._effective_grain == "hour":
            return
        self._history.append(self._snapshot())
        self._range, self._grain = "custom", "auto"
        self._start = point["start"].date()
        self._end = (point["end"] - timedelta(microseconds=1)).date()
        self._render()

    def _go_back(self):
        if self._history:
            self._range, self._grain, self._year, self._start, self._end = self._history.pop()
            self._render()

    def _refresh(self):
        try:
            self._days, self._skipped = normalize_history(_read_history())
            self._load_error = False
        except (OSError, ValueError, TypeError, OverflowError):
            self._days, self._skipped, self._load_error = {}, 0, True
        self._resolve_range()
        self._render()

    def _sync_controls(self):
        for key, button in self._range_buttons.items():
            button.setChecked(key == self._range)
            button.setText({"30": _tr("近30天", "30 days"), "year": _tr("整年", "Year"),
                            "all": _tr("全部", "All time"), "custom": _tr("自定义", "Custom")}[key])
        today = date.today()
        earliest = min([d.year for d in self._days if d <= today] + [today.year])
        self._year_combo.blockSignals(True)
        self._year_combo.clear()
        for year in range(today.year, max(1899, earliest - 1), -1):
            self._year_combo.addItem(str(year), year)
        self._year_combo.setCurrentIndex(self._year_combo.findData(self._year))
        self._year_combo.blockSignals(False)
        self._year_combo.setVisible(self._range == "year")
        self._year_combo.setAccessibleName(_tr("选择年份", "Choose year"))
        self._grain_label.setText(_tr("气泡粒度", "Group by"))
        self._grain_combo.blockSignals(True)
        self._grain_combo.clear()
        names = {"hour": _tr("小时", "Hour"), "day": _tr("日", "Day"),
                 "week": _tr("周", "Week"), "month": _tr("月", "Month")}
        auto = names[choose_grain(self._start, self._end)]
        self._grain_combo.addItem(_tr(f"自动 · 按{auto}", f"Auto · {auto}"), "auto")
        for key in ("day", "week", "month"):
            self._grain_combo.addItem(_tr(f"按{names[key]}", names[key]), key)
        self._grain_combo.setCurrentIndex(self._grain_combo.findData(self._grain))
        self._grain_combo.blockSignals(False)
        self._grain_combo.setAccessibleName(_tr("每个气泡代表的时间", "Time represented by each bubble"))
        self._custom.setVisible(self._range == "custom")
        date_range = (self._range, self._start, self._end)
        if date_range != self._synced_date_range:
            self._start_edit.setDate(QDate(self._start.year, self._start.month, self._start.day))
            self._end_edit.setDate(QDate(self._end.year, self._end.month, self._end.day))
            self._synced_date_range = date_range
            self._date_error.clear()
        self._from_label.setText(_tr("从", "From"))
        if self._date_error.text():
            self._date_error.setText(_tr("开始日期需早于结束日期", "Start must precede end"))
        self._to_label.setText(_tr("至", "To"))
        self._apply_button.setText(_tr("查看", "Apply"))
        self._back_button.setVisible(bool(self._history))
        self._back_button.setText(_tr("← 返回", "← Back"))

    def _render(self):
        self._sync_controls()
        selected = {d: rows for d, rows in self._days.items() if self._start <= d <= self._end}
        minutes = sum(len(rows) for rows in selected.values())
        total = sum(r["blinks"] for rows in selected.values() for r in rows)
        recorded_days = sum(bool(rows) for rows in selected.values())
        mean = total / minutes if minutes else None
        self._effective_grain = choose_grain(self._start, self._end) if self._grain == "auto" else self._grain
        self._points, unplaced = aggregate_periods(self._days, self._start, self._end, self._effective_grain)
        self._title.setText(_tr("统计", "Statistics"))
        self._range_label.setText(f"{self._start:%Y/%m/%d} — {self._end:%Y/%m/%d}")
        self._export_button.setText(_tr("导出 CSV", "Export CSV"))
        self._export_button.setEnabled(bool(minutes) and not self._load_error)
        self._export_button.setToolTip(_tr("导出当前日期范围内已保存的逐分钟记录", "Export saved minute records in this date range"))
        contents = [
            (_tr("总眨眼", "Total blinks"), f"{total:,}" if minutes else "—", _tr("当前日期范围", "In this date range")),
            (_tr("记录时长", "Recorded time"), _duration(minutes), _tr("按已保存分钟计算", "Based on saved minutes")),
            (_tr("记录天数", "Recorded days"), str(recorded_days), _tr(f"范围共 {(self._end-self._start).days+1:,} 天", f"Of {(self._end-self._start).days+1:,} calendar days")),
            (_tr("记录平均频率", "Recorded average"), f"{mean:.1f}" if mean is not None else "—", _tr("次 / 记录分钟", "Blinks / saved minute")),
        ]
        for metric, content in zip(self._metrics, contents):
            metric.set_content(content[0], "—" if self._load_error else content[1], content[2])
        if not self._load_error:
            self._metrics[1].set_duration(minutes)
            self._metrics[2].set_unit(_tr(f"/ {(self._end-self._start).days+1:,} 天", f"/ {(self._end-self._start).days+1:,} days"), (f"/ {(self._end-self._start).days+1:,} 天", f"/ {(self._end-self._start).days+1:,} days"))
            self._metrics[3].set_unit(_tr("次/分", "/min"), ("次/分", "/min"))
        self._chart_title.setText(_tr("眨眼频率与记录时长", "Blink frequency and recorded time"))
        names = {"hour": _tr("每小时", "Hourly"), "day": _tr("每天", "Daily"),
                 "week": _tr("每周", "Weekly"), "month": _tr("每月", "Monthly")}
        self._chart_hint.setText(names[self._effective_grain])
        day_rates = [sum(r["blinks"] for r in rows) / len(rows) for rows in selected.values() if rows]
        axis_max = max(30, math.ceil(max(day_rates, default=0) / 10) * 10)
        point_mean = sum(p["total"] or 0 for p in self._points) / sum(p["minutes"] for p in self._points) if any(p["minutes"] for p in self._points) else None
        self._chart.set_data(self._points, self._effective_grain, point_mean, axis_max=axis_max)
        self._chart.set_language()
        self._help_button.setAccessibleName(_tr("图表说明", "About this chart"))
        self._help_button.setToolTip(_tr("查看计算方式、颜色与参考范围", "Frequency, colors and reference range"))
        self._reference_note.setText(_tr('浅绿带：一般参考 15–20 次/分   ·   灰虚线：本期记录平均', 'Green band: general reference 15–20/min   ·   Dashed line: recorded average'))
        self._metrics[3].setToolTip(_tr(f'总眨眼 {total:,} ÷ 记录分钟 {minutes:,}。按日、周、月分组不改变同一范围的平均。', f'{total:,} blinks ÷ {minutes:,} saved minutes. Grouping does not change the average.'))
        has_points = any(p["minutes"] for p in self._points)
        self._chart.setVisible(has_points and not self._load_error)
        self._empty.setVisible(not has_points or self._load_error)
        self._empty_title.setText(_tr("这段时间还没有记录", "No records in this period"))
        self._empty_description.setText(_tr("试试其他日期范围，或使用 Dryless 开始积累记录。", "Try another date range, or use Dryless to start recording."))
        if self._load_error:
            self._empty_title.setText(_tr("暂时无法读取记录", "History could not be read"))
            self._empty_description.setText(_tr("历史文件暂时无法读取或解析，原文件未修改。", "The history file could not be read or parsed. It was not changed."))
        elif minutes and not has_points:
            self._empty_title.setText(_tr("这些记录缺少小时信息", "These records have no hourly timestamps"))
            self._empty_description.setText(_tr("切换到按日、周或月，可以查看已有记录。", "Switch to day, week or month to view these records."))
        self._chart_note.setText(_tr(
            "悬停查看数值 · 点击气泡展开 · 空白表示无记录，0 次记录保留 · 虚线轮廓表示部分周期",
            "Hover for values · Click to explore · Gaps mean no records; recorded zeroes remain · Dashed outline: partial period"))
        self._chart_note.hide()
        self._explanation.setText(_tr(
            "频率 = 总眨眼 ÷ 记录分钟；面积表示累计记录时长。历史记录包含未识别人脸时段；参考带不代表个人健康范围。",
            "Frequency = total blinks ÷ saved minutes; area shows recorded time. Saved history includes untracked time. The reference band is not a personal health assessment."))
        messages = []
        if self._skipped:
            messages.append(_tr(f"已跳过 {self._skipped} 条格式异常的记录", f"Skipped {self._skipped} invalid records"))
        if unplaced:
            messages.append(_tr(f"{unplaced} 条记录缺少有效时间，仅小时图未计入；日/周/月及导出均保留", f"{unplaced} records lack valid times: excluded only from hourly points, retained in daily/weekly/monthly views and export"))
        if self._export_message:
            messages.append(self._export_message)
        self._status.setText(" · ".join(messages))
        self._status.setVisible(bool(messages))

    def _show_chart_help(self):
        message = _tr(
            "频率 = 总眨眼次数 ÷ 已保存分钟数。同一日期范围按日、周或月分组，平均值不变。\n\n"
            "气泡面积表示记录时长；红 → 黄 → 绿表示频率从低到高，不代表越高越健康。\n\n"
            "浅绿带固定为一般参考 15–20 次/分；灰色虚线随当前记录平均值变化。一般参考不代表个人健康范围。\n\n"
            "空白表示无记录，真实 0 次记录保留。历史记录可能包含未识别人脸的时段。\n\n"
            "悬停查看数值，点击气泡展开更短周期；虚线轮廓表示仅覆盖部分周期。\n\n"
            "一般参考来源：NEI · Visual System",
            "Frequency = total blinks ÷ saved minutes. Changing day/week/month grouping does not change the average for the same date range.\n\n"
            "Bubble area represents recorded time. Red → yellow → green shows lower to higher frequency, not a health score.\n\n"
            "The pale green band is a fixed general reference of 15–20/min. The dashed line follows the recorded average. The reference is not a personal health assessment.\n\n"
            "Gaps mean no records; real zeroes remain. Older saved records may include untracked time.\n\n"
            "Hover for values; click a bubble to explore. Dashed outlines mark partial periods.\n\n"
            "General reference: NEI · Visual System")
        QMessageBox.information(self, _tr("图表说明", "About this chart"), message)

    def _export_rows(self):
        return [[d.isoformat(), item["record_index"], item["minute"], item["time"], item["blinks"]]
                for d, records in sorted(self._days.items()) if self._start <= d <= self._end
                for item in records]

    def _export_csv(self):
        self._refresh()
        rows = self._export_rows()
        if not rows or self._load_error:
            return
        filename = f"dryless-minutes-{self._start}-{self._end}.csv"
        target, _ = QFileDialog.getSaveFileName(self, _tr("导出分钟记录", "Export minute records"), filename,
                                               _tr("CSV 文件 (*.csv)", "CSV files (*.csv)"))
        if not target:
            return
        if not target.lower().endswith(".csv"):
            target += ".csv"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                             dir=os.path.dirname(os.path.abspath(target)),
                                             prefix=".dryless-export-", suffix=".tmp", delete=False) as output:
                temporary = output.name
                writer = csv.writer(output)
                writer.writerow(["date", "record_index", "minute", "time", "blinks"])
                writer.writerows(rows)
            os.replace(temporary, target)
        except (OSError, csv.Error, TypeError, ValueError) as error:
            if temporary and os.path.exists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass
            QMessageBox.warning(self, _tr("导出失败", "Export failed"),
                                _tr(f"无法保存 CSV：\n{error}", f"Could not save the CSV:\n{error}"))
            return
        self._export_message = _tr(f"已导出 {len(rows):,} 条分钟记录 · {os.path.basename(target)}",
                                   f"Exported {len(rows):,} minute records · {os.path.basename(target)}")
        self._render()

    def update_stats(self):
        self._refresh()

    def retranslate(self):
        self._export_message = ""
        self._render()
