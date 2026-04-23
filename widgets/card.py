"""Rounded light card container with a subtle border."""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import theme as T


class Card(QFrame):
    """对齐设计稿的 Card 原语。"""
    def __init__(self, parent=None, padding=(16, 18, 16, 18)):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            f"QFrame#Card {{"
            f"  background: {T.C_CARD};"
            f"  border: 1px solid {T.C_BORDER};"
            f"  border-radius: {T.R_CARD}px;"
            f"}}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(padding[0], padding[1], padding[2], padding[3])
        lay.setSpacing(0)
        self._lay = lay

    def layout(self):
        return self._lay


class SectionLabel(QLabel):
    """小节标题：#AEA89F 大写轻字距。"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:10px;"
            f"letter-spacing:1px; font-weight:500;"
            f"background:transparent; border:none;"
        )
