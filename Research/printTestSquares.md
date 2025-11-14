```markdown
# Klipper Bed Mesh Test Print Generator - Implementation Guide

## Overview
This guide provides a complete implementation specification for generating 2-layer test print files (STL/3MF) from Klipper bed mesh data. The software allows users to modify bed mesh Z-values and automatically generate test squares for the modified areas.

## Architecture

### Components
1. **Klipper Data Parser** - Extracts bed mesh configuration and Z-values
2. **Mesh Modifier Interface** - Allows users to adjust Z-values for specific grid cells
3. **3D Model Generator** - Converts modified grid cells to 3D geometry
4. **File Exporter** - Outputs STL or 3MF files for slicer import

---

## 1. Data Requirements from Klipper

### Configuration Parameters to Extract

From `printer.cfg` or via Moonraker API:

```
# Required parameters from [bed_mesh] section
mesh_config = {
    'mesh_min': (float, float),      # e.g., (30.0, 30.0) - lower-left corner
    'mesh_max': (float, float),      # e.g., (320.0, 320.0) - upper-right corner
    'probe_count': (int, int),       # e.g., (7, 7) - grid dimensions
    'mesh_pps': (int, int),          # e.g., (2, 2) - interpolation points per segment
    'algorithm': str,                # 'lagrange' or 'bicubic'
    'fade_start': float,             # Optional: Z height where compensation starts fading
    'fade_end': float,               # Optional: Z height where compensation ends
    'fade_target': float,            # Optional: Target Z position for fade
}

# Current mesh profile data
mesh_data = {
    'name': str,                     # Profile name (e.g., 'default')
    'points': [[float]],             # 2D array of Z-offset values
    'mesh_params': dict,             # Copy of mesh_config for this profile
}
```

### Accessing Mesh Data

**Option 1: Parse saved profile from printer.cfg**
```
# Profiles are stored as:
# [bed_mesh <profile_name>]
# version = 1
# points = 
#     0.123, 0.145, 0.167, ...
#     0.098, 0.112, 0.134, ...
```

**Option 2: Query via Moonraker API**
```
# GET request to Moonraker
GET http://printer-ip/printer/objects/query?bed_mesh

# Returns current mesh state including:
# - mesh_matrix (the Z-values)
# - mesh_min, mesh_max
# - probed_matrix
# - profiles (available saved profiles)
```

**Option 3: Use BED_MESH_OUTPUT command**
```
BED_MESH_OUTPUT
# Outputs mesh to console/log
```

---

## 2. Grid Calculation

### Converting Mesh Parameters to Real-World Coordinates

```
import numpy as np

def calculate_grid_coordinates(mesh_config, mesh_data):
    """
    Calculate XY coordinates for each grid point.
    
    Returns:
        grid_x: (rows, cols) array of X coordinates
        grid_y: (rows, cols) array of Y coordinates
        z_values: (rows, cols) array of Z offset values
    """
    mesh_min_x, mesh_min_y = mesh_config['mesh_min']
    mesh_max_x, mesh_max_y = mesh_config['mesh_max']
    
    # Get actual mesh dimensions from data
    rows = len(mesh_data['points'])
    cols = len(mesh_data['points'])
    
    # Calculate cell spacing
    x_spacing = (mesh_max_x - mesh_min_x) / (cols - 1)
    y_spacing = (mesh_max_y - mesh_min_y) / (rows - 1)
    
    # Generate coordinate grids
    x_coords = np.linspace(mesh_min_x, mesh_max_x, cols)
    y_coords = np.linspace(mesh_min_y, mesh_max_y, rows)
    
    grid_x, grid_y = np.meshgrid(x_coords, y_coords)
    z_values = np.array(mesh_data['points'])
    
    return grid_x, grid_y, z_values, x_spacing, y_spacing
```

### Identifying Modified Cells

```
class MeshModificationTracker:
    """Track which grid cells have been modified by the user."""
    
    def __init__(self, rows, cols):
        self.original_z = None  # Store original Z values
        self.current_z = None   # Store current Z values
        self.modified_cells = set()  # Set of (row, col) tuples
        
    def mark_modified(self, row, col):
        """Mark a cell as modified."""
        self.modified_cells.add((row, col))
        
    def get_modified_cells(self):
        """Return list of modified (row, col) tuples."""
        return list(self.modified_cells)
```

---

## 3. 3D Model Generation

### Setting Up Trimesh

```
pip install trimesh numpy
```

### Test Square Generation Parameters

```
# Configuration for 2-layer test prints
test_config = {
    'layer_height': 0.2,           # Standard layer height in mm
    'num_layers': 2,               # Always 2 for quick test
    'square_padding': 2.0,         # Padding around cell center (mm)
    'base_thickness': 0.2,         # First layer thickness
}

# Calculate test square height
test_height = test_config['layer_height'] * test_config['num_layers']  # 0.4mm
```

### Generate Test Square for Single Cell

```
import trimesh
import numpy as np

def create_test_square(center_x, center_y, x_spacing, y_spacing, test_height, padding=2.0):
    """
    Create a 2-layer test square centered on a grid cell.
    
    Args:
        center_x: X coordinate of cell center
        center_y: Y coordinate of cell center
        x_spacing: X dimension of grid cell
        y_spacing: Y dimension of grid cell
        test_height: Total height (2 * layer_height)
        padding: Additional size beyond cell boundaries
        
    Returns:
        trimesh.Trimesh: 3D mesh of test square
    """
    # Calculate square dimensions
    # Use the smaller of the cell dimensions to fit within grid
    cell_size = min(x_spacing, y_spacing) - padding
    
    # Create a box primitive
    # extents = [width, depth, height]
    box = trimesh.creation.box(
        extents=[cell_size, cell_size, test_height]
    )
    
    # Translate to correct position
    # Move Z up by half height so base sits at Z=0
    translation = [center_x, center_y, test_height / 2]
    box.apply_translation(translation)
    
    return box

```

### Generate Test Squares for All Modified Cells

```
def generate_test_print_mesh(grid_x, grid_y, modified_cells, x_spacing, y_spacing, test_height):
    """
    Generate combined mesh with test squares for all modified cells.
    
    Args:
        grid_x: 2D array of X coordinates
        grid_y: 2D array of Y coordinates
        modified_cells: List of (row, col) tuples
        x_spacing: Grid spacing in X
        y_spacing: Grid spacing in Y
        test_height: Height of each test square
        
    Returns:
        trimesh.Trimesh: Combined mesh of all test squares
    """
    meshes = []
    
    for row, col in modified_cells:
        center_x = grid_x[row, col]
        center_y = grid_y[row, col]
        
        square = create_test_square(
            center_x, center_y, 
            x_spacing, y_spacing, 
            test_height,
            padding=2.0
        )
        
        meshes.append(square)
    
    # Combine all meshes into single mesh
    if len(meshes) == 1:
        combined = meshes
    else:
        combined = trimesh.util.concatenate(meshes)
    
    return combined
```

---

## 4. Alternative: Manual Mesh Construction

If you need more control over vertex placement or want to understand the underlying geometry:

```
def create_box_mesh_manual(center_x, center_y, width, depth, height):
    """
    Manually construct a box mesh from vertices and faces.
    
    Returns:
        vertices: (n, 3) array of vertex positions
        faces: (m, 3) array of triangle indices
    """
    half_w = width / 2
    half_d = depth / 2
    
    # Define 8 vertices of the box
    vertices = np.array([
        # Bottom face (Z=0)
        [center_x - half_w, center_y - half_d, 0],      # 0: back-left-bottom
        [center_x + half_w, center_y - half_d, 0],      # 1: back-right-bottom
        [center_x + half_w, center_y + half_d, 0],      # 2: front-right-bottom
        [center_x - half_w, center_y + half_d, 0],      # 3: front-left-bottom
        
        # Top face (Z=height)
        [center_x - half_w, center_y - half_d, height], # 4: back-left-top
        [center_x + half_w, center_y - half_d, height], # 5: back-right-top
        [center_x + half_w, center_y + half_d, height], # 6: front-right-top
        [center_x - half_w, center_y + half_d, height], # 7: front-left-top
    ])
    
    # Define faces (triangles) with counter-clockwise winding for outward normals
    faces = np.array([
        # Bottom face (looking from below, counter-clockwise)
        [1][2], [3][1],
        
        # Top face (looking from above, counter-clockwise)
        [4][5][6], [4][6][7],
        
        # Side faces
        [2][5], [5][4],  # Back face
        [2][1][6], [2][6][5],  # Right face
        [1][3][7], [1][7][6],  # Front face
        [3][4], [3][4][7],  # Left face
    ])
    
    return vertices, faces


def create_mesh_from_arrays(vertices, faces):
    """Create trimesh object from vertex and face arrays."""
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        process=True  # Automatically merge vertices, fix normals, etc.
    )
    return mesh
```

---

## 5. File Export

### Export to STL (Binary Format - Recommended)

```
def export_to_stl(mesh, filename='bed_mesh_test.stl'):
    """
    Export mesh to binary STL format.
    
    Args:
        mesh: trimesh.Trimesh object
        filename: Output filename
    """
    mesh.export(filename, file_type='stl')
    print(f"Exported {len(mesh.faces)} faces to {filename}")
```

### Export to 3MF (Preferred Format)

```
def export_to_3mf(mesh, filename='bed_mesh_test.3mf', metadata=None):
    """
    Export mesh to 3MF format with optional metadata.
    
    Args:
        mesh: trimesh.Trimesh object
        filename: Output filename
        meta Dict of metadata to embed in file
    """
    # Add metadata to mesh object
    if meta
        mesh.metadata.update(metadata)
    
    # Export to 3MF
    mesh.export(filename, file_type='3mf')
    print(f"Exported to {filename}")
    
    return filename


# Example usage with metadata
metadata = {
    'title': 'Bed Mesh Test Print',
    'description': f'Test squares for modified mesh cells',
    'layer_height': '0.2mm',
    'num_layers': '2',
    'modified_cells': str(len(modified_cells)),
}

export_to_3mf(combined_mesh, 'test_print.3mf', metadata)
```

### Why 3MF is Better

- **Smaller file size**: Vertices stored once vs. repeated in STL
- **Metadata support**: Can embed print settings, cell information
- **Native support**: OrcaSlicer, PrusaSlicer, Cura all prefer 3MF
- **Better precision**: More efficient floating-point encoding

---

## 6. Complete Implementation Example

```
import trimesh
import numpy as np
from typing import List, Tuple, Dict

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
        
        self.x_spacing = (mesh_max_x - mesh_min_x) / (cols - 1)
        self.y_spacing = (mesh_max_y - mesh_min_y) / (rows - 1)
        
    def mark_cell_modified(self, row: int, col: int):
        """Mark a grid cell as modified."""
        self.modified_cells.add((row, col))
        
    def generate_test_mesh(self, layer_height: float = 0.2, num_layers: int = 2) -> trimesh.Trimesh:
        """
        Generate 3D mesh with test squares for all modified cells.
        
        Args:
            layer_height: Layer height in mm
            num_layers: Number of layers (typically 2)
            
        Returns:
            Combined trimesh object
        """
        test_height = layer_height * num_layers
        meshes = []
        
        for row, col in self.modified_cells:
            center_x = self.grid_x[row, col]
            center_y = self.grid_y[row, col]
            
            # Use smaller dimension minus padding
            cell_size = min(self.x_spacing, self.y_spacing) - 2.0
            
            # Create box primitive
            box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])
            box.apply_translation([center_x, center_y, test_height / 2])
            
            meshes.append(box)
        
        if not meshes:
            raise ValueError("No modified cells to generate test print")
        
        # Combine all meshes
        if len(meshes) == 1:
            return meshes
        else:
            return trimesh.util.concatenate(meshes)
    
    def export(self, filename: str, layer_height: float = 0.2, file_format: str = '3mf'):
        """
        Generate and export test print file.
        
        Args:
            filename: Output filename
            layer_height: Layer height for test print
            file_format: 'stl' or '3mf'
        """
        mesh = self.generate_test_mesh(layer_height=layer_height)
        
        # Add metadata
        mesh.metadata['title'] = 'Bed Mesh Test Print'
        mesh.metadata['modified_cells'] = len(self.modified_cells)
        mesh.metadata['layer_height'] = f'{layer_height}mm'
        
        # Export
        if not filename.endswith(f'.{file_format}'):
            filename = f'{filename}.{file_format}'
            
        mesh.export(filename, file_type=file_format)
        
        return filename


# Usage example
if __name__ == '__main__':
    # Sample configuration (replace with actual Klipper data)
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
    
    # Mark some cells as modified (e.g., user adjusted these)
    generator.mark_cell_modified(2, 3)  # Center cell
    generator.mark_cell_modified(3, 3)
    generator.mark_cell_modified(2, 4)
    
    # Generate and export
    output_file = generator.export('bed_test_print', layer_height=0.2, file_format='3mf')
    print(f"Generated: {output_file}")
```

---

## 7. Integration with Klipper/Moonraker

### Reading Mesh Data via Moonraker API

```
import requests
import json

class KlipperMeshReader:
    """Read bed mesh data from Klipper via Moonraker API."""
    
    def __init__(self, moonraker_url: str):
        self.base_url = moonraker_url.rstrip('/')
        
    def get_bed_mesh_data(self):
        """Fetch current bed mesh data."""
        url = f"{self.base_url}/printer/objects/query?bed_mesh"
        response = requests.get(url)
        data = response.json()
        
        bed_mesh = data['result']['status']['bed_mesh']
        
        return {
            'mesh_min': bed_mesh['mesh_min'],
            'mesh_max': bed_mesh['mesh_max'],
            'mesh_matrix': bed_mesh['mesh_matrix'],
            'profiles': bed_mesh.get('profiles', {}),
        }
    
    def get_mesh_config(self):
        """Fetch bed_mesh configuration."""
        url = f"{self.base_url}/printer/objects/query?configfile"
        response = requests.get(url)
        data = response.json()
        
        config = data['result']['status']['configfile']['settings']['bed_mesh']
        
        return {
            'mesh_min': tuple(config['mesh_min']),
            'mesh_max': tuple(config['mesh_max']),
            'probe_count': tuple(config['probe_count']),
            'mesh_pps': tuple(config.get('mesh_pps', (2, 2))),
            'algorithm': config.get('algorithm', 'lagrange'),
        }


# Usage
reader = KlipperMeshReader('http://192.168.1.100')
config = reader.get_mesh_config()
data = reader.get_bed_mesh_data()

# Create generator with live data
generator = BedMeshTestGenerator(config, {'points': data['mesh_matrix']})
```

---

## 8. Advanced Features

### Generate Grid Overlay Visualization

```
def generate_full_grid_visual(generator, test_height=0.4):
    """Generate visual showing all grid cells (not just modified ones)."""
    meshes = []
    
    rows, cols = generator.z_values.shape
    
    for row in range(rows):
        for col in range(cols):
            center_x = generator.grid_x[row, col]
            center_y = generator.grid_y[row, col]
            
            # Smaller squares for visualization
            cell_size = min(generator.x_spacing, generator.y_spacing) - 3.0
            
            box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])
            box.apply_translation([center_x, center_y, test_height / 2])
            
            meshes.append(box)
    
    return trimesh.util.concatenate(meshes)
```

### Add Labels to Test Squares

```
def add_cell_labels_to_mesh(mesh, modified_cells):
    """Add text labels to identify which cell each square represents."""
    # This would require a text rendering library like:
    # - trimesh.path.text (for 2D text)
    # - PIL for rasterizing text
    # - Or export cell info as metadata
    
    mesh.metadata['cells'] = {
        f'square_{i}': {'row': row, 'col': col}
        for i, (row, col) in enumerate(modified_cells)
    }
    
    return mesh
```

---

## 9. Testing and Validation

### Validate Generated Mesh

```
def validate_mesh(mesh: trimesh.Trimesh) -> bool:
    """Validate that generated mesh is watertight and printable."""
    
    checks = {
        'is_watertight': mesh.is_watertight,
        'is_volume': mesh.is_volume,
        'has_faces': len(mesh.faces) > 0,
        'has_vertices': len(mesh.vertices) > 0,
    }
    
    print("Mesh Validation:")
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}: {result}")
    
    return all(checks.values())


# Usage
mesh = generator.generate_test_mesh()
if validate_mesh(mesh):
    generator.export('test_print.3mf')
else:
    print("Error: Generated mesh failed validation")
```

---

## 10. Summary Checklist

### Data Collection
- [ ] Extract `mesh_min`, `mesh_max`, `probe_count` from Klipper config
- [ ] Get current mesh Z-values (from saved profile or API)
- [ ] Calculate grid coordinates and spacing
- [ ] Track which cells user has modified

### Mesh Generation
- [ ] Set layer height and number of layers (typically 0.2mm × 2 = 0.4mm total)
- [ ] Calculate test square dimensions (cell size minus padding)
- [ ] Generate box primitive for each modified cell
- [ ] Position boxes at correct XY coordinates
- [ ] Ensure Z=0 is at bed surface, height extends upward

### Export
- [ ] Combine all test squares into single mesh
- [ ] Validate mesh is watertight
- [ ] Add metadata (cell info, layer height, etc.)
- [ ] Export to 3MF (preferred) or STL
- [ ] Verify file can be opened in slicer

### User Workflow
1. User loads current bed mesh from Klipper
2. User adjusts Z-values for specific grid cells
3. Software generates test print file
4. User opens file in slicer (OrcaSlicer, PrusaSlicer, etc.)
5. User sets print parameters (speed, temp, etc.)
6. Slicer generates G-code
7. User prints test squares
8. User measures results and further refines mesh if needed

---

## Dependencies

```
# Install required packages
pip install trimesh numpy requests

# Optional dependencies for advanced features
pip install networkx  # For mesh processing
pip install rtree     # For spatial queries
pip install shapely   # For 2D geometry operations
```

---

## References

- Klipper Bed Mesh Documentation: https://www.klipper3d.org/Bed_Mesh.html
- Trimesh Documentation: https://trimesh.org/
- 3MF Specification: https://3mf.io/specification/
- Moonraker API: https://moonraker.readthedocs.io/

---

## Notes for Claude/Codex Implementation

- **Priority**: Focus on 3MF export over STL (better format)
- **Validation**: Always validate mesh before export
- **Error Handling**: Check for empty modified_cells list
- **Coordinate System**: Klipper uses standard Cartesian (X right, Y forward, Z up)
- **Testing**: Test with various grid sizes (5x5, 7x7, 9x9, 10x10)
- **Performance**: For large meshes (>100 cells), consider batching or progress indicators
- **User Experience**: Display cell coordinates and Z-values in UI
- **Safety**: Validate that test squares don't exceed bed boundaries
```

Sources
[1] How to create a 3D mesh from a heightmap represented as a float ... https://stackoverflow.com/questions/67028493/how-to-create-a-3d-mesh-from-a-heightmap-represented-as-a-float-array
[2] Model file formats | DataMesh https://datamesh.com/support/user-manual/datamesh-importer/previous-versions-importer/version-updated-july-2024-importer/model-file-formats-2/
[3] Bed Level Calibration Square Grid by wsreith - Printables.com https://www.printables.com/model/69956-bed-level-calibration-square-grid
[4] 3D Manufacturing Format (3MF) - The Library of Congress https://www.loc.gov/preservation/digital/formats/fdd/fdd000557.shtml
[5] Generating 3D meshes from non-rectangular height maps - Reddit https://www.reddit.com/r/GraphicsProgramming/comments/oe2mub/generating_3d_meshes_from_nonrectangular_height/
[6] How to Achieve Perfect 3D Printer Bed Leveling? - eufymake US https://www.eufymake.com/blogs/maintenance-guides/how-to-level-a-3d-printer-bed
[7] The Difference Explained (And Why 3MF Is the New Standard) https://www.snapmaker.com/blog/3mf-vs-stl/
