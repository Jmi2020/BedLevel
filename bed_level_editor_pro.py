#!/usr/bin/env python3
"""
Enhanced Bed Level Editor for Elegoo OrangeStorm Giga - UX/UI Optimized
Beautiful, intuitive interface for precise bed mesh editing
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, FancyBboxPatch
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import numpy as np
from scipy import interpolate
import re
import os
import json
from datetime import datetime

class MeshModificationTracker:
    """
    Tracks modifications to mesh cells with history support
    Supports marking changes as "working" and maintains modification history
    """
    def __init__(self, original_mesh):
        """
        Initialize tracker with original mesh data

        Args:
            original_mesh: numpy array of original mesh values
        """
        self.original_mesh = original_mesh.copy()
        self.modification_history = {}  # {(y, x): [{'value': float, 'timestamp': str, 'working': bool}]}
        self.working_cells = set()  # Set of (y, x) tuples marked as working

    def get_modified_cells(self, current_mesh, include_working=True):
        """
        Get list of cells that differ from original

        Args:
            current_mesh: Current mesh data
            include_working: If False, exclude cells marked as working

        Returns:
            List of (y, x) tuples of modified cells
        """
        modified = []
        for y in range(current_mesh.shape[0]):
            for x in range(current_mesh.shape[1]):
                if not np.isclose(current_mesh[y, x], self.original_mesh[y, x], atol=1e-6):
                    if include_working or (y, x) not in self.working_cells:
                        modified.append((y, x))
        return modified

    def record_modification(self, y, x, old_value, new_value):
        """
        Record a modification to the history

        Args:
            y: Y index
            x: X index
            old_value: Previous value
            new_value: New value
        """
        key = (y, x)
        if key not in self.modification_history:
            self.modification_history[key] = []

        self.modification_history[key].append({
            'old_value': float(old_value),
            'new_value': float(new_value),
            'timestamp': datetime.now().isoformat(),
            'working': False
        })

    def mark_as_working(self, cells):
        """
        Mark cells as working (tested and approved)

        Args:
            cells: List of (y, x) tuples
        """
        for cell in cells:
            self.working_cells.add(cell)
            # Update history to mark as working
            if cell in self.modification_history:
                if self.modification_history[cell]:
                    self.modification_history[cell][-1]['working'] = True

    def unmark_as_working(self, cells):
        """
        Remove working status from cells

        Args:
            cells: List of (y, x) tuples
        """
        for cell in cells:
            self.working_cells.discard(cell)
            if cell in self.modification_history:
                if self.modification_history[cell]:
                    self.modification_history[cell][-1]['working'] = False

    def get_working_cells(self):
        """Get list of cells marked as working"""
        return list(self.working_cells)

    def get_untested_cells(self, current_mesh):
        """Get modified cells that haven't been marked as working"""
        all_modified = self.get_modified_cells(current_mesh, include_working=True)
        return [cell for cell in all_modified if cell not in self.working_cells]

    def get_cell_history(self, y, x):
        """
        Get modification history for a specific cell

        Returns:
            List of modification records or empty list
        """
        return self.modification_history.get((y, x), [])

    def reset_cell_to_original(self, y, x, current_mesh):
        """
        Reset a cell to its original value

        Args:
            y: Y index
            x: X index
            current_mesh: Current mesh to modify

        Returns:
            Original value
        """
        original_value = self.original_mesh[y, x]
        current_mesh[y, x] = original_value

        # Record the reset in history
        if (y, x) in self.modification_history:
            self.record_modification(y, x, current_mesh[y, x], original_value)

        # Remove from working cells
        self.working_cells.discard((y, x))

        return original_value

    def clear_history(self):
        """Clear all modification history and working status"""
        self.modification_history.clear()
        self.working_cells.clear()

    def update_original(self, new_original_mesh):
        """
        Update the original mesh (useful after saving)

        Args:
            new_original_mesh: New baseline mesh
        """
        self.original_mesh = new_original_mesh.copy()
        self.clear_history()

    def get_statistics(self, current_mesh):
        """
        Get modification statistics

        Returns:
            Dictionary with stats
        """
        all_modified = self.get_modified_cells(current_mesh, include_working=True)
        untested = self.get_untested_cells(current_mesh)
        working = self.get_working_cells()

        return {
            'total_modified': len(all_modified),
            'working': len(working),
            'untested': len(untested),
            'cells': all_modified
        }

class BedMeshTestGenerator:
    """
    Generates test print 3D models for modified mesh cells
    Creates 2-layer (0.4mm) test squares positioned at mesh cell locations
    """
    def __init__(self, mesh_min, mesh_max, x_count, y_count):
        """
        Initialize test generator with mesh parameters

        Args:
            mesh_min: Tuple (x_min, y_min) in mm
            mesh_max: Tuple (x_max, y_max) in mm
            x_count: Number of X mesh points
            y_count: Number of Y mesh points
        """
        self.mesh_min = mesh_min
        self.mesh_max = mesh_max
        self.x_count = x_count
        self.y_count = y_count

        # Calculate spacing between mesh points
        self.x_spacing = (mesh_max[0] - mesh_min[0]) / (x_count - 1) if x_count > 1 else 0
        self.y_spacing = (mesh_max[1] - mesh_min[1]) / (y_count - 1) if y_count > 1 else 0

    def get_cell_center(self, x_index, y_index):
        """
        Get the physical XY coordinates of a mesh cell center

        Args:
            x_index: X grid index (0 to x_count-1)
            y_index: Y grid index (0 to y_count-1)

        Returns:
            Tuple (x_mm, y_mm) in absolute bed coordinates
        """
        x_mm = self.mesh_min[0] + (x_index * self.x_spacing)
        y_mm = self.mesh_min[1] + (y_index * self.y_spacing)
        return (x_mm, y_mm)

    def create_test_square(self, center_x, center_y, test_height=0.4, padding=2.0):
        """
        Create a test square mesh at the specified position

        Args:
            center_x: X coordinate in mm
            center_y: Y coordinate in mm
            test_height: Height in mm (default 0.4mm = 2 layers @ 0.2mm)
            padding: Padding around square in mm (default 2mm)

        Returns:
            trimesh.Trimesh object
        """
        import trimesh

        # Calculate square size (cell size minus padding)
        cell_size = min(self.x_spacing, self.y_spacing) - padding
        if cell_size <= 0:
            cell_size = 10.0  # Fallback minimum size

        # Create box centered at origin
        box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])

        # Translate to position (Z at test_height/2 to sit on bed)
        translation = [center_x, center_y, test_height / 2]
        box.apply_translation(translation)

        return box

    def generate_test_print(self, cells, test_height=0.4, padding=2.0):
        """
        Generate a single test print mesh for multiple cells

        Args:
            cells: List of (y, x) tuples representing grid indices
            test_height: Height of test squares in mm
            padding: Padding around each square in mm

        Returns:
            trimesh.Trimesh object containing all test squares
        """
        import trimesh

        meshes = []
        for (y_idx, x_idx) in cells:
            center_x, center_y = self.get_cell_center(x_idx, y_idx)
            square = self.create_test_square(center_x, center_y, test_height, padding)
            meshes.append(square)

        # Combine all meshes
        if len(meshes) == 1:
            return meshes[0]
        else:
            return trimesh.util.concatenate(meshes)

    def export_3mf(self, mesh, filepath, print_name="BedLevel_Test"):
        """
        Export mesh to 3MF format

        Args:
            mesh: trimesh.Trimesh object
            filepath: Output file path
            print_name: Name for the print model

        Returns:
            True if successful, False otherwise
        """
        try:
            import trimesh

            # 3MF export with metadata
            mesh.export(filepath, file_type='3mf')
            return True
        except Exception as e:
            print(f"3MF export error: {e}")
            return False

    def export_stl(self, mesh, filepath):
        """
        Export mesh to STL format (binary)

        Args:
            mesh: trimesh.Trimesh object
            filepath: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # STL binary export (smaller file size)
            mesh.export(filepath, file_type='stl')
            return True
        except Exception as e:
            print(f"STL export error: {e}")
            return False

    def get_cell_info(self, cells):
        """
        Get descriptive information about cells

        Args:
            cells: List of (y, x) tuples

        Returns:
            List of dictionaries with cell info
        """
        info = []
        for (y_idx, x_idx) in cells:
            center_x, center_y = self.get_cell_center(x_idx, y_idx)
            info.append({
                'grid': f"[{x_idx}, {y_idx}]",
                'position': f"({center_x:.1f}, {center_y:.1f})",
                'y_idx': y_idx,
                'x_idx': x_idx
            })
        return info

    def generate_test_squares_scene(self, cells, test_height=0.4, padding=2.0):
        """
        Generate a trimesh Scene with separate test squares at correct positions.
        This preserves individual object positions for Elegoo Slicer.

        Args:
            cells: List of (y, x) tuples representing grid indices
            test_height: Height of test squares in mm
            padding: Padding around each square in mm

        Returns:
            trimesh.Scene with positioned test squares
        """
        import trimesh
        import numpy as np

        if not cells:
            raise ValueError("No cells provided for test print generation")

        scene = trimesh.Scene()

        # Calculate square size
        cell_size = min(self.x_spacing, self.y_spacing) - padding
        if cell_size < 5.0:
            print(f"Warning: Cell size {cell_size:.1f}mm is small. Consider reducing padding.")
            cell_size = max(cell_size, 5.0)

        for (y_idx, x_idx) in sorted(cells):
            # Get center position for this cell
            center_x, center_y = self.get_cell_center(x_idx, y_idx)

            # Create box at ORIGIN first (important for transforms)
            box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])

            # Create 4x4 transformation matrix
            # This tells Elegoo Slicer exactly where to place the object
            transform = np.eye(4)
            transform[0, 3] = center_x  # X translation
            transform[1, 3] = center_y  # Y translation
            transform[2, 3] = test_height / 2  # Z translation (half height so base at Z=0)

            # Create unique node name for this test square
            node_name = f"mesh_test_r{y_idx:02d}_c{x_idx:02d}"

            # Add metadata to the mesh itself
            box.metadata['cell_row'] = y_idx
            box.metadata['cell_col'] = x_idx
            box.metadata['position_x_mm'] = float(center_x)
            box.metadata['position_y_mm'] = float(center_y)
            box.metadata['cell_size_mm'] = float(cell_size)
            box.metadata['grid_index'] = f"[{x_idx}, {y_idx}]"

            # Add to scene with transform
            scene.add_geometry(
                box,
                node_name=node_name,
                geom_name=node_name,
                transform=transform
            )

        # Add scene-level metadata
        scene.metadata['title'] = 'Klipper Bed Mesh Test Print'
        scene.metadata['generator'] = 'BedLevelEditorPro'
        scene.metadata['num_test_squares'] = len(cells)
        scene.metadata['mesh_min'] = list(self.mesh_min)
        scene.metadata['mesh_max'] = list(self.mesh_max)
        scene.metadata['test_height_mm'] = float(test_height)
        scene.metadata['square_size_mm'] = float(cell_size)

        return scene

    def calculate_object_center(self, cells):
        """
        Calculate the center point of the combined test square object.
        This is where Elegoo Slicer's move tool anchors.

        Args:
            cells: List of (y, x) tuples

        Returns:
            Tuple (center_x, center_y) in mm
        """
        if not cells:
            return (0, 0)

        x_coords = []
        y_coords = []

        for (y_idx, x_idx) in cells:
            center_x, center_y = self.get_cell_center(x_idx, y_idx)
            x_coords.append(center_x)
            y_coords.append(center_y)

        # Average of all cell centers = center of combined object
        avg_x = sum(x_coords) / len(x_coords)
        avg_y = sum(y_coords) / len(y_coords)

        return (round(avg_x, 2), round(avg_y, 2))

    def export_scene_3mf(self, cells, filepath, test_height=0.4, padding=2.0):
        """
        Export 3MF with correct build transforms for Elegoo Slicer position preservation.

        Args:
            cells: List of (y, x) tuples
            filepath: Output file path
            test_height: Height of test squares in mm
            padding: Padding around each square in mm

        Returns:
            Tuple (success: bool, position_guide_path: str or None, center_coord: tuple or None)
        """
        try:
            import trimesh
            import zipfile
            from datetime import datetime
            import xml.etree.ElementTree as ET

            # Ensure .3mf extension
            if not filepath.endswith('.3mf'):
                filepath = f'{filepath}.3mf'

            # Calculate square size
            cell_size = min(self.x_spacing, self.y_spacing) - padding
            if cell_size < 5.0:
                cell_size = max(cell_size, 5.0)

            # Create temporary directory for 3MF contents
            import tempfile
            import shutil
            temp_dir = tempfile.mkdtemp()

            try:
                # Create directory structure
                objects_dir = os.path.join(temp_dir, '3D', 'Objects')
                os.makedirs(objects_dir, exist_ok=True)

                # XML namespace
                ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
                ET.register_namespace('', ns)

                # Create root model element for main file
                root = ET.Element('{%s}model' % ns)
                root.set('unit', 'millimeter')
                root.set('xml:lang', 'en-US')

                # Add metadata
                metadata_items = [
                    ('Application', 'BedLevelEditorPro'),
                    ('CreationDate', datetime.now().strftime('%Y-%m-%d')),
                    ('Title', 'Bed Mesh Test Print')
                ]
                for name, value in metadata_items:
                    meta = ET.SubElement(root, '{%s}metadata' % ns)
                    meta.set('name', name)
                    meta.text = value

                # Create resources section
                resources = ET.SubElement(root, '{%s}resources' % ns)

                # Create build section
                build = ET.SubElement(root, '{%s}build' % ns)

                # Generate each test square
                mesh_object_id = 1  # ID for mesh objects in separate files
                wrapper_object_id = 2  # ID for wrapper objects in main file (even numbers)

                for idx, (y_idx, x_idx) in enumerate(sorted(cells), 1):
                    # Get position for this cell
                    center_x, center_y = self.get_cell_center(x_idx, y_idx)

                    # Create test square mesh at origin
                    box = trimesh.creation.box(extents=[cell_size, cell_size, test_height])

                    # Create individual object file
                    mesh_filename = f'mesh_test_r{y_idx:02d}_c{x_idx:02d}_{idx}.model'
                    mesh_path = os.path.join(objects_dir, mesh_filename)

                    # Build object file XML
                    obj_root = ET.Element('{%s}model' % ns)
                    obj_root.set('unit', 'millimeter')
                    obj_root.set('xml:lang', 'en-US')

                    obj_resources = ET.SubElement(obj_root, '{%s}resources' % ns)
                    obj_object = ET.SubElement(obj_resources, '{%s}object' % ns)
                    obj_object.set('id', str(mesh_object_id))
                    obj_object.set('type', 'model')

                    # Add mesh geometry
                    mesh = ET.SubElement(obj_object, '{%s}mesh' % ns)
                    vertices = ET.SubElement(mesh, '{%s}vertices' % ns)
                    triangles = ET.SubElement(mesh, '{%s}triangles' % ns)

                    # Add vertices
                    for v in box.vertices:
                        vertex = ET.SubElement(vertices, '{%s}vertex' % ns)
                        vertex.set('x', f'{v[0]:.6f}')
                        vertex.set('y', f'{v[1]:.6f}')
                        vertex.set('z', f'{v[2]:.6f}')

                    # Add triangles
                    for face in box.faces:
                        triangle = ET.SubElement(triangles, '{%s}triangle' % ns)
                        triangle.set('v1', str(face[0]))
                        triangle.set('v2', str(face[1]))
                        triangle.set('v3', str(face[2]))

                    # Add empty build section to object file
                    ET.SubElement(obj_root, '{%s}build' % ns)

                    # Write object file
                    obj_tree = ET.ElementTree(obj_root)
                    obj_tree.write(mesh_path, encoding='UTF-8', xml_declaration=True)

                    # Create wrapper object in main file that references the external mesh
                    wrapper_obj = ET.SubElement(resources, '{%s}object' % ns)
                    wrapper_obj.set('id', str(wrapper_object_id))
                    wrapper_obj.set('type', 'model')

                    # Add component that references the external file
                    components = ET.SubElement(wrapper_obj, '{%s}components' % ns)
                    component = ET.SubElement(components, '{%s}component' % ns)
                    component.set('objectid', str(mesh_object_id))
                    component.set('{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path',
                                f'/3D/Objects/{mesh_filename}')
                    component.set('transform', '1 0 0 0 1 0 0 0 1 0 0 0')  # Identity transform

                    # Add build item with position transform
                    transform = f'1 0 0 0 1 0 0 0 1 {center_x:.6f} {center_y:.6f} {test_height/2:.6f}'
                    item = ET.SubElement(build, '{%s}item' % ns)
                    item.set('objectid', str(wrapper_object_id))
                    item.set('transform', transform)

                    wrapper_object_id += 2  # Increment by 2 to keep even numbers

                # Write main 3dmodel.model file
                tree = ET.ElementTree(root)
                model_path = os.path.join(temp_dir, '3D', '3dmodel.model')
                tree.write(model_path, encoding='UTF-8', xml_declaration=True)

                # Create [Content_Types].xml
                content_types_path = os.path.join(temp_dir, '[Content_Types].xml')
                with open(content_types_path, 'w') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n')
                    f.write('  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n')
                    f.write('  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n')
                    f.write('</Types>\n')

                # Create _rels/.rels
                rels_dir = os.path.join(temp_dir, '_rels')
                os.makedirs(rels_dir, exist_ok=True)
                rels_path = os.path.join(rels_dir, '.rels')
                with open(rels_path, 'w') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n')
                    f.write('  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n')
                    f.write('</Relationships>\n')

                # Create ZIP archive (3MF is a ZIP file)
                with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            arc_name = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arc_name)

            finally:
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)

            # Calculate center coordinate for move tool
            center_coord = self.calculate_object_center(cells)

            # Export position guide JSON
            guide_path = filepath.replace('.3mf', '_positions.json')
            self.export_position_guide(cells, guide_path, test_height, center_coord)

            return True, guide_path, center_coord

        except Exception as e:
            print(f"3MF export error: {e}")
            import traceback
            traceback.print_exc()
            return False, None, None

    def export_position_guide(self, cells, filepath, test_height=0.4, center_coord=None):
        """
        Export JSON file with position information for verification.

        Args:
            cells: List of (y, x) tuples
            filepath: Output JSON file path
            test_height: Height of test squares in mm
            center_coord: Tuple (x, y) center coordinate for move tool
        """
        import json

        cell_info = []
        for (y_idx, x_idx) in sorted(cells):
            center_x, center_y = self.get_cell_center(x_idx, y_idx)
            cell_info.append({
                'grid_index': [x_idx, y_idx],
                'position_mm': [round(center_x, 2), round(center_y, 2)],
                'row': y_idx,
                'col': x_idx
            })

        guide_data = {
            'move_tool_coordinate': {
                'x': center_coord[0] if center_coord else 0,
                'y': center_coord[1] if center_coord else 0,
                'z': 0,
                'instruction': 'Enter these coordinates in Elegoo Slicer Move tool to position the test squares correctly'
            },
            'mesh_config': {
                'mesh_min': list(self.mesh_min),
                'mesh_max': list(self.mesh_max),
                'x_count': self.x_count,
                'y_count': self.y_count,
                'x_spacing': round(self.x_spacing, 2),
                'y_spacing': round(self.y_spacing, 2)
            },
            'test_print': {
                'num_squares': len(cells),
                'test_height_mm': test_height,
                'square_size_mm': round(min(self.x_spacing, self.y_spacing) - 2.0, 2)
            },
            'modified_cells': cell_info,
            'instructions': {
                'elegoo_slicer': [
                    '1. Open Elegoo Slicer',
                    '2. File → Open Project',
                    '3. Select the .3mf file (object will be centered)',
                    '4. Click on the imported object to select it',
                    '5. Click the Move tool in the left toolbar',
                    '6. In the position dialog, enter these coordinates:',
                    f'   X: {center_coord[0] if center_coord else 0}',
                    f'   Y: {center_coord[1] if center_coord else 0}',
                    '   Z: 0',
                    '7. Press Enter to apply the position',
                    '8. Verify test squares are now at mesh grid locations',
                    '9. Slice and generate G-code',
                    '10. Print and verify first layer adhesion'
                ],
                'troubleshooting': {
                    'object_centered': 'Use Move tool and enter the coordinates above',
                    'objects_off_bed': 'Verify Klipper mesh_min/mesh_max match printer bed size',
                    'wrong_position': 'Double-check you entered X and Y values correctly',
                    'z_not_zero': 'Z should be 0 so squares sit on the bed'
                }
            }
        }

        with open(filepath, 'w') as f:
            json.dump(guide_data, f, indent=2)

    def create_reference_frame(self, test_height=0.4):
        """
        Create a thin frame around the mesh boundaries.
        Helps visualize the bed coordinate system in slicer.

        Args:
            test_height: Height of frame in mm

        Returns:
            trimesh.Trimesh object
        """
        import trimesh

        frame_width = 2.0  # Width of frame lines
        frame_meshes = []

        # Bottom edge
        bottom = trimesh.creation.box(
            extents=[self.mesh_max[0] - self.mesh_min[0], frame_width, test_height]
        )
        bottom.apply_translation([
            (self.mesh_min[0] + self.mesh_max[0]) / 2,
            self.mesh_min[1],
            test_height / 2
        ])
        frame_meshes.append(bottom)

        # Top edge
        top = trimesh.creation.box(
            extents=[self.mesh_max[0] - self.mesh_min[0], frame_width, test_height]
        )
        top.apply_translation([
            (self.mesh_min[0] + self.mesh_max[0]) / 2,
            self.mesh_max[1],
            test_height / 2
        ])
        frame_meshes.append(top)

        # Left edge
        left = trimesh.creation.box(
            extents=[frame_width, self.mesh_max[1] - self.mesh_min[1], test_height]
        )
        left.apply_translation([
            self.mesh_min[0],
            (self.mesh_min[1] + self.mesh_max[1]) / 2,
            test_height / 2
        ])
        frame_meshes.append(left)

        # Right edge
        right = trimesh.creation.box(
            extents=[frame_width, self.mesh_max[1] - self.mesh_min[1], test_height]
        )
        right.apply_translation([
            self.mesh_max[0],
            (self.mesh_min[1] + self.mesh_max[1]) / 2,
            test_height / 2
        ])
        frame_meshes.append(right)

        return trimesh.util.concatenate(frame_meshes)

    def export_with_reference_frame(self, cells, filepath, test_height=0.4, padding=2.0, add_frame=True):
        """
        Export STL with optional reference frame showing bed boundaries.
        Use this if 3MF positioning doesn't work in Elegoo Slicer.

        Args:
            cells: List of (y, x) tuples
            filepath: Output file path
            test_height: Height in mm
            padding: Padding around squares in mm
            add_frame: If True, adds frame around bed edges

        Returns:
            True if successful, False otherwise
        """
        try:
            import trimesh

            meshes = []

            # Generate test squares
            for (y_idx, x_idx) in cells:
                center_x, center_y = self.get_cell_center(x_idx, y_idx)
                square = self.create_test_square(center_x, center_y, test_height, padding)
                meshes.append(square)

            # Add reference frame if requested
            if add_frame:
                frame = self.create_reference_frame(test_height)
                meshes.append(frame)

            # Combine all meshes
            if len(meshes) == 1:
                combined = meshes[0]
            else:
                combined = trimesh.util.concatenate(meshes)

            # Ensure .stl extension
            if not filepath.endswith('.stl'):
                filepath = f'{filepath}.stl'

            # Export to STL
            combined.export(filepath, file_type='stl')

            return True

        except Exception as e:
            print(f"STL export with frame error: {e}")
            return False

class ModernButton(tk.Frame):
    """Custom button using Frame - complete control, no tkinter Button issues"""
    def __init__(self, parent, text="", command=None, bg='#4a90e2', fg='white',
                 font=None, width=None, height=None, cursor='hand2', **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, **kwargs)

        # Store properties
        self.default_bg = bg
        self.default_fg = fg
        self.hover_bg = self.lighten_color(bg)
        self.command = command
        self.text = text

        # Create label inside frame
        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            cursor=cursor,
            highlightthickness=0,
            borderwidth=0
        )

        # Apply width/height if specified
        if width:
            self.label.config(width=width)
        if height:
            self.label.config(height=height)

        self.label.pack(fill=tk.BOTH, expand=True, padx=kwargs.get('padx', 10),
                       pady=kwargs.get('pady', 5), ipady=kwargs.get('ipady', 0))

        # Bind events to both frame and label
        for widget in (self, self.label):
            widget.bind('<Enter>', self._on_enter)
            widget.bind('<Leave>', self._on_leave)
            widget.bind('<Button-1>', self._on_click)

    def lighten_color(self, hex_color):
        """Lighten a hex color by 20%"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _on_enter(self, event):
        """Handle mouse enter"""
        self.config(bg=self.hover_bg)
        self.label.config(bg=self.hover_bg)

    def _on_leave(self, event):
        """Handle mouse leave"""
        self.config(bg=self.default_bg)
        self.label.config(bg=self.default_bg)

    def _on_click(self, event):
        """Handle click"""
        if self.command:
            self.command()

    def config(self, **kwargs):
        """Override config to handle both frame and label"""
        # Handle bg specially
        if 'bg' in kwargs:
            super().config(bg=kwargs['bg'])
            if hasattr(self, 'label'):
                self.label.config(bg=kwargs['bg'])
        # Pass other configs to parent
        super().config(**{k: v for k, v in kwargs.items() if k != 'bg'})

    def pack(self, **kwargs):
        """Override pack to handle properly"""
        # Remove padx/pady/ipady if present (we handle them internally)
        kwargs.pop('padx', None)
        kwargs.pop('pady', None)
        kwargs.pop('ipady', None)
        super().pack(**kwargs)

class BedLevelEditorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Level Editor Pro - Elegoo OrangeStorm Giga")
        self.root.geometry("1680x980")

        # Make window resizable with minimum size constraints
        self.root.resizable(True, True)
        self.root.minsize(1200, 800)  # Minimum size to prevent UI breaking

        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "printer.cfg")
        self.mesh_data = None
        self.original_mesh_data = None
        self.x_count = 10
        self.y_count = 10
        self.selected_point = None
        self.selected_region = []
        self.mesh_min = (16, 10)
        self.mesh_max = (786, 767)
        self.mesh_pps = (4, 4)

        # UI state
        self.region_mode = False
        self.region_start = None
        self.is_modified = False

        # Modification tracking
        self.modification_tracker = None
        self.show_modifications = True  # Show/hide modification indicators

        # Undo stack
        self.undo_stack = []  # List of (mesh_snapshot, description) tuples
        self.max_undo_steps = 50  # Maximum undo history

        # Test print generation
        self.test_generator = BedMeshTestGenerator(self.mesh_min, self.mesh_max, self.x_count, self.y_count)

        # Color scheme - Modern, professional palette
        self.colors = {
            'bg_dark': '#1e1e2e',
            'bg_medium': '#2a2a3e',
            'bg_light': '#363654',
            'fg_primary': '#ffffff',
            'fg_secondary': '#b4b4c8',
            'accent_blue': '#4a90e2',
            'accent_green': '#27ae60',
            'accent_orange': '#f39c12',
            'accent_red': '#e74c3c',
            'accent_purple': '#9b59b6',
            'accent_teal': '#16a085',
            'region_highlight': '#ff6b6b',
            'selection_border': '#4af2a1',
        }

        # Font configuration
        self.fonts = {
            'title': ('Segoe UI', 11, 'bold'),
            'heading': ('Segoe UI', 10, 'bold'),
            'normal': ('Segoe UI', 9),
            'small': ('Segoe UI', 8),
            'mono': ('Consolas', 9),
        }

        self.setup_ui()
        self.load_mesh_data()

        # Keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self.save_mesh_data())
        self.root.bind('<Control-z>', lambda e: self.undo_last_change())
        self.root.bind('<Control-Shift-Z>', lambda e: self.reset_mesh_data())  # Changed to Ctrl+Shift+Z for full reset
        self.root.bind('<Control-o>', lambda e: self.browse_file())
        self.root.bind('<Escape>', lambda e: self.clear_region())

    def setup_ui(self):
        """Setup modern, intuitive UI"""
        self.root.configure(bg=self.colors['bg_dark'])

        # Main container with padding
        main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # ========== TOP TOOLBAR ==========
        self.create_top_toolbar(main_container)

        # ========== CONTENT AREA WITH RESIZABLE PANES ==========
        # Create a PanedWindow for resizable divider
        paned_window = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Left pane: Visualization
        left_frame = tk.Frame(paned_window, bg=self.colors['bg_dark'])
        paned_window.add(left_frame, weight=3)  # Takes 75% by default

        self.create_visualization_panel(left_frame)

        # Right pane: Control Panel
        right_frame = tk.Frame(paned_window, bg=self.colors['bg_dark'])
        paned_window.add(right_frame, weight=1)  # Takes 25% by default

        self.create_control_panel(right_frame)

        # ========== STATUS BAR ==========
        self.create_status_bar(main_container)

    def create_top_toolbar(self, parent):
        """Create modern top toolbar"""
        toolbar = tk.Frame(parent, bg=self.colors['bg_medium'], relief=tk.FLAT, bd=0)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Left section - File info
        left_section = tk.Frame(toolbar, bg=self.colors['bg_medium'])
        left_section.pack(side=tk.LEFT, padx=15, pady=12)

        tk.Label(left_section, text="📁", font=self.fonts['title'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).pack(side=tk.LEFT, padx=(0, 8))

        self.file_label = tk.Label(left_section, text=os.path.basename(self.config_file),
                                   font=self.fonts['normal'], bg=self.colors['bg_medium'],
                                   fg=self.colors['accent_blue'])
        self.file_label.pack(side=tk.LEFT)

        # Center section - View buttons
        center_section = tk.Frame(toolbar, bg=self.colors['bg_medium'])
        center_section.pack(side=tk.LEFT, expand=True)

        view_buttons = [
            ("🔄 Reload", self.load_mesh_data, self.colors['accent_blue']),
            ("📊 3D View", self.show_3d_view, self.colors['accent_teal']),
            ("🔬 Interpolated", self.show_interpolated, self.colors['accent_purple']),
        ]

        for text, command, color in view_buttons:
            btn = ModernButton(center_section, text=text, command=command,
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=5)

        # Right section - Action buttons
        right_section = tk.Frame(toolbar, bg=self.colors['bg_medium'])
        right_section.pack(side=tk.RIGHT, padx=15, pady=8)

        action_buttons = [
            ("📂 Open", self.browse_file, self.colors['accent_blue']),
            ("💾 Save", self.save_mesh_data, self.colors['accent_green']),
            ("↩️ Reset", self.reset_mesh_data, self.colors['accent_orange']),
        ]

        for text, command, color in action_buttons:
            btn = ModernButton(right_section, text=text, command=command,
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, padx=18, pady=8, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=4)

    def create_visualization_panel(self, parent):
        """Create the main visualization area"""
        viz_container = tk.Frame(parent, bg=self.colors['bg_medium'], relief=tk.FLAT)
        viz_container.pack(fill=tk.BOTH, expand=True)

        # Header with mode indicator
        header = tk.Frame(viz_container, bg=self.colors['bg_medium'])
        header.pack(fill=tk.X, padx=15, pady=(12, 8))

        tk.Label(header, text="Bed Mesh Visualization", font=self.fonts['title'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).pack(side=tk.LEFT)

        self.mode_indicator = tk.Label(header, text="● POINT MODE", font=self.fonts['normal'],
                                       bg=self.colors['bg_medium'], fg=self.colors['accent_blue'])
        self.mode_indicator.pack(side=tk.RIGHT)

        # Matplotlib figure with fixed layout
        self.fig = Figure(figsize=(11, 9), facecolor=self.colors['bg_medium'])
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_container)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Mouse events
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # Store colorbar reference
        self.cbar = None
        self.cbar_ax = None

    def create_control_panel(self, parent):
        """Create modern control panel"""
        # Scrollable container
        canvas = tk.Canvas(parent, bg=self.colors['bg_dark'], highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_dark'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        # Bind mouse wheel to canvas and all child widgets
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows/Mac
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)  # Linux scroll up
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)  # Linux scroll down

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ===== SELECTION MODE =====
        mode_section = self.create_section(scrollable_frame, "🎯 Selection Mode")

        self.mode_var = tk.StringVar(value="single")

        mode_frame = tk.Frame(mode_section, bg=self.colors['bg_light'])
        mode_frame.pack(fill=tk.X, pady=5)

        single_btn = tk.Radiobutton(mode_frame, text="Point", variable=self.mode_var,
                                    value="single", command=self.change_selection_mode,
                                    bg=self.colors['bg_light'], fg=self.colors['fg_primary'],
                                    selectcolor=self.colors['accent_blue'], font=self.fonts['normal'],
                                    activebackground=self.colors['bg_light'], cursor='hand2')
        single_btn.pack(side=tk.LEFT, padx=10, pady=5)

        region_btn = tk.Radiobutton(mode_frame, text="Region (Drag)", variable=self.mode_var,
                                    value="region", command=self.change_selection_mode,
                                    bg=self.colors['bg_light'], fg=self.colors['fg_primary'],
                                    selectcolor=self.colors['region_highlight'], font=self.fonts['normal'],
                                    activebackground=self.colors['bg_light'], cursor='hand2')
        region_btn.pack(side=tk.LEFT, padx=10, pady=5)

        # ===== SELECTION INFO =====
        info_section = self.create_section(scrollable_frame, "📍 Selection Info")

        self.point_label = tk.Label(info_section, text="No selection", font=self.fonts['normal'],
                                    bg=self.colors['bg_light'], fg=self.colors['fg_secondary'])
        self.point_label.pack(pady=8)

        self.coord_label = tk.Label(info_section, text="Click on a point to begin",
                                    font=self.fonts['small'], bg=self.colors['bg_light'],
                                    fg=self.colors['accent_blue'])
        self.coord_label.pack(pady=(0, 8))

        # ===== VALUE ADJUSTMENT =====
        adjust_section = self.create_section(scrollable_frame, "⚙️ Adjust Value")

        # Value display (larger, prominent)
        value_frame = tk.Frame(adjust_section, bg=self.colors['bg_dark'], relief=tk.FLAT, bd=2)
        value_frame.pack(fill=tk.X, pady=10, padx=10)

        tk.Label(value_frame, text="Z-Offset (mm)", font=self.fonts['small'],
                bg=self.colors['bg_dark'], fg=self.colors['fg_secondary']).pack(pady=(8, 2))

        self.value_var = tk.StringVar(value="0.000")
        value_entry = tk.Entry(value_frame, textvariable=self.value_var,
                              font=('Consolas', 16, 'bold'), justify=tk.CENTER, width=12,
                              bg=self.colors['bg_medium'], fg=self.colors['accent_green'],
                              relief=tk.FLAT, insertbackground=self.colors['accent_green'])
        value_entry.pack(pady=(0, 4), ipady=8)
        value_entry.bind('<Return>', lambda e: self.update_selection_value())

        # Hint label for relative adjustments
        hint_label = tk.Label(value_frame, text="Tip: Use +0.01 or -0.02 for relative adjustments",
                             font=self.fonts['small'], bg=self.colors['bg_dark'],
                             fg=self.colors['fg_secondary'], wraplength=260)
        hint_label.pack(pady=(0, 8))

        # Quick adjust buttons (bigger, clearer)
        quick_frame = tk.Frame(adjust_section, bg=self.colors['bg_light'])
        quick_frame.pack(fill=tk.X, pady=10, padx=10)

        tk.Label(quick_frame, text="Quick Adjust", font=self.fonts['small'],
                bg=self.colors['bg_light'], fg=self.colors['fg_secondary']).pack(pady=(0, 8))

        btn_frame = tk.Frame(quick_frame, bg=self.colors['bg_light'])
        btn_frame.pack()

        adjustments = [
            ("--\n0.1", -0.1, self.colors['accent_red']),
            ("-\n0.01", -0.01, self.colors['accent_orange']),
            ("+\n0.01", 0.01, self.colors['accent_blue']),
            ("++\n0.1", 0.1, self.colors['accent_green']),
        ]

        for label, value, color in adjustments:
            btn = ModernButton(btn_frame, text=label, command=lambda v=value: self.quick_adjust(v),
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, width=6, height=2, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=3)

        # Slider (smoother, labeled)
        slider_frame = tk.Frame(adjust_section, bg=self.colors['bg_light'])
        slider_frame.pack(fill=tk.X, pady=10, padx=10)

        tk.Label(slider_frame, text="Fine Adjustment", font=self.fonts['small'],
                bg=self.colors['bg_light'], fg=self.colors['fg_secondary']).pack()

        self.slider_var = tk.DoubleVar(value=0)
        slider = tk.Scale(slider_frame, from_=-0.5, to=0.5, resolution=0.001,
                         orient=tk.HORIZONTAL, variable=self.slider_var,
                         command=self.on_slider_change, bg=self.colors['bg_light'],
                         fg=self.colors['fg_primary'], highlightthickness=0,
                         troughcolor=self.colors['bg_dark'], length=320,
                         sliderlength=30, font=self.fonts['small'])
        slider.pack(pady=8)

        # Update button (prominent)
        update_btn = ModernButton(adjust_section, text="✓ UPDATE SELECTION", command=self.update_selection_value,
                                 bg=self.colors['accent_green'], fg='white',
                                 font=self.fonts['heading'], relief=tk.FLAT, cursor='hand2')
        update_btn.pack(fill=tk.X, padx=10, pady=10, ipady=8)

        # ===== REGION TOOLS =====
        region_section = self.create_section(scrollable_frame, "🔧 Region Tools")

        # Quick offset buttons for region
        tk.Label(region_section, text="Quick Offset (Region)", font=self.fonts['small'],
                bg=self.colors['bg_light'], fg=self.colors['fg_secondary']).pack(pady=(10, 5))

        offset_frame = tk.Frame(region_section, bg=self.colors['bg_light'])
        offset_frame.pack(pady=(0, 10))

        offset_buttons = [
            ("-0.05", -0.05, self.colors['accent_red']),
            ("-0.01", -0.01, self.colors['accent_orange']),
            ("+0.01", 0.01, self.colors['accent_blue']),
            ("+0.05", 0.05, self.colors['accent_green']),
        ]

        for label, value, color in offset_buttons:
            btn = ModernButton(offset_frame, text=label, command=lambda v=value: self.apply_region_offset(v),
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, width=6, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=3)

        region_buttons = [
            ("📊 Average Region", self.average_region, self.colors['accent_orange']),
            ("✨ Smooth Region", self.smooth_region, self.colors['accent_purple']),
            ("🗑️ Clear Selection", self.clear_region, self.colors['bg_light']),
        ]

        for text, command, color in region_buttons:
            btn = ModernButton(region_section, text=text, command=command,
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, cursor='hand2')
            btn.pack(fill=tk.X, padx=10, pady=4, ipady=6)

        # ===== MODIFICATION TRACKING =====
        mod_section = self.create_section(scrollable_frame, "🎯 Modification Tracking")

        # Show/hide modifications checkbox
        self.show_mods_var = tk.BooleanVar(value=True)
        show_check = tk.Checkbutton(mod_section, text="Show modification indicators",
                                    variable=self.show_mods_var, command=self.toggle_modifications,
                                    bg=self.colors['bg_light'], fg=self.colors['fg_primary'],
                                    selectcolor=self.colors['accent_green'], font=self.fonts['normal'],
                                    activebackground=self.colors['bg_light'], cursor='hand2')
        show_check.pack(padx=10, pady=8, anchor=tk.W)

        # Legend
        legend_frame = tk.Frame(mod_section, bg=self.colors['bg_dark'], relief=tk.FLAT)
        legend_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(legend_frame, text="Legend:", font=self.fonts['small'],
                bg=self.colors['bg_dark'], fg=self.colors['fg_secondary']).pack(anchor=tk.W, padx=5, pady=2)

        tk.Label(legend_frame, text="🟧 Orange = Modified (untested)", font=self.fonts['small'],
                bg=self.colors['bg_dark'], fg=self.colors['accent_orange']).pack(anchor=tk.W, padx=5, pady=2)

        tk.Label(legend_frame, text="🟩 Green = Working (tested)", font=self.fonts['small'],
                bg=self.colors['bg_dark'], fg=self.colors['accent_green']).pack(anchor=tk.W, padx=5, pady=2)

        # Modification action buttons
        mod_buttons = [
            ("✓ Mark Selection as Working", self.mark_selection_as_working, self.colors['accent_green']),
            ("✗ Unmark Selection", self.unmark_selection_as_working, self.colors['accent_orange']),
            ("↺ Reset Selection to Original", self.reset_selection_to_original, self.colors['accent_red']),
        ]

        for text, command, color in mod_buttons:
            btn = ModernButton(mod_section, text=text, command=command,
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, cursor='hand2')
            btn.pack(fill=tk.X, padx=10, pady=4, ipady=6)

        # Test print generation button (prominent)
        tk.Frame(mod_section, height=10, bg=self.colors['bg_light']).pack()  # Spacer

        test_print_btn = ModernButton(mod_section, text="🖨️ GENERATE TEST PRINT",
                                     command=self.open_test_print_dialog,
                                     bg=self.colors['accent_blue'], fg='white',
                                     font=self.fonts['heading'], relief=tk.FLAT, cursor='hand2')
        test_print_btn.pack(fill=tk.X, padx=10, pady=8, ipady=10)

        # ===== STATISTICS =====
        stats_section = self.create_section(scrollable_frame, "📈 Mesh Statistics")

        self.stats_text = tk.Text(stats_section, height=9, bg=self.colors['bg_dark'],
                                 fg=self.colors['fg_primary'], font=self.fonts['mono'],
                                 relief=tk.FLAT, padx=10, pady=10, wrap=tk.NONE)
        self.stats_text.pack(padx=10, pady=10, fill=tk.BOTH)

        # ===== BATCH OPERATIONS =====
        batch_section = self.create_section(scrollable_frame, "⚡ Batch Operations")

        batch_buttons = [
            ("📏 Flatten All", self.flatten_mesh, self.colors['accent_orange']),
            ("↕️ Offset All", self.offset_all, self.colors['accent_purple']),
        ]

        for text, command, color in batch_buttons:
            btn = ModernButton(batch_section, text=text, command=command,
                             bg=color, fg='white', font=self.fonts['normal'],
                             relief=tk.FLAT, cursor='hand2')
            btn.pack(fill=tk.X, padx=10, pady=4, ipady=6)

        # Undo button (starts disabled/grayed)
        self.undo_btn = ModernButton(batch_section, text="↶ UNDO (Ctrl+Z)", command=self.undo_last_change,
                                     bg=self.colors['bg_light'], fg='white', font=self.fonts['heading'],
                                     relief=tk.FLAT, cursor='hand2')
        self.undo_btn.pack(fill=tk.X, padx=10, pady=(10, 4), ipady=8)

    def create_section(self, parent, title):
        """Create a styled section container"""
        section = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        section.pack(fill=tk.X, pady=(0, 12))

        # Section header
        header = tk.Frame(section, bg=self.colors['bg_medium'])
        header.pack(fill=tk.X)

        tk.Label(header, text=title, font=self.fonts['heading'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).pack(
                    side=tk.LEFT, padx=12, pady=8)

        # Section content area
        content = tk.Frame(section, bg=self.colors['bg_light'])
        content.pack(fill=tk.BOTH, expand=True)

        return content

    def create_status_bar(self, parent):
        """Create bottom status bar"""
        self.status_bar = tk.Frame(parent, bg=self.colors['bg_medium'], height=30)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

        self.status_label = tk.Label(self.status_bar, text="Ready",
                                     font=self.fonts['small'], bg=self.colors['bg_medium'],
                                     fg=self.colors['fg_secondary'])
        self.status_label.pack(side=tk.LEFT, padx=15, pady=6)

        # Shortcuts hint
        shortcuts = tk.Label(self.status_bar,
                            text="Shortcuts: Ctrl+S=Save | Ctrl+Z=Reset | Ctrl+O=Open | Esc=Clear",
                            font=self.fonts['small'], bg=self.colors['bg_medium'],
                            fg=self.colors['fg_secondary'])
        shortcuts.pack(side=tk.RIGHT, padx=15, pady=6)

    def update_status(self, message, color=None):
        """Update status bar message"""
        if color is None:
            color = self.colors['fg_secondary']
        self.status_label.config(text=message, fg=color)
        self.root.update_idletasks()

    def change_selection_mode(self):
        """Change between single point and region selection modes"""
        self.region_mode = (self.mode_var.get() == "region")
        self.clear_region()

        if self.region_mode:
            self.mode_indicator.config(text="● REGION MODE", fg=self.colors['region_highlight'])
            self.update_status("Region mode: Click and drag to select multiple points", self.colors['accent_blue'])
        else:
            self.mode_indicator.config(text="● POINT MODE", fg=self.colors['accent_blue'])
            self.update_status("Point mode: Click on individual points", self.colors['accent_blue'])

        self.point_label.config(text="No selection")
        self.coord_label.config(text="Make a selection to begin")

    def browse_file(self):
        """Browse for printer.cfg file"""
        filename = filedialog.askopenfilename(
            title="Select printer.cfg file",
            initialdir=os.path.dirname(self.config_file),
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = filename
            self.file_label.config(text=os.path.basename(self.config_file))
            self.load_mesh_data()

    def load_mesh_data(self):
        """Load mesh data from printer.cfg"""
        try:
            self.update_status("Loading mesh data...", self.colors['accent_blue'])

            if not os.path.exists(self.config_file):
                messagebox.showerror("Error", f"Config file not found: {self.config_file}")
                self.update_status("Error: File not found", self.colors['accent_red'])
                return

            with open(self.config_file, 'r') as f:
                content = f.read()

            # Find the bed_mesh section
            mesh_match = re.search(
                r'\[bed_mesh default\].*?points =\s*(.*?)(?=\n(?:#\*#\s*)?(?:x_count|mesh_x_pps|mesh_y_pps|algo|min_x|max_x|min_y|max_y)|$)',
                content,
                re.DOTALL
            )

            if not mesh_match:
                messagebox.showerror("Error", "Could not find bed_mesh default section")
                self.update_status("Error: No mesh data found", self.colors['accent_red'])
                return

            points_text = mesh_match.group(1)

            # Extract all points
            points = []
            for line in points_text.split('\n'):
                line = line.strip()
                if line.startswith('#*#') and ',' in line:
                    values = line.replace('#*#', '').strip().split(',')
                    row = [float(v.strip()) for v in values if v.strip()]
                    if row:
                        points.append(row)

            if not points:
                messagebox.showerror("Error", "No mesh points found")
                self.update_status("Error: No points found", self.colors['accent_red'])
                return

            self.mesh_data = np.array(points)
            self.original_mesh_data = self.mesh_data.copy()
            self.y_count, self.x_count = self.mesh_data.shape
            self.is_modified = False

            # Initialize modification tracker
            self.modification_tracker = MeshModificationTracker(self.original_mesh_data)

            # Extract mesh parameters
            x_count_match = re.search(r'#\*#\s*x_count\s*=\s*(\d+)', content)
            y_count_match = re.search(r'#\*#\s*y_count\s*=\s*(\d+)', content)
            mesh_x_pps_match = re.search(r'#\*#\s*mesh_x_pps\s*=\s*(\d+)', content)
            mesh_y_pps_match = re.search(r'#\*#\s*mesh_y_pps\s*=\s*(\d+)', content)

            if x_count_match:
                self.x_count = int(x_count_match.group(1))
            if y_count_match:
                self.y_count = int(y_count_match.group(1))
            if mesh_x_pps_match and mesh_y_pps_match:
                self.mesh_pps = (int(mesh_x_pps_match.group(1)), int(mesh_y_pps_match.group(1)))

            # Update test generator with current mesh parameters
            self.test_generator = BedMeshTestGenerator(self.mesh_min, self.mesh_max, self.x_count, self.y_count)

            self.update_plot()
            self.update_statistics()

            self.update_status(f"✓ Loaded {self.x_count}x{self.y_count} mesh ({self.x_count * self.y_count} points)",
                             self.colors['accent_green'])

            messagebox.showinfo("Success",
                              f"Loaded {self.x_count}x{self.y_count} mesh ({self.x_count * self.y_count} points)\n"
                              f"Interpolation: {self.mesh_pps[0]}x{self.mesh_pps[1]} pps")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mesh data: {str(e)}")
            self.update_status(f"Error: {str(e)}", self.colors['accent_red'])

    def save_mesh_data(self):
        """Save mesh data back to printer.cfg"""
        if self.mesh_data is None:
            messagebox.showerror("Error", "No mesh data to save")
            return

        try:
            self.update_status("Saving mesh data...", self.colors['accent_blue'])

            with open(self.config_file, 'r') as f:
                content = f.read()

            mesh_pattern = r'(\[bed_mesh default\].*?points =\s*).*?(?=#\*#\s*x_count)'

            points_str = ""
            for row in self.mesh_data:
                points_str += "#*# \t  "
                points_str += ", ".join([f"{val:.6f}" for val in row])
                points_str += "\n"

            new_content = re.sub(mesh_pattern, r'\1\n' + points_str, content, flags=re.DOTALL)

            backup_file = self.config_file + ".backup"
            with open(backup_file, 'w') as f:
                f.write(content)

            with open(self.config_file, 'w') as f:
                f.write(new_content)

            self.original_mesh_data = self.mesh_data.copy()
            self.is_modified = False

            self.update_status(f"✓ Saved successfully! Backup: {os.path.basename(backup_file)}",
                             self.colors['accent_green'])

            messagebox.showinfo("Success", f"Mesh data saved!\nBackup created: {backup_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save mesh data: {str(e)}")
            self.update_status(f"Error saving: {str(e)}", self.colors['accent_red'])

    def reset_mesh_data(self):
        """Reset mesh data to original values"""
        if self.original_mesh_data is None:
            return

        if messagebox.askyesno("Confirm Reset", "Reset all changes to original values?"):
            self.mesh_data = self.original_mesh_data.copy()
            self.clear_region()
            self.is_modified = False
            self.update_plot()
            self.update_statistics()
            self.update_status("Reset to original values", self.colors['accent_orange'])
            messagebox.showinfo("Reset", "Mesh data reset to original values")

    def generate_interpolated_mesh(self):
        """Generate interpolated mesh using bicubic interpolation"""
        if self.mesh_data is None:
            return None, None, None

        x_orig = np.linspace(0, self.x_count - 1, self.x_count)
        y_orig = np.linspace(0, self.y_count - 1, self.y_count)

        segments_x = self.x_count - 1
        segments_y = self.y_count - 1
        points_x = segments_x * self.mesh_pps[0] + 1
        points_y = segments_y * self.mesh_pps[1] + 1

        x_interp = np.linspace(0, self.x_count - 1, points_x)
        y_interp = np.linspace(0, self.y_count - 1, points_y)

        f = interpolate.RectBivariateSpline(y_orig, x_orig, self.mesh_data, kx=3, ky=3, s=0)
        z_interp = f(y_interp, x_interp)

        X_interp, Y_interp = np.meshgrid(x_interp, y_interp)

        return X_interp, Y_interp, z_interp

    def show_3d_view(self):
        """Show 3D visualization of mesh"""
        if self.mesh_data is None:
            messagebox.showwarning("Warning", "No mesh data loaded")
            return

        self.update_status("Opening 3D visualization...", self.colors['accent_blue'])

        window = tk.Toplevel(self.root)
        window.title("3D Bed Mesh Visualization")
        window.geometry("1000x800")
        window.configure(bg=self.colors['bg_dark'])

        fig3d = Figure(figsize=(10, 8), facecolor=self.colors['bg_dark'])
        ax3d = fig3d.add_subplot(111, projection='3d')

        x = np.linspace(self.mesh_min[0], self.mesh_max[0], self.x_count)
        y = np.linspace(self.mesh_min[1], self.mesh_max[1], self.y_count)
        X, Y = np.meshgrid(x, y)

        surf = ax3d.plot_surface(X, Y, self.mesh_data, cmap='RdYlGn_r',
                                alpha=0.95, linewidth=0.3, edgecolor='gray',
                                antialiased=True)

        ax3d.set_xlabel('X (mm)', color=self.colors['fg_primary'], fontsize=11, labelpad=10)
        ax3d.set_ylabel('Y (mm)', color=self.colors['fg_primary'], fontsize=11, labelpad=10)
        ax3d.set_zlabel('Z Offset (mm)', color=self.colors['fg_primary'], fontsize=11, labelpad=10)
        ax3d.set_title('3D Bed Mesh Surface', color=self.colors['fg_primary'],
                      fontsize=14, fontweight='bold', pad=20)

        ax3d.xaxis.pane.fill = False
        ax3d.yaxis.pane.fill = False
        ax3d.zaxis.pane.fill = False
        ax3d.xaxis.pane.set_edgecolor('#444')
        ax3d.yaxis.pane.set_edgecolor('#444')
        ax3d.zaxis.pane.set_edgecolor('#444')
        ax3d.tick_params(colors=self.colors['fg_primary'], labelsize=9)
        ax3d.set_facecolor(self.colors['bg_dark'])
        fig3d.patch.set_facecolor(self.colors['bg_dark'])

        cbar = fig3d.colorbar(surf, ax=ax3d, shrink=0.5, aspect=5, pad=0.1)
        cbar.set_label('Z Offset (mm)', color=self.colors['fg_primary'], fontsize=10)
        cbar.ax.tick_params(labelsize=9, colors=self.colors['fg_primary'])

        canvas3d = FigureCanvasTkAgg(fig3d, master=window)
        canvas3d.draw()
        canvas3d.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Stats at bottom
        stats_frame = tk.Frame(window, bg=self.colors['bg_medium'])
        stats_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        range_val = np.max(self.mesh_data) - np.min(self.mesh_data)
        stats_text = f"📊 Range: {range_val:.4f}mm  •  Min: {np.min(self.mesh_data):.4f}mm  •  Max: {np.max(self.mesh_data):.4f}mm  •  Mean: {np.mean(self.mesh_data):.4f}mm"

        tk.Label(stats_frame, text=stats_text, bg=self.colors['bg_medium'],
                fg=self.colors['fg_primary'], font=self.fonts['normal']).pack(pady=12)

        self.update_status("3D view opened", self.colors['accent_green'])

    def show_interpolated(self):
        """Show interpolated mesh preview"""
        if self.mesh_data is None:
            messagebox.showwarning("Warning", "No mesh data loaded")
            return

        self.update_status("Generating interpolated mesh...", self.colors['accent_blue'])

        X_interp, Y_interp, z_interp = self.generate_interpolated_mesh()

        if X_interp is None:
            return

        window = tk.Toplevel(self.root)
        window.title("Interpolated Mesh Preview - What Klipper Actually Uses")
        window.geometry("1400x800")
        window.configure(bg=self.colors['bg_dark'])

        fig_interp = Figure(figsize=(14, 8), facecolor=self.colors['bg_dark'])

        ax1 = fig_interp.add_subplot(121, projection='3d')
        ax2 = fig_interp.add_subplot(122, projection='3d')

        # Original mesh
        x = np.linspace(self.mesh_min[0], self.mesh_max[0], self.x_count)
        y = np.linspace(self.mesh_min[1], self.mesh_max[1], self.y_count)
        X, Y = np.meshgrid(x, y)

        surf1 = ax1.plot_surface(X, Y, self.mesh_data, cmap='RdYlGn_r',
                                alpha=0.95, linewidth=0.5, antialiased=True)
        ax1.set_title(f'Original Probed Mesh\n{self.x_count}x{self.y_count} = {self.x_count * self.y_count} points',
                     color=self.colors['fg_primary'], fontsize=11, fontweight='bold', pad=15)

        # Interpolated mesh
        x_full = np.linspace(self.mesh_min[0], self.mesh_max[0], z_interp.shape[1])
        y_full = np.linspace(self.mesh_min[1], self.mesh_max[1], z_interp.shape[0])
        X_full, Y_full = np.meshgrid(x_full, y_full)

        surf2 = ax2.plot_surface(X_full, Y_full, z_interp, cmap='RdYlGn_r',
                                alpha=0.95, linewidth=0.2, antialiased=True)
        ax2.set_title(f'Interpolated Mesh (Klipper Uses This)\n{z_interp.shape[1]}x{z_interp.shape[0]} = {z_interp.shape[1] * z_interp.shape[0]} points\n(mesh_pps: {self.mesh_pps[0]}x{self.mesh_pps[1]})',
                     color=self.colors['fg_primary'], fontsize=11, fontweight='bold', pad=15)

        for ax in [ax1, ax2]:
            ax.set_xlabel('X (mm)', color=self.colors['fg_primary'], fontsize=9, labelpad=8)
            ax.set_ylabel('Y (mm)', color=self.colors['fg_primary'], fontsize=9, labelpad=8)
            ax.set_zlabel('Z (mm)', color=self.colors['fg_primary'], fontsize=9, labelpad=8)
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('#444')
            ax.yaxis.pane.set_edgecolor('#444')
            ax.zaxis.pane.set_edgecolor('#444')
            ax.tick_params(colors=self.colors['fg_primary'], labelsize=8)
            ax.set_facecolor(self.colors['bg_dark'])

        fig_interp.patch.set_facecolor(self.colors['bg_dark'])
        fig_interp.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.07)

        canvas_interp = FigureCanvasTkAgg(fig_interp, master=window)
        canvas_interp.draw()
        canvas_interp.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Info label
        info_frame = tk.Frame(window, bg=self.colors['bg_medium'])
        info_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        info_text = f"✨ Bicubic interpolation with {self.mesh_pps[0]}x{self.mesh_pps[1]} points per segment creates a {z_interp.shape[1]}x{z_interp.shape[0]} mesh from your {self.x_count}x{self.y_count} probed points"
        tk.Label(info_frame, text=info_text, bg=self.colors['bg_medium'],
                fg=self.colors['accent_blue'], font=self.fonts['normal'],
                wraplength=1300).pack(pady=12)

        self.update_status("Interpolation preview opened", self.colors['accent_green'])

    def update_plot(self):
        """Update the heatmap visualization with improved contrast and stability"""
        if self.mesh_data is None:
            return

        self.ax.clear()

        # Create heatmap with better interpolation
        im = self.ax.imshow(self.mesh_data, cmap='RdYlGn_r', aspect='auto',
                           interpolation='bilinear', alpha=0.95)

        # Colorbar - create once and reuse the same axes
        if self.cbar is None:
            self.cbar = self.fig.colorbar(im, ax=self.ax, label='Z-Offset (mm)', pad=0.02)
            self.cbar.ax.tick_params(labelsize=9, colors=self.colors['fg_primary'])
            self.cbar.set_label('Z-Offset (mm)', color=self.colors['fg_primary'], fontsize=10)
        else:
            self.cbar.update_normal(im)

        # Grid
        self.ax.set_xticks(np.arange(self.x_count))
        self.ax.set_yticks(np.arange(self.y_count))
        self.ax.set_xticklabels(np.arange(self.x_count), fontsize=9)
        self.ax.set_yticklabels(np.arange(self.y_count), fontsize=9)
        self.ax.grid(True, color='white', linewidth=0.5, alpha=0.2, linestyle=':')

        # Labels
        self.ax.set_xlabel('X Index', color=self.colors['fg_primary'], fontsize=10, fontweight='bold')
        self.ax.set_ylabel('Y Index', color=self.colors['fg_primary'], fontsize=10, fontweight='bold')
        self.ax.set_title('Bed Mesh Heat Map', color=self.colors['fg_primary'],
                         fontsize=12, fontweight='bold', pad=15)

        # Four-heater layout dividers
        half_x = self.x_count / 2
        half_y = self.y_count / 2
        if self.x_count % 2 == 0:
            self.ax.axvline(half_x - 0.5, color='white', linewidth=1.5, alpha=0.3, linestyle='--')
        if self.y_count % 2 == 0:
            self.ax.axhline(half_y - 0.5, color='white', linewidth=1.5, alpha=0.3, linestyle='--')

        # Quadrant labels (subtle)
        if self.x_count >= 4 and self.y_count >= 4:
            quad_labels = [
                ("03", self.x_count / 4 - 0.5, self.y_count / 4 - 0.5),
                ("02", 3 * self.x_count / 4 - 0.5, self.y_count / 4 - 0.5),
                ("00", self.x_count / 4 - 0.5, 3 * self.y_count / 4 - 0.5),
                ("01", 3 * self.x_count / 4 - 0.5, 3 * self.y_count / 4 - 0.5),
            ]
            for label, x_pos, y_pos in quad_labels:
                self.ax.text(x_pos, y_pos, label, ha='center', va='center',
                           color='white', fontsize=28, alpha=0.15, fontweight='bold',
                           family='monospace')

        # Overlay numeric values with IMPROVED CONTRAST
        vmin, vmax = self.mesh_data.min(), self.mesh_data.max()
        norm = plt.Normalize(vmin=vmin, vmax=vmax)

        for y in range(self.y_count):
            for x in range(self.x_count):
                value = self.mesh_data[y, x]
                norm_value = norm(value)

                # IMPROVED: Better contrast logic
                # Use dark text on light backgrounds (norm > 0.45)
                # Use light text on dark backgrounds (norm <= 0.45)
                if norm_value > 0.45:
                    text_color = '#1a1a1a'  # Dark text
                else:
                    text_color = '#f0f0f0'  # Light text

                self.ax.text(x, y, f"{value:.2f}", ha='center', va='center',
                           color=text_color, fontsize=8, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='black',
                                   alpha=0.15, edgecolor='none'))

        # Highlight modified cells (if tracking enabled and show_modifications is True)
        if self.show_modifications and self.modification_tracker:
            modified_cells = self.modification_tracker.get_modified_cells(self.mesh_data, include_working=True)
            working_cells = set(self.modification_tracker.get_working_cells())
            untested_cells = set(self.modification_tracker.get_untested_cells(self.mesh_data))

            for (y, x) in modified_cells:
                if (y, x) in working_cells:
                    # Green border for working (tested) modifications
                    rect = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=2,
                                   edgecolor=self.colors['accent_green'], facecolor='none',
                                   linestyle='-', alpha=0.6)
                elif (y, x) in untested_cells:
                    # Orange border for untested modifications
                    rect = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=2,
                                   edgecolor=self.colors['accent_orange'], facecolor='none',
                                   linestyle='-', alpha=0.7)
                else:
                    # Default orange for modified
                    rect = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=2,
                                   edgecolor=self.colors['accent_orange'], facecolor='none',
                                   linestyle='-', alpha=0.7)
                self.ax.add_patch(rect)

        # Highlight selected region
        if self.selected_region:
            for (y, x) in self.selected_region:
                rect = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=2.5,
                               edgecolor=self.colors['region_highlight'], facecolor='none',
                               linestyle='-', alpha=0.9)
                self.ax.add_patch(rect)

        # Highlight selected point
        if self.selected_point is not None and not self.region_mode:
            y, x = self.selected_point
            # Outer glow
            glow = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=5,
                           edgecolor=self.colors['selection_border'], facecolor='none',
                           alpha=0.3)
            self.ax.add_patch(glow)
            # Inner border
            selection = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=3,
                                 edgecolor=self.colors['selection_border'], facecolor='none',
                                 linestyle='-', alpha=1.0)
            self.ax.add_patch(selection)

        # Styling
        self.ax.tick_params(colors=self.colors['fg_primary'], labelsize=9)
        self.ax.set_facecolor(self.colors['bg_dark'])

        # Adjust layout with proper spacing
        self.fig.subplots_adjust(left=0.08, right=0.92, top=0.95, bottom=0.08)
        self.canvas.draw_idle()  # Use draw_idle instead of draw for better performance

    def on_mouse_press(self, event):
        """Handle mouse press event"""
        if event.inaxes != self.ax or self.mesh_data is None:
            return

        x = int(round(event.xdata))
        y = int(round(event.ydata))

        if not (0 <= x < self.x_count and 0 <= y < self.y_count):
            return

        if self.region_mode:
            self.region_start = (y, x)
            self.selected_region = [(y, x)]
        else:
            self.selected_point = (y, x)
            value = self.mesh_data[y, x]
            self.value_var.set(f"{value:.6f}")
            self.slider_var.set(0)

            x_phys = self.mesh_min[0] + (x / (self.x_count - 1)) * (self.mesh_max[0] - self.mesh_min[0])
            y_phys = self.mesh_min[1] + (y / (self.y_count - 1)) * (self.mesh_max[1] - self.mesh_min[1])

            self.point_label.config(text=f"Point [{x}, {y}]")
            self.coord_label.config(text=f"X:{x_phys:.1f}mm  Y:{y_phys:.1f}mm  Z:{value:.4f}mm")
            self.update_status(f"Selected point [{x}, {y}] = {value:.4f}mm", self.colors['accent_blue'])

        self.update_plot()

    def on_mouse_release(self, event):
        """Handle mouse release event"""
        if self.region_mode and self.region_start is not None:
            if self.selected_region:
                avg_value = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
                self.value_var.set(f"{avg_value:.6f}")
                self.point_label.config(text=f"Region: {len(self.selected_region)} points")
                self.coord_label.config(text=f"Average Z: {avg_value:.4f}mm")
                self.update_status(f"Selected {len(self.selected_region)} points, avg: {avg_value:.4f}mm",
                                 self.colors['region_highlight'])
            self.region_start = None

    def on_mouse_move(self, event):
        """Handle mouse move event for region selection"""
        if not self.region_mode or self.region_start is None:
            return

        if event.inaxes != self.ax or self.mesh_data is None:
            return

        x_end = int(round(event.xdata))
        y_end = int(round(event.ydata))

        if not (0 <= x_end < self.x_count and 0 <= y_end < self.y_count):
            return

        y_start, x_start = self.region_start
        y_min, y_max = min(y_start, y_end), max(y_start, y_end)
        x_min, x_max = min(x_start, x_end), max(x_start, x_end)

        self.selected_region = [(y, x) for y in range(y_min, y_max + 1)
                               for x in range(x_min, x_max + 1)]

        self.update_plot()

    def on_slider_change(self, value):
        """Handle slider change"""
        if self.selected_point is None and not self.selected_region:
            return

        if self.selected_point and not self.region_mode:
            y, x = self.selected_point
            base_value = self.mesh_data[y, x]
            new_value = base_value + float(value)
            self.value_var.set(f"{new_value:.6f}")
        elif self.selected_region:
            avg_value = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
            new_value = avg_value + float(value)
            self.value_var.set(f"{new_value:.6f}")

    def quick_adjust(self, delta):
        """Quick adjustment buttons"""
        if self.selected_point is None and not self.selected_region:
            messagebox.showwarning("Warning", "Please make a selection first")
            return

        try:
            current = float(self.value_var.get())
            new_value = current + delta
            self.value_var.set(f"{new_value:.6f}")
            self.update_selection_value()
        except ValueError:
            pass

    def save_undo_state(self, description="Change"):
        """Save current mesh state to undo stack"""
        if self.mesh_data is None:
            return

        # Create snapshot of current state
        snapshot = self.mesh_data.copy()

        # Add to undo stack
        self.undo_stack.append((snapshot, description))

        # Limit stack size
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

        # Update undo button state if it exists
        if hasattr(self, 'undo_btn'):
            self.undo_btn.config(bg=self.colors['accent_blue'])

    def undo_last_change(self):
        """Undo the last modification"""
        if not self.undo_stack:
            messagebox.showinfo("Undo", "No changes to undo")
            return

        # Pop the last state
        previous_state, description = self.undo_stack.pop()

        # Restore the mesh data
        self.mesh_data = previous_state.copy()

        # Update displays
        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Undone: {description}", self.colors['accent_orange'])

        # Update undo button appearance
        if hasattr(self, 'undo_btn'):
            if not self.undo_stack:
                self.undo_btn.config(bg=self.colors['bg_light'])

        # Clear selection after undo to avoid confusion
        self.clear_region()

    def update_selection_value(self):
        """Update the selected point or region value (supports absolute and relative adjustments)"""
        try:
            value_str = self.value_var.get().strip()

            # Check if it's a relative adjustment (starts with + or -)
            is_relative = value_str.startswith('+') or value_str.startswith('-')

            # Save state before making changes
            if is_relative:
                offset = float(value_str)
                self.save_undo_state(f"Apply {offset:+.4f}mm offset")
            else:
                new_value = float(value_str)
                self.save_undo_state(f"Set to {new_value:.4f}mm")

            if is_relative:
                # Parse relative adjustment
                offset = float(value_str)

                if self.region_mode and self.selected_region:
                    # Apply offset to all cells in region
                    for (y, x) in self.selected_region:
                        old_value = self.mesh_data[y, x]
                        new_value = old_value + offset
                        self.mesh_data[y, x] = new_value
                        # Record modification in tracker
                        if self.modification_tracker:
                            self.modification_tracker.record_modification(y, x, old_value, new_value)
                    self.update_status(f"Applied {offset:+.4f}mm offset to {len(self.selected_region)} points",
                                     self.colors['accent_green'])
                elif self.selected_point is not None:
                    # Apply offset to single point
                    y, x = self.selected_point
                    old_value = self.mesh_data[y, x]
                    new_value = old_value + offset
                    self.mesh_data[y, x] = new_value
                    # Record modification in tracker
                    if self.modification_tracker:
                        self.modification_tracker.record_modification(y, x, old_value, new_value)
                    self.update_status(f"Applied {offset:+.4f}mm offset to point [{x}, {y}]",
                                     self.colors['accent_green'])
                    # Update value display to show new absolute value
                    self.value_var.set(f"{new_value:.6f}")
                else:
                    messagebox.showwarning("Warning", "Please make a selection first")
                    return
            else:
                # Absolute value (existing behavior)
                new_value = float(value_str)

                if self.region_mode and self.selected_region:
                    for (y, x) in self.selected_region:
                        old_value = self.mesh_data[y, x]
                        self.mesh_data[y, x] = new_value
                        # Record modification in tracker
                        if self.modification_tracker:
                            self.modification_tracker.record_modification(y, x, old_value, new_value)
                    self.update_status(f"Updated {len(self.selected_region)} points to {new_value:.4f}mm",
                                     self.colors['accent_green'])
                elif self.selected_point is not None:
                    y, x = self.selected_point
                    old_value = self.mesh_data[y, x]
                    self.mesh_data[y, x] = new_value
                    # Record modification in tracker
                    if self.modification_tracker:
                        self.modification_tracker.record_modification(y, x, old_value, new_value)
                    self.update_status(f"Updated point [{x}, {y}] to {new_value:.4f}mm",
                                     self.colors['accent_green'])
                else:
                    messagebox.showwarning("Warning", "Please make a selection first")
                    return

            self.slider_var.set(0)
            self.is_modified = True
            self.update_plot()
            self.update_statistics()
        except ValueError:
            messagebox.showerror("Error", "Invalid value entered. Use absolute (0.05) or relative (+0.01, -0.02)")
            self.update_status("Error: Invalid value", self.colors['accent_red'])

    def clear_region(self):
        """Clear region selection"""
        self.selected_region = []
        self.region_start = None
        self.selected_point = None
        self.point_label.config(text="No selection")
        self.coord_label.config(text="Make a selection to begin")
        self.update_plot()
        self.update_status("Selection cleared", self.colors['fg_secondary'])

    def average_region(self):
        """Average all values in selected region"""
        if not self.selected_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return

        self.save_undo_state("Average region")
        avg = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
        for (y, x) in self.selected_region:
            old_value = self.mesh_data[y, x]
            self.mesh_data[y, x] = avg
            # Record modification in tracker
            if self.modification_tracker:
                self.modification_tracker.record_modification(y, x, old_value, avg)

        self.value_var.set(f"{avg:.6f}")
        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Averaged {len(self.selected_region)} points to {avg:.4f}mm",
                         self.colors['accent_green'])
        messagebox.showinfo("Success", f"Averaged {len(self.selected_region)} points to {avg:.6f}mm")

    def smooth_region(self):
        """Smooth values in selected region using neighboring points"""
        if not self.selected_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return

        self.save_undo_state("Smooth region")
        smoothed = self.mesh_data.copy()

        for (y, x) in self.selected_region:
            neighbors = []
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.y_count and 0 <= nx < self.x_count:
                        neighbors.append(self.mesh_data[ny, nx])
            smoothed[y, x] = np.mean(neighbors)

        for (y, x) in self.selected_region:
            old_value = self.mesh_data[y, x]
            self.mesh_data[y, x] = smoothed[y, x]
            # Record modification in tracker
            if self.modification_tracker:
                self.modification_tracker.record_modification(y, x, old_value, smoothed[y, x])

        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Smoothed {len(self.selected_region)} points", self.colors['accent_green'])
        messagebox.showinfo("Success", f"Smoothed {len(self.selected_region)} points")

    def apply_region_offset(self, offset):
        """Apply relative offset to all cells in selected region"""
        if not self.selected_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return

        self.save_undo_state(f"Region offset {offset:+.4f}mm")
        # Apply offset to each cell in region
        for (y, x) in self.selected_region:
            old_value = self.mesh_data[y, x]
            new_value = old_value + offset
            self.mesh_data[y, x] = new_value
            # Record modification in tracker
            if self.modification_tracker:
                self.modification_tracker.record_modification(y, x, old_value, new_value)

        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Applied {offset:+.4f}mm offset to {len(self.selected_region)} points",
                         self.colors['accent_green'])

    def toggle_modifications(self):
        """Toggle display of modification indicators"""
        self.show_modifications = self.show_mods_var.get()
        self.update_plot()
        status = "shown" if self.show_modifications else "hidden"
        self.update_status(f"Modification indicators {status}", self.colors['accent_blue'])

    def mark_selection_as_working(self):
        """Mark selected cells as working (tested)"""
        if not self.modification_tracker:
            return

        cells_to_mark = []

        if self.region_mode and self.selected_region:
            cells_to_mark = self.selected_region
        elif self.selected_point is not None:
            cells_to_mark = [self.selected_point]
        else:
            messagebox.showwarning("Warning", "Please make a selection first")
            return

        # Only mark cells that are actually modified
        modified_cells = self.modification_tracker.get_modified_cells(self.mesh_data, include_working=True)
        cells_to_mark = [cell for cell in cells_to_mark if cell in modified_cells]

        if not cells_to_mark:
            messagebox.showinfo("Info", "Selected cells are not modified")
            return

        self.modification_tracker.mark_as_working(cells_to_mark)
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Marked {len(cells_to_mark)} cells as working", self.colors['accent_green'])
        messagebox.showinfo("Success", f"Marked {len(cells_to_mark)} cells as working (tested)")

    def unmark_selection_as_working(self):
        """Remove working status from selected cells"""
        if not self.modification_tracker:
            return

        cells_to_unmark = []

        if self.region_mode and self.selected_region:
            cells_to_unmark = self.selected_region
        elif self.selected_point is not None:
            cells_to_unmark = [self.selected_point]
        else:
            messagebox.showwarning("Warning", "Please make a selection first")
            return

        # Only unmark cells that are actually marked as working
        working_cells = self.modification_tracker.get_working_cells()
        cells_to_unmark = [cell for cell in cells_to_unmark if cell in working_cells]

        if not cells_to_unmark:
            messagebox.showinfo("Info", "Selected cells are not marked as working")
            return

        self.modification_tracker.unmark_as_working(cells_to_unmark)
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Unmarked {len(cells_to_unmark)} cells", self.colors['accent_orange'])
        messagebox.showinfo("Success", f"Removed working status from {len(cells_to_unmark)} cells")

    def reset_selection_to_original(self):
        """Reset selected cells to their original values"""
        if not self.modification_tracker:
            return

        cells_to_reset = []

        if self.region_mode and self.selected_region:
            cells_to_reset = self.selected_region
        elif self.selected_point is not None:
            cells_to_reset = [self.selected_point]
        else:
            messagebox.showwarning("Warning", "Please make a selection first")
            return

        if not messagebox.askyesno("Confirm", f"Reset {len(cells_to_reset)} cells to original values?"):
            return

        # Reset each cell
        for (y, x) in cells_to_reset:
            self.modification_tracker.reset_cell_to_original(y, x, self.mesh_data)

        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Reset {len(cells_to_reset)} cells to original", self.colors['accent_green'])
        messagebox.showinfo("Success", f"Reset {len(cells_to_reset)} cells to original values")

    def open_test_print_dialog(self):
        """Open dialog for test print generation"""
        if not self.modification_tracker:
            messagebox.showwarning("Warning", "No modification tracker available")
            return

        # Get untested cells
        untested_cells = self.modification_tracker.get_untested_cells(self.mesh_data)

        if not untested_cells:
            response = messagebox.askyesno("No Untested Modifications",
                                          "No untested modifications found.\n\n"
                                          "Would you like to generate test prints for all modified cells instead?")
            if response:
                untested_cells = self.modification_tracker.get_modified_cells(self.mesh_data, include_working=True)
            else:
                return

        if not untested_cells:
            messagebox.showinfo("Info", "No modified cells to generate test prints for.")
            return

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Generate Test Print")
        dialog.geometry("700x650")
        dialog.configure(bg=self.colors['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()

        # Main frame with padding
        main_frame = tk.Frame(dialog, bg=self.colors['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        tk.Label(main_frame, text="🖨️ Generate Test Print", font=self.fonts['title'],
                bg=self.colors['bg_dark'], fg=self.colors['fg_primary']).pack(pady=(0, 15))

        # Warning if many cells
        if len(untested_cells) > 10:
            warning_frame = tk.Frame(main_frame, bg=self.colors['accent_orange'], relief=tk.FLAT, bd=2)
            warning_frame.pack(fill=tk.X, pady=(0, 15))

            tk.Label(warning_frame, text=f"⚠️  Warning: {len(untested_cells)} cells selected",
                    font=self.fonts['heading'], bg=self.colors['accent_orange'],
                    fg='white').pack(pady=8)

            tk.Label(warning_frame, text="Consider batching into multiple prints for easier testing",
                    font=self.fonts['small'], bg=self.colors['accent_orange'],
                    fg='white').pack(pady=(0, 8))

        # Cells list frame
        cells_frame = tk.LabelFrame(main_frame, text="Modified Cells", font=self.fonts['heading'],
                                   bg=self.colors['bg_medium'], fg=self.colors['fg_primary'],
                                   relief=tk.FLAT, bd=2)
        cells_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Scrollable list of cells
        list_canvas = tk.Canvas(cells_frame, bg=self.colors['bg_dark'], highlightthickness=0, height=200)
        scrollbar = tk.Scrollbar(cells_frame, orient="vertical", command=list_canvas.yview)
        list_frame = tk.Frame(list_canvas, bg=self.colors['bg_dark'])

        list_frame.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=list_frame, anchor="nw")
        list_canvas.configure(yscrollcommand=scrollbar.set)

        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Display cell information
        cell_info = self.test_generator.get_cell_info(untested_cells)
        for info in cell_info:
            cell_text = f"Grid {info['grid']} → Position {info['position']} mm"
            tk.Label(list_frame, text=cell_text, font=self.fonts['mono'],
                    bg=self.colors['bg_dark'], fg=self.colors['fg_secondary'],
                    anchor='w').pack(fill=tk.X, pady=2, padx=5)

        # Configuration frame
        config_frame = tk.LabelFrame(main_frame, text="Configuration", font=self.fonts['heading'],
                                     bg=self.colors['bg_medium'], fg=self.colors['fg_primary'],
                                     relief=tk.FLAT, bd=2)
        config_frame.pack(fill=tk.X, pady=(0, 15))

        config_inner = tk.Frame(config_frame, bg=self.colors['bg_medium'])
        config_inner.pack(fill=tk.X, padx=15, pady=15)

        # Print name
        tk.Label(config_inner, text="Print Name:", font=self.fonts['normal'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).grid(row=0, column=0, sticky='w', pady=5)

        name_var = tk.StringVar(value=f"BedLevel_Test_{len(untested_cells)}cells")
        name_entry = tk.Entry(config_inner, textvariable=name_var, font=self.fonts['normal'],
                             bg=self.colors['bg_dark'], fg=self.colors['fg_primary'], width=30)
        name_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=(10, 0))

        # Layer height
        tk.Label(config_inner, text="Layer Height (mm):", font=self.fonts['normal'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).grid(row=1, column=0, sticky='w', pady=5)

        layer_var = tk.StringVar(value="0.2")
        layer_entry = tk.Entry(config_inner, textvariable=layer_var, font=self.fonts['normal'],
                              bg=self.colors['bg_dark'], fg=self.colors['fg_primary'], width=30)
        layer_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=(10, 0))

        # Test height (layers)
        tk.Label(config_inner, text="Test Layers:", font=self.fonts['normal'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).grid(row=2, column=0, sticky='w', pady=5)

        layers_var = tk.StringVar(value="2")
        layers_entry = tk.Entry(config_inner, textvariable=layers_var, font=self.fonts['normal'],
                               bg=self.colors['bg_dark'], fg=self.colors['fg_primary'], width=30)
        layers_entry.grid(row=2, column=1, sticky='ew', pady=5, padx=(10, 0))

        # Format selection
        tk.Label(config_inner, text="Export Format:", font=self.fonts['normal'],
                bg=self.colors['bg_medium'], fg=self.colors['fg_primary']).grid(row=3, column=0, sticky='w', pady=5)

        format_var = tk.StringVar(value="3mf")
        format_frame = tk.Frame(config_inner, bg=self.colors['bg_medium'])
        format_frame.grid(row=3, column=1, sticky='w', pady=5, padx=(10, 0))

        tk.Radiobutton(format_frame, text="3MF (recommended)", variable=format_var, value="3mf",
                      bg=self.colors['bg_medium'], fg=self.colors['fg_primary'],
                      selectcolor=self.colors['accent_blue'], font=self.fonts['normal'],
                      activebackground=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 15))

        tk.Radiobutton(format_frame, text="STL", variable=format_var, value="stl",
                      bg=self.colors['bg_medium'], fg=self.colors['fg_primary'],
                      selectcolor=self.colors['accent_blue'], font=self.fonts['normal'],
                      activebackground=self.colors['bg_medium']).pack(side=tk.LEFT)

        config_inner.columnconfigure(1, weight=1)

        # Batch generation option (if >10 cells)
        batch_var = tk.BooleanVar(value=False)
        if len(untested_cells) > 10:
            batch_check = tk.Checkbutton(config_frame, text="Split into multiple files (max 10 cells per file)",
                                        variable=batch_var, bg=self.colors['bg_medium'],
                                        fg=self.colors['fg_primary'], selectcolor=self.colors['accent_blue'],
                                        font=self.fonts['normal'], activebackground=self.colors['bg_medium'])
            batch_check.pack(padx=15, pady=(0, 10))

        # Button frame
        button_frame = tk.Frame(main_frame, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X)

        def generate_print():
            try:
                # Get configuration
                print_name = name_var.get().strip()
                if not print_name:
                    print_name = "BedLevel_Test"

                layer_height = float(layer_var.get())
                test_layers = int(layers_var.get())
                test_height = layer_height * test_layers
                file_format = format_var.get()
                batch_mode = batch_var.get()

                # Ask for save location
                extension = "3mf" if file_format == "3mf" else "stl"
                filetypes = [("3MF files", "*.3mf")] if file_format == "3mf" else [("STL files", "*.stl")]

                # Import filedialog (used in both batch and single mode)
                from tkinter import filedialog

                if batch_mode and len(untested_cells) > 10:
                    # Batch mode - ask for directory
                    save_dir = filedialog.askdirectory(title="Select directory for batch files")
                    if not save_dir:
                        return

                    # Split into batches of 10
                    batch_size = 10
                    batches = [untested_cells[i:i+batch_size] for i in range(0, len(untested_cells), batch_size)]

                    success_count = 0
                    guide_files = []

                    for idx, batch in enumerate(batches, 1):
                        batch_name = f"{print_name}_batch{idx}"
                        filepath = os.path.join(save_dir, f"{batch_name}.{extension}")

                        # Generate and export using scene-based methods
                        if file_format == "3mf":
                            # Use scene export for positioned objects
                            success, guide_path, center_coord = self.test_generator.export_scene_3mf(
                                batch, filepath, test_height=test_height
                            )
                            if success and guide_path:
                                guide_files.append(os.path.basename(guide_path))
                        else:
                            # Use STL with reference frame
                            success = self.test_generator.export_with_reference_frame(
                                batch, filepath, test_height=test_height, add_frame=True
                            )

                        if success:
                            success_count += 1

                    dialog.destroy()
                    self.update_status(f"Generated {success_count} batch files", self.colors['accent_green'])

                    guide_info = ""
                    if guide_files:
                        guide_info = f"\n\nPosition guides: {len(guide_files)} JSON files"

                    messagebox.showinfo("Success",
                                      f"Generated {success_count} test print files\n"
                                      f"Location: {save_dir}\n"
                                      f"Total cells: {len(untested_cells)}{guide_info}")
                else:
                    # Single file mode
                    filepath = filedialog.asksaveasfilename(
                        defaultextension=f".{extension}",
                        filetypes=filetypes,
                        initialfile=f"{print_name}.{extension}",
                        title="Save Test Print"
                    )

                    if not filepath:
                        return

                    # Generate and export using scene-based methods
                    guide_path = None
                    center_coord = None
                    if file_format == "3mf":
                        # Use scene export for positioned objects
                        success, guide_path, center_coord = self.test_generator.export_scene_3mf(
                            untested_cells, filepath, test_height=test_height
                        )
                    else:
                        # Use STL with reference frame
                        success = self.test_generator.export_with_reference_frame(
                            untested_cells, filepath, test_height=test_height, add_frame=True
                        )
                        # Calculate center for STL too
                        center_coord = self.test_generator.calculate_object_center(untested_cells)

                    if success:
                        dialog.destroy()
                        self.update_status(f"Test print saved: {os.path.basename(filepath)}",
                                         self.colors['accent_green'])

                        success_msg = (
                            f"✓ Test print generated successfully!\n\n"
                            f"File: {os.path.basename(filepath)}\n"
                            f"Cells: {len(untested_cells)}\n"
                            f"Height: {test_height:.2f}mm ({test_layers} layers)"
                        )

                        if center_coord:
                            success_msg += f"\n\n{'='*50}"
                            success_msg += f"\n📍 POSITION IN ELEGOO SLICER:"
                            success_msg += f"\n{'='*50}"
                            success_msg += f"\n\n1. Open Elegoo Slicer"
                            success_msg += f"\n2. File → Open Project"
                            success_msg += f"\n3. Select the .3mf file"
                            success_msg += f"\n4. Click the object, then click Move tool"
                            success_msg += f"\n5. Enter these coordinates:\n"
                            success_msg += f"\n   X: {center_coord[0]}"
                            success_msg += f"\n   Y: {center_coord[1]}"
                            success_msg += f"\n   Z: 0\n"
                            success_msg += f"\n6. Press Enter to apply"
                            success_msg += f"\n7. Slice and print!"

                        if guide_path:
                            success_msg += f"\n\n📄 Position guide: {os.path.basename(guide_path)}"

                        messagebox.showinfo("Success", success_msg)
                    else:
                        messagebox.showerror("Error", "Failed to export test print")

            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate test print: {str(e)}")

        # Buttons
        ModernButton(button_frame, text="✓ Generate", command=generate_print,
                    bg=self.colors['accent_green'], fg='white', font=self.fonts['heading'],
                    relief=tk.FLAT, cursor='hand2', width=15).pack(side=tk.LEFT, padx=5, ipady=8)

        ModernButton(button_frame, text="✗ Cancel", command=dialog.destroy,
                    bg=self.colors['accent_red'], fg='white', font=self.fonts['heading'],
                    relief=tk.FLAT, cursor='hand2', width=15).pack(side=tk.LEFT, padx=5, ipady=8)

    def update_statistics(self):
        """Update statistics display"""
        if self.mesh_data is None:
            return

        range_val = np.max(self.mesh_data) - np.min(self.mesh_data)

        # Get modification statistics if tracker is available
        mod_stats_text = ""
        if self.modification_tracker:
            mod_stats = self.modification_tracker.get_statistics(self.mesh_data)
            mod_stats_text = f"""
╠════════════════════════════════╣
║   MODIFICATION TRACKING        ║
╠════════════════════════════════╣
  Modified:   {mod_stats['total_modified']} cells
  Working:    {mod_stats['working']} cells
  Untested:   {mod_stats['untested']} cells
"""

        stats = f"""
╔════════════════════════════════╗
║      MESH STATISTICS           ║
╠════════════════════════════════╣
  Points:     {self.x_count} × {self.y_count} = {self.x_count * self.y_count}

  Min:        {np.min(self.mesh_data):.6f} mm
  Max:        {np.max(self.mesh_data):.6f} mm
  Range:      {range_val:.6f} mm

  Mean:       {np.mean(self.mesh_data):.6f} mm
  Std Dev:    {np.std(self.mesh_data):.6f} mm{mod_stats_text}╚════════════════════════════════╝
        """

        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats.strip())

    def flatten_mesh(self):
        """Flatten all mesh points to average"""
        if self.mesh_data is None:
            return

        if messagebox.askyesno("Confirm", "Set all points to average value?"):
            self.save_undo_state("Flatten mesh")
            avg = np.mean(self.mesh_data)
            # Track modifications for all cells
            if self.modification_tracker:
                for y in range(self.y_count):
                    for x in range(self.x_count):
                        old_value = self.mesh_data[y, x]
                        self.modification_tracker.record_modification(y, x, old_value, avg)
            self.mesh_data.fill(avg)
            self.is_modified = True
            self.update_plot()
            self.update_statistics()
            self.update_status(f"Flattened mesh to {avg:.4f}mm", self.colors['accent_green'])

    def offset_all(self):
        """Offset all points by a value"""
        if self.mesh_data is None:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Offset All Points")
        dialog.geometry("400x200")
        dialog.configure(bg=self.colors['bg_medium'])

        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Enter offset value (mm):", bg=self.colors['bg_medium'],
                fg=self.colors['fg_primary'], font=self.fonts['heading']).pack(pady=20)

        offset_var = tk.StringVar(value="0.0")
        entry = tk.Entry(dialog, textvariable=offset_var, font=('Consolas', 14),
                        bg=self.colors['bg_dark'], fg=self.colors['fg_primary'],
                        justify=tk.CENTER, width=15)
        entry.pack(pady=10, ipady=5)
        entry.focus_set()

        def apply_offset():
            try:
                offset = float(offset_var.get())
                self.save_undo_state(f"Offset all {offset:+.4f}mm")
                # Track modifications for all cells
                if self.modification_tracker:
                    for y in range(self.y_count):
                        for x in range(self.x_count):
                            old_value = self.mesh_data[y, x]
                            new_value = old_value + offset
                            self.modification_tracker.record_modification(y, x, old_value, new_value)
                self.mesh_data += offset
                self.is_modified = True
                self.update_plot()
                self.update_statistics()
                dialog.destroy()
                self.update_status(f"Applied offset of {offset:.4f}mm to all points",
                                 self.colors['accent_green'])
                messagebox.showinfo("Success", f"Applied offset of {offset:.6f}mm to all points")
            except ValueError:
                messagebox.showerror("Error", "Invalid offset value")

        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)

        ModernButton(btn_frame, text="Apply", command=apply_offset,
                    bg=self.colors['accent_green'], fg='white',
                    font=self.fonts['heading'], padx=30, pady=10).pack(side=tk.LEFT, padx=5)

        ModernButton(btn_frame, text="Cancel", command=dialog.destroy,
                    bg=self.colors['accent_red'], fg='white',
                    font=self.fonts['normal'], padx=30, pady=10).pack(side=tk.LEFT, padx=5)

        entry.bind('<Return>', lambda e: apply_offset())

def main():
    root = tk.Tk()
    app = BedLevelEditorPro(root)
    root.mainloop()

if __name__ == "__main__":
    main()
