Remove-Item __main__.dist -r -fo

./compile_ui.ps1

nuitka `
    -o "Media Downloader Deluxe.exe" `
    --enable-plugin=pyqt6 `
    --standalone `
    --include-data-dir=media_downloader_deluxe/ui=ui/ `
    --include-data-dir=media_downloader_deluxe/icons=icons/ `
    --include-data-dir=media_downloader_deluxe/langs=langs/ `
    --include-data-dir=media_downloader_deluxe/lib=lib `
    --windows-icon-from-ico=media_downloader_deluxe/icons/appicon.ico `
    --disable-console `
    --include-module=optparse `
    --include-package=xml `
    --include-package=http `
    --include-module=hmac `
    --include-package=ctypes `
    --include-module=uuid `
    --nofollow-import-to=yt_dlp `
    --show-progress `
    --show-memory `
    media_downloader_deluxe/__main__.py
