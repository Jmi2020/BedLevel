#!/usr/bin/env python3
"""
Enhanced Bed Level Editor for Elegoo OrangeStorm Giga
Features:
- 3D visualization of bed mesh
- Interpolated mesh preview (bicubic with mesh_pps)
- Region selection and bulk editing
- Profile comparison
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import numpy as np
from scipy import interpolate
import re
import os

class BedLevelEditorEnhanced:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Bed Level Editor - Elegoo OrangeStorm Giga")
        self.root.geometry("1600x950")

        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "printer.cfg")
        self.mesh_data = None
        self.original_mesh_data = None
        self.x_count = 10
        self.y_count = 10
        self.selected_point = None
        self.selected_region = []  # For region selection
        self.mesh_min = (16, 10)
        self.mesh_max = (786, 767)
        self.mesh_pps = (4, 4)  # Points per segment for interpolation
        self.cbar = None
        self.cell_labels = []

        # Region selection state
        self.region_mode = False
        self.region_start = None

        # Color scheme
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.highlight_color = "#4a90e2"
        self.region_color = "#ff6b6b"

        self.setup_ui()
        self.load_mesh_data()

    def setup_ui(self):
        """Setup the user interface"""
        self.root.configure(bg=self.bg_color)

        # Top frame for controls
        control_frame = tk.Frame(self.root, bg=self.bg_color, padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # File info
        tk.Label(control_frame, text="Config File:", bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.file_label = tk.Label(control_frame, text=self.config_file, bg=self.bg_color,
                                   fg=self.highlight_color, font=("Arial", 9))
        self.file_label.pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = tk.Frame(control_frame, bg=self.bg_color)
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="Browse...", command=self.browse_file,
                 bg="#9b59b6", fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Load", command=self.load_mesh_data,
                 bg=self.highlight_color, fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="3D View", command=self.show_3d_view,
                 bg="#3498db", fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Interpolated", command=self.show_interpolated,
                 bg="#16a085", fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Save", command=self.save_mesh_data,
                 bg="#27ae60", fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Reset", command=self.reset_mesh_data,
                 bg="#e74c3c", fg=self.fg_color, padx=12, pady=5).pack(side=tk.LEFT, padx=3)

        # Main content frame
        content_frame = tk.Frame(self.root, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Heatmap
        left_panel = tk.Frame(content_frame, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_panel, text="Bed Mesh Visualization (Click to Select / Drag for Region)",
                bg=self.bg_color, fg=self.fg_color, font=("Arial", 11, "bold")).pack(pady=5)

        # Matplotlib figure
        self.fig = Figure(figsize=(10, 8.5), facecolor=self.bg_color)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=left_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # Right panel - Controls
        right_panel = tk.Frame(content_frame, bg=self.bg_color, width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        # Selection mode toggle
        mode_frame = tk.LabelFrame(right_panel, text="Selection Mode", bg=self.bg_color,
                                   fg=self.fg_color, font=("Arial", 10, "bold"))
        mode_frame.pack(fill=tk.X, pady=10)

        self.mode_var = tk.StringVar(value="single")
        tk.Radiobutton(mode_frame, text="Single Point", variable=self.mode_var, value="single",
                      command=self.change_selection_mode, bg=self.bg_color, fg=self.fg_color,
                      selectcolor=self.bg_color, activebackground=self.bg_color).pack(anchor=tk.W, padx=5, pady=2)
        tk.Radiobutton(mode_frame, text="Region Selection", variable=self.mode_var, value="region",
                      command=self.change_selection_mode, bg=self.bg_color, fg=self.fg_color,
                      selectcolor=self.bg_color, activebackground=self.bg_color).pack(anchor=tk.W, padx=5, pady=2)

        # Point/Region info
        info_frame = tk.LabelFrame(right_panel, text="Selection Info", bg=self.bg_color,
                                   fg=self.fg_color, font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, pady=10)

        self.point_label = tk.Label(info_frame, text="No selection", bg=self.bg_color,
                                    fg=self.fg_color, font=("Arial", 10))
        self.point_label.pack(pady=5)

        self.coord_label = tk.Label(info_frame, text="", bg=self.bg_color,
                                    fg=self.highlight_color, font=("Arial", 9))
        self.coord_label.pack(pady=2)

        # Value adjustment
        adjust_frame = tk.LabelFrame(right_panel, text="Adjust Value", bg=self.bg_color,
                                    fg=self.fg_color, font=("Arial", 10, "bold"))
        adjust_frame.pack(fill=tk.X, pady=10)

        tk.Label(adjust_frame, text="Z-Offset:", bg=self.bg_color,
                fg=self.fg_color).pack(pady=5)

        self.value_var = tk.StringVar(value="0.000")
        value_entry = tk.Entry(adjust_frame, textvariable=self.value_var,
                              font=("Arial", 12), justify=tk.CENTER, width=15)
        value_entry.pack(pady=5)
        value_entry.bind('<Return>', lambda e: self.update_selection_value())

        # Slider for fine adjustment
        tk.Label(adjust_frame, text="Fine Adjustment (±0.5mm):", bg=self.bg_color,
                fg=self.fg_color, font=("Arial", 9)).pack(pady=(10, 5))

        self.slider_var = tk.DoubleVar(value=0)
        slider = tk.Scale(adjust_frame, from_=-0.5, to=0.5, resolution=0.001,
                         orient=tk.HORIZONTAL, variable=self.slider_var,
                         command=self.on_slider_change, bg=self.bg_color,
                         fg=self.fg_color, highlightbackground=self.bg_color,
                         troughcolor=self.highlight_color, length=280)
        slider.pack(pady=5)

        # Quick adjustment buttons
        quick_frame = tk.Frame(adjust_frame, bg=self.bg_color)
        quick_frame.pack(pady=10)

        adjustments = [("++", 0.1), ("+", 0.01), ("-", -0.01), ("--", -0.1)]
        for label, value in adjustments:
            tk.Button(quick_frame, text=label, command=lambda v=value: self.quick_adjust(v),
                     bg=self.highlight_color, fg=self.fg_color, width=4, pady=2).pack(side=tk.LEFT, padx=2)

        tk.Button(adjust_frame, text="Update Selection", command=self.update_selection_value,
                 bg="#27ae60", fg=self.fg_color, padx=20, pady=8, font=("Arial", 10, "bold")).pack(pady=10)

        # Region tools
        region_frame = tk.LabelFrame(right_panel, text="Region Tools", bg=self.bg_color,
                                     fg=self.fg_color, font=("Arial", 10, "bold"))
        region_frame.pack(fill=tk.X, pady=10)

        tk.Button(region_frame, text="Average Region", command=self.average_region,
                 bg="#f39c12", fg=self.fg_color, pady=5).pack(fill=tk.X, padx=5, pady=3)
        tk.Button(region_frame, text="Smooth Region", command=self.smooth_region,
                 bg="#d35400", fg=self.fg_color, pady=5).pack(fill=tk.X, padx=5, pady=3)
        tk.Button(region_frame, text="Clear Selection", command=self.clear_region,
                 bg="#95a5a6", fg=self.fg_color, pady=5).pack(fill=tk.X, padx=5, pady=3)

        # Statistics
        stats_frame = tk.LabelFrame(right_panel, text="Mesh Statistics", bg=self.bg_color,
                                   fg=self.fg_color, font=("Arial", 10, "bold"))
        stats_frame.pack(fill=tk.X, pady=10)

        self.stats_text = tk.Text(stats_frame, height=8, bg="#1a1a1a", fg=self.fg_color,
                                 font=("Courier", 9), relief=tk.FLAT)
        self.stats_text.pack(padx=5, pady=5, fill=tk.BOTH)

        # Batch operations
        batch_frame = tk.LabelFrame(right_panel, text="Batch Operations", bg=self.bg_color,
                                   fg=self.fg_color, font=("Arial", 10, "bold"))
        batch_frame.pack(fill=tk.X, pady=10)

        tk.Button(batch_frame, text="Level All (Flatten)", command=self.flatten_mesh,
                 bg="#e67e22", fg=self.fg_color, pady=5).pack(fill=tk.X, padx=5, pady=3)
        tk.Button(batch_frame, text="Offset All Points", command=self.offset_all,
                 bg="#9b59b6", fg=self.fg_color, pady=5).pack(fill=tk.X, padx=5, pady=3)

    def change_selection_mode(self):
        """Change between single point and region selection modes"""
        self.region_mode = (self.mode_var.get() == "region")
        self.clear_region()
        self.point_label.config(text="No selection")
        self.coord_label.config(text="")

    def browse_file(self):
        """Browse for printer.cfg file"""
        filename = filedialog.askopenfilename(
            title="Select printer.cfg file",
            initialdir=os.path.dirname(self.config_file),
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = filename
            self.file_label.config(text=self.config_file)
            self.load_mesh_data()

    def load_mesh_data(self):
        """Load mesh data from printer.cfg"""
        try:
            if not os.path.exists(self.config_file):
                messagebox.showerror("Error", f"Config file not found: {self.config_file}")
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
                return

            self.mesh_data = np.array(points)
            self.original_mesh_data = self.mesh_data.copy()
            self.y_count, self.x_count = self.mesh_data.shape

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

            self.update_plot()
            self.update_statistics()
            messagebox.showinfo("Success", f"Loaded {self.x_count}x{self.y_count} mesh ({self.x_count * self.y_count} points)\nInterpolation: {self.mesh_pps[0]}x{self.mesh_pps[1]} pps")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mesh data: {str(e)}")

    def save_mesh_data(self):
        """Save mesh data back to printer.cfg"""
        if self.mesh_data is None:
            messagebox.showerror("Error", "No mesh data to save")
            return

        try:
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
            messagebox.showinfo("Success", f"Mesh data saved!\nBackup created: {backup_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save mesh data: {str(e)}")

    def reset_mesh_data(self):
        """Reset mesh data to original values"""
        if self.original_mesh_data is None:
            return

        if messagebox.askyesno("Confirm Reset", "Reset all changes to original values?"):
            self.mesh_data = self.original_mesh_data.copy()
            self.clear_region()
            self.update_plot()
            self.update_statistics()
            messagebox.showinfo("Reset", "Mesh data reset to original values")

    def generate_interpolated_mesh(self):
        """Generate interpolated mesh using bicubic interpolation"""
        if self.mesh_data is None:
            return None, None, None

        # Original grid coordinates
        x_orig = np.linspace(0, self.x_count - 1, self.x_count)
        y_orig = np.linspace(0, self.y_count - 1, self.y_count)

        # Interpolated grid
        segments_x = self.x_count - 1
        segments_y = self.y_count - 1
        points_x = segments_x * self.mesh_pps[0] + 1
        points_y = segments_y * self.mesh_pps[1] + 1

        x_interp = np.linspace(0, self.x_count - 1, points_x)
        y_interp = np.linspace(0, self.y_count - 1, points_y)

        # Perform bicubic interpolation
        f = interpolate.RectBivariateSpline(y_orig, x_orig, self.mesh_data, kx=3, ky=3, s=0)
        z_interp = f(y_interp, x_interp)

        X_interp, Y_interp = np.meshgrid(x_interp, y_interp)

        return X_interp, Y_interp, z_interp

    def show_3d_view(self):
        """Show 3D visualization of mesh"""
        if self.mesh_data is None:
            messagebox.showwarning("Warning", "No mesh data loaded")
            return

        # Create new window for 3D view
        window = tk.Toplevel(self.root)
        window.title("3D Bed Mesh Visualization")
        window.geometry("900x700")
        window.configure(bg=self.bg_color)

        fig3d = Figure(figsize=(9, 7), facecolor=self.bg_color)
        ax3d = fig3d.add_subplot(111, projection='3d')

        # Generate mesh grid
        x = np.linspace(self.mesh_min[0], self.mesh_max[0], self.x_count)
        y = np.linspace(self.mesh_min[1], self.mesh_max[1], self.y_count)
        X, Y = np.meshgrid(x, y)

        # Plot surface
        surf = ax3d.plot_surface(X, Y, self.mesh_data, cmap='RdYlGn_r',
                                alpha=0.9, linewidth=0.5, edgecolor='gray')

        # Labels
        ax3d.set_xlabel('X (mm)', color=self.fg_color, fontsize=10)
        ax3d.set_ylabel('Y (mm)', color=self.fg_color, fontsize=10)
        ax3d.set_zlabel('Z Offset (mm)', color=self.fg_color, fontsize=10)
        ax3d.set_title('3D Bed Mesh Surface', color=self.fg_color, fontsize=12, fontweight='bold')

        # Styling
        ax3d.xaxis.pane.fill = False
        ax3d.yaxis.pane.fill = False
        ax3d.zaxis.pane.fill = False
        ax3d.xaxis.pane.set_edgecolor('gray')
        ax3d.yaxis.pane.set_edgecolor('gray')
        ax3d.zaxis.pane.set_edgecolor('gray')
        ax3d.tick_params(colors=self.fg_color)
        ax3d.set_facecolor(self.bg_color)
        fig3d.patch.set_facecolor(self.bg_color)

        # Colorbar
        fig3d.colorbar(surf, ax=ax3d, shrink=0.5, aspect=5, label='Z Offset (mm)')

        canvas3d = FigureCanvasTkAgg(fig3d, master=window)
        canvas3d.draw()
        canvas3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add statistics
        stats_frame = tk.Frame(window, bg=self.bg_color)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)

        stats_text = f"Range: {np.max(self.mesh_data) - np.min(self.mesh_data):.4f}mm  |  "
        stats_text += f"Min: {np.min(self.mesh_data):.4f}mm  |  "
        stats_text += f"Max: {np.max(self.mesh_data):.4f}mm"

        tk.Label(stats_frame, text=stats_text, bg=self.bg_color, fg=self.fg_color,
                font=("Courier", 10)).pack()

    def show_interpolated(self):
        """Show interpolated mesh preview"""
        if self.mesh_data is None:
            messagebox.showwarning("Warning", "No mesh data loaded")
            return

        X_interp, Y_interp, z_interp = self.generate_interpolated_mesh()

        if X_interp is None:
            return

        # Create new window
        window = tk.Toplevel(self.root)
        window.title("Interpolated Mesh Preview (What Klipper Actually Uses)")
        window.geometry("1100x700")
        window.configure(bg=self.bg_color)

        fig_interp = Figure(figsize=(11, 7), facecolor=self.bg_color)

        # Show side-by-side comparison
        ax1 = fig_interp.add_subplot(121, projection='3d')
        ax2 = fig_interp.add_subplot(122, projection='3d')

        # Original mesh (probed points)
        x = np.linspace(self.mesh_min[0], self.mesh_max[0], self.x_count)
        y = np.linspace(self.mesh_min[1], self.mesh_max[1], self.y_count)
        X, Y = np.meshgrid(x, y)

        surf1 = ax1.plot_surface(X, Y, self.mesh_data, cmap='RdYlGn_r', alpha=0.9)
        ax1.set_title(f'Original Probed Mesh\n{self.x_count}x{self.y_count} points',
                     color=self.fg_color, fontsize=10, fontweight='bold')

        # Interpolated mesh
        x_full = np.linspace(self.mesh_min[0], self.mesh_max[0], z_interp.shape[1])
        y_full = np.linspace(self.mesh_min[1], self.mesh_max[1], z_interp.shape[0])
        X_full, Y_full = np.meshgrid(x_full, y_full)

        surf2 = ax2.plot_surface(X_full, Y_full, z_interp, cmap='RdYlGn_r', alpha=0.9)
        ax2.set_title(f'Interpolated Mesh (Klipper Uses This)\n{z_interp.shape[1]}x{z_interp.shape[0]} points ({self.mesh_pps[0]}x{self.mesh_pps[1]} pps)',
                     color=self.fg_color, fontsize=10, fontweight='bold')

        # Style both axes
        for ax in [ax1, ax2]:
            ax.set_xlabel('X (mm)', color=self.fg_color, fontsize=9)
            ax.set_ylabel('Y (mm)', color=self.fg_color, fontsize=9)
            ax.set_zlabel('Z (mm)', color=self.fg_color, fontsize=9)
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.tick_params(colors=self.fg_color, labelsize=8)
            ax.set_facecolor(self.bg_color)

        fig_interp.patch.set_facecolor(self.bg_color)
        fig_interp.tight_layout()

        canvas_interp = FigureCanvasTkAgg(fig_interp, master=window)
        canvas_interp.draw()
        canvas_interp.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Info label
        info_text = f"Bicubic interpolation with {self.mesh_pps[0]}x{self.mesh_pps[1]} points per segment creates a {z_interp.shape[1]}x{z_interp.shape[0]} mesh from your {self.x_count}x{self.y_count} probed points"
        tk.Label(window, text=info_text, bg=self.bg_color, fg=self.highlight_color,
                font=("Arial", 10), wraplength=1000).pack(pady=10)

    def update_plot(self):
        """Update the heatmap visualization"""
        if self.mesh_data is None:
            return

        self.ax.clear()
        self.cell_labels = []

        # Create heatmap
        im = self.ax.imshow(self.mesh_data, cmap='RdYlGn_r', aspect='auto', interpolation='nearest')

        # Add colorbar
        if hasattr(self, 'cbar') and self.cbar is not None:
            try:
                self.cbar.remove()
            except:
                pass
        self.cbar = self.fig.colorbar(im, ax=self.ax, label='Z-Offset (mm)')

        # Add grid
        self.ax.set_xticks(np.arange(self.x_count))
        self.ax.set_yticks(np.arange(self.y_count))
        self.ax.set_xticklabels(np.arange(self.x_count))
        self.ax.set_yticklabels(np.arange(self.y_count))
        self.ax.grid(True, color='white', linewidth=0.5, alpha=0.3)

        # Labels
        self.ax.set_xlabel('X Index', color='white', fontsize=10)
        self.ax.set_ylabel('Y Index', color='white', fontsize=10)
        self.ax.set_title('Bed Mesh Heat Map', color='white', fontsize=12, fontweight='bold')

        # Show four-heater layout
        half_x = self.x_count / 2
        half_y = self.y_count / 2
        if self.x_count % 2 == 0:
            self.ax.axvline(half_x - 0.5, color='white', linewidth=2, alpha=0.4)
        if self.y_count % 2 == 0:
            self.ax.axhline(half_y - 0.5, color='white', linewidth=2, alpha=0.4)

        # Label quadrants
        if self.x_count >= 4 and self.y_count >= 4:
            quad_labels = [
                ("03", self.x_count / 4 - 0.5, self.y_count / 4 - 0.5),
                ("02", 3 * self.x_count / 4 - 0.5, self.y_count / 4 - 0.5),
                ("00", self.x_count / 4 - 0.5, 3 * self.y_count / 4 - 0.5),
                ("01", 3 * self.x_count / 4 - 0.5, 3 * self.y_count / 4 - 0.5),
            ]
            for label, x_pos, y_pos in quad_labels:
                self.ax.text(x_pos, y_pos, label, ha='center', va='center',
                             color='white', fontsize=24, alpha=0.25, fontweight='bold')

        # Overlay numeric values
        text_threshold = 0.55
        for y in range(self.y_count):
            for x in range(self.x_count):
                value = self.mesh_data[y, x]
                norm_value = im.norm(value)
                text_color = '#111111' if norm_value > text_threshold else '#f7f7f7'
                label = self.ax.text(x, y, f"{value:.2f}", ha='center', va='center',
                                     color=text_color, fontsize=8, fontweight='bold')
                self.cell_labels.append(label)

        # Highlight selected region
        if self.selected_region:
            for (y, x) in self.selected_region:
                rect = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=2,
                               edgecolor=self.region_color, facecolor='none')
                self.ax.add_patch(rect)

        # Highlight selected point
        if self.selected_point is not None and not self.region_mode:
            y, x = self.selected_point
            selection = Rectangle((x - 0.5, y - 0.5), 1, 1, linewidth=3,
                                 edgecolor=self.highlight_color, facecolor='none')
            self.ax.add_patch(selection)
            self.ax.scatter([x], [y], s=120, facecolors='none',
                           edgecolors='white', linewidths=2)

        # Style
        self.ax.tick_params(colors='white')
        self.fig.patch.set_facecolor(self.bg_color)
        self.ax.set_facecolor('#1a1a1a')

        self.canvas.draw()

    def on_mouse_press(self, event):
        """Handle mouse press event"""
        if event.inaxes != self.ax or self.mesh_data is None:
            return

        x = int(round(event.xdata))
        y = int(round(event.ydata))

        if not (0 <= x < self.x_count and 0 <= y < self.y_count):
            return

        if self.region_mode:
            # Start region selection
            self.region_start = (y, x)
            self.selected_region = [(y, x)]
        else:
            # Single point selection
            self.selected_point = (y, x)
            value = self.mesh_data[y, x]
            self.value_var.set(f"{value:.6f}")
            self.slider_var.set(0)

            x_phys = self.mesh_min[0] + (x / (self.x_count - 1)) * (self.mesh_max[0] - self.mesh_min[0])
            y_phys = self.mesh_min[1] + (y / (self.y_count - 1)) * (self.mesh_max[1] - self.mesh_min[1])

            self.point_label.config(text=f"Point [{x}, {y}]")
            self.coord_label.config(text=f"~X:{x_phys:.1f} Y:{y_phys:.1f} Z:{value:.3f}")

        self.update_plot()

    def on_mouse_release(self, event):
        """Handle mouse release event"""
        if self.region_mode and self.region_start is not None:
            # Finalize region selection
            if self.selected_region:
                avg_value = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
                self.value_var.set(f"{avg_value:.6f}")
                self.point_label.config(text=f"Region: {len(self.selected_region)} points")
                self.coord_label.config(text=f"Avg Z: {avg_value:.3f}")
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

        # Update region selection
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
            base_value = self.mesh_data[y, x] - self.slider_var.get()
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

    def update_selection_value(self):
        """Update the selected point or region value"""
        try:
            new_value = float(self.value_var.get())

            if self.region_mode and self.selected_region:
                # Update all points in region
                for (y, x) in self.selected_region:
                    self.mesh_data[y, x] = new_value
            elif self.selected_point is not None:
                # Update single point
                y, x = self.selected_point
                self.mesh_data[y, x] = new_value
            else:
                messagebox.showwarning("Warning", "Please make a selection first")
                return

            self.slider_var.set(0)
            self.update_plot()
            self.update_statistics()
        except ValueError:
            messagebox.showerror("Error", "Invalid value entered")

    def clear_region(self):
        """Clear region selection"""
        self.selected_region = []
        self.region_start = None
        self.update_plot()

    def average_region(self):
        """Average all values in selected region"""
        if not self.selected_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return

        avg = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
        for (y, x) in self.selected_region:
            self.mesh_data[y, x] = avg

        self.value_var.set(f"{avg:.6f}")
        self.update_plot()
        self.update_statistics()
        messagebox.showinfo("Success", f"Averaged {len(self.selected_region)} points to {avg:.6f}")

    def smooth_region(self):
        """Smooth values in selected region using neighboring points"""
        if not self.selected_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return

        # Create a copy for calculating smoothed values
        smoothed = self.mesh_data.copy()

        for (y, x) in self.selected_region:
            # Get neighbors
            neighbors = []
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.y_count and 0 <= nx < self.x_count:
                        neighbors.append(self.mesh_data[ny, nx])

            # Average neighbors
            smoothed[y, x] = np.mean(neighbors)

        # Apply smoothed values
        for (y, x) in self.selected_region:
            self.mesh_data[y, x] = smoothed[y, x]

        self.update_plot()
        self.update_statistics()
        messagebox.showinfo("Success", f"Smoothed {len(self.selected_region)} points")

    def update_statistics(self):
        """Update statistics display"""
        if self.mesh_data is None:
            return

        stats = f"""
Points:    {self.x_count} x {self.y_count} = {self.x_count * self.y_count}
Min:       {np.min(self.mesh_data):.6f} mm
Max:       {np.max(self.mesh_data):.6f} mm
Range:     {np.max(self.mesh_data) - np.min(self.mesh_data):.6f} mm
Mean:      {np.mean(self.mesh_data):.6f} mm
Std Dev:   {np.std(self.mesh_data):.6f} mm
        """

        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats.strip())

    def flatten_mesh(self):
        """Flatten all mesh points to average"""
        if self.mesh_data is None:
            return

        if messagebox.askyesno("Confirm", "Set all points to average value?"):
            avg = np.mean(self.mesh_data)
            self.mesh_data.fill(avg)
            self.update_plot()
            self.update_statistics()

    def offset_all(self):
        """Offset all points by a value"""
        if self.mesh_data is None:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Offset All Points")
        dialog.geometry("300x150")
        dialog.configure(bg=self.bg_color)

        tk.Label(dialog, text="Enter offset value (mm):", bg=self.bg_color,
                fg=self.fg_color).pack(pady=10)

        offset_var = tk.StringVar(value="0.0")
        entry = tk.Entry(dialog, textvariable=offset_var, font=("Arial", 12))
        entry.pack(pady=10)

        def apply_offset():
            try:
                offset = float(offset_var.get())
                self.mesh_data += offset
                self.update_plot()
                self.update_statistics()
                dialog.destroy()
                messagebox.showinfo("Success", f"Applied offset of {offset:.6f} mm to all points")
            except ValueError:
                messagebox.showerror("Error", "Invalid offset value")

        tk.Button(dialog, text="Apply", command=apply_offset, bg=self.highlight_color,
                 fg=self.fg_color, padx=20, pady=5).pack(pady=10)

def main():
    root = tk.Tk()
    app = BedLevelEditorEnhanced(root)
    root.mainloop()

if __name__ == "__main__":
    main()
