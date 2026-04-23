"""Dryless design tokens."""

from PyQt6.QtGui import QColor

BRAND = "#4A9E80"
BRAND_DIM = "rgba(74,158,128,38)"
BRAND_MID = "#3D8268"
BRAND_SOFT = "#E8F2EC"

ALERT_LEVELS = [
    {"c": "#D4A020", "bg": "rgba(212,160,32,36)", "label": "Mild", "sec": "8s"},
    {"c": "#C96820", "bg": "rgba(201,104,32,36)", "label": "Moderate", "sec": "13s"},
    {"c": "#C04428", "bg": "rgba(192,68,40,36)", "label": "Strong", "sec": "18s"},
    {"c": "#B02828", "bg": "rgba(176,40,40,36)", "label": "Urgent", "sec": "23s+"},
]


def alert_levels():
    """Return alert level metadata with labels translated to current language."""
    from i18n import t

    keys = ["alert_l0", "alert_l1", "alert_l2", "alert_l3"]
    return [dict(lvl, label=t(keys[i])) for i, lvl in enumerate(ALERT_LEVELS)]


S_BG = "#101010"
S_BORDER = "#222222"
S_TEXT = "#EAEAEA"
S_TEXT_DIM = "#8A8A8A"
S_HOVER = "#1E1E1E"
S_ACTIVE = "#2D2D2D"

C_BG = "#F5F3EE"
C_SURFACE = "#FFFFFF"
C_BORDER = "#E4DFD8"
C_TEXT = "#1A1816"
C_TEXT2 = "#7C766F"
C_TEXT3 = "#AEA89F"
C_CARD = "#FFFFFF"
C_TITLEBAR = "#F7F5F0"

WARN = "#C8901A"
DANGER = "#C05050"

R_WINDOW = 14
R_CARD = 10
R_SM = 7
R_XS = 5

FONT_UI = "Inter"
FONT_FB = ["Microsoft YaHei UI", "PingFang SC", "Segoe UI", "sans-serif"]
FONT_MONO = "Consolas"


def qc(hex_str: str) -> QColor:
    return QColor(hex_str)


def qc_alpha(hex_str: str, alpha: int) -> QColor:
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


def rgba(hex_str: str, alpha_f: float) -> str:
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    a = max(0.0, min(1.0, float(alpha_f)))
    return f"rgba({r},{g},{b},{a:.3f})"
