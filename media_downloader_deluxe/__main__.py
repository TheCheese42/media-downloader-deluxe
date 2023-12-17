import importlib
import shutil
import sys
from pathlib import Path

import config

try:
    # Put this inside try so it's not counted as above imports (cornflakes)
    config.init_config()
    sys.path.insert(0, str(config.YT_DLP_PATH))
    import yt_dlp  # type: ignore
    import yt_dlp.version  # type: ignore
except ImportError:
    shutil.copyfile(
        Path(__file__).parent / "lib" / "yt-dlp",
        config.YT_DLP_PATH,
    )
    importlib.invalidate_caches()
    import yt_dlp  # type: ignore
    import yt_dlp.version  # type: ignore

import functools
import sys
import traceback
import webbrowser
from subprocess import getoutput
from typing import Optional

import enums
import lang
import utils
from model import LOGGER, DownloadManager, is_writable
from PyQt6.QtCore import QLibraryInfo, Qt, QTimer, QTranslator
from PyQt6.QtGui import QCloseEvent, QFont, QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow
from ui.about_ui import Ui_Dialog as Ui_About
from ui.licenses_ui import Ui_Dialog as Ui_Licenses
from ui.settings_ui import Ui_Dialog as Ui_Settings
from ui.window_ui import Ui_MainWindow
from version import __version__

APPICON = None


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__(None)
        self.lang = self.get_lang_dict()
        # XXX self.prev_text_edit_text = ""
        # XXX self.te_history = []
        # XXX self.undo_history = []
        self.path = config.get_config_value("default_dir")
        self.setWindowIcon(APPICON)
        self.setWindowState(Qt.WindowState.WindowActive)
        self.setupUi(self)
        self.cleanup_dl()
        self.lang_map = {
            "de_DE": self.actionDeutsch,
            "en_US": self.actionEnglish,
        }
        self._last_type_index = 0
        self.connectSignalsSlots()

        self.music_to_idx_conversion = {
            0: 0,
            1: 2,
            2: 5,
        }

        self.light_stylesheet = self.styleSheet()
        self.dark_stylesheet = """
            QWidget {
                background-color: rgb(40, 40, 40);
                color: white;
                selection-background-color: transparent;
            }
            QPlainTextEdit {
                background-color: rgb(60, 60, 60);
            }
            QMenu {
                background-color: rgb(20, 20, 20);
            }
            QMenuBar {
                background-color: rgb(25, 25, 25);
            }
            QMenu:hover {
                background-color: rgb(35, 35, 35);
            }
            QMenu:pressed {
                background-color: rgb(45, 45, 45);
            }
            QCheckBox::indicator:hover {
                color: rgb(50, 50, 50);
            }
            QCheckBox::indicator:pressed {
                background-color: rgb(60, 60, 60);
            }
            QComboBox:selected {
                background-color: rgb(40, 40, 40);
            }
        """
        self.apply_dark()
        self.apply_lang()

        def _ask_update_ytdlp():
            try:
                if not utils.is_ytdlp_latest_version():
                    self.ask_update_ytdlp()
            except ConnectionError:
                pass

        QTimer.singleShot(100, _ask_update_ytdlp)

    def cleanup_dl(self):
        self.manager = None
        self.progress_bar.setValue(0)
        self.progress_display.setText("(0/0)")
        self.downloading = False
        self.start_btn.setEnabled(True)
        self.actionCancel.setDisabled(True)

        # Tricky: This is not a True/False field but holds an url instead of
        # True and is None instead of False
        self.should_show_dl_error: Optional[str] = None
        # Same here but with amount of total videos
        self.should_show_success: Optional[int] = None
        # These are normal
        self.should_stop_timer = False
        self.should_cleanup = False

    def ask_update_ytdlp(self):
        old_version = yt_dlp.version.__version__
        new_version = utils.fetch_latest_ytdlp_version()
        if utils.ask_yes_no_question(
            self,
            self.lang["question_update_ytdlp_title"],
            self.lang["question_update_ytdlp_desc"].format(
                current=old_version,
                latest=new_version,
            )
        ):
            utils.update_ytdlp()
            utils.reload_zip_module(
                config.YT_DLP_PATH, "yt_dlp"
            )
            yt_dlp.version = utils.reload_zip_module(
                config.YT_DLP_PATH / "yt_dlp", "version"
            )
            utils.show_info(
                self,
                self.lang["update_updating_title"],
                self.lang["update_updating_desc"].format(
                    old=old_version,
                    new=new_version,
                ),
            )
            utils.restart_process()

    def get_lang_dict(self) -> lang.LangDict:
        return lang.LangDict.from_langcode(config.get_config_value("locale"))

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.setWindowTitle("Media Downloader Deluxe")
        self.actionUndo.setDisabled(True)
        self.actionRedo.setDisabled(True)
        self.output_path_display.setText(self.path)
        QTimer.singleShot(
            0,
            lambda: self.lang_map[
                config.get_config_value("locale")
            ].setChecked(True)
        )

    def connectSignalsSlots(self):
        self.actionOpen.triggered.connect(self.open)
        self.actionClear_list.triggered.connect(self.clear_list)
        self.actionOpen_in_Explorer.triggered.connect(self.open_in_explorer)
        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionCancel.triggered.connect(self.cancel)
        self.actionExit.triggered.connect(self.close)
        self.actionOpen_Settings.triggered.connect(self.open_settings)
        self.actionDark_mode.toggled.connect(self.dark_mode)
        self.actionAbout.triggered.connect(self.about)
        self.actionOpen_source_licenses.triggered.connect(self.licenses)
        self.actionList_of_supported_sites.triggered.connect(
            self.list_of_supported_sites
        )
        self.text_edit.textChanged.connect(self.text_edit_changed)
        self.actionEnglish.toggled.connect(
            functools.partial(self.change_lang, "en_US")
        )
        self.actionDeutsch.toggled.connect(
            functools.partial(self.change_lang, "de_DE")
        )
        self.output_path_change_btn.clicked.connect(self.set_output_path)
        self.type_box.currentTextChanged.connect(self.type_changed)
        self.start_btn.clicked.connect(self.start)

    def verify_input(self):
        if not self.text_edit.toPlainText().strip():
            utils.show_error(
                self,
                self.lang["no_input_title"],
                self.lang["no_input_desc"],
            )
            return False
        text = self.text_edit.toPlainText()
        formatted = ""
        for line in text.splitlines():
            formatted += line.strip() + "\n" if line.strip() else ""
        self.text_edit.setPlainText(formatted)
        for idx, line in enumerate(
            self.text_edit.toPlainText().splitlines(),
            start=1,
        ):
            line = line.strip()
            if not utils.is_valid_url(line):
                utils.show_error(
                    self,
                    self.lang["malformed_url_title"],
                    self.lang["malformed_url_desc"].format(
                        idx=idx, url=line
                    ),
                )
                return False
        return True

    def cancel(self):
        if not self.downloading:
            return

        try:
            self.manager.killall()
        except Exception:
            utils.show_error(
                self,
                self.lang["killall_error_title"],
                self.lang["killall_error_desc"],
            )
        self.should_stop_timer = True
        QTimer.singleShot(1000, self.cleanup_dl)

    def start(self):
        if not self.verify_input():
            return

        if self.downloading:
            return

        path = Path(self.path)
        if not is_writable(path):
            utils.show_error(
                self,
                self.lang["not_writable_title"],
                self.lang["not_writable_desc"],
            )
            return

        if not utils.has_internet_connection():
            utils.show_error(
                self,
                self.lang["no_connection_title"],
                self.lang["no_connection_desc"],
            )
            return

        self.downloading = True
        self.start_btn.setDisabled(True)
        self.actionCancel.setEnabled(True)

        urls = list(map(str.strip, self.text_edit.toPlainText().splitlines()))
        parallel = self.checkBox.isChecked()
        type = enums.Type(self.type_box.currentIndex())
        if type == enums.Type.Music:
            quality = enums.MusicQuality(self.quality_box.currentIndex())
        else:
            quality = enums.Quality(self.quality_box.currentIndex())
        max_parallel = config.get_config_value("max_parallel_downloads")  # noqa

        def err_callback(url, err=None):
            self.manager.killall()
            self.should_show_dl_error = url

        def thread_done_callback(url, success):
            if not self.downloading:
                # Got cancelled
                return

            if not parallel:
                try:
                    self.manager.start_next()
                except RuntimeError:
                    pass
            if self.manager.is_completed():
                self.progress_bar.setValue(100)
                self.progress_display.setText(
                    f"({len(self.manager.threads)}/"
                    f"{len(self.manager.threads)})"
                )
                self.should_stop_timer = True
                if success:
                    self.should_show_success = len(urls)
                self.should_cleanup = True

        self.manager = DownloadManager(
            urls,
            type,
            quality,
            path,
            err_callback,
            parallel=True,  # Extra data
        )
        self.manager.register_thread_done_callback(thread_done_callback)

        if parallel:
            self.manager.start_all()
        else:
            self.manager.start_next()

        self.progress_updater = QTimer()
        self.progress_updater.timeout.connect(self.update_progress)
        self.progress_updater.setInterval(500)
        self.progress_updater.start()

    def update_progress(self):
        if self.should_show_dl_error:
            self.show_download_error(self.should_show_dl_error)
        if self.should_show_success:
            self.show_success(self.should_show_success)
        if self.should_stop_timer:
            self.progress_updater.stop()
        if self.should_cleanup:
            self.cleanup_dl()
            return

        threads = self.manager.threads
        if self.manager.data.get("parallel"):
            percents = []
            for thread in threads:
                percents.append(thread.percent)
            avg = round(sum(percents) / len(threads))
            self.progress_bar.setValue(avg)
        else:
            self.progress_bar.setValue(self.manager.current_thread.percent)
        total = len(threads)
        finished = 0
        for thread in threads:
            if thread.done:
                finished += 1
        self.progress_display.setText(f"({finished}/{total})")

    def show_success(self, amount: int):
        utils.show_info(
            self,
            self.lang["success_title"],
            self.lang["success_desc"].format(
                amount=amount
            )
        )

    def show_download_error(self, url: str):
        utils.show_error(
            self,
            self.lang["download_error_title"],
            self.lang["download_error_desc"].format(
                url=url,
            ),
        )

    def type_changed(self):
        self.quality_box.setCurrentIndex(0)
        self.apply_lang()

    def set_output_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setDirectory(self.path)
        if file_dialog.exec():
            dir = file_dialog.selectedFiles()[0]
            self.path = dir
            self.output_path_display.setText(dir)

    def change_lang(self, locale: str):
        previous_lang = config.get_config_value("locale")
        self.lang_map[previous_lang].blockSignals(True)
        self.lang_map[previous_lang].setChecked(False)
        self.lang_map[previous_lang].blockSignals(False)
        self.lang_map[locale].blockSignals(True)
        self.lang_map[locale].setChecked(True)
        self.lang_map[locale].blockSignals(False)
        config.set_config_value("locale", locale)
        self.lang = self.get_lang_dict()
        self.apply_lang()

    def apply_lang(self):
        self.menuFile.setTitle(self.lang["file"])
        self.actionOpen.setText(self.lang["open"])
        self.actionClear_list.setText(self.lang["clear_list"])
        self.actionOpen_in_Explorer.setText(
            self.lang["open_in_explorer"]
        )
        self.actionUndo.setText(self.lang["undo"])
        self.actionRedo.setText(self.lang["redo"])
        self.actionCancel.setText(self.lang["cancel"])
        self.actionExit.setText(self.lang["exit"])
        self.menuSettings.setTitle(self.lang["settings"])
        self.actionOpen_Settings.setText(self.lang["open_settings"])
        self.menuView.setTitle(self.lang["view"])
        self.actionDark_mode.setText(self.lang["dark_mode"])
        self.menuLanguage.setTitle(self.lang["language"])
        self.menuHelp.setTitle(self.lang["help"])
        self.actionAbout.setText(self.lang["about"])
        self.actionOpen_source_licenses.setText(
            self.lang["open_source_licenses"]
        )
        self.actionList_of_supported_sites.setText(
            self.lang["list_of_supported_sites"]
        )
        self.type_label.setText(self.lang["type"])
        prev_type_index = self.type_box.currentIndex()
        self.type_box.blockSignals(True)
        self.type_box.clear()
        self.type_box.addItems([
            self.lang["video"],
            self.lang["music"],
            self.lang["video_only"],
        ])
        self.type_box.setCurrentIndex(prev_type_index)
        self.type_box.blockSignals(False)
        self.quality_label.setText(self.lang["quality"])
        prev_quality_index = self.quality_box.currentIndex()
        self.quality_box.blockSignals(True)
        self.quality_box.clear()
        if self.type_box.currentText() in (
            self.lang["video"],
            self.lang["video_only"],
        ):
            self.quality_box.addItems([
                self.lang["best"],
                self.lang["good"],
                self.lang["normal"],
                self.lang["bad"],
                self.lang["very_bad"],
                self.lang["worst"],
            ])
        else:
            self.quality_box.addItems([
                self.lang["best"],
                self.lang["normal"],
                self.lang["worst"],
            ])
        self.quality_box.setCurrentIndex(prev_quality_index)
        self.quality_box.blockSignals(False)
        self.checkBox.setText(self.lang["download_in_parallel"])
        self.output_path_label.setText(self.lang["output_path"])
        self.output_path_change_btn.setText(self.lang["change"])
        self.start_btn.setText(self.lang["start"])
        self.progress_label.setText(self.lang["progress"])

    def text_edit_changed(self):
        # XXX prev = self.prev_text_edit_text
        # XXX self.prev_text_edit_text = self.text_edit.toPlainText()
        # XXX self.te_history.insert(0, prev)
        # XXX self.te_history = self.te_history[:50]
        self.actionUndo.setDisabled(False)

    def open(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setDirectory(self.path)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        if file_dialog.exec():
            file = file_dialog.selectedFiles()[0]
            try:
                with open(file, "r", encoding="utf-8") as fp:
                    content = fp.read()
            except Exception as e:
                return utils.show_error(
                    self,
                    self.lang["error_open_title"],
                    self.lang["error_open_text"].format(
                        file=file, error=e.__class__.__name__
                    ),
                )
            content = content.strip()
            self.text_edit.setPlainText(content)

    def clear_list(self):
        self.text_edit.setPlainText("")

    def open_in_explorer(self):
        utils.open_explorer(self.path)

    def undo(self):
        self.text_edit.undo()
        self.actionRedo.setDisabled(False)

    def redo(self):
        self.text_edit.redo()

    # XXX def undo(self):
    # XXX     current = self.te_history[0]
    # XXX     try:
    # XXX         before = self.te_history[1]
    # XXX     except IndexError:
    # XXX         return
    # XXX     self.text_edit.blockSignals(True)
    # XXX     self.text_edit.setPlainText(before)
    # XXX     self.text_edit.blockSignals(False)
    # XXX     self.te_history.remove(current)
    # XXX     self.undo_history.insert(0, current)
    # XXX     if len(self.te_history) < 2:
    # XXX         self.actionUndo.setDisabled(True)
    # XXX     self.actionRedo.setDisabled(False)

    # XXX def redo(self):
    # XXX     current = self.text_edit.toPlainText()
    # XXX     try:
    # XXX         last_before_undo = self.undo_history[0]
    # XXX     except IndexError:
    # XXX         return
    # XXX     self.text_edit.blockSignals(True)
    # XXX     self.text_edit.setPlainText(last_before_undo)
    # XXX     self.text_edit.blockSignals(False)
    # XXX     self.undo_history.remove(last_before_undo)
    # XXX     self.te_history.insert(0, current)
    # XXX     if not self.undo_history:
    # XXX         self.actionRedo.setDisabled(True)
    # XXX     self.actionUndo.setDisabled(False)

    def closeEvent(self, event: QCloseEvent):
        if self.downloading:
            response = utils.ask_yes_no_question(
                self,
                self.lang["close_confirm_title"],
                self.lang["close_confirm_desc"],
            )
            if response:
                pass
            else:
                event.ignore()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            max_parallel_downloads = dialog.spinBox.value()
            default_output_path = dialog.output_path_display.text()
            config.set_config_value(
                "max_parallel_downloads", max_parallel_downloads
            )
            config.set_config_value(
                "default_dir", default_output_path
            )
            self.path = default_output_path
            self.output_path_display.setText(self.path)

    def dark_mode(self):
        dark = self.actionDark_mode.isChecked()
        config.set_config_value("dark", dark)
        self.apply_dark()

    def apply_dark(self):
        dark = config.get_config_value("dark")
        self.setStyleSheet(
            self.dark_stylesheet if dark else self.light_stylesheet
        )

    def about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def licenses(self):
        dialog = LicensesDialog(self)
        dialog.exec()

    def list_of_supported_sites(self):
        try:
            webbrowser.WindowsDefault().open(
                "https://ytb-dl.github.io/ytb-dl/supportedsites.html"
            )
        except Exception:
            getoutput(
                "start https://ytb-dl.github.io/ytb-dl/supportedsites.html"
            )


class LicensesDialog(QDialog, Ui_Licenses):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowIcon(APPICON)
        self.setupUi(self)
        self.setFixedSize(self.size())

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.setWindowTitle(self.parent().lang["window_licenses"])
        self.header.setText(self.parent().lang["licenses_header"])


class AboutDialog(QDialog, Ui_About):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowIcon(APPICON)
        self.setupUi(self)
        self.setFixedSize(self.size())

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.setWindowTitle(self.parent().lang["window_about"])
        self.label.setText(self.parent().lang["about_author"])
        self.version.setText(self.parent().lang["about_version"].format(
            version=__version__,
        ))


class SettingsDialog(QDialog, Ui_Settings):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowIcon(APPICON)
        self.setupUi(self)
        self.setMinimumSize(self.minimumSize())
        self.output_path_change_btn.clicked.connect(self.change_output_path)
        self.update_ytdlp.clicked.connect(self.update_ytdlp_action)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.setWindowTitle(self.parent().lang["window_settings"])
        self.spinBox.setValue(
            config.get_config_value("max_parallel_downloads")
        )
        self.output_path_display.setText(
            config.get_config_value("default_dir")
        )
        self.yt_dlp_version.setText(yt_dlp.version.__version__)
        self.label.setText(self.parent().lang["settings_header"])
        self.label_2.setText(
            self.parent().lang["settings_max_parallel_downloads"]
        )
        self.output_path_label.setText(
            self.parent().lang["settings_default_output_path"]
        )
        self.output_path_change_btn.setText(
            self.parent().lang["settings_change"]
        )
        self.label_3.setText(self.parent().lang["settings_ytdlp_version"])
        self.update_ytdlp.setText(self.parent().lang["settings_update"])

    def update_ytdlp_action(self):
        self.update_ytdlp.setDisabled(True)
        old_version = yt_dlp.version.__version__
        try:
            if utils.is_ytdlp_latest_version():
                utils.show_info(
                    self,
                    self.parent().lang["settings_update_uptodate_title"],
                    self.parent().lang[
                        "settings_update_uptodate_desc"
                    ].format(version=old_version),
                )
            else:
                self.update_ytdlp.setDisabled(True)
                self.update_ytdlp.setText(
                    self.parent().lang["settings_updating"]
                )
                utils.update_ytdlp()
                utils.reload_zip_module(config.YT_DLP_PATH, "yt_dlp")
                yt_dlp.version = utils.reload_zip_module(
                    config.YT_DLP_PATH / "yt_dlp", "version"
                )
                new_version = yt_dlp.version.__version__
                self.update_ytdlp.setEnabled(True)
                self.update_ytdlp.setText(
                    self.parent().lang["settings_update"]
                )
                utils.show_info(
                    self,
                    self.parent().lang["settings_update_updating_title"],
                    self.parent().lang["settings_update_updating_desc"].format(
                        old=old_version,
                        new=new_version,
                    ),
                )
        except ConnectionError:
            utils.show_error(
                self,
                self.parent().lang["settings_update_noconn_title"],
                self.parent().lang["settings_update_noconn_desc"],
            )
        self.update_ytdlp.setDisabled(False)

    def change_output_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setDirectory(config.get_config_value("default_dir"))
        if file_dialog.exec():
            dir = file_dialog.selectedFiles()[0]
            config.set_config_value("default_dir", dir)
            self.output_path_display.setText(dir)


def exchook(*exc_info):
    text = "".join(traceback.format_exception(*exc_info))
    LOGGER.error(text)


if __name__ == "__main__":
    sys.excepthook = exchook
    lang.LangDict.set_languages_path(Path(__file__).parent / "langs")
    app = QApplication(sys.argv)

    APPICON = QIcon(str(Path(__file__).parent / "icons/appicon.png"))

    app.setApplicationName("Media Downloader Deluxe")
    app.setFont(QFont("Calibri", 11))
    locale = config.get_config_value("locale")
    translator = QTranslator()
    translator.load(
        'qt_' + locale[:2], QLibraryInfo.path(
            QLibraryInfo.LibraryPath.TranslationsPath
        )
    )
    app.installTranslator(translator)
    win = Window()
    win.show()
    code = app.exec()
    sys.exit(code)
