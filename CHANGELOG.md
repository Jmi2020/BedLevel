# Changelog

## v3.0 - Pro Edition (Latest) 🎨
**Date**: 2025-11-14

### Major UX/UI Overhaul

#### Fixed Issues
- ✅ **Text Contrast Fixed**: Light backgrounds now have dark text, dark backgrounds have light text
- ✅ **No More Resize Bug**: Stable plot layout, no jumping when clicking points
- ✅ **Button Visibility**: All buttons have proper contrast (white text on colored backgrounds)

#### New Design Features
- 🎨 **Modern Dark Theme**: Professional color scheme with proper contrast ratios
- 🎨 **Hover Effects**: Buttons lighten on hover for better feedback
- 🎨 **Status Bar**: Real-time feedback at bottom with keyboard shortcuts
- 🎨 **Mode Indicator**: Clear visual indicator showing Point vs Region mode
- 🎨 **Better Typography**: Segoe UI fonts, proper sizing hierarchy
- 🎨 **Improved Layout**: Organized sections with clear visual grouping

#### Enhanced Usability
- ⌨️ **Keyboard Shortcuts**:
  - Ctrl+S = Save
  - Ctrl+Z = Reset
  - Ctrl+O = Open file
  - Esc = Clear selection
- 📊 **Better Value Display**: Large, prominent Z-offset value in monospace font
- 🎯 **Visual Selection**: Glowing border on selected point, red border for regions
- 📈 **Prettier Statistics**: Boxed layout with clear formatting
- 🔄 **Smooth Interactions**: No jarring visual changes

#### Text Readability Improvements
- Text on light cells: Dark text (#1a1a1a) with subtle background
- Text on dark cells: Light text (#f0f0f0) with subtle background
- Threshold: 45% normalized value (was 55%, now more accurate)
- Added semi-transparent bbox for better readability

#### Performance Improvements
- Use `draw_idle()` instead of `draw()` for better responsiveness
- Stable colorbar (created once, updated in place)
- Fixed layout with `constrained` layout manager
- Reduced unnecessary redraws

#### Visual Enhancements
- Gradient backgrounds on sections
- Consistent spacing and padding
- Icon emojis for better visual navigation
- Modern button styling with relief=FLAT
- Professional color palette

### Files
- `bed_level_editor_pro.py` - New Pro version (1,100+ lines)

---

## v2.0 - Enhanced Edition
**Date**: 2025-11-14

### Features Added
- 3D visualization with rotatable surface plots
- Interpolated mesh preview (shows what Klipper uses)
- Region selection with drag-to-select
- Region tools (average, smooth)
- Bicubic interpolation preview

### Files
- `bed_level_editor_enhanced.py`

---

## v1.0 - Standard Edition
**Date**: 2025-11-14

### Initial Release
- Basic 2D heatmap visualization
- Point-by-point editing
- Batch operations (flatten, offset all)
- File browser
- Statistics panel
- Auto-backup on save

### Files
- `bed_level_editor.py`
