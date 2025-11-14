# Bed Level Editor for Elegoo OrangeStorm Giga

Visual tools for manually adjusting bed leveling mesh points in your 3D printer configuration.

## Two Versions Available

### 1. **bed_level_editor.py** (Standard Version)
Simple, straightforward editor for basic mesh editing.

### 2. **bed_level_editor_enhanced.py** (Enhanced Version) ⭐ NEW!
Advanced editor with 3D visualization, interpolation preview, and region selection.

---

## Standard Version Features

- **Visual Heatmap**: Color-coded mesh display (red = high, green = low)
- **Click to Edit**: Select and edit individual points
- **Multiple Adjustment Methods**:
  - Direct value entry
  - Fine adjustment slider (±0.5mm)
  - Quick adjustment buttons (±0.01mm, ±0.1mm)
- **4-Bed Layout**: Visual quadrant labels (00, 01, 02, 03)
- **Statistics**: Min, max, range, mean, standard deviation
- **Batch Operations**: Flatten or offset all points
- **File Browser**: Load any printer.cfg file
- **Safe Editing**: Automatic backup before saving

## Enhanced Version Features ⭐

All standard features PLUS:

### 🎨 3D Visualization
- **Rotatable 3D Surface**: View your bed mesh as a 3D surface plot
- **Interactive**: Zoom, rotate, and pan to inspect from any angle
- **Color-mapped**: Same color scheme as heatmap for consistency

### 🔍 Interpolated Mesh Preview
- **See What Klipper Uses**: Preview the interpolated mesh that Klipper actually uses
- **Side-by-Side Comparison**: Compare your 10x10 probed points vs the interpolated mesh
- **Bicubic Interpolation**: Shows the mesh with mesh_pps (4x4 by default)
- **Detailed Stats**: Understand how interpolation affects your mesh

### ✏️ Region Selection & Bulk Editing
- **Selection Modes**: Switch between single point and region selection
- **Drag to Select**: Click and drag to select multiple points
- **Region Operations**:
  - Average all points in a region
  - Smooth region using neighboring points
  - Set all points in region to a specific value
- **Visual Feedback**: Selected regions highlighted in red

### 📊 Advanced Analysis
- Identify problem areas quickly
- Better understanding of bed warping
- Visualize the effect of interpolation on your mesh

---

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies:
- matplotlib >= 3.5.0 (plotting and visualization)
- numpy >= 1.21.0 (numerical operations)
- scipy >= 1.7.0 (interpolation, enhanced version only)

## Usage

### Standard Version
```bash
python3 bed_level_editor.py
```

### Enhanced Version (Recommended)
```bash
python3 bed_level_editor_enhanced.py
```

Or use the launcher:
```bash
./run_editor.sh
```

## How to Use

### Basic Editing (Both Versions)

1. **Load a mesh**:
   - Click "Browse..." to select a printer.cfg file
   - Or it auto-loads from the same directory

2. **Adjust a point**:
   - Click on any point in the heatmap
   - Enter a new value or use slider/buttons
   - Click "Update Point" or press Enter

3. **Save changes**:
   - Click "Save" button
   - Backup created as `printer.cfg.backup`

4. **Reset if needed**:
   - Click "Reset" to restore original values

### Enhanced Features (Enhanced Version Only)

#### 3D Visualization
- Click "3D View" button to see your mesh as a 3D surface
- Drag to rotate, scroll to zoom
- Great for identifying warping patterns

#### Interpolation Preview
- Click "Interpolated" button
- See side-by-side comparison of:
  - Your 10x10 probed mesh (left)
  - The interpolated mesh Klipper uses (right)
- Helps understand how bicubic interpolation works

#### Region Selection
1. Switch to "Region Selection" mode (radio button)
2. Click and drag to select multiple points
3. Use region tools:
   - **Average Region**: Sets all points to average value
   - **Smooth Region**: Smooths using neighbors
   - **Update Selection**: Sets all points to entered value
4. Click "Clear Selection" when done

## Understanding the Display

### Heatmap Colors
- **Red/Orange**: Higher points (nozzle farther from bed)
- **Yellow/Green**: Lower points (nozzle closer to bed)
- **Numbers**: Z-offset values displayed on each cell

### Grid Coordinates
- X axis (horizontal): 0-9
- Y axis (vertical): 0-9
- Total: 100 points

### Quadrant Labels (for 4-Bed Layout)
- **03**: Upper-left (heater_bed3)
- **02**: Upper-right (heater_bed2)
- **00**: Lower-left (heater_bed)
- **01**: Lower-right (heater_bed1)

### Physical Coordinates
- Bed range: X: 16-786mm, Y: 10-767mm
- Approximate position shown when point selected

## Understanding Your Mesh

### Current Values
- Your mesh values are typically around -4.3 to -4.5mm
- **Less negative** (e.g., -4.28) = nozzle closer to bed
- **More negative** (e.g., -4.54) = nozzle farther from bed

### Interpolation (mesh_pps)
- Your config uses 4x4 mesh_pps
- Turns 10x10 (100 points) into 37x37 (1369 points)
- Klipper uses bicubic interpolation
- The enhanced version shows you this interpolated mesh

### Mesh Fade
- Your config fades from 1mm to 30mm height
- Compensation gradually reduces as Z increases
- Completely disabled above 30mm

## Tips

- **Start Conservative**: Make small adjustments (±0.05mm)
- **Test After Changes**: Run test prints to verify
- **Use 3D View**: Helps identify overall bed shape
- **Check Interpolation**: See if your adjustments will have the desired effect
- **Use Region Selection**: Fix large areas faster
- **Keep Backups**: The tool creates backups, but keep extras safe

## Troubleshooting

### File Not Found
- Use "Browse..." button to select your printer.cfg
- Make sure the file exists in the expected location

### Changes Not Applied
- Restart Klipper firmware after saving
- Run `BED_MESH_PROFILE LOAD=default` in console
- Or rehome and run your start gcode

### Values Look Wrong
- Click "Reset" to restore original values
- Restore from .backup file if needed

### 3D View Not Working
- Make sure matplotlib and scipy are installed
- Try `pip install --upgrade matplotlib scipy`

## Safety Guidelines

⚠️ **IMPORTANT**:
- **Never edit** while Klipper is printing
- **Stop Klipper** before saving changes
- **Always test** with a small print first
- **Keep backups** of working configurations
- **Document changes** so you can revert if needed

## After Editing

1. Save changes in the editor
2. **Stop Klipper** services
3. Verify backup was created
4. **Restart Klipper** firmware
5. Home printer and load mesh
6. Run a test print (small, single layer)
7. Observe first layer adhesion
8. Fine-tune as needed

## File Structure

```
/home/user/BedLevel/
├── printer.cfg                   # Your printer configuration
├── printer.cfg.backup            # Automatic backup (created on save)
├── bed_level_editor.py           # Standard editor
├── bed_level_editor_enhanced.py  # Enhanced editor ⭐
├── run_editor.sh                 # Launcher script
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── AGENTS.md                     # Development guidelines
└── klipper-reference/            # Klipper source (reference, gitignored)
```

## Klipper Configuration Reference

Your OrangeStorm Giga uses:
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

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.

## References

- [Klipper Bed Mesh Documentation](https://www.klipper3d.org/Bed_Mesh.html)
- [Elegoo OrangeStorm Giga](https://www.elegoo.com/products/elegoo-orangestorm-giga-3d-printer)
- [Klipper GitHub](https://github.com/Klipper3d/klipper)
