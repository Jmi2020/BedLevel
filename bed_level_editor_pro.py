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

class ModernButton(tk.Button):
    """Styled button with hover effects"""
    def __init__(self, parent, **kwargs):
        # Get the desired background color before modifying kwargs
        self.default_bg = kwargs.get('bg', '#4a90e2')
        self.default_fg = kwargs.get('fg', 'white')
        self.hover_bg = self.lighten_color(self.default_bg)

        # Set all color states explicitly to prevent system defaults
        kwargs['fg'] = self.default_fg
        kwargs['bg'] = self.default_bg
        kwargs['activeforeground'] = self.default_fg
        kwargs['activebackground'] = self.default_bg  # Same as bg when clicked
        kwargs['highlightthickness'] = 0  # Remove focus border
        kwargs['borderwidth'] = 0  # Remove border

        super().__init__(parent, **kwargs)

        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def lighten_color(self, hex_color):
        """Lighten a hex color by 20%"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'

    def on_enter(self, e):
        self.config(bg=self.hover_bg, activebackground=self.hover_bg)

    def on_leave(self, e):
        self.config(bg=self.default_bg, activebackground=self.default_bg)

class BedLevelEditorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Level Editor Pro - Elegoo OrangeStorm Giga")
        self.root.geometry("1680x980")

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
        self.root.bind('<Control-z>', lambda e: self.reset_mesh_data())
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

        # ========== CONTENT AREA ==========
        content_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Left: Visualization
        left_frame = tk.Frame(content_frame, bg=self.colors['bg_dark'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.create_visualization_panel(left_frame)

        # Right: Control Panel
        right_frame = tk.Frame(content_frame, bg=self.colors['bg_dark'], width=380)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        right_frame.pack_propagate(False)

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
        value_entry.pack(pady=(0, 8), ipady=8)
        value_entry.bind('<Return>', lambda e: self.update_selection_value())

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

    def update_selection_value(self):
        """Update the selected point or region value"""
        try:
            new_value = float(self.value_var.get())

            if self.region_mode and self.selected_region:
                for (y, x) in self.selected_region:
                    self.mesh_data[y, x] = new_value
                self.update_status(f"Updated {len(self.selected_region)} points to {new_value:.4f}mm",
                                 self.colors['accent_green'])
            elif self.selected_point is not None:
                y, x = self.selected_point
                self.mesh_data[y, x] = new_value
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
            messagebox.showerror("Error", "Invalid value entered")
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

        avg = np.mean([self.mesh_data[y, x] for y, x in self.selected_region])
        for (y, x) in self.selected_region:
            self.mesh_data[y, x] = avg

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
            self.mesh_data[y, x] = smoothed[y, x]

        self.is_modified = True
        self.update_plot()
        self.update_statistics()
        self.update_status(f"Smoothed {len(self.selected_region)} points", self.colors['accent_green'])
        messagebox.showinfo("Success", f"Smoothed {len(self.selected_region)} points")

    def update_statistics(self):
        """Update statistics display"""
        if self.mesh_data is None:
            return

        range_val = np.max(self.mesh_data) - np.min(self.mesh_data)

        stats = f"""
╔════════════════════════════════╗
║      MESH STATISTICS           ║
╠════════════════════════════════╣
  Points:     {self.x_count} × {self.y_count} = {self.x_count * self.y_count}

  Min:        {np.min(self.mesh_data):.6f} mm
  Max:        {np.max(self.mesh_data):.6f} mm
  Range:      {range_val:.6f} mm

  Mean:       {np.mean(self.mesh_data):.6f} mm
  Std Dev:    {np.std(self.mesh_data):.6f} mm
╚════════════════════════════════╝
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
