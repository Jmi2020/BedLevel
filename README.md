# Bed Level Editor for the Elegoo OrangeStorm Giga

If you own an OrangeStorm Giga, you already know the joke: the printer is enormous, the auto bed leveling is optimistic, and the interpolation step turns your first layer into modern art. This project is the antidote—three GUI editors (Standard, Enhanced, Pro) that let you wrangle the 10×10 mesh manually so you can actually get plastic to stick.

> **TL;DR**: Elegoo gave us four heater tiles and a firmware that thinks averages solve everything. This repo gives you a heatmap, sliders, batch tools, and a native macOS app to fix the mess.

## Why This Exists
- **Interpolation gremlins** – Klipper smooths the mesh, but the Giga’s 700 mm bed happily drifts between probe points. The default auto-level can’t see the sag.
- **Four-bed reality** – Each quadrant behaves differently; you need visibility per tile, not a single “it’s fine” number.
- **First-layer despair** – Watching a 1 kg spool air-print is expensive therapy. These editors let you nudge every point, flatten, offset, or surgically tweak hot spots before slicing again.

## Editions
| Edition | Command | Best For |
| --- | --- | --- |
| **Pro** (recommended) | `python3 bed_level_editor_pro.py` | Full-featured dark UI, stats, live status, keyboard shortcuts, quadrant overlay, and native macOS build option. |
| **Enhanced** | `python3 bed_level_editor_enhanced.py` | Adds 3D previews and region tools if you like surface plots. |
| **Standard** | `python3 bed_level_editor.py` | Lightweight Tkinter window for quick edits without bells or whistles. |

Each edition reads `printer.cfg`, draws a heatmap of the 100 mesh points, and saves back with an automatic `.backup` so you can undo Elegoo’s “assistance.”

## Features at a Glance
- Visual heatmap with per-cell values, stats panel, and quadrant labels (Pro/Enhanced).
- Point editing via text box, sliders, and quick ± buttons.
- Batch operations: “Level All,” offsets, flattening.
- Mesh statistics: min/max/range/mean/std dev.
- Region selection (Enhanced/Pro) with averaging or smoothing.
- Backup on save: `printer.cfg.backup` appears before any overwrite.
- File browser, undo stack (Pro), and working-cell tracker for test squares.

## Install & Run
1. **Install dependencies** (once per machine):
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch the editor** you want:
   ```bash
   python3 bed_level_editor_pro.py      # Pro edition
   python3 bed_level_editor_enhanced.py # Enhanced edition
   python3 bed_level_editor.py          # Standard edition
   ```
3. Select your `printer.cfg` when prompted, click any point, adjust, and press Save. Restart Klipper afterward so the mesh reloads, then finally enjoy a sane first layer.

## Build a macOS App Bundle
You can ship the Pro editor as a `.app` for teammates who don’t want Python.

### Option A – PyInstaller (recommended)
```bash
./build_pyinstaller_app.sh
open "dist/Bed Level Editor Pro.app"
```
- Creates `.venv-pyinstaller`, installs PyInstaller, and emits a universal bundle.
- Set `PYTHON_BIN=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3` if you want to force the system Framework build (handy for Tk compatibility).

### Option B – py2app (legacy workflow)
```bash
./build_macos_app.sh
open "dist/Bed Level Editor Pro.app"
```
- Keeps the original py2app pipeline for anyone who still needs it.
- Both scripts wipe `build/` and `dist/` automatically; delete the matching virtualenv folder when switching between methods.

Gatekeeper tip: right-click → **Open** the first time if macOS complains about unsigned apps. Keep `printer.cfg` accessible; the GUI will prompt for it on launch.

## Repository Layout
```
BedLevel/
├── bed_level_editor.py            # Standard Tkinter heatmap
├── bed_level_editor_enhanced.py   # Adds 3D/surface tools
├── bed_level_editor_pro.py        # Modern UI + macOS build hooks
├── build_macos_app.sh             # py2app pipeline
├── build_pyinstaller_app.sh       # PyInstaller pipeline
├── printer.cfg / printer.cfg.backup
├── requirements.txt
├── README.md (this file)
└── Examples/, Research/           # Print experiments & notes
```

## Safety & Tips
- Stop Klipper before saving, otherwise the firmware rewrites over you.
- After edits, restart Klipper, load the mesh, and run a small test print (remember the four-bed heaters heat independently).
- The `.backup` file sticks around—don’t delete it until you’ve confirmed the new mesh behaves.
- If you upgrade firmware or swap beds, re-probe from scratch and then fine-tune via the editor.

## Contributing
Pull requests are welcome. Follow PEP 8, keep comments concise, and document UI changes with screenshots or GIFs. If you devise a better way to shame Elegoo into fixing interpolation, include it in the README so the rest of us can celebrate.

Happy printing, and may your giga-scale first layer finally stay put.
