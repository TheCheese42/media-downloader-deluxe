./compile_ui.ps1

nuitka `
    -o "Media Downloader Deluxe.exe" `
    --enable-plugin=pyqt6 `
    --standalone `
    --onefile `
    --include-data-dir=media_downloader_deluxe/ui=ui/ `
    --include-data-dir=media_downloader_deluxe/icons=icons/ `
    --include-data-dir=media_downloader_deluxe/langs=langs/ `
    --include-data-dir=media_downloader_deluxe/lib=lib `
    --windows-icon-from-ico=media_downloader_deluxe/icons/appicon.ico `
    --windows-console-mode=attach `
    --include-module=optparse `
    --include-package=xml `
    --include-package=http `
    --include-module=hmac `
    --include-package=ctypes `
    --include-module=uuid `
    --include-package=concurrent `
    --include-module=asyncio `
    --nofollow-import-to=yt_dlp `
    --python-flag="no_asserts" `
    --python-flag="no_docstrings" `
    --python-flag="-m" `
    media_downloader_deluxe
