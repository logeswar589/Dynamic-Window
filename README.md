# DynamicWin

A floating desktop widget for Windows 10 and 11 inspired by Apple's Dynamic Island. Built with Python and PySide6.

It sits quietly at the top of your screen as a small digital clock. Clicking it or pressing `Ctrl + Win + Space` expands it into quick-access widgets for media playback, hardware monitoring, countdown timers, reminders, and a temporary file tray.

---

## Features

- **Fluid Morphing Animations:** Smooth transitions between collapsed clock pill and expanded multi-widget panels.
- **Live Media Player:** Real-time Windows GSMTC integration displaying song titles, artists, album thumbnails, and transport controls (Play / Pause / Next / Prev) for Spotify, Apple Music, browsers, and Windows Media Player.
- **Real-time System Monitor:** Instant live tracking of CPU %, RAM %, and Battery percentage with smooth animated progress bars.
- **Timer & Stopwatch:** High-precision stopwatch with centisecond accuracy and customizable countdown timers with quick presets (1m, 3m, 5m, 10m) and visual alarm alerts.
- **Quick Reminders & To-Dos:** Lightweight persistent task manager to pin quick thoughts, reminders, or checklist items right from your desktop.
- **Drag & Drop File Tray:** Quick temporary dropzone to stash files, drag them directly into applications, or open them in File Explorer.
- **Customization & Settings:**
  - Dark Mode ("Black") & Light Mode ("White") themes.
  - Glassmorphic UI translucency toggle.
  - Windows Startup toggle (launch on boot via Windows registry).
- **Global Hotkey & System Tray:**
  - Press `Ctrl + Win + Space` anywhere to toggle or expand the island.
  - System Tray icon for background running, quick toggle, startup settings, and safe exit.

---

## Getting Started

### Prerequisites

- **Windows 10 / 11**
- **Python 3.10+** (Make sure to check *"Add Python to PATH"* during installation)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/dynamic-window.git
   cd dynamic-window
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   - Double-click **`run.bat`** (Recommended - handles setup automatically)
   - Or run from terminal:
     ```bash
     python main.py
     ```

---

## Shortcuts & Controls

| Action | Shortcut / Mouse Control |
| :--- | :--- |
| **Toggle Island** | `Ctrl + Win + Space` (Global) |
| **Expand / Collapse** | Left-click on the idle island pill |
| **Cycle Widgets** | Left-click on the expanded island background |
| **Close / Collapse** | Click the close `✕` icon or use the hotkey |
| **System Tray** | Click the tray icon to show/hide, or right-click for the context menu |

---

## Project Structure

```text
├── main.py                  # Application entry point, system tray & global events
├── island.py                # Main Dynamic Island window, morphing animation & layout
├── styles.py                # Design tokens, color palettes & styling constants
├── keyboard_listener.py     # Low-level Windows API hotkey listener (Ctrl + Win + Space)
├── win_media_listener.py    # Asynchronous Windows Media (GSMTC) session listener
├── run.bat                  # One-click launch and dependency installer
├── requirements.txt         # Required Python packages
├── widgets/
│   ├── __init__.py
│   ├── base.py              # Base class for island widgets
│   ├── idle.py              # Collapsed pill displaying the live digital clock
│   ├── media.py             # Expanded media player with controls & cover art
│   ├── sysmon.py            # CPU, RAM, and Battery real-time visualizer
│   ├── timer.py             # Stopwatch and countdown timer with presets
│   ├── reminder.py          # Quick to-do list & task reminder widget
│   ├── filetray.py          # Drag-and-drop file staging area
│   └── settings.py          # Themes (Dark/Light), Glassy UI & Startup toggles
└── LICENSE                  # MIT License
```

---

## Built With

- [PySide6 (Qt for Python)](https://wiki.qt.io/Qt_for_Python) - Smooth GUI rendering and QPropertyAnimation
- [winrt-Windows.Media.Control](https://pypi.org/project/winrt-Windows.Media.Control/) - Windows Media transport controls
- [psutil](https://github.com/giampaolo/psutil) - Lightweight cross-platform hardware metrics

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Developed by **Loki**.
