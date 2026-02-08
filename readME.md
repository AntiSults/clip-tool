# 🎬 Clip Tool

**Clip Tool** is a lightweight desktop application for quickly trimming video clips and exporting them into smaller, high-quality files.  
It was built primarily to trim **CS2 (Counter-Strike 2)** gameplay clips recorded with OBS, but it works with any common video format.

> ⚠️ **Note:** This is my **first Python project**.  
> The code prioritizes practicality and learning over perfection.

---

## ✨ Features

- Open and preview video files (`.mp4`, `.mkv`, `.mov`)
- Mark **start** and **end** cut points directly on the timeline
- Visual cut markers on the scrub bar
- Frame-accurate nudging (±1s / ±100ms)
- High-quality export using **FFmpeg (H.264 + AAC)**
- Optional deletion of the original clip after export
- Keyboard shortcuts for fast workflow
- Windows `.exe` build in `/dist`.

---

## 🎮 Primary Use Case

Clip Tool was created to speed up the process of:

- Trimming **CS2 clips**
- Removing dead time before/after highlights
- Exporting smaller, share-ready clips for Discord, Twitter/X, or storage

---

## ⌨️ Keyboard Shortcuts

| Key             | Action                      |
| --------------- | --------------------------- |
| `Space`         | Play / Pause                |
| `C`             | Set cut mark                |
| `S`             | Swap cut mode (Start ↔ End) |
| `← / →`         | Nudge ±1 second             |
| `Shift + ← / →` | Nudge ±100 ms               |

---

## 📤 Export Details

- Video codec: `libx264`
- Audio codec: `AAC`
- Pixel format: `yuv420p` (maximum compatibility)
- Configurable quality via CRF
- Uses `imageio-ffmpeg` to bundle FFmpeg automatically

---

## 🖥️ Running from Source

### Requirements

- Python 3.10+
- Windows (tested)
- FFmpeg (handled automatically)

## 🤖 AI Usage Disclosure

AI assistance (ChatGPT) was used sparingly as a learning and troubleshooting aid. All core functionality, architecture, and implementation decisions were made manually. AI was not used to generate the project wholesale, but to clarify concepts, debug issues, and accelerate learning. Overall AI usage was low.

## Author

Anti Sults
