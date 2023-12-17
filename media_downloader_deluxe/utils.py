import importlib
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipimport
from pathlib import Path
from typing import Union

import config
import yt_dlp.version  # type: ignore
from PyQt6.QtWidgets import QMessageBox


def has_internet_connection():
    url = config.get_config_value("conntest_url")
    try:
        with urllib.request.urlopen(url, timeout=1):
            pass
    except urllib.error.URLError:
        return False
    return True


def is_valid_url(url):
    pattern = r'^(http|https):\/\/(([\w.-]+)(\.[\w.-]+)+|localhost)(:\d{4})?([\/\w\.-]*)*\/?(\?[\w-]+=[\w-]+)?(&[\w-]+=[\w-]+)*$'  # noqa
    return bool(re.match(pattern, url))


def find_key(dict: dict, value: str):
    for k, v in dict.items():
        if v == value:
            return k


def restart_process():
    if "__compiled__" in globals():
        os.execv(sys.argv[0], sys.argv)
    else:
        os.execv(sys.executable, [os.path.basename(sys.executable)] + sys.argv)


def reload_zip_module(path: Union[str, Path], module: str):
    importlib.invalidate_caches()
    zipimport._zip_directory_cache = {}
    if module in sys.modules:
        del sys.modules[module]

    importer = zipimport.zipimporter(path)
    module_obj = importer.load_module(module)
    sys.modules[module] = module_obj
    importlib.invalidate_caches()
    return module_obj


def get_current_ytdlp_version() -> str:
    return yt_dlp.version.__version__


def open_explorer(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _install_ytdlp(path: Union[str, Path]) -> str:
    """Installs yt-dlp to a local path, returning the path"""
    try:
        return urllib.request.urlretrieve(
            "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp",  # noqa
            path,
        )[0]
    except urllib.error.URLError:
        raise ConnectionError(
            "Could not install latest yt-dlp zipimport binary"
        )


def update_ytdlp():
    config.YT_DLP_PATH.unlink(missing_ok=True)
    _install_ytdlp(config.YT_DLP_PATH)


def add_ytdlp_to_path():
    sys.path.insert(0, str(config.YT_DLP_PATH))


def fetch_latest_ytdlp_version() -> str:
    try:
        with urllib.request.urlopen(
            "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest"
        ) as response:
            # Above url redirects to url containing the version
            out = response.url.split("/")[-1]
    except urllib.error.URLError:
        raise ConnectionError("Could not fetch latest yt-dlp version")
    return out


def is_ytdlp_latest_version() -> bool:
    installed = yt_dlp.version.__version__
    latest = fetch_latest_ytdlp_version()
    return installed == latest


def show_error(parent, title: str, desc: str) -> int:
    messagebox = QMessageBox(parent)
    messagebox.setIcon(QMessageBox.Icon.Critical)
    messagebox.setWindowTitle(title)
    messagebox.setText(desc)
    messagebox.setStandardButtons(QMessageBox.StandardButton.Ok)
    messagebox.setDefaultButton(QMessageBox.StandardButton.Ok)
    return messagebox.exec()


def show_warning(parent, title: str, desc: str) -> int:
    messagebox = QMessageBox(parent)
    messagebox.setIcon(QMessageBox.Icon.Warning)
    messagebox.setWindowTitle(title)
    messagebox.setText(desc)
    messagebox.setStandardButtons(QMessageBox.StandardButton.Ok)
    messagebox.setDefaultButton(QMessageBox.StandardButton.Ok)
    return messagebox.exec()


def show_info(parent, title: str, desc: str) -> int:
    messagebox = QMessageBox(parent)
    messagebox.setIcon(QMessageBox.Icon.Information)
    messagebox.setWindowTitle(title)
    messagebox.setText(desc)
    messagebox.setStandardButtons(QMessageBox.StandardButton.Ok)
    messagebox.setDefaultButton(QMessageBox.StandardButton.Ok)
    return messagebox.exec()


def ask_yes_no_question(
    parent,
    title: str,
    desc: str,
) -> bool:
    messagebox = QMessageBox(parent)
    messagebox.setIcon(QMessageBox.Icon.Question)
    messagebox.setWindowTitle(title)
    messagebox.setText(desc)
    messagebox.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    messagebox.setDefaultButton(QMessageBox.StandardButton.Yes)
    reply = messagebox.exec()
    if reply == QMessageBox.StandardButton.Yes:
        return True
    return False
