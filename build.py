"""Build a versioned Windows portable EXE without deleting previous builds."""
import json
import os
from pathlib import Path
import platform
import subprocess
import shutil
import sys
from importlib import metadata
from version import VERSION

ROOT = Path(__file__).resolve().parent

def main():
    if sys.platform != "win32":
        raise SystemExit("This builder targets Windows. See docs/MAC_HANDOFF.md for macOS.")
    # Resolve Git before PATH isolation. Source ZIPs carry SOURCE_COMMIT instead.
    git = shutil.which("git")
    if git and (ROOT / ".git").exists():
        revision = subprocess.run([git, "-c", "safe.directory=" + str(ROOT),
            "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    elif (ROOT / "SOURCE_COMMIT").is_file():
        revision = (ROOT / "SOURCE_COMMIT").read_text().strip()
    else:
        revision = os.environ.get("GITHUB_SHA", "unversioned-source")
    # Prevent DLLs from unrelated installed software from entering the package.
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    os.environ["PATH"] = os.pathsep.join(map(str, (
        Path(sys.prefix) / "Scripts", Path(sys.base_prefix),
        Path(sys.base_prefix) / "DLLs", windows / "System32", windows)))
    out = ROOT / "dist" / VERSION
    work = ROOT / "build" / VERSION
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    data = [("face_landmarker.task", "."), ("icon.ico", "."), ("icon.png", "."),
            ("assets/fonts", "assets/fonts"), ("assets/icons", "assets/icons"),
            ("LICENSE", "."), ("THIRD_PARTY_NOTICES.md", "."),
            ("release-assets.json", ".")]
    for family in ("polite", "sharp", "original", "blip", "microbreak"):
        data.append(("sounds/" + family, "sounds/" + family))
    for name in ("BUILTIN-SOUNDS.md", "akx-LICENSE.md", "breaktimer-LICENSE.md",
                 "workrave-COPYING", "workrave-LICENSES.md"):
        data.append(("sounds/" + name, "sounds"))
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--onefile", "--windowed", "--name", "Dryless",
            "--distpath", str(out), "--workpath", str(work / "pyinstaller"),
            "--specpath", str(work), "--icon", str(ROOT / "assets/icons/desktop-eye-transparent.ico"),
            "--collect-all", "mediapipe", "--copy-metadata", "mediapipe",
            "--hidden-import", "cv2", "--hidden-import", "winsound",
            "--hidden-import", "PyQt6.QtWidgets"]
    for excluded in ("flask", "flask_socketio", "tkinter", "scipy", "pandas",
                     "onnxruntime", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets"):
        args += ["--exclude-module", excluded]
    for source, target in data:
        if not (ROOT / source).exists():
            raise FileNotFoundError(source)
        args += ["--add-data", str(ROOT / source) + os.pathsep + target]
    args.append(str(ROOT / "main.py"))
    subprocess.run(args, cwd=ROOT, check=True)
    info = {"version": VERSION, "platform": platform.platform(), "python": sys.version,
            "revision": revision, "packages": {d.metadata["Name"]: d.version for d in metadata.distributions()}}
    (out / "build-info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(str(out / "Dryless.exe"))

if __name__ == "__main__":
    main()
