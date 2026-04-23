"""Settings screen with sliders and a live config preview."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import config
import theme as T
from i18n import t
from widgets import SectionLabel, SliderRow, ToggleRow, Toggle
from config import save_config


def _fnt(size, weight=400):
    f = QFont(T.FONT_UI)
    f.setFamilies([T.FONT_UI] + T.FONT_FB)
    f.setPixelSize(int(size))
    m = {400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
         600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold}
    f.setWeight(m.get(weight, QFont.Weight.Normal))
    return f


class _Section(QWidget):
    def __init__(self, title):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 20)
        v.setSpacing(0)
        self._header = QLabel(title)
        self._header.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:11px; font-weight:500; background:transparent; border:none;"
            f"letter-spacing:1px; padding-bottom:9px;"
            f"border-bottom:1px solid {T.C_BORDER};"
        )
        v.addWidget(self._header)
        v.addSpacing(14)
        self._v = v

    def setTitle(self, title):
        self._header.setText(title)

    def add(self, w):
        self._v.addWidget(w)

    def addSpacing(self, n):
        self._v.addSpacing(n)

    def addLayout(self, l):
        self._v.addLayout(l)


class SettingsScreen(QWidget):
    soundToggled = pyqtSignal(bool)
    languageChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = {
            "alertSec": config.NO_BLINK_ALERT_SEC,
            "intervalSec": config.ALERT_INTERVAL_SEC,
            "sensitivity": config.BLINK_RATIO_THRESHOLD,
            "everyN": config.PROCESS_EVERY_N_FRAMES,
            "sound": True,
            "res": f"{config.CAMERA_WIDTH}×{config.CAMERA_HEIGHT}",
        }

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(28)

        # 左：表单
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 4, 0)
        lv.setSpacing(0)

        # 提醒阈值
        self._s1 = _Section(t("section_alert"))
        self._s_alert = SliderRow(
            t("slider_alert_lbl"), t("slider_alert_tip"),
            5, 20, 1, t("unit_s"),
        )
        self._s_alert.setValue(self._cfg["alertSec"])
        self._s_alert.valueChanged.connect(self._on_alert_sec)
        self._s1.add(self._s_alert)
        self._s1.addSpacing(16)
        self._s_int = SliderRow(
            t("slider_int_lbl"), t("slider_int_tip"),
            3, 10, 1, t("unit_s"),
        )
        self._s_int.setValue(self._cfg["intervalSec"])
        self._s_int.valueChanged.connect(self._on_int_sec)
        self._s1.add(self._s_int)
        lv.addWidget(self._s1)

        # 检测参数
        self._s2 = _Section(t("section_detect"))
        self._s_sens = SliderRow(
            t("slider_sens_lbl"), t("slider_sens_tip"),
            0.4, 0.8, 0.05, "", decimals=2,
        )
        self._s_sens.setValue(self._cfg["sensitivity"])
        self._s_sens.valueChanged.connect(self._on_sens)
        self._s2.add(self._s_sens)
        self._s2.addSpacing(16)
        self._s_n = SliderRow(
            t("slider_n_lbl"), t("slider_n_tip"),
            1, 5, 1, t("unit_frames"),
        )
        self._s_n.setValue(self._cfg["everyN"])
        self._s_n.valueChanged.connect(self._on_n)
        self._s2.add(self._s_n)
        lv.addWidget(self._s2)

        # 声音提醒
        self._s3 = _Section(t("section_sound"))
        self._tg = ToggleRow(t("sound_enable"), t("sound_enable_tip"),
                             self._cfg["sound"])
        self._tg.toggled.connect(self._on_sound)
        self._s3.add(self._tg)
        self._s3.addSpacing(6)
        self._vol_hint = QLabel(t("vol_hint"))
        self._vol_hint.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:11px; background:transparent; border:none;")
        self._s3.add(self._vol_hint)
        self._s3.addSpacing(10)

        self._preview_lbl = QLabel(t("preview_label"))
        self._preview_lbl.setFont(_fnt(13, 500))
        self._preview_lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        self._s3.add(self._preview_lbl)
        self._s3.addSpacing(8)
        prow = QHBoxLayout()
        prow.setSpacing(8)
        self._preview_btns = []
        preview_keys = ["preview_l0", "preview_l1", "preview_l2", "preview_l3"]
        for i, key in enumerate(preview_keys):
            b = QPushButton(f"▶ {t(key)}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{T.C_SURFACE};"
                f"border:1px solid {T.C_BORDER}; border-radius:7px;"
                f"color:{T.C_TEXT2}; font-size:12px; padding:8px 0;}}"
                f"QPushButton:hover{{border-color:{T.BRAND}; color:{T.BRAND};}}"
            )
            b.clicked.connect(lambda _c, lvl=i: self._preview_alert(lvl))
            prow.addWidget(b, 1)
            self._preview_btns.append((b, key))
        self._s3.addLayout(prow)
        lv.addWidget(self._s3)

        # 摄像头
        self._s4 = _Section(t("section_camera"))
        self._cam_hint = QLabel(t("cam_hint"))
        self._cam_hint.setStyleSheet(f"color:{T.C_TEXT3}; font-size:11px; background:transparent; border:none;")
        self._s4.add(self._cam_hint)
        self._s4.addSpacing(12)
        self._resl = QLabel(t("cam_res"))
        self._resl.setFont(_fnt(13, 500))
        self._resl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        self._s4.add(self._resl)
        self._s4.addSpacing(8)
        res_row = QHBoxLayout()
        res_row.setSpacing(8)
        self._res_buttons = {}
        for r in ("640×480", "1280×720", "1920×1080"):
            b = QPushButton(r)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            b.setChecked(r == self._cfg["res"])
            b.clicked.connect(lambda _c, rr=r: self._set_res(rr))
            self._res_buttons[r] = b
            res_row.addWidget(b)
        res_row.addStretch(1)
        self._s4.addLayout(res_row)
        self._refresh_res_btns()
        lv.addWidget(self._s4)

        # 语言
        self._s5 = _Section(t("section_language"))
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        self._lang_buttons = {}
        for code, key in [("zh", "lang_zh"), ("en", "lang_en")]:
            b = QPushButton(t(key))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            b.setChecked(getattr(config, "LANGUAGE", "zh") == code)
            b.clicked.connect(lambda _c, lc=code: self._set_language(lc))
            self._lang_buttons[code] = b
            lang_row.addWidget(b)
        lang_row.addStretch(1)
        self._s5.addLayout(lang_row)
        self._refresh_lang_btns()
        lv.addWidget(self._s5)

        lv.addStretch(1)
        root.addWidget(left, 1)

        # 右：代码预览
        right = QWidget()
        right.setFixedWidth(300)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(10)

        self._config_lbl = QLabel(t("config_label"))
        self._config_lbl.setStyleSheet(
            f"color:{T.C_TEXT3}; font-size:11px; font-weight:500; letter-spacing:1px; background:transparent; border:none;")
        rv.addWidget(self._config_lbl)

        self._code = QLabel()
        self._code.setStyleSheet(
            "background:#1A1816; border-radius:10px; padding:16px 18px;"
            "color:#8A9A86; font-family:Consolas,'Cascadia Code',monospace;"
            "font-size:12px; line-height:2;"
        )
        self._code.setTextFormat(Qt.TextFormat.RichText)
        self._code.setWordWrap(False)
        rv.addWidget(self._code)

        self._hint1 = QLabel()
        self._hint1.setStyleSheet(
            f"background:{T.BRAND_SOFT}; color:{T.BRAND_MID};"
            f"border:1px solid rgba(74,158,128,60);"
            f"border-radius:8px; padding:11px 14px;"
            f"font-size:12.5px; line-height:1.6;"
        )
        self._hint1.setWordWrap(True)
        rv.addWidget(self._hint1)

        self._hint2 = QLabel()
        self._hint2.setStyleSheet(
            f"background:{T.C_BG}; color:{T.C_TEXT2};"
            f"border:1px solid {T.C_BORDER};"
            f"border-radius:8px; padding:11px 14px;"
            f"font-size:12px; line-height:1.6;"
        )
        self._hint2.setWordWrap(True)
        rv.addWidget(self._hint2)

        rv.addStretch(1)
        root.addWidget(right)

        self._refresh_preview()

    # ── callbacks ───────────────────────────────────
    def _set_cfg(self, k, v):
        self._cfg[k] = v
        self._refresh_preview()

    def _on_alert_sec(self, v):
        config.NO_BLINK_ALERT_SEC = int(v)
        self._set_cfg("alertSec", int(v))
        save_config()

    def _on_int_sec(self, v):
        config.ALERT_INTERVAL_SEC = int(v)
        self._set_cfg("intervalSec", int(v))
        save_config()

    def _on_sens(self, v):
        config.BLINK_RATIO_THRESHOLD = float(v)
        self._set_cfg("sensitivity", round(float(v), 2))
        save_config()

    def _on_n(self, v):
        config.PROCESS_EVERY_N_FRAMES = int(v)
        self._set_cfg("everyN", int(v))
        save_config()

    def _on_sound(self, v):
        self._set_cfg("sound", bool(v))
        self.soundToggled.emit(bool(v))

    def _set_res(self, r):
        self._cfg["res"] = r
        try:
            w, h = r.split("×")
            config.CAMERA_WIDTH = int(w)
            config.CAMERA_HEIGHT = int(h)
            save_config()
        except Exception:
            pass
        self._refresh_res_btns()
        self._refresh_preview()

    def _set_language(self, lang_code: str):
        config.LANGUAGE = lang_code
        save_config()
        self._refresh_lang_btns()
        self.languageChanged.emit()

    def _refresh_res_btns(self):
        for r, b in self._res_buttons.items():
            active = r == self._cfg["res"]
            b.setChecked(active)
            if active:
                b.setStyleSheet(
                    f"QPushButton{{background:{T.BRAND_SOFT};"
                    f"color:{T.BRAND_MID}; border:1.5px solid {T.BRAND};"
                    f"border-radius:7px; padding:6px 14px; font-size:13px;}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:{T.C_SURFACE};"
                    f"color:{T.C_TEXT2}; border:1px solid {T.C_BORDER};"
                    f"border-radius:7px; padding:7px 14px; font-size:13px;}}"
                    f"QPushButton:hover{{border-color:{T.BRAND};}}"
                )

    def _refresh_lang_btns(self):
        current = getattr(config, "LANGUAGE", "zh")
        for code, b in self._lang_buttons.items():
            active = code == current
            b.setChecked(active)
            if active:
                b.setStyleSheet(
                    f"QPushButton{{background:{T.BRAND_SOFT};"
                    f"color:{T.BRAND_MID}; border:1.5px solid {T.BRAND};"
                    f"border-radius:7px; padding:6px 14px; font-size:13px;}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:{T.C_SURFACE};"
                    f"color:{T.C_TEXT2}; border:1px solid {T.C_BORDER};"
                    f"border-radius:7px; padding:7px 14px; font-size:13px;}}"
                    f"QPushButton:hover{{border-color:{T.BRAND};}}"
                )

    def _preview_alert(self, level: int):
        try:
            from alert import AlertManager
            am = AlertManager()
            am._play_alert(level)
        except Exception:
            pass

    def _refresh_preview(self):
        c = self._cfg
        try:
            w, h = c["res"].split("×")
        except Exception:
            w, h = "640", "480"

        lines = [
            f'<span style="color:#4A5A48">{t("code_comment_alert")}</span>',
            f'NO_BLINK_ALERT_SEC <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{c["alertSec"]}</span>',
            f'ALERT_INTERVAL_SEC <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{c["intervalSec"]}</span>',
            '',
            f'<span style="color:#4A5A48">{t("code_comment_detect")}</span>',
            f'BLINK_RATIO_THRESHOLD <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{c["sensitivity"]}</span>',
            f'PROCESS_EVERY_N_FRAMES <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{c["everyN"]}</span>',
            '',
            f'<span style="color:#4A5A48">{t("code_comment_camera")}</span>',
            f'CAMERA_INDEX <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">0</span>',
            f'CAMERA_WIDTH <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{w}</span>',
            f'CAMERA_HEIGHT <span style="color:#D0D0CE">=</span> '
            f'<span style="color:#7ABA86">{h}</span>',
        ]
        self._code.setText("<br>".join(lines))

        top_lvl = c["alertSec"] + c["intervalSec"] * 3
        self._hint1.setText(t("hint1_fmt", alert=c["alertSec"], intv=c["intervalSec"], top=top_lvl))
        pct = int(round((1 - c["sensitivity"]) * 100))
        self._hint2.setText(t("hint2_fmt", sens=c["sensitivity"], pct=pct))

    def retranslate(self):
        """Update all labels to current language."""
        self._s1.setTitle(t("section_alert"))
        self._s2.setTitle(t("section_detect"))
        self._s3.setTitle(t("section_sound"))
        self._s4.setTitle(t("section_camera"))
        self._s5.setTitle(t("section_language"))
        self._s_alert.setTexts(t("slider_alert_lbl"), t("slider_alert_tip"))
        self._s_int.setTexts(t("slider_int_lbl"), t("slider_int_tip"))
        self._s_sens.setTexts(t("slider_sens_lbl"), t("slider_sens_tip"))
        self._s_n.setTexts(t("slider_n_lbl"), t("slider_n_tip"))
        self._tg.setTexts(t("sound_enable"), t("sound_enable_tip"))
        self._vol_hint.setText(t("vol_hint"))
        self._preview_lbl.setText(t("preview_label"))
        for b, key in self._preview_btns:
            b.setText(f"▶ {t(key)}")
        self._cam_hint.setText(t("cam_hint"))
        self._resl.setText(t("cam_res"))
        self._config_lbl.setText(t("config_label"))
        self._refresh_lang_btns()
        self._refresh_preview()
