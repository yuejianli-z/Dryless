"""
Build script for Dryless.
Run with: `python build.py`
Output: `dist/Dryless.exe` as a single-file executable.
"""
import os
import sys
import shutil
import subprocess

# ── 项目根目录 ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))

# ── 打包前清理旧文件 ──────────────────────────────────────────
for folder in ["build", "dist"]:
    path = os.path.join(ROOT, folder)
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"Cleaned: {folder}/")

spec_file = os.path.join(ROOT, "Dryless.spec")
if os.path.exists(spec_file):
    os.remove(spec_file)

# ── 需要额外打包进去的数据文件 ────────────────────────────────
datas = [
    (os.path.join(ROOT, "face_landmarker.task"), "."),
    (os.path.join(ROOT, "sounds"),               "sounds"),
    (os.path.join(ROOT, "icon.png"),             "."),
    (os.path.join(ROOT, "icon.ico"),             "."),
]

font_dir = os.path.join(ROOT, "assets", "fonts")
if os.path.isdir(font_dir):
    datas.append((font_dir, "assets/fonts"))

datas_args = []
for src, dst in datas:
    if os.path.exists(src):
        datas_args += ["--add-data", f"{src}{os.pathsep}{dst}"]

# ── 构造 PyInstaller 命令 ─────────────────────────────────────
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "Dryless",
    "--icon", os.path.join(ROOT, "icon.ico"),
    "--hidden-import", "mediapipe",
    "--hidden-import", "mediapipe.tasks",
    "--hidden-import", "mediapipe.tasks.c",
    "--hidden-import", "mediapipe.tasks.python",
    "--hidden-import", "mediapipe.tasks.python.vision",
    "--hidden-import", "mediapipe.python",
    "--collect-all", "mediapipe",
    "--hidden-import", "cv2",
    "--hidden-import", "PyQt6.QtWidgets",
    "--hidden-import", "PyQt6.QtCore",
    "--hidden-import", "PyQt6.QtGui",
    "--hidden-import", "numpy",
    "--hidden-import", "winsound",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL",
    "--exclude-module", "flask",
    "--exclude-module", "flask_socketio",
    "--exclude-module", "tkinter",
    "--exclude-module", "scipy",
    "--exclude-module", "pandas",
] + datas_args + [
    os.path.join(ROOT, "main.py"),
]

print("=" * 60)
print("Building Dryless...")
print("This may take 3-10 minutes, please wait.")
print("=" * 60)

result = subprocess.run(cmd, cwd=ROOT)

if result.returncode == 0:
    exe_path = os.path.join(ROOT, "dist", "Dryless.exe")
    size_mb = os.path.getsize(exe_path) / 1024 / 1024
    print()
    print("=" * 60)
    print(f"Build successful!")
    print(f"  Output: {exe_path}")
    print(f"  Size:   {size_mb:.1f} MB")
    print("=" * 60)
else:
    print()
    print("=" * 60)
    print("Build failed. Check the error above.")
    print("Make sure PyInstaller is installed:")
    print("  pip install pyinstaller")
    print("=" * 60)
