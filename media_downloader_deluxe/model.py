import contextlib
import ctypes
import datetime
import inspect
import re
import threading
from pathlib import Path
from subprocess import getstatusoutput
from typing import Any, Callable, Optional, Union
import math

from config import FFMPEG_PATH, LOGGER_PATH, create_app_dir
from enums import Quality, Type
from yt_dlp import YoutubeDL  # type: ignore
from yt_dlp.utils import DownloadError  # type: ignore


def is_writable(path: Union[str, Path]):
    path = Path(path)
    if path.is_dir() and path.exists():
        try:
            name = Path(str(datetime.datetime.now().timestamp()))
            full = path / name
            with open(full, "w", encoding="utf-8") as fp:
                fp.write("0")
            full.unlink()
        except PermissionError:
            return False
        return True
    return False


def can_write(file: Union[str, Path]):
    file = Path(file)
    if file.is_file() and file.exists():
        try:
            with open(file, "r+", encoding="utf-8") as fp:
                first_char = fp.read(1)
                print(first_char)
                fp.seek(0)
                fp.write("0")
                fp.seek(0)
                fp.write(first_char)
        except PermissionError:
            return False
        except UnicodeDecodeError:
            try:
                with open(file, "r+b") as fp:
                    first_char = fp.read(1)
                    print(first_char)
                    fp.seek(0)
                    fp.write(b"0")
                    fp.seek(0)
                    fp.write(first_char)
            except PermissionError:
                return False
        return True
    return False


class Logger:
    def __init__(self):
        self.first_log = True

    def log(self, text: str):
        create_app_dir()
        if not LOGGER_PATH.exists():
            with open(LOGGER_PATH, "x"):
                pass
        if self.first_log:
            mode = "w"
        else:
            mode = "a"
        self.first_log = False
        with open(LOGGER_PATH, mode=mode, encoding="utf-8") as fp:
            iso_string = datetime.datetime.now().replace(
                microsecond=0
            ).isoformat()
            fp.write(f"[{iso_string}]{text}\n")

    def debug(self, msg: str):
        self.log(f"[DEBUG] {msg}")

    def warning(self, msg: str):
        self.log(f"[WARNING] {msg}")
        print(msg)

    def error(self, msg: str):
        self.log(f"[ERROR] {msg}")
        print(msg)


LOGGER = Logger()


class Downloader:
    @staticmethod
    def dl(
        urls: list[str],
        path: Union[str, Path],
        options: dict,
        progress_hooks: Optional[list[Callable]] = None,
    ) -> int:
        if progress_hooks is None:
            progress_hooks = []
        ydl_opts = {
            "logger": LOGGER,
            "ffmpeg_location": str(FFMPEG_PATH),
            "progress_hooks": progress_hooks,
            "outtmpl": f"{path}/%(title)s.%(ext)s",
            "retries": math.inf,
            **options,
        }
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.download(urls)

    @staticmethod
    def video(
        urls: list[str],
        quality: Quality,
        path: Union[str, Path],
        options: dict = None,
    ):
        if options is None:
            options = {}

        if quality == Quality.Best:
            format = "mp4"
        elif quality == Quality.Good:
            format = "(bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720][ext=mp4])[ext=mp4]"  # noqa
        elif quality == Quality.Normal:
            format = "(bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480][ext=mp4])[ext=mp4]"  # noqa
        elif quality == Quality.Bad:
            format = "(bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360][ext=mp4])[ext=mp4]"  # noqa
        elif quality == Quality.VeryBad:
            format = "(bestvideo[height<=240][ext=mp4]+bestaudio/best[height<=240][ext=mp4])[ext=mp4]"  # noqa
        elif quality == Quality.Worst:
            format = "(worstvideo[ext=mp4]+worstaudio/worst[ext=mp4])[ext=mp4]"
        else:
            raise ValueError(f"Invalid value for quality: {quality}")

        return Downloader.dl(urls, path, {"format": format, **options})

    @staticmethod
    def audio(
        urls: list[str],
        quality: Quality,
        path: Union[str, Path],
        options: dict = None,
    ):
        if options is None:
            options = {}

        if quality == Quality.Best:
            format = "bestaudio"
        elif quality == Quality.Normal:
            format = "bestaudio[abr<=100]"
        elif quality == Quality.Worst:
            format = "worstaudio"
        else:
            raise ValueError(f"Invalid value for quality: {quality}")

        return Downloader.dl(
            urls,
            path,
            {"format": format, "final_ext": ".mp3", **options},
        )

    @staticmethod
    def video_only(
        urls: list[str],
        quality: Quality,
        path: Union[str, Path],
        options: dict = None
    ):
        if options is None:
            options = {}

        if quality == Quality.Best:
            format = "bestvideo[ext=mp4]"
        elif quality == Quality.Good:
            format = "bestvideo[height<=720][ext=mp4]"
        elif quality == Quality.Normal:
            format = "bestvideo[height<=480][ext=mp4]"
        elif quality == Quality.Bad:
            format = "bestvideo[height<=360][ext=mp4]"
        elif quality == Quality.VeryBad:
            format = "bestvideo[height<=240][ext=mp4]"
        elif quality == Quality.Worst:
            format = "worstvideo[ext=mp4]"
        else:
            raise ValueError(f"Invalid value for quality: {quality}")

        return Downloader.dl(urls, path, {"format": format, **options})

    @staticmethod
    def convert(
        path: Union[str, Path],
        new_ext: str,
        options: Optional[str] = None
    ):
        path = Path(path).resolve()
        new = path.with_suffix(new_ext)
        if options:
            options = f" {options}"
        else:
            options = " -y"
        status, output = getstatusoutput(
            f"\"{FFMPEG_PATH}\" -i \"{path}\"{options} \"{new}\""
        )
        if status:
            if status == 4294967283:
                LOGGER.debug(output)
                raise PermissionError(
                    f"FFmpeg got no permissions to write to {new}"
                )
            else:
                LOGGER.error(output)
                raise RuntimeError(f"FFmpeg returned exit code {status}.")
        LOGGER.debug(output)
        path.unlink()


class PathNotWritableError(Exception):
    pass


class DownloadManager:
    def __init__(
        self,
        urls: list[str],
        type_: Type,
        quality: Quality,
        path: Union[str, Path],
        error_callback: Callable[[str, Optional[Exception]], None],
        **kwargs,
    ):
        self.urls = urls
        self.type = type_
        self.quality = quality
        self.error_callback = error_callback
        self.data = kwargs
        self.path = path

        # Only if not parallel
        self.current_thread: Optional[DLThread] = None
        self.current_thread_idx = 0
        self.thread_done_callback: Optional[Callable[[str], None]] = None

        self.threads: list[DLThread] = []
        self.url_to_threads: dict[str, DLThread] = {}

        def dl(url: str):
            with contextlib.suppress(ThreadKilled):

                def hook(d: dict):
                    if self.url_to_threads[url].killed:
                        # Kill only works after the actual download started
                        self.url_to_threads[url].kill()

                    if d["status"] == "downloading":
                        percent = int(float(
                            re.search(
                                r"([\d\.]+)%", d['_percent_str']
                            ).group(1)
                        ))
                        self.url_to_threads[url].percent = percent
                    if d["status"] == "finished":
                        self.url_to_threads[url].done = True
                        if type_ == Type.Music:
                            print("Musicc")
                            Downloader.convert(
                                Path(path) / d["filename"], ".mp3"
                            )
                    if d["status"] == "error":
                        self.url_to_threads[url].done = True
                        self.url_to_threads[url].errored = True
                        if self.error_callback:
                            self.error_callback(url)
                        # XXX if self.thread_done_callback:
                        # XXX     self.thread_done_callback(url, False)

                options = {"progress_hooks": [hook]}

                try:
                    if type_ == Type.Video:
                        Downloader.video(
                            [url], quality.to_standard(), path, options
                        )
                    elif type_ == Type.Music:
                        Downloader.audio(
                            [url], quality.to_standard(), path, options
                        )
                    elif type_ == Type.VideoOnly:
                        Downloader.video_only(
                            [url], quality.to_standard(), path, options
                        )
                except DownloadError as e:
                    self.url_to_threads[url].done = True
                    self.url_to_threads[url].errored = True
                    self.error_callback(url, e)

                if self.thread_done_callback:
                    self.thread_done_callback(url, self.was_successful())

        for url in urls:
            thread = DLThread(target=dl, args=(url,), daemon=True)
            self.threads.append(thread)
            self.url_to_threads[url] = thread

    def register_thread_done_callback(
        self, callback: Optional[Callable[[str, Optional[bool]], None]]
    ):
        self.thread_done_callback = callback

    def is_completed(self) -> bool:
        for thread in self.threads:
            if not thread.done:
                return False
        return True

    def was_successful(self) -> bool:
        """
        This will return True if all Threads ended without errors.
        Otherwise, or if not every thread ended yet, it will return False.
        """
        for thread in self.threads:
            if not thread.done or thread.errored:
                return False
        return True

    def start_all(self):
        for thread in self.threads:
            if not thread.is_alive() and not thread.killed:
                thread.start()

    def start_next(self):
        try:
            thread_to_start = self.threads[self.current_thread_idx]
            self.current_thread_idx += 1
        except IndexError:
            raise RuntimeError("All threads were started already")
        if not thread_to_start.is_alive() and not thread_to_start.killed:
            thread_to_start.start()

    def killall(self):
        for thread in self.threads:
            thread.kill()


def _async_raise(tid, exc):
    if not inspect.isclass(exc):
        raise TypeError("Only types can be raised (not instances)")

    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid), ctypes.py_object(exc)
    )
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadKilled(Exception):
    pass


class DLThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.percent = 0
        self.done = False
        self.started = False
        self.errored = False
        self.killed = False

    def start(self) -> None:
        self.started = True
        return super().start()

    def _get_my_tid(self):
        if not self.is_alive():
            raise threading.ThreadError("Thread is not active")

        return self.ident

    def raise_exc(self, exc):
        _async_raise(self._get_my_tid(), exc)

    def kill(self):
        self.killed = True
        if self.started:
            self.raise_exc(ThreadKilled)
