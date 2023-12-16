# Media Downloader Deluxe

A high quality, tidy GUI wrapper around basic youtube-dl.

Useful for downloading videos and music from all kinds of websites.

## UI compiling

The UI has to be compiled using the pyuic6 command line utility. It's located in the scripts/bin folder of the virtual environment after install all the dependencies. To compile a `.ui` file, run the following command:

```shell
pyuic6 path/to/file.ui -o path/to/file_ui.py
```

It's important to have to `.py` file in the same folder as the `.ui` file. Also it must have the same name but end with `_ui`, like in the sample command above.

## Get binary dependencies

The program requires yt-dlp and ffmpeg to run. To allow dynamically updating yt-dlp, it makes use of it's zipimport binaries. Initially, one has to be shipped via the `media_downloader_deluxe/lib` folder. You can get the binary here: `https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp`. When first running the program, it will be copied over to appdata folder. The binary is cross-platform.
