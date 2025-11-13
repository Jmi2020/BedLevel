# Bed Level Editor for Elegoo OrangeStorm Giga

A visual tool for manually adjusting bed leveling mesh points in your 3D printer configuration.

## Features

- **Visual Heatmap**: See your bed mesh as a color-coded heatmap (red = high, green = low)
- **Click to Edit**: Click any of the 100 points on the grid to select and edit
- **Multiple Adjustment Methods**:
  - Direct value entry
  - Fine adjustment slider (±0.5mm)
  - Quick adjustment buttons (±0.01mm, ±0.1mm)
- **Statistics**: View min, max, range, mean, and standard deviation
- **Batch Operations**: Flatten entire mesh or offset all points
- **Safe Editing**: Automatic backup created before saving

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the editor:
```bash
python3 bed_level_editor.py
```

2. The tool will automatically load your printer.cfg file

3. **To adjust a point**:
   - Click on any point in the heatmap
   - The point will be highlighted with a white star
   - Use one of these methods to adjust:
     - Type a new value in the entry field and press Enter or click "Update Point"
     - Use the slider for fine adjustments
     - Use the quick adjustment buttons (++, +, -, --)

4. **Batch operations**:
   - "Level All" - Sets all points to the average value
   - "Offset All Points" - Add/subtract a value from all points

5. **Save your changes**:
   - Click the "Save" button
   - A backup will be created as `printer.cfg.backup`

6. **Reset if needed**:
   - Click "Reset" to restore original values

## Understanding the Display

- **Heatmap Colors**:
  - Red/Orange = Higher points (farther from nozzle)
  - Yellow/Green = Lower points (closer to nozzle)

- **Grid Coordinates**:
  - X axis (horizontal): 0-9
  - Y axis (vertical): 0-9
  - Total: 100 points

- **Physical Coordinates**:
  - Bed range: X: 16-786mm, Y: 10-767mm
  - Approximate position shown when point selected

## Tips

- Your bed mesh shows all values are negative (around -4.3 to -4.5mm)
- Smaller (less negative) values = nozzle closer to bed
- Larger (more negative) values = nozzle farther from bed
- After editing, restart Klipper to apply changes
- Always test print after making significant adjustments

## Troubleshooting

- If the tool can't find printer.cfg, check the path in the code
- Make sure Klipper is not running when you save changes
- Keep the backup file safe in case you need to revert

## Next Steps After Editing

1. Save your changes in the editor
2. Restart Klipper firmware
3. Run a test print to verify the adjustments
4. Fine-tune as needed

## File Structure

```
/home/user/BedLevel/
├── printer.cfg           # Your printer configuration
├── printer.cfg.backup    # Automatic backup (created on save)
├── bed_level_editor.py   # The editor tool
├── requirements.txt      # Python dependencies
└── README.md            # This file
```
