import json
import locale
from pathlib import Path

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
FFMPEG_PATH = (Path(
    __file__
).parent / "lib" / "ffmpeg" / "bin" / "ffmpeg").resolve()


def config_exists():
    return CONFIG_PATH.exists()


def create_app_dir():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()


def init_config():
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


def _get_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _overwrite_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(config, fp)


def get_config_value(key: str):
    return _get_config()[key]


def set_config_value(key: str, value: str):
    config = _get_config()
    config[key] = value
    _overwrite_config(config)
