[![Supported Python Versions](https://img.shields.io/badge/python-3.12%20%7C%203.13-%234B8BBE)](https://www.python.org/downloads/) [![Downloads](https://img.shields.io/github/downloads/Rayness/YouTube-Downloader/total)](https://github.com/Rayness/YouTube-Downloader/releases) [![Release date](https://img.shields.io/github/release-date/Rayness/YouTube-Downloader)]() [![Version tag](https://img.shields.io/github/v/tag/Rayness/YouTube-Downloader)]()
<p align="center">
  <img src="https://github.com/user-attachments/assets/9b7b0afc-d138-4496-9e87-176246057eeb" width="500" style="border-radius: 20px">
</p>

[English Readme](https://github.com/Rayness/YouTube-Downloader/blob/main/README.md)
• [Russian Readme](https://github.com/Rayness/YouTube-Downloader/blob/main/README.ru.md)

## General information
This small program is designed to download video content in audio and video formats from the YouTube, Twitch and other platforms are also supported, such as: Rutube, Vkvideo, ok and many others. The full list can be found [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), most likely videos will be downloaded from all these sources if they (the sources) are not blocked in your country.

> [!NOTE]
> The app also has a website: [cliptide.ru](https://cliptide.ru/index.html)
> 
> So far, it's only in Russian and English, but I'll add a translation into other languages later.

### Old version with graphical interface:
<img src="https://github.com/user-attachments/assets/5f04bb15-5e93-4a0a-a6d7-562cd5280fc4" width="600">

## Download

**[Current version](https://github.com/Rayness/YouTube-Downloader/releases/tag/v1.7.0)** - 1.7.0

## How to run:
- Like any other application;
  - If you downloaded the installer, then run it and follow the installation instructions;
  - If you downloaded the archive, then extract the contents to any folder and run "ClipTide.exe"

## How to use:
After launching the graphical interface, you need to:
1. Paste the link to the video (copy from the url line in the browser);
2. Select the desired video format and quality (by default, the video will be downloaded in mp4 in FullHD);
3. Click the "Add to queue" button;
4. Repeat the first three steps as many times as necessary, or go to the fifth;
5. Click the "Start download" button;
6. Wait until all the videos are downloaded, or close the program if you want, the queue will be saved;
  - If you closed the program, then launch it and repeat the action from the fifth step, but this time without closing the program.
7. After downloading, the folder with the downloaded videos will open and you can close the program.

## Known errors:
1. Problem: Incorrect display of playlist downloads, how to determine: the indicator spins for a very long time and nothing happens for a long time. If you wait, the playlist name will appear in the queue without a preview. The entire playlist will be downloaded.
  - Solution: Do not add playlists to the queue, or wait;

## Future plans:
- [x] Add auto-update ( Updater added );
- [ ] Transfer the project to Electron ( someday );
- [ ] Make a mobile application ( not very soon )

## License
This project is now licensed under **GNU GPLv3**. See [LICENSE](LICENSE) for details.  

## Third-party licenses  
This project uses the following libraries:  
- **pywebview** (BSD 3-Clause) — [https://github.com/r0x0r/pywebview](https://github.com/r0x0r/pywebview)  
- **yt-dlp** (Public Domain) — [https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **FFmpeg** (LGPL/GPL) — https://ffmpeg.org
