<div align="center">

# ClipTide

### Modern Media Downloader with Beautiful UI

[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-%234B8BBE?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Downloads](https://img.shields.io/github/downloads/Rayness/YouTube-Downloader/total?style=for-the-badge&logo=github)](https://github.com/Rayness/YouTube-Downloader/releases)
[![Version](https://img.shields.io/github/v/tag/Rayness/YouTube-Downloader?style=for-the-badge&logo=semver&label=version)](https://github.com/Rayness/YouTube-Downloader/releases)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg?style=for-the-badge&logo=gnu)](LICENSE)

<img src="https://github.com/user-attachments/assets/9b7b0afc-d138-4496-9e87-176246057eeb" width="650" style="border-radius: 20px">

**[Website](https://cliptide.ru)** • **[Download](https://github.com/Rayness/YouTube-Downloader/releases)** • **[Documentation](#-quick-start)** • **[Report Bug](https://github.com/Rayness/YouTube-Downloader/issues)**

[English](README.md) • [Русский](README.ru.md)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎥 **Multi-Platform Support**
Download content from YouTube, Twitch, Rutube, VKVideo, and [1000+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### 🎨 **Beautiful Themes**
5 stunning built-in themes: ClipTide, DarkTide, Forest, Neon City, and Sunset

### 🌍 **Multilingual**
Full support for English, Russian, Ukrainian, Chinese, Japanese, German, French, Italian, and Polish

</td>
<td width="50%">

### 🔄 **Format Conversion**
Built-in converter powered by FFmpeg for seamless format changes

### 📥 **Queue System**
Add multiple downloads and let them process in the background

### ⚙️ **Advanced Options**
Proxy support, subtitle downloads, audio language selection, and more

</td>
</tr>
</table>

---

## 📸 Screenshots

<div align="center">

### Modern Interface
<img src="https://github.com/user-attachments/assets/4bd9f3bb-25a7-467c-96f6-42ce111f8427" width="700">

*ClipTide's sleek and intuitive interface*

</div>

---

## 🚀 Quick Start

### 📦 Installation

#### Option 1: Installer (Recommended)
1. Download the latest installer from [Releases](https://github.com/Rayness/YouTube-Downloader/releases)
2. Run `ClipTide-Setup.exe`
3. Follow the installation wizard
4. Launch ClipTide from your Start Menu

#### Option 2: Portable Version
1. Download `ClipTide-Portable.zip` from [Releases](https://github.com/Rayness/YouTube-Downloader/releases)
2. Extract to your preferred location
3. Run `ClipTide.exe`

### 🎯 How to Use

1. **Paste URL** - Copy and paste the video link from your browser
2. **Select Format** - Choose your desired quality and format (default: MP4 FullHD)
3. **Add to Queue** - Click "Add to queue" button
4. **Start Download** - Click "Start download" and wait for completion
5. **Enjoy** - Your downloaded files will automatically open in the folder

> **💡 Tip:** The download queue is automatically saved. You can close the app anytime and resume later!

---

## 🛠️ Development

### Prerequisites

- Python 3.12 or 3.13
- Git
- Windows OS (for building executables)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/Rayness/YouTube-Downloader.git
cd YouTube-Downloader

# Install dependencies
pip install -r requirements.txt

# Run the application
python start.py
```

### Project Structure

```
ClipTide/
├── app/                    # Main application code
│   ├── core/              # Core functionality
│   ├── modules/           # Feature modules
│   │   ├── downloader/    # Download module
│   │   ├── converter/     # Format converter
│   │   └── settings/      # Settings manager
│   └── utils/             # Utility functions
├── data/                   # Application data
│   ├── ui/                # Frontend files
│   │   ├── scripts/       # JavaScript modules
│   │   ├── styles/        # CSS stylesheets
│   │   └── themes/        # Theme definitions
│   └── localization/      # Translation files
├── update/                # Auto-updater
└── start.py               # Application entry point
```

### Building from Source

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller ClipTide.spec
pyinstaller updater.spec

# Output will be in dist/ folder
```

---

## 🎨 Customization

### Themes

ClipTide comes with 5 beautiful themes:

- **ClipTide** - Default light theme with ocean vibes
- **DarkTide** - Sleek dark mode
- **Forest** - Nature-inspired green palette
- **Neon City** - Futuristic cyberpunk aesthetics
- **Sunset** - Warm evening colors

Create your own theme by adding a new folder in `data/ui/themes/` with `config.json` and `styles.css`.

### Languages

To contribute a translation:
1. Copy `data/localization/en.json`
2. Translate the values (keep the keys unchanged)
3. Save as `data/localization/[language_code].json`
4. Submit a pull request!

---

## 🔧 Configuration

### Download Settings
- **Output Folder** - Choose where files are saved
- **Quality** - Select from 144p to 8K
- **Format** - MP4, WebM, MKV, MP3, and more
- **Subtitles** - Auto-download, embed, or save separately

### Network Settings
- **Proxy Support** - HTTP/HTTPS/SOCKS5
- **Connection Timeout** - Adjust for slow networks
- **Parallel Downloads** - Control concurrent downloads

### Advanced Features
- **Audio Language** - Select preferred audio track
- **Subtitle Languages** - Download multiple subtitle tracks
- **Notifications** - Desktop notifications on completion
- **Auto-update** - Stay up to date automatically

---

## 📚 FAQ

<details>
<summary><b>Why is the download slow?</b></summary>
<br>
Download speed depends on your internet connection and the source server. Try enabling proxy if the site is throttled in your region.
</details>

<details>
<summary><b>Can I download entire playlists?</b></summary>
<br>
Yes! Just paste the playlist URL, and all videos will be added to the queue automatically.
</details>

<details>
<summary><b>What video formats are supported?</b></summary>
<br>
ClipTide supports MP4, WebM, MKV, FLV, 3GP, and many others. For audio: MP3, M4A, WAV, FLAC, OGG, and more.
</details>

<details>
<summary><b>Is it legal to download videos?</b></summary>
<br>
Downloading videos is legal for personal use in most countries. Always respect copyright laws and terms of service of the platforms you download from.
</details>

---

## 🗺️ Roadmap

- [x] Multi-language support
- [x] Auto-updater
- [x] Theme system
- [x] Built-in converter
- [ ] Electron migration (future)
- [ ] Mobile application (future)
- [ ] Browser extension (planned)
- [ ] Cloud sync (planned)

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. 🐛 **Report Bugs** - Open an issue with details
2. 💡 **Suggest Features** - Share your ideas
3. 🌍 **Translate** - Add support for more languages
4. 🎨 **Create Themes** - Design new color schemes
5. 💻 **Submit PRs** - Fix bugs or add features

### Development Guidelines

- Follow PEP 8 style guide for Python
- Write clear commit messages
- Test your changes before submitting
- Update documentation when needed

---

## 📄 License

This project is licensed under **GNU General Public License v3.0** - see [LICENSE](LICENSE) for details.

### Third-Party Licenses

ClipTide uses the following open-source libraries:

- **[pywebview](https://github.com/r0x0r/pywebview)** - BSD 3-Clause License
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Public Domain
- **[FFmpeg](https://ffmpeg.org)** - LGPL/GPL License

---

## 💖 Support

If you find ClipTide useful, consider supporting the project:

- ⭐ **Star this repository**
- 🐛 **Report bugs and issues**
- 💡 **Suggest new features**
- 🌍 **Help with translations**
- ☕ **[Buy me a coffee](https://boosty.to/rayness/donate)**

---

## 📞 Contact

- **Website:** [cliptide.ru](https://cliptide.ru)
- **GitHub:** [@Rayness](https://github.com/Rayness)
- **Issues:** [Report a bug](https://github.com/Rayness/YouTube-Downloader/issues)

---

<div align="center">

**Made with ❤️ by [Rayness](https://github.com/Rayness)**

*Download the web, one clip at a time* 🌊

[![GitHub stars](https://img.shields.io/github/stars/Rayness/YouTube-Downloader?style=social)](https://github.com/Rayness/YouTube-Downloader/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Rayness/YouTube-Downloader?style=social)](https://github.com/Rayness/YouTube-Downloader/network/members)

</div>
