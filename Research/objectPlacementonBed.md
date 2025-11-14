Now I have the information I need about Elegoo Slicer. Let me create the implementation guide.

```markdown
# Elegoo Slicer - Bed Mesh Test Print Position Fix
## Implementation Guide for Coding Agents

## Overview
Elegoo Slicer is based on OrcaSlicer (forked from Bambu Studio → PrusaSlicer → Slic3r), and by default **centers objects on the build plate when importing**. This guide provides solutions to generate test squares that maintain their bed mesh positions when imported into Elegoo Slicer.

---

## The Problem

**Elegoo Slicer behavior:**
- When you import STL/3MF files, objects are auto-centered on the build plate
- The "Center Object" option is checked by default, which prevents manual positioning
- Imported models lose their absolute coordinate positions

**What we need:**
- Test squares to appear at their exact bed mesh grid locations
- Positions to be locked/preserved after import
- Ability to generate G-code with objects in specific locations

---

## Solution Architecture

### Three-Tiered Approach

1. **Generate 3MF Scene with Transform Matrices** (primary method)
2. **Add positioning metadata for manual verification** (fallback)
3. **Generate slicer-ready project file** (Elegoo Slicer specific)

---

## Implementation Part 1: Scene-Based 3MF Export

### Updated Core Class Methods

```
import trimesh
import trimesh.scene
import numpy as np
from typing import List, Tuple, Dict
import json

class BedMeshTestGenerator:
    """Generate test print files from Klipper bed mesh modifications."""
    
    def __init__(self, mesh_config: Dict, mesh_ Dict):
        self.mesh_config = mesh_config
        self.mesh_data = mesh_data
        self.grid_x = None
        self.grid_y = None
        self.z_values = None
        self.x_spacing = None
        self.y_spacing = None
        self.modified_cells = set()
        self.cell_metadata = {}  # Store info about each cell
        
        self._calculate_grid()
        
    def _calculate_grid(self):
        """Calculate grid coordinates from mesh config."""
        mesh_min_x, mesh_min_y = self.mesh_config['mesh_min']
        mesh_max_x, mesh_max_y = self.mesh_config['mesh_max']
        
        rows = len(self.mesh_data['points'])
        cols = len(self.mesh_data['points'])
        
        x_coords = np.linspace(mesh_min_x, mesh_max_x, cols)
        y_coords = np.linspace(mesh_min_y, mesh_max_y, rows)
        
        self.grid_x, self.grid_y = np.meshgrid(x_coords, y_coords)
        self.z_values = np.array(self.mesh_data['points'])
        
        self.x_spacing = (mesh_max_x - mesh_min_x) / (cols - 1) if cols > 1 else 10
        self.y_spacing = (mesh_max_y - mesh_min_y) / (rows - 1) if rows > 1 else 10
        
    def mark_cell_modified(self, row: int, col: int, new_z_value: float = None):
        """
        Mark a grid cell as modified.
        
        Args:
            row: Row index in mesh grid
            col: Column index in mesh grid
            new_z_value: Optional new Z offset value for this cell
        """
        self.modified_cells.add((row, col))
        
        # Store metadata for this cell
        self.cell_metadata[(row, col)] = {
            'row': row,
            'col': col,
            'x': float(self.grid_x[row, col]),
            'y': float(self.grid_y[row, col]),
            'original_z': float(self.z_values[row, col]),
            'new_z': new_z_value if new_z_value is not None else float(self.z_values[row, col])
        }
```

### Generate Individual Test Squares (Separate Objects)

```
    def generate_test_squares_scene(self, layer_height: float = 0.2, 
                                   num_layers: int = 2,
                                   square_padding: float = 2.0) -> trimesh.Scene:
        """
        Generate a trimesh Scene with separate test squares at correct positions.
        This preserves individual object positions for Elegoo Slicer.
        
        Args:
            layer_height: Layer height in mm (default 0.2)
            num_layers: Number of layers for test print (default 2)
            square_padding: Padding to subtract from cell size (default 2.0mm)
            
        Returns:
            trimesh.Scene with positioned test squares
        """
        if not self.modified_cells:
            raise ValueError("No modified cells marked. Use mark_cell_modified() first.")
        
        test_height = layer_height * num_layers
        scene = trimesh.Scene()
        
        # Calculate square size (use smaller dimension for square aspect)
        cell_size = min(self.x_spacing, self.y_spacing) - square_padding
        
        # Ensure minimum printable size
        if cell_size < 5.0:
            print(f"Warning: Cell size {cell_size}mm is very small. Consider reducing padding.")
            cell_size = max(cell_size, 5.0)
        
        for row, col in sorted(self.modified_cells):
            # Get center position for this cell
            center_x = self.grid_x[row, col]
            center_y = self.grid_y[row, col]
            
            # Create box at ORIGIN first (important for transforms)
            box = trimesh.creation.box(
                extents=[cell_size, cell_size, test_height]
            )
            
            # Create 4x4 transformation matrix
            # This tells Elegoo Slicer exactly where to place the object
            transform = np.eye(4)
            transform[1] = center_x  # X translation
            transform[2][1] = center_y  # Y translation
            transform[3][1] = test_height / 2  # Z translation (half height so base at Z=0)
            
            # Create unique node name for this test square
            node_name = f"mesh_test_r{row:02d}_c{col:02d}"
            
            # Add metadata to the mesh itself
            box.metadata['cell_row'] = row
            box.metadata['cell_col'] = col
            box.metadata['position_x_mm'] = float(center_x)
            box.metadata['position_y_mm'] = float(center_y)
            box.metadata['cell_size_mm'] = float(cell_size)
            
            if (row, col) in self.cell_meta
                box.metadata['original_z'] = self.cell_metadata[(row, col)]['original_z']
                box.metadata['new_z'] = self.cell_metadata[(row, col)]['new_z']
            
            # Add to scene with transform
            scene.add_geometry(
                box,
                node_name=node_name,
                geom_name=node_name,
                transform=transform
            )
        
        # Add scene-level metadata
        scene.metadata['title'] = 'Klipper Bed Mesh Test Print'
        scene.metadata['generator'] = 'BedMeshTestGenerator'
        scene.metadata['layer_height_mm'] = layer_height
        scene.metadata['num_layers'] = num_layers
        scene.metadata['num_test_squares'] = len(self.modified_cells)
        scene.metadata['mesh_min'] = self.mesh_config['mesh_min']
        scene.metadata['mesh_max'] = self.mesh_config['mesh_max']
        
        return scene
```

---

## Implementation Part 2: Export for Elegoo Slicer

### Export Scene to 3MF with Positions

```
    def export_for_elegoo_slicer(self, filename: str, 
                                 layer_height: float = 0.2,
                                 num_layers: int = 2) -> str:
        """
        Export 3MF file optimized for Elegoo Slicer with preserved positions.
        
        Args:
            filename: Output filename (will add .3mf if missing)
            layer_height: Layer height in mm
            num_layers: Number of layers for test squares
            
        Returns:
            Path to exported file
        """
        # Generate scene with positioned objects
        scene = self.generate_test_squares_scene(
            layer_height=layer_height,
            num_layers=num_layers
        )
        
        # Ensure .3mf extension
        if not filename.endswith('.3mf'):
            filename = f'{filename}.3mf'
        
        # Export scene
        # trimesh will write individual objects with their transform matrices
        scene.export(filename, file_type='3mf')
        
        print(f"✓ Exported {len(self.modified_cells)} test squares to: {filename}")
        print(f"  Layer height: {layer_height}mm")
        print(f"  Total height: {layer_height * num_layers}mm")
        print(f"  Test square size: ~{min(self.x_spacing, self.y_spacing) - 2.0:.1f}mm")
        
        # Also export position guide
        guide_file = filename.replace('.3mf', '_positions.json')
        self._export_position_guide(guide_file)
        
        return filename
    
    def _export_position_guide(self, filename: str):
        """Export JSON file with position information for verification."""
        guide_data = {
            'mesh_config': self.mesh_config,
            'modified_cells': [
                self.cell_metadata[cell] for cell in sorted(self.modified_cells)
            ],
            'instructions': {
                'elegoo_slicer': [
                    '1. Open Elegoo Slicer',
                    '2. File → Open Project (NOT Add Model)',
                    '3. Select the .3mf file',
                    '4. UNCHECK "Center Object" for each imported part',
                    '5. Verify positions match the coordinates in this file',
                    '6. Lock object placement (right-click → Lock)',
                    '7. Slice and print'
                ]
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(guide_data, f, indent=2)
        
        print(f"✓ Position guide exported to: {filename}")
```

---

## Implementation Part 3: Alternative STL Export with Reference Frame

For Elegoo Slicer versions that don't properly handle 3MF transforms, provide an STL with a reference frame:

```
    def export_with_reference_frame(self, filename: str,
                                    layer_height: float = 0.2,
                                    num_layers: int = 2,
                                    add_frame: bool = True) -> str:
        """
        Export STL with optional reference frame showing bed boundaries.
        Use this if 3MF positioning doesn't work in Elegoo Slicer.
        
        Args:
            filename: Output filename
            layer_height: Layer height in mm
            num_layers: Number of layers
            add_frame: If True, adds thin frame around bed edges
            
        Returns:
            Path to exported file
        """
        test_height = layer_height * num_layers
        meshes = []
        
        # Generate test squares
        cell_size = min(self.x_spacing, self.y_spacing) - 2.0
        
        for row, col in sorted(self.modified_cells):
            center_x = self.grid_x[row, col]
            center_y = self.grid_y[row, col]
            
            box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])
            box.apply_translation([center_x, center_y, test_height / 2])
            
            meshes.append(box)
        
        # Add reference frame if requested
        if add_frame:
            frame = self._create_reference_frame(test_height)
            meshes.append(frame)
        
        # Combine all meshes
        if len(meshes) == 1:
            combined = meshes
        else:
            combined = trimesh.util.concatenate(meshes)
        
        # Export to STL
        if not filename.endswith('.stl'):
            filename = f'{filename}.stl'
        
        combined.export(filename, file_type='stl')
        
        print(f"✓ Exported combined mesh with {len(self.modified_cells)} squares to: {filename}")
        if add_frame:
            print("  ✓ Reference frame included")
        
        return filename
    
    def _create_reference_frame(self, height: float) -> trimesh.Trimesh:
        """
        Create a thin frame around the mesh boundaries.
        Helps visualize the bed coordinate system in slicer.
        """
        mesh_min_x, mesh_min_y = self.mesh_config['mesh_min']
        mesh_max_x, mesh_max_y = self.mesh_config['mesh_max']
        
        frame_width = 2.0  # Width of frame lines
        frame_meshes = []
        
        # Bottom edge
        bottom = trimesh.creation.box(
            extents=[mesh_max_x - mesh_min_x, frame_width, height]
        )
        bottom.apply_translation([
            (mesh_min_x + mesh_max_x) / 2,
            mesh_min_y,
            height / 2
        ])
        frame_meshes.append(bottom)
        
        # Top edge
        top = trimesh.creation.box(
            extents=[mesh_max_x - mesh_min_x, frame_width, height]
        )
        top.apply_translation([
            (mesh_min_x + mesh_max_x) / 2,
            mesh_max_y,
            height / 2
        ])
        frame_meshes.append(top)
        
        # Left edge
        left = trimesh.creation.box(
            extents=[frame_width, mesh_max_y - mesh_min_y, height]
        )
        left.apply_translation([
            mesh_min_x,
            (mesh_min_y + mesh_max_y) / 2,
            height / 2
        ])
        frame_meshes.append(left)
        
        # Right edge
        right = trimesh.creation.box(
            extents=[frame_width, mesh_max_y - mesh_min_y, height]
        )
        right.apply_translation([
            mesh_max_x,
            (mesh_min_y + mesh_max_y) / 2,
            height / 2
        ])
        frame_meshes.append(right)
        
        return trimesh.util.concatenate(frame_meshes)
```

---

## Implementation Part 4: Validation and Debugging

### Verify Export Contains Correct Positions

```
    def validate_export(self, filename: str) -> bool:
        """
        Validate that exported 3MF contains correct position data.
        
        Args:
            filename: Path to .3mf file to validate
            
        Returns:
            True if validation passes
        """
        import zipfile
        import xml.etree.ElementTree as ET
        
        try:
            with zipfile.ZipFile(filename, 'r') as z:
                # Read the 3D model XML
                model_xml = z.read('3D/3dmodel.model').decode('utf-8')
                
                root = ET.fromstring(model_xml)
                
                # Define XML namespace
                ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
                
                # Find all build items
                items = root.findall('.//m:item', ns)
                
                print(f"\n=== 3MF Validation for {filename} ===")
                print(f"Found {len(items)} objects in 3MF file")
                
                if len(items) != len(self.modified_cells):
                    print(f"⚠ Warning: Expected {len(self.modified_cells)} objects, found {len(items)}")
                
                # Check each item for transform
                for idx, item in enumerate(items):
                    obj_id = item.get('objectid')
                    transform = item.get('transform')
                    
                    print(f"\nObject {idx + 1}:")
                    print(f"  ID: {obj_id}")
                    
                    if transform:
                        print(f"  Transform: {transform}")
                        # Parse transform matrix (format: "m00 m01 m02 m10 m11 m12 m20 m21 m22 tx ty tz")
                        values = [float(x) for x in transform.split()]
                        if len(values) == 12:
                            tx, ty, tz = values[4], values[5], values[6]
                            print(f"  Position: X={tx:.2f}, Y={ty:.2f}, Z={tz:.2f} mm")
                        elif len(values) == 16:
                            tx, ty, tz = values[7], values[8], values[9]
                            print(f"  Position: X={tx:.2f}, Y={ty:.2f}, Z={tz:.2f} mm")
                    else:
                        print(f"  ⚠ No transform matrix found!")
                
                print("\n=== Validation Complete ===\n")
                return True
                
        except Exception as e:
            print(f"✗ Validation failed: {e}")
            return False
```

---

## Implementation Part 5: Complete Usage Example

```
def main():
    """Complete example of generating positioned test prints for Elegoo Slicer."""
    
    # Sample Klipper bed mesh configuration
    mesh_config = {
        'mesh_min': (30.0, 30.0),
        'mesh_max': (320.0, 320.0),
        'probe_count': (7, 7),
    }
    
    # Sample mesh data (7x7 grid)
    mesh_data = {
        'name': 'default',
        'points': [
            [0.100, 0.095, 0.090, 0.085, 0.090, 0.095, 0.100],
            [0.080, 0.075, 0.070, 0.065, 0.070, 0.075, 0.080],
            [0.060, 0.055, 0.050, 0.045, 0.050, 0.055, 0.060],
            [0.040, 0.035, 0.030, 0.025, 0.030, 0.035, 0.040],
            [0.060, 0.055, 0.050, 0.045, 0.050, 0.055, 0.060],
            [0.080, 0.075, 0.070, 0.065, 0.070, 0.075, 0.080],
            [0.100, 0.095, 0.090, 0.085, 0.090, 0.095, 0.100],
        ]
    }
    
    # Create generator
    generator = BedMeshTestGenerator(mesh_config, mesh_data)
    
    # Mark some cells as modified (user would do this in UI)
    # Example: center area needs adjustment
    generator.mark_cell_modified(2, 3, new_z_value=0.040)  # Was 0.045, adjusted to 0.040
    generator.mark_cell_modified(3, 3, new_z_value=0.020)  # Was 0.025, adjusted to 0.020
    generator.mark_cell_modified(3, 4, new_z_value=0.025)  # Was 0.030, adjusted to 0.025
    generator.mark_cell_modified(4, 3, new_z_value=0.040)  # Was 0.045, adjusted to 0.040
    
    print(f"Marked {len(generator.modified_cells)} cells for testing\n")
    
    # Method 1: Export 3MF with positioned objects (RECOMMENDED)
    print("=" * 60)
    print("METHOD 1: 3MF Scene Export (Recommended)")
    print("=" * 60)
    
    output_3mf = generator.export_for_elegoo_slicer(
        filename='bed_mesh_test',
        layer_height=0.2,
        num_layers=2
    )
    
    # Validate the export
    generator.validate_export(output_3mf)
    
    # Method 2: Export STL with reference frame (FALLBACK)
    print("\n" + "=" * 60)
    print("METHOD 2: STL with Reference Frame (Fallback)")
    print("=" * 60)
    
    output_stl = generator.export_with_reference_frame(
        filename='bed_mesh_test_framed',
        layer_height=0.2,
        num_layers=2,
        add_frame=True
    )
    
    print("\n" + "=" * 60)
    print("IMPORT INSTRUCTIONS FOR ELEGOO SLICER")
    print("=" * 60)
    print("\n3MF Import (Method 1):")
    print("  1. Open Elegoo Slicer")
    print("  2. File → Open Project (NOT 'Add Model')")
    print("  3. Select: bed_mesh_test.3mf")
    print("  4. For EACH imported object:")
    print("     - Right-click on object")
    print("     - UNCHECK 'Center Object' if checked")
    print("     - Verify position in Move tool matches _positions.json")
    print("     - Right-click → Lock Placement")
    print("  5. Slice and generate G-code")
    print("  6. Print and measure results")
    
    print("\nSTL Import (Method 2 - if Method 1 doesn't work):")
    print("  1. Open Elegoo Slicer")
    print("  2. Add → Import STL: bed_mesh_test_framed.stl")
    print("  3. Use Move tool to verify position")
    print("  4. Reference frame shows mesh boundaries")
    print("  5. DO NOT use 'Center' or 'Auto Arrange'")
    print("  6. Slice and print")
    
    print("\n" + "=" * 60)
    print("FILES GENERATED")
    print("=" * 60)
    print(f"  -  {output_3mf}")
    print(f"  -  {output_3mf.replace('.3mf', '_positions.json')}")
    print(f"  -  {output_stl}")
    print("\n")


if __name__ == '__main__':
    main()
```

---

## Implementation Part 6: Elegoo Slicer Specific Workarounds

### Understanding Elegoo Slicer's Coordinate System

```
class ElegooSlicerHelper:
    """Helper functions for Elegoo Slicer compatibility."""
    
    @staticmethod
    def get_slicer_instructions() -> dict:
        """Get detailed instructions for different Elegoo Slicer scenarios."""
        return {
            'import_3mf_with_positions': [
                "1. Launch Elegoo Slicer",
                "2. Click 'File' → 'Open Project' (DO NOT use 'Add Model')",
                "3. Navigate to your .3mf file and open it",
                "4. Multiple objects should appear on the bed",
                "5. Click on first object to select it",
                "6. Look at left toolbar - find 'Move' tool",
                "7. UNCHECK the 'Center Object' checkbox",
                "8. Verify X/Y coordinates match the position guide JSON",
                "9. Right-click object → 'Lock Placement'",
                "10. Repeat steps 5-9 for each test square",
                "11. When all objects are positioned and locked, click 'Slice'"
            ],
            'manual_positioning': [
                "If auto-positioning fails:",
                "1. Import the 3MF/STL normally",
                "2. Select first test square",
                "3. Click 'Move' tool in left toolbar",
                "4. UNCHECK 'Center Object'",
                "5. Open the _positions.json file",
                "6. Manually enter X and Y coordinates from JSON",
                "7. Set Z to 0 (objects should sit on bed)",
                "8. Lock the object placement",
                "9. Repeat for remaining squares"
            ],
            'troubleshooting': {
                'objects_centered': "Uncheck 'Center Object' in Move tool",
                'objects_overlapping': "Spacing was calculated wrong, check mesh_min/mesh_max",
                'objects_off_bed': "Klipper coordinates don't match printer bed size",
                'cant_move_objects': "Must uncheck 'Center Object' first",
                'positions_reset_after_slice': "Lock placement before slicing"
            }
        }
    
    @staticmethod
    def verify_printer_bed_size(mesh_config: dict, printer_bed_size: tuple) -> bool:
        """
        Verify mesh coordinates fit within printer bed.
        
        Args:
            mesh_config: Dict with mesh_min and mesh_max
            printer_bed_size: Tuple of (width, depth) in mm
            
        Returns:
            True if mesh fits within bed
        """
        mesh_min_x, mesh_min_y = mesh_config['mesh_min']
        mesh_max_x, mesh_max_y = mesh_config['mesh_max']
        bed_width, bed_depth = printer_bed_size
        
        print(f"\n=== Bed Size Verification ===")
        print(f"Printer bed: {bed_width} x {bed_depth} mm")
        print(f"Mesh area: {mesh_min_x}-{mesh_max_x} x {mesh_min_y}-{mesh_max_y} mm")
        print(f"Mesh dimensions: {mesh_max_x - mesh_min_x} x {mesh_max_y - mesh_min_y} mm")
        
        fits = (
            mesh_min_x >= 0 and 
            mesh_min_y >= 0 and
            mesh_max_x <= bed_width and
            mesh_max_y <= bed_depth
        )
        
        if fits:
            print("✓ Mesh fits within printer bed")
        else:
            print("✗ ERROR: Mesh coordinates exceed printer bed!")
            if mesh_max_x > bed_width:
                print(f"  - X extends {mesh_max_x - bed_width:.1f}mm beyond bed width")
            if mesh_max_y > bed_depth:
                print(f"  - Y extends {mesh_max_y - bed_depth:.1f}mm beyond bed depth")
        
        print()
        return fits
```

---

## Implementation Part 7: Testing Suite

```
def test_export_pipeline():
    """Test the complete export pipeline."""
    
    print("=== Running Export Pipeline Tests ===\n")
    
    # Test configuration
    mesh_config = {
        'mesh_min': (30.0, 30.0),
        'mesh_max': (320.0, 320.0),
        'probe_count': (5, 5),
    }
    
    mesh_data = {
        'points': [
            [0.10, 0.09, 0.08, 0.09, 0.10],
            [0.08, 0.07, 0.06, 0.07, 0.08],
            [0.06, 0.05, 0.04, 0.05, 0.06],
            [0.08, 0.07, 0.06, 0.07, 0.08],
            [0.10, 0.09, 0.08, 0.09, 0.10],
        ]
    }
    
    # Create generator
    gen = BedMeshTestGenerator(mesh_config, mesh_data)
    
    # Test 1: Mark cells
    print("Test 1: Marking cells...")
    gen.mark_cell_modified(2, 2, 0.03)  # Center cell
    gen.mark_cell_modified(1, 2, 0.06)  # Above center
    assert len(gen.modified_cells) == 2
    print("✓ Cell marking works\n")
    
    # Test 2: Scene generation
    print("Test 2: Generating scene...")
    scene = gen.generate_test_squares_scene(layer_height=0.2, num_layers=2)
    assert len(scene.geometry) == 2
    print(f"✓ Scene generated with {len(scene.geometry)} objects\n")
    
    # Test 3: 3MF export
    print("Test 3: Exporting 3MF...")
    output = gen.export_for_elegoo_slicer('test_output', layer_height=0.2)
    assert output.endswith('.3mf')
    print(f"✓ 3MF exported to {output}\n")
    
    # Test 4: Validation
    print("Test 4: Validating 3MF...")
    valid = gen.validate_export(output)
    assert valid
    print("✓ 3MF validation passed\n")
    
    # Test 5: Bed size check
    print("Test 5: Bed size verification...")
    helper = ElegooSlicerHelper()
    fits = helper.verify_printer_bed_size(mesh_config, (350, 350))
    assert fits
    print("✓ Bed size check passed\n")
    
    print("=== All Tests Passed ===\n")


if __name__ == '__main__':
    # Run tests first
    test_export_pipeline()
    
    # Then run main example
    main()
```

---

## Key Points for Elegoo Slicer

### Critical Facts About Elegoo Slicer

1. **Based on OrcaSlicer**: Elegoo Slicer is forked from OrcaSlicer → Bambu Studio → PrusaSlicer → Slic3r
2. **Default behavior**: Centers objects on import
3. **"Center Object" checkbox**: Must be UNCHECKED to manually position objects
4. **Import method matters**: Use "Open Project" not "Add Model" for 3MF positioning
5. **Coordinate system**: Origin (0,0) at front-left corner, Z=0 at bed surface
6. **Lock placement**: Right-click → Lock Placement to prevent auto-arrangement

### File Format Priority

1. **Best: 3MF with Scene** - Individual objects with transform matrices
2. **Good: 3MF Project** - Saved Elegoo Slicer project file
3. **Fallback: STL with frame** - Single combined mesh with reference geometry
4. **Last resort: Individual STLs** - Import and position manually

---

## Dependencies

```
# Required packages
pip install trimesh numpy

# Optional for advanced features
pip install networkx   # Mesh processing
pip install rtree      # Spatial indexing
```

---

## Summary Checklist for Implementation

### Data Layer
- [ ] Parse Klipper mesh configuration (mesh_min, mesh_max, probe_count)
- [ ] Calculate grid coordinates and spacing
- [ ] Track modified cells with metadata (row, col, X, Y, Z values)

### Generation Layer
- [ ] Create individual box primitives at origin
- [ ] Build 4x4 transformation matrices for each box
- [ ] Add to trimesh.Scene with unique node names
- [ ] Include metadata in scene and individual meshes

### Export Layer
- [ ] Export scene to 3MF format
- [ ] Generate position guide JSON file
- [ ] Optionally create STL with reference frame
- [ ] Validate exported 3MF contains transforms

### User Guidance Layer
- [ ] Print import instructions for Elegoo Slicer
- [ ] Provide position verification data
- [ ] Include troubleshooting tips
- [ ] Verify printer bed size compatibility

---

## References

- Elegoo Slicer User Manual V1.7
- OrcaSlicer Documentation (parent project)
- 3MF Core Specification
- Klipper Bed Mesh Documentation
- Trimesh Python Library

---

## Notes for Coding Agent

**Priority Tasks:**
1. Implement `generate_test_squares_scene()` - creates Scene with transforms
2. Implement `export_for_elegoo_slicer()` - exports 3MF with positioned objects
3. Implement `validate_export()` - verifies 3MF contains position data
4. Add position guide JSON export

**Testing:**
- Test with various grid sizes (5x5, 7x7, 9x9)
- Verify exported 3MF opens in Elegoo Slicer
- Confirm objects appear at correct bed positions
- Test with different bed sizes (Elegoo Neptune series)

**Edge Cases:**
- Handle very small cells (< 5mm) - warn user
- Handle mesh coordinates outside bed bounds - validation error
- Handle single modified cell - no concatenation needed
- Handle very large grids (>10x10) - performance consideration

**User Experience:**
- Clear console output with checkmarks (✓) for success
- Warning symbols (⚠) for potential issues
- Error symbols (✗) for failures
- Generate position guide for manual verification
- Include step-by-step Elegoo Slicer instructions
```

Sources
[1] Bed Level Calibration Square Grid by wsreith - Printables.com https://www.printables.com/model/69956-bed-level-calibration-square-grid
[2] Model file formats | DataMesh https://datamesh.com/support/user-manual/datamesh-importer/previous-versions-importer/version-updated-july-2024-importer/model-file-formats-2/
[3] How to create a 3D mesh from a heightmap represented as a float ... https://stackoverflow.com/questions/67028493/how-to-create-a-3d-mesh-from-a-heightmap-represented-as-a-float-array
[4] Best method for 3D printer bed levelling - YouTube https://www.youtube.com/watch?v=RZRY6kunAvs
[5] An introduction to the 3MF file format - UltiMaker https://ultimaker.com/learn/an-introduction-to-the-3mf-file-format/
[6] Bed Mesh - Klipper documentation https://www.klipper3d.org/Bed_Mesh.html
[7] Converting Map Height Data Into 3D Tiles : 6 Steps - Instructables https://www.instructables.com/Converting-Map-Height-Data-Into-3D-Tiles/
[8] Defining complex geometries using trimesh - Flexcompute https://www.flexcompute.com/tidy3d/examples/notebooks/CreatingGeometryUsingTrimesh/
[9] klipper - GitSkyAlex https://git.skyalex.net/SkyAlex/klipper/src/commit/0b05a38361ea9455b3bed736a4d8d3af760da907/docs/Bed_Mesh.md?display=source
[10] Am i missing something with 3mf files? : r/ElegooCentauriCarbon https://www.reddit.com/r/ElegooCentauriCarbon/comments/1lpm9ha/am_i_missing_something_with_3mf_files/
[11] This Is How You ACTUALLY Use Elegoo Slicer - YouTube https://www.youtube.com/watch?v=INjgjcJmU54
[12] The ONLY Elegoo Slicer Tutorial You Need - Beginners Guide! https://www.youtube.com/watch?v=dXaUODY7aUk
[13] Ok this is going to be a newbie question.....why am I having g issues ... https://www.facebook.com/groups/2343515562674370/posts/2582275242131733/
[14] How to prepare and slice an STL file for 3d printing - YouTube https://www.youtube.com/watch?v=lpf38aMk8d8
[15] ELEGOO Neptune 4 Plus Compatibility & Setup Guide - SimplyPrint https://simplyprint.io/compatibility/elegoo-neptune-4-plus
[16] How to position and support your 3d printed resin models in Chitubox. https://www.youtube.com/watch?v=-IFTDv_i4-0
[17] 3mf file with more objects, position is lost when importing – PrusaSlicer https://forum.prusa3d.com/forum/prusaslicer/3mf-file-with-more-objects-position-is-lost-when-importing/
[18] ELEGOO Neptune 4 PLUS Guide: Setup, Firmware Update, Slicing ... https://www.youtube.com/watch?v=qjh1lnXSqcM
[19] How to use CHITUBOX 3d slicer - YouTube https://www.youtube.com/watch?v=jeebjF_2Bug
[20] Elegoo slicer - Reddit https://www.reddit.com/r/elegoo/comments/1imd9yx/elegoo_slicer/
[21] What slicers work with Elegoo Centauri Carbon? - Facebook https://www.facebook.com/groups/2343515562674370/posts/2548814758811115/
[22] SatelLite 3D Slicer - ELEGOO https://www.elegoo.com/pages/satellite-3d-slicer
[23] Elegoo's new FREE Slicer has one awesome feature! - YouTube https://www.youtube.com/watch?v=xcQkmaRXyCU
[24] OrcaSlicer vs PrusaSlicer vs Cura - Comparing the Most Popular ... https://www.obico.io/blog/orcaslicer%20vs%20prusaslicer%20vs%20cura/
[25] ELEGOO 3D Slicing Software User Manual V1.7 https://manuals.plus/m/bc9f1c17d18666fd10689ed6651f587ee780f785fd36e3ff02c3eae6a6c45779
[26] Three Slicers: Cura, PrusaSlicer, IdeaMaker - Which One is the Best? https://www.youtube.com/watch?v=MReQCGJLszc
[27] Coordinate systems - 3D Slicer documentation - Read the Docs https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html
[28] [PDF] User Manual ELEGOO 3D Slicing Software https://3dprinteq.dk/wp-content/uploads/ElegooSlicer-User-Manual_V1.1.7.pdf
