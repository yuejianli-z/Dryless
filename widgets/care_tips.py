"""Quiet, fixed-height eye-care carousel; no action buttons or notifications."""
from PyQt6.QtCore import Qt, QTimer, QEvent, QRectF
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QFrame, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication
import config
import theme as T
from microbreak import PRESENCE_MINUTES
from widgets.soft_icon import SoftIcon

# Reviewed 2026-09-13. Concise paraphrases of patient-facing eye-care guidance.
SOURCES = (
    'https://www.worcsacute.nhs.uk/leaflets/dry-eye-and-blepharitis-treatment-guide/',
    'https://www.mayoclinic.org/diseases-conditions/eyestrain/diagnosis-treatment/drc-20372403',
    'https://www.gloshospitals.nhs.uk/your-visit/patient-information-leaflets/dry-eye/',
)
TIPS = (
    ('eye', ('自然轻眨', 'Gentle blinks'),
     ('轻柔地完整眨眼，让上下眼睑自然闭合。', 'Blink gently, letting your eyelids close fully.')),
    ('distance', ('远眺休息', 'Look away'),
     (f'每 {PRESENCE_MINUTES} 分钟，看约 6 米远处至少 20 秒。', f'Every {PRESENCE_MINUTES} min, look 6 m away for at least 20 sec.')),
    ('eye_closed', ('短暂闭眼', 'Rest your eyes'),
     ('用眼间隙，轻闭双眼 10 秒，再自然睁开。', 'Between tasks, close your eyes gently for 10 sec.')),
)

class _Pages(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.index = 0
        self.setFixedSize(len(TIPS) * 12 + 2, 12)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(len(TIPS)):
            p.setBrush(QColor(T.BRAND if i == self.index else T.C_BORDER))
            p.drawRoundedRect(QRectF(i * 12, 3, 10 if i == self.index else 5, 5), 2.5, 2.5)

class CareTips(QFrame):
    INTERVAL_MS = 20000
    def __init__(self, parent=None):
        super().__init__(parent)
        self._index = 0
        self._hovered = False
        self._alert_active = False
        self._tracked_window = None
        self.setObjectName('CareTips')
        self.setFixedHeight(106)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(f'QFrame#CareTips{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}'
                          f'QFrame#CareTips:focus{{border-color:{T.CONTROL_FOCUS};}}')
        layout = QVBoxLayout(self); layout.setContentsMargins(14, 10, 14, 12); layout.setSpacing(7)
        heading = QHBoxLayout(); heading.setContentsMargins(0,0,0,0)
        self._caption = QLabel(); self._caption.setFont(T.ui_font(11, 500))
        self._caption.setStyleSheet(f'color:{T.C_TEXT2};background:transparent;')
        self._caption.setFixedHeight(16)
        self._pages = _Pages()
        heading.addWidget(self._caption); heading.addStretch(); heading.addWidget(self._pages)
        layout.addLayout(heading)
        content = QHBoxLayout(); content.setSpacing(12)
        self._icon = SoftIcon('eye', size=38, glyph_size=25)
        self._icon.setObjectName('TipIcon')
        content.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QVBoxLayout(); text.setContentsMargins(0,0,0,0); text.setSpacing(2)
        self._title = QLabel(); self._title.setFont(T.ui_font(15, 600)); self._title.setFixedHeight(21)
        self._title.setStyleSheet(f'color:{T.C_TEXT};background:transparent;')
        self._body = QLabel(); self._body.setFont(T.ui_font(13)); self._body.setWordWrap(True)
        self._body.setFixedHeight(36); self._body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._body.setStyleSheet(f'color:{T.C_TEXT2};background:transparent;')
        text.addWidget(self._title); text.addWidget(self._body); content.addLayout(text,1)
        layout.addLayout(content)
        self._timer = QTimer(self); self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._advance)
        self.retranslate()

    def retranslate(self):
        lang = 0 if config.LANGUAGE == 'zh' else 1
        glyph, title, body = TIPS[self._index]
        self._caption.setText(('护眼小贴士', 'EYE CARE')[lang])
        self._title.setText(title[lang]); self._body.setText(body[lang])
        self._icon._name = glyph; self._icon.update()
        self._pages.index = self._index; self._pages.update()
        self.setAccessibleName(('护眼小贴士', 'Eye-care tip')[lang] + f' {self._index+1}/{len(TIPS)} · ' + title[lang])
        self.setAccessibleDescription(body[lang])
        self.setToolTip('')

    def _can_rotate(self):
        return self.isVisible() and not self.window().isMinimized() and not self._hovered and not self.hasFocus() and not self._alert_active

    def _sync_timer(self):
        if self._can_rotate():
            if not self._timer.isActive(): self._timer.start()
        else:
            self._timer.stop()

    def _advance(self):
        if self._can_rotate():
            self._index = (self._index + 1) % len(TIPS)
            self.retranslate()

    def setAlertActive(self, active):
        self._alert_active = bool(active); self._sync_timer()

    def enterEvent(self, event):
        self._hovered = True; self._sync_timer(); super().enterEvent(event)
    def leaveEvent(self, event):
        self._hovered = False; self._sync_timer(); super().leaveEvent(event)
    def focusInEvent(self, event):
        self._sync_timer(); super().focusInEvent(event)
    def focusOutEvent(self, event):
        super().focusOutEvent(event); self._sync_timer()
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._index = (self._index + (1 if event.key() == Qt.Key.Key_Right else -1)) % len(TIPS)
            self.retranslate(); event.accept()
        else: super().keyPressEvent(event)
    def showEvent(self, event):
        super().showEvent(event)
        if self._tracked_window is not self.window():
            if self._tracked_window: self._tracked_window.removeEventFilter(self)
            self._tracked_window = self.window(); self._tracked_window.installEventFilter(self)
        self._hovered = self.underMouse()
        self._sync_timer()
    def hideEvent(self, event):
        self._timer.stop(); super().hideEvent(event)
    def eventFilter(self, watched, event):
        if watched is self._tracked_window and event.type() == QEvent.Type.WindowStateChange:
            self._sync_timer()
        return super().eventFilter(watched, event)
