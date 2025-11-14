# Bed Level Editor for Elegoo OrangeStorm Giga

Professional visual tools for manually adjusting bed leveling mesh points in your 3D printer configuration.

## 🌟 Three Versions Available

### 1. **bed_level_editor_pro.py** (Pro Edition) ⭐⭐⭐ **RECOMMENDED**
**Beautiful, intuitive interface with professional UX/UI design.**

**Latest improvements:**
- ✅ Fixed text contrast (dark text on light, light on dark)
- ✅ Fixed resize bug (stable plot layout)
- ✅ Modern dark theme with perfect contrast
- ✅ Hover effects on buttons
- ✅ Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+O, Esc)
- ✅ Real-time status bar with feedback
- ✅ Mode indicator (Point/Region)
- ✅ Smooth, professional experience

### 2. **bed_level_editor_enhanced.py** (Enhanced Edition) ⭐⭐
Advanced editor with 3D visualization and region selection.

### 3. **bed_level_editor.py** (Standard Edition) ⭐
Simple, straightforward editor for basic mesh editing.

---

## 🎨 Pro Edition Features (NEW!)

### Modern Design
- **Dark Theme**: Easy on the eyes with professional color palette
- **Better Contrast**: All text is readable on any background
- **Hover Effects**: Buttons light up when you hover over them
- **Visual Feedback**: Status bar shows what's happening in real-time
- **Mode Indicator**: Always know if you're in Point or Region mode

### Fixed Issues
- **Text Readability**: Dark text on light cells, light text on dark cells
- **Stable Layout**: No more resizing/jumping when selecting points
- **Smooth Performance**: Uses optimized drawing for better responsiveness

### Keyboard Shortcuts ⌨️
- `Ctrl+S` - Save mesh data
- `Ctrl+Z` - Reset to original
- `Ctrl+O` - Open file browser
- `Esc` - Clear selection

### Enhanced UI Elements
- **Large Value Display**: Easy-to-read Z-offset in monospace font
- **Quick Adjust Buttons**: Color-coded for direction (red=down, green=up)
- **Selection Highlight**: Glowing green border on selected points
- **Region Highlight**: Red borders for multi-point selections
- **Organized Sections**: Clear visual grouping of controls

---

## Standard & Enhanced Features

### Common Features (All Versions)
- ✅ Visual heatmap with color-coded display
- ✅ 10x10 grid editing (100 points)
- ✅ Multiple adjustment methods
- ✅ Statistics panel
- ✅ Batch operations
- ✅ File browser
- ✅ Automatic backups

### Enhanced & Pro Only
- ✅ 3D surface visualization
- ✅ Interpolated mesh preview
- ✅ Region selection (drag to select)
- ✅ Region tools (average, smooth)
- ✅ Side-by-side comparisons

### Pro Only
- ✅ Modern dark UI
- ✅ Perfect text contrast
- ✅ Hover effects
- ✅ Keyboard shortcuts
- ✅ Status bar feedback
- ✅ Optimized performance

---

## 🚀 Installation

```bash
pip install -r requirements.txt
```

**Dependencies:**
- matplotlib >= 3.5.0 (visualization)
- numpy >= 1.21.0 (numerical operations)
- scipy >= 1.7.0 (interpolation)

---

## 💻 Usage

### Pro Edition (Recommended)
```bash
python3 bed_level_editor_pro.py
```

### Enhanced Edition
```bash
python3 bed_level_editor_enhanced.py
```

### Standard Edition
```bash
python3 bed_level_editor.py
```

---

## 📖 How to Use (Pro Edition)

### Quick Start
1. **Launch**: Run `python3 bed_level_editor_pro.py`
2. **Select Mode**: Choose "Point" or "Region" mode
3. **Select Points**: Click (point) or drag (region) on the heatmap
4. **Adjust Value**: Use entry box, slider, or quick buttons
5. **Update**: Click "UPDATE SELECTION" or press Enter
6. **Save**: Click "💾 Save" or press Ctrl+S

### Selection Modes

#### Point Mode (Default)
- Click on any point to select it
- Value shown in large display
- Coordinates shown below
- Green glow around selected point

#### Region Mode
- Click and drag to select multiple points
- Red borders show selected region
- Average value displayed
- All points update together

### Adjustment Methods
1. **Direct Entry**: Type exact value and press Enter
2. **Fine Slider**: Drag slider for precise ±0.5mm adjustment
3. **Quick Buttons**:
   - `--` : -0.1mm (red)
   - `-` : -0.01mm (orange)
   - `+` : +0.01mm (blue)
   - `++` : +0.1mm (green)

### View Options
- **🔄 Reload**: Reload mesh from file
- **📊 3D View**: Open rotatable 3D surface visualization
- **🔬 Interpolated**: See side-by-side probed vs interpolated mesh

### Region Tools
- **📊 Average Region**: Set all points to average value
- **✨ Smooth Region**: Smooth using neighbor averaging
- **🗑️ Clear Selection**: Deselect all points

### Batch Operations
- **📏 Flatten All**: Set entire mesh to average
- **↕️ Offset All**: Add/subtract value from all points

---

## 🎨 Understanding the Display

### Heatmap Colors
- **Red/Orange**: Higher points (nozzle farther from bed)
- **Yellow/Green**: Lower points (nozzle closer to bed)
- **Numbers on cells**: Exact Z-offset values
- **Better contrast**: Dark text on light, light on dark

### Grid Layout
- **X axis**: 0-9 (horizontal)
- **Y axis**: 0-9 (vertical)
- **Total**: 100 points
- **White dashed lines**: Divide 4-bed layout

### Quadrant Labels (4-Bed Layout)
- **03**: Upper-left (heater_bed3)
- **02**: Upper-right (heater_bed2)
- **00**: Lower-left (heater_bed)
- **01**: Lower-right (heater_bed1)

### Visual Indicators
- **Green glow**: Selected point (Point mode)
- **Red borders**: Selected region (Region mode)
- **● Indicator**: Current mode (top right)
- **Status bar**: Current action/feedback (bottom)

---

## 💡 Understanding Your Mesh

### Current Values
- Typical range: -4.3 to -4.5mm
- **Less negative** (-4.28) = nozzle closer to bed
- **More negative** (-4.54) = nozzle farther from bed

### Interpolation
- Your config: 4x4 mesh_pps
- Converts: 10x10 (100 points) → 37x37 (1,369 points)
- Algorithm: Bicubic with tension 0.2
- **View it**: Click "🔬 Interpolated" button

### Mesh Fade
- Starts: 1mm height
- Ends: 30mm height
- Effect: Gradually reduces compensation
- Above 30mm: No compensation applied

---

## ⚡ Pro Tips

### Workflow
1. **Start with 3D View** - See overall bed shape
2. **Check Interpolation** - Verify smoothness
3. **Use Region Mode** - Fix large areas faster
4. **Test Small Changes** - ±0.05mm at a time
5. **Save Often** - Backups are automatic

### Keyboard Shortcuts Save Time
- `Ctrl+S` after each major change
- `Esc` to quickly clear selection
- `Ctrl+Z` if you make a mistake

### Region Selection is Powerful
- Select warped quadrants and average them
- Smooth bumpy areas
- Level entire sections at once

### Visual Feedback Helps
- Watch status bar for confirmation
- Mode indicator shows current state
- Hover over buttons to see them light up

---

## 🔧 Troubleshooting

### Text Hard to Read
✅ **Fixed in Pro Edition!** Dark text on light backgrounds, light on dark.

### Plot Resizes When Clicking
✅ **Fixed in Pro Edition!** Stable layout, no jumping.

### Can't See Button Text
✅ **Fixed in Pro Edition!** All buttons have white text on colored backgrounds.

### Values Not Updating
- Make sure you click "UPDATE SELECTION" or press Enter
- Check that you have a selection active
- Watch status bar for confirmation

### Changes Not Applied in Klipper
- Restart Klipper after saving
- Run `BED_MESH_PROFILE LOAD=default`
- Rehome and load start gcode

---

## ⚠️ Safety Guidelines

**CRITICAL:**
- ❌ Never edit while printing
- ❌ Don't save while Klipper is running
- ✅ Always stop Klipper first
- ✅ Test with small prints
- ✅ Keep backup files safe
- ✅ Document your changes

**After Editing:**
1. Save in editor (Ctrl+S)
2. **Stop Klipper services**
3. Verify `.backup` file created
4. **Restart Klipper**
5. Home and load mesh
6. Test with small print
7. Observe first layer
8. Fine-tune as needed

---

## 📁 File Structure

```
/home/user/BedLevel/
├── printer.cfg                   # Your printer config
├── printer.cfg.backup            # Auto-backup (on save)
│
├── bed_level_editor_pro.py       # Pro edition ⭐⭐⭐ (RECOMMENDED)
├── bed_level_editor_enhanced.py  # Enhanced edition ⭐⭐
├── bed_level_editor.py           # Standard edition ⭐
│
├── run_editor.sh                 # Launcher script
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── CHANGELOG.md                  # Version history
├── AGENTS.md                     # Development guidelines
└── klipper-reference/            # Klipper source (gitignored)
```

---

## 📊 Feature Comparison

| Feature | Standard | Enhanced | Pro |
|---------|----------|----------|-----|
| 2D Heatmap | ✅ | ✅ | ✅ |
| Point Editing | ✅ | ✅ | ✅ |
| Batch Operations | ✅ | ✅ | ✅ |
| File Browser | ✅ | ✅ | ✅ |
| Statistics | ✅ | ✅ | ✅ |
| 3D Visualization | ❌ | ✅ | ✅ |
| Interpolation Preview | ❌ | ✅ | ✅ |
| Region Selection | ❌ | ✅ | ✅ |
| Region Tools | ❌ | ✅ | ✅ |
| Modern Dark UI | ❌ | ❌ | ✅ |
| Fixed Text Contrast | ❌ | ❌ | ✅ |
| Hover Effects | ❌ | ❌ | ✅ |
| Keyboard Shortcuts | ❌ | ❌ | ✅ |
| Status Bar | ❌ | ❌ | ✅ |
| Stable Layout | ❌ | ❌ | ✅ |

---

## 🎓 Klipper Configuration Reference

Your OrangeStorm Giga configuration:
```ini
[bed_mesh]
speed: 120
horizontal_move_z: 5
mesh_min: 16,10
mesh_max: 786,767
probe_count: 10,10          # 100 points
algorithm: bicubic
bicubic_tension: 0.2
mesh_pps: 4, 4              # Interpolates to 37x37
fade_start: 1.0
fade_end: 30.0
```

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and detailed changes.

---

## 👥 Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.

---

## 📚 References

- [Klipper Bed Mesh Docs](https://www.klipper3d.org/Bed_Mesh.html)
- [Elegoo OrangeStorm Giga](https://www.elegoo.com/products/elegoo-orangestorm-giga-3d-printer)
- [Klipper GitHub](https://github.com/Klipper3d/klipper)

---

## 🌟 What's New in Pro Edition

### v3.0 Release Highlights
- ✨ **Fixed text contrast** - Perfect readability on all backgrounds
- ✨ **Fixed resize bug** - Stable, smooth visualization
- ✨ **Modern UI** - Professional dark theme
- ✨ **Keyboard shortcuts** - Work faster with hotkeys
- ✨ **Better feedback** - Status bar shows everything
- ✨ **Hover effects** - Interactive, responsive buttons
- ✨ **Mode indicator** - Always know your mode
- ✨ **Optimized performance** - Faster, smoother

**Upgrade to Pro Edition for the best experience!**
