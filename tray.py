"""System tray integration powered by pystray."""

import threading
from PIL import Image, ImageDraw
import pystray
from i18n import t


def _create_icon_image(color="green"):
    """生成托盘图标（一个简单的眼睛图案）"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if color == "green":
        fill = (0, 200, 0, 255)
    elif color == "red":
        fill = (255, 0, 0, 255)
    else:
        fill = (128, 128, 128, 255)

    # 绘制眼睛形状（椭圆）
    draw.ellipse([8, 16, 56, 48], fill=fill, outline=(255, 255, 255, 255), width=2)
    # 绘制瞳孔
    draw.ellipse([24, 24, 40, 40], fill=(0, 0, 0, 255))

    return img


class TrayManager:
    """系统托盘管理器"""

    def __init__(self, on_toggle_pause, on_toggle_preview, on_quit, icon_path=None):
        self._on_toggle_pause = on_toggle_pause
        self._on_toggle_preview = on_toggle_preview
        self._on_quit = on_quit
        self._icon_path = icon_path
        self._paused = False
        self._preview_visible = True
        self._icon = None
        self._thread = None

    def _get_image(self, color=None):
        if self._icon_path:
            try:
                return Image.open(self._icon_path).convert("RGBA").resize((128, 128), Image.LANCZOS)
            except Exception:
                pass
        return _create_icon_image(color or "green")

    def start(self):
        self._icon = pystray.Icon(
            "dryless",
            self._get_image(),
            t("tray_running"),
            menu=self._build_menu(),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def _build_menu(self):
        """构建右键菜单"""
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: t("tray_resume") if self._paused else t("tray_pause"),
                self._handle_toggle_pause,
            ),
            pystray.MenuItem(
                lambda item: t("tray_show") if not self._preview_visible else t("tray_hide"),
                self._handle_toggle_preview,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_quit"), self._handle_quit),
        )

    def _handle_toggle_pause(self, icon, item):
        self._paused = not self._paused
        if self._paused:
            self.update_icon("gray")
            icon.title = t("tray_paused")
        else:
            self.update_icon("green")
            icon.title = t("tray_running")
        self._on_toggle_pause(self._paused)

    def _handle_toggle_preview(self, icon, item):
        self._preview_visible = not self._preview_visible
        self._on_toggle_preview(self._preview_visible)

    def _handle_quit(self, icon, item):
        icon.stop()
        self._on_quit()

    def update_icon(self, color):
        if self._icon:
            self._icon.icon = self._get_image(color)

    def stop(self):
        """停止托盘"""
        if self._icon:
            self._icon.stop()
