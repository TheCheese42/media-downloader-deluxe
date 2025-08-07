import json
import locale
import platform
from pathlib import Path
from typing import Any, Union

from PyQt6.QtCore import QStandardPaths

CONFIG_DIR = Path(
    QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
) / "Media Downloader Deluxe"
CONFIG_PATH = CONFIG_DIR / ".config"
LOGGER_PATH = CONFIG_DIR / "latest.log"
YT_DLP_PATH = CONFIG_DIR / "yt-dlp"

SUPPORTED_LOCALES = ["de_DE", "en_US"]
DEFAULT_LOCALE = "en_US"
SYSTEM_LOCALE = locale.getlocale()[0]
FFMPEG_BIN_NAME = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
FFMPEG_PATH: Union[str, Path] = (Path(
    __file__
).parent / "lib" / "ffmpeg" / "bin" / FFMPEG_BIN_NAME).resolve()
ROOT_PATH = Path(__file__).parent
if "__compiled__" in globals():
    # With nuitka, __file__ will show the file in a subfolder that doesn't
    # exist.
    # With nuitka: app_name.dist/app_name/paths.py
    # Actual: app_name.dist/paths.py
    # That's why we go back another folder using .parent twice.
    ROOT_PATH = Path(__file__).parent.parent
LANGS_PATH = ROOT_PATH / "langs"


def config_exists() -> bool:
    return CONFIG_PATH.exists()


def create_app_dir() -> None:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()


def init_config() -> None:
    create_app_dir()

    if not config_exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "locale": (
                        SYSTEM_LOCALE
                        if SYSTEM_LOCALE in SUPPORTED_LOCALES
                        else DEFAULT_LOCALE
                    ),
                    "dark": False,
                    "default_dir": QStandardPaths.writableLocation(
                        QStandardPaths.StandardLocation.MoviesLocation
                    ),
                    "max_parallel_downloads": 10,
                    "conntest_url": "https://8.8.8.8"
                }, fp
            )


def _get_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)  # type: ignore[no-any-return]


def _overwrite_config(config: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(config, fp)


def get_config_value(key: str) -> Any:
    return _get_config()[key]


def set_config_value(key: str, value: Any) -> None:
    config = _get_config()
    config[key] = value
    _overwrite_config(config)
