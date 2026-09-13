"""Consistent, keyboard-accessible native selection menus and date popovers."""
from PyQt6.QtCore import QDate, QLocale, QPoint, QPointF, QRectF, QSize, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTextCharFormat
from PyQt6.QtWidgets import (
    QCalendarWidget, QComboBox, QDateEdit, QMenu, QProxyStyle, QStyle,
    QStyleOptionMenuItem, QToolButton, QVBoxLayout, QWidget,
)

import config
import theme as T


def _popup_position(popup, anchor):
    popup.ensurePolished()
    popup.adjustSize()
    owner = anchor.window()
    while owner.parentWidget() is not None and owner.windowType() == Qt.WindowType.Popup:
        owner = owner.parentWidget().window()
    bounds = owner.frameGeometry().intersected(anchor.screen().availableGeometry()).adjusted(8, 8, -8, -8)
    size = popup.sizeHint().expandedTo(popup.minimumSize())
    width = min(max(size.width(), anchor.width()), bounds.width())
    height = min(size.height(), bounds.height())
    popup.resize(width, height)
    below = anchor.mapToGlobal(QPoint(0, anchor.height() + 5))
    above = anchor.mapToGlobal(QPoint(0, -5-height))
    x = max(bounds.left(), min(below.x(), bounds.right()-width+1))
    y = below.y() if below.y()+height <= bounds.bottom()+1 else above.y()
    y = max(bounds.top(), min(y, bounds.bottom()-height+1))
    return QPoint(x, y)


class _MenuStyle(QProxyStyle):
    def __init__(self, parent):
        super().__init__('Fusion')
        self.setParent(parent)

    def sizeFromContents(self, kind, option, size, widget=None):
        result = super().sizeFromContents(kind, option, size, widget)
        if kind == QStyle.ContentsType.CT_MenuItem:
            if option.menuItemType == QStyleOptionMenuItem.MenuItemType.Separator:
                return QSize(result.width(), 9)
            return QSize(max(result.width(), option.fontMetrics.horizontalAdvance(option.text)+52), 32)
        return result


class StyledMenu(QMenu):
    """QMenu behavior with a rounded surface, consistent rows and check marks."""
    def __init__(self, parent=None, font=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._row_style = _MenuStyle(self)
        self.setStyle(self._row_style)
        self.setStyleSheet('QMenu{background:transparent;border:0;padding:6px;} QMenu::item{height:32px;min-height:32px;min-width:106px;padding:0 30px 0 12px;border:0;background:transparent;}')
        if font is not None:
            self.setFont(QFont(font))
        self.setMouseTracking(True)

    def sizeHint(self):
        hint = super().sizeHint()
        text_width = max((self.fontMetrics().horizontalAdvance(action.text()) +
                          (24 if not action.icon().isNull() else 0)
                          for action in self.actions() if not action.isSeparator()), default=0)
        return QSize(max(160, hint.width(), text_width+54), hint.height())

    def popup_below(self, anchor):
        self.setMinimumWidth(max(anchor.width(), self.minimumWidth()))
        self.popup(_popup_position(self, anchor))
        checked = next((action for action in self.actions() if action.isChecked()), None)
        if checked is not None:
            self.setActiveAction(checked)

    def showEvent(self, event):
        super().showEvent(event)
        anchor = self.parentWidget()
        if isinstance(anchor, QToolButton):
            QTimer.singleShot(0, lambda: self.move(_popup_position(self, anchor)) if self.isVisible() else None)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(T.C_BORDER), 1))
        painter.setBrush(QColor(T.C_CARD))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 10, 10)
        painter.setFont(self.font())
        for action in self.actions():
            if not action.isVisible():
                continue
            rect = QRectF(self.actionGeometry(action))
            if not rect.intersects(QRectF(self.rect())):
                continue
            if action.isSeparator():
                painter.setPen(QPen(QColor(T.C_BORDER), 1))
                painter.drawLine(QPointF(rect.left()+8, rect.center().y()), QPointF(rect.right()-8, rect.center().y()))
                continue
            checked = action.isChecked()
            active = action == self.activeAction() and action.isEnabled()
            if checked or active:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(T.BRAND_SOFT if checked else T.C_SURFACE))
                painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(QColor(T.C_TEXT if action.isEnabled() else T.C_TEXT3))
            text_rect = rect.adjusted(12, 0, -30, 0)
            text = action.text().replace('&&', '\0').replace('&', '').replace('\0', '&')
            if not action.icon().isNull():
                action.icon().paint(painter, int(text_rect.left()), int(rect.center().y()-8), 16, 16)
                text_rect.adjust(24, 0, 0, 0)
            centered = bool(self.parentWidget() and self.parentWidget().property('centerMenuText'))
            if centered:
                text_rect = rect.adjusted(30, 0, -30, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter if centered else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            if checked:
                painter.setPen(QPen(QColor(T.BRAND), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                x, y = rect.right()-17, rect.center().y()
                painter.drawLine(QPointF(x-4, y), QPointF(x-1, y+3))
                painter.drawLine(QPointF(x-1, y+3), QPointF(x+5, y-4))
            elif action.menu() is not None:
                painter.setPen(QPen(QColor(T.C_TEXT2), 1.4))
                x, y = rect.right()-15, rect.center().y()
                painter.drawLine(QPointF(x-2, y-4), QPointF(x+2, y))
                painter.drawLine(QPointF(x+2, y), QPointF(x-2, y+4))


def build_menu(parent=None, font=None):
    return StyledMenu(parent, font)


class StyledComboBox(QComboBox):
    """Keep the normal QComboBox model/signals while presenting StyledMenu."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection_menu = None

    def showPopup(self):
        if not self.count() or not self.isEnabled():
            return
        if self._selection_menu is not None:
            self._selection_menu.close()
            self._selection_menu.deleteLater()
        menu = self._selection_menu = build_menu(self, self.font())
        for index in range(self.count()):
            action = menu.addAction(self.itemIcon(index), self.itemText(index))
            action.setData(index)
            action.setCheckable(True)
            action.setChecked(index == self.currentIndex())
            action.setEnabled(bool(self.model().flags(self.model().index(index, self.modelColumn(), self.rootModelIndex())) & Qt.ItemFlag.ItemIsEnabled))
            action.triggered.connect(lambda checked=False, value=index: self._choose(value))
        menu.aboutToHide.connect(lambda: QComboBox.hidePopup(self))
        menu.popup_below(self)

    def _choose(self, index):
        self.setCurrentIndex(index)
        self.activated.emit(index)
        self.textActivated.emit(self.itemText(index))

    def hidePopup(self):
        if self._selection_menu is not None:
            self._selection_menu.hide()
        super().hidePopup()


class _Calendar(QCalendarWidget):
    def paintCell(self, painter, rect, date):
        if date == self.selectedDate():
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(rect, QColor(T.C_CARD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(T.BRAND_SOFT))
            painter.drawRoundedRect(QRectF(rect).adjusted(2, 1, -2, -1), 5, 5)
            painter.setFont(self.font())
            painter.setPen(QColor(T.C_TEXT))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
            painter.restore()
        else:
            super().paintCell(painter, rect, date)


class _CalendarPopup(QWidget):
    def __init__(self, edit):
        super().__init__(edit, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName('DrylessCalendarPopup')
        self.setStyleSheet('QWidget#DrylessCalendarPopup{background:transparent;border:none;}')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.calendar = _Calendar(self)
        self.calendar.setFont(edit.font())
        self.calendar.setMinimumSize(280, 230)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setStyleSheet(
            f'QCalendarWidget QWidget{{background:{T.C_CARD};color:{T.C_TEXT};border:none;}}'
            f'QCalendarWidget QToolButton{{background:transparent;color:{T.C_TEXT};border:none;border-radius:6px;padding:5px;}}'
            f'QCalendarWidget QToolButton:hover{{background:{T.C_SURFACE};}}'
            f'QCalendarWidget QAbstractItemView{{background:{T.C_CARD};color:{T.C_TEXT};selection-background-color:{T.BRAND_SOFT};selection-color:{T.C_TEXT};outline:none;border:none;}}'
            f'QCalendarWidget QSpinBox{{background:{T.C_SURFACE};color:{T.C_TEXT};border:none;border-radius:6px;padding:3px;}}')
        regular = QTextCharFormat()
        regular.setForeground(QColor(T.C_TEXT))
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            self.calendar.setWeekdayTextFormat(day, regular)
        header = self.calendar.headerTextFormat()
        header.setBackground(QColor(T.C_SURFACE))
        header.setForeground(QColor(T.C_TEXT))
        self.calendar.setHeaderTextFormat(header)
        layout.addWidget(self.calendar)
        self.calendar.clicked.connect(edit._choose_date)
        self.calendar.activated.connect(edit._choose_date)
        self._month_menu = None
        self.calendar.currentPageChanged.connect(self._sync_month_check)

    def _sync_month_check(self, year, month):
        if self._month_menu is not None:
            for action in self._month_menu.actions():
                action.setChecked(action.data() == month)

    def update_month_menu(self):
        button = self.calendar.findChild(QToolButton, 'qt_calendar_monthbutton')
        if button is None:
            return
        menu = build_menu(button, self.calendar.font())
        for month in range(1, 13):
            action = menu.addAction(self.calendar.locale().monthName(month))
            action.setData(month)
            action.setCheckable(True)
            action.setChecked(month == self.calendar.monthShown())
            action.triggered.connect(lambda checked=False, value=month: self.calendar.setCurrentPage(self.calendar.yearShown(), value))
        old_menu = self._month_menu
        self._month_menu = menu
        button.setMenu(menu)
        if old_menu is not None:
            old_menu.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(T.C_BORDER), 1))
        painter.setBrush(QColor(T.C_CARD))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 10, 10)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)


class StyledDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._date_popup = None

    def calendarWidget(self):
        if self._date_popup is None:
            self._date_popup = _CalendarPopup(self)
        return self._date_popup.calendar

    def _show_calendar(self):
        calendar = self.calendarWidget()
        calendar.setFont(self.font())
        calendar.setLocale(QLocale('zh_CN' if str(config.LANGUAGE).startswith('zh') else 'en_US'))
        calendar.setDateRange(self.minimumDate(), self.maximumDate())
        calendar.setSelectedDate(self.date())
        calendar.setCurrentPage(self.date().year(), self.date().month())
        self._date_popup.update_month_menu()
        self._date_popup.move(_popup_position(self._date_popup, self))
        self._date_popup.show()
        calendar.setFocus(Qt.FocusReason.PopupFocusReason)

    def _choose_date(self, date):
        self.setDate(date)
        self._date_popup.hide()
        self.setFocus(Qt.FocusReason.PopupFocusReason)

    def mousePressEvent(self, event):
        if self.calendarPopup() and event.button() == Qt.MouseButton.LeftButton and event.position().x() >= self.width()-28:
            self._show_calendar()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self.calendarPopup() and (event.key() == Qt.Key.Key_F4 or
                (event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.AltModifier)):
            self._show_calendar()
            event.accept()
            return
        super().keyPressEvent(event)
