"""User-initiated project links shared by the Windows UI."""
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

PROJECT_URL = "https://github.com/yuejianli-z/Dryless"
ISSUES_URL = PROJECT_URL + "/issues"


def open_project():
    return QDesktopServices.openUrl(QUrl(PROJECT_URL))


def open_issues():
    return QDesktopServices.openUrl(QUrl(ISSUES_URL))
