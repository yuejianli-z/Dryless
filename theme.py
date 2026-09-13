"""Dryless design tokens."""

from PyQt6.QtGui import QColor, QFont

BRAND = "#355A48"
SUCCESS = "#448361"
BRAND_DIM = "rgba(63,108,86,25)"
BRAND_MID = "#355A48"
BRAND_HOVER = "#294B3A"
CONTROL_BORDER = "#B8C8BD"
CONTROL_FOCUS = "#8AA594"
BRAND_SOFT = "#DDE9E1"

ALERT_LEVELS = [
    {"c": "#D4A020", "bg": "rgba(212,160,32,36)", "label": "Mild", "sec": "8s"},
    {"c": "#C96820", "bg": "rgba(201,104,32,36)", "label": "Moderate", "sec": "13s"},
    {"c": "#C04428", "bg": "rgba(192,68,40,36)", "label": "Strong", "sec": "18s"},
]


def alert_levels():
    """Return alert level metadata with labels translated to current language."""
    from i18n import t

    keys = ["alert_l0", "alert_l1", "alert_l2"]
    import config
    return [dict(lvl, label=t(keys[i]), sec=f"{config.NO_BLINK_ALERT_SEC + i * config.ALERT_INTERVAL_SEC}s" + ("+" if i == 2 else "")) for i, lvl in enumerate(ALERT_LEVELS)]


S_BG = "#E8EEE7"
S_BORDER = "#DFE6DC"
S_TEXT = "#314D3D"
S_TEXT_DIM = "#6A7D70"
S_HOVER = "#DFE8DC"
S_ACTIVE = "#D7E3D2"

C_BG = "#F1F5EF"
C_SURFACE = "#E8EEE5"
C_BORDER = "#DFE6DC"
C_TEXT = "#1A1A1A"
C_TEXT2 = "#626B60"
C_TEXT3 = "#798174"
C_CARD = "#FAFCF8"
C_TITLEBAR = "#F1F5EF"

WARN = "#C8901A"
DANGER = "#C05050"

R_WINDOW = 18
R_CARD = 18
R_SM = 8
R_XS = 6

FONT_UI = "Dryless Sans"
FONT_FB = ["Microsoft YaHei UI", "Dryless CJK", "PingFang SC", "Segoe UI", "sans-serif"]
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

ICON_BG = "#E3EBDE"
ICON_FG = "#4A6858"

MATTE_TOP = "#EBF0E8"
MATTE_BOTTOM = "#E5ECE2"
CARD_FILL = C_CARD


# Desktop reading hierarchy, in logical pixels. Keep the shared font metrics
# and natural tracking; display/brand typography is deliberately independent.
TYPE_NAV = 16
TYPE_SECTION = 16
TYPE_BODY = 14
TYPE_CONTROL = 14
TYPE_CAPTION = 13

def ui_font(size=13, weight=400):
    """Use one type policy for widgets and charts, retaining fractional advances."""
    font = QFont(FONT_UI)
    font.setFamilies([FONT_UI] + FONT_FB)
    font.setPixelSize(int(size))
    font.setWeight(QFont.Weight(int(weight)))
    # Full hinting rounds horizontal glyph metrics differently at each size.
    # Light vertical hinting retains clear strokes and the designed spacing.
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    return font
