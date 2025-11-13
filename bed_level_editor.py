#!/usr/bin/env python3
"""
Bed Level Editor for Elegoo OrangeStorm Giga
Allows visual editing of bed mesh points in printer.cfg
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import re
import os

class BedLevelEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Level Editor - Elegoo OrangeStorm Giga")
        self.root.geometry("1200x800")

        self.config_file = "/home/user/BedLevel/printer.cfg"
        self.mesh_data = None
        self.original_mesh_data = None
        self.x_count = 10
        self.y_count = 10
        self.selected_point = None
        self.mesh_min = (16, 10)
        self.mesh_max = (786, 767)

        # Color scheme
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.highlight_color = "#4a90e2"

        self.setup_ui()
        self.load_mesh_data()

    def setup_ui(self):
        """Setup the user interface"""
        # Configure root
        self.root.configure(bg=self.bg_color)

        # Top frame for controls
        control_frame = tk.Frame(self.root, bg=self.bg_color, padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # File info
        tk.Label(control_frame, text="Config File:", bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text=self.config_file, bg=self.bg_color, fg=self.highlight_color,
                font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = tk.Frame(control_frame, bg=self.bg_color)
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="Load", command=self.load_mesh_data,
                 bg=self.highlight_color, fg=self.fg_color, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Save", command=self.save_mesh_data,
                 bg="#27ae60", fg=self.fg_color, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Reset", command=self.reset_mesh_data,
                 bg="#e74c3c", fg=self.fg_color, padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        # Main content frame
        content_frame = tk.Frame(self.root, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Heatmap
        left_panel = tk.Frame(content_frame, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_panel, text="Bed Mesh Visualization (Click to Select Point)",
                bg=self.bg_color, fg=self.fg_color, font=("Arial", 11, "bold")).pack(pady=5)

        # Matplotlib figure
        self.fig = Figure(figsize=(8, 7), facecolor=self.bg_color)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=left_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        # Right panel - Controls
        right_panel = tk.Frame(content_frame, bg=self.bg_color, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        # Point info
        info_frame = tk.LabelFrame(right_panel, text="Selected Point", bg=self.bg_color,
                                   fg=self.fg_color, font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, pady=10)

        self.point_label = tk.Label(info_frame, text="No point selected", bg=self.bg_color,
                                    fg=self.fg_color, font=("Arial", 10))
        self.point_label.pack(pady=5)

        self.coord_label = tk.Label(info_frame, text="", bg=self.bg_color,
                                    fg=self.highlight_color, font=("Arial", 9))
        self.coord_label.pack(pady=2)

        # Value adjustment
        adjust_frame = tk.LabelFrame(right_panel, text="Adjust Value", bg=self.bg_color,
                                    fg=self.fg_color, font=("Arial", 10, "bold"))
        adjust_frame.pack(fill=tk.X, pady=10)

        tk.Label(adjust_frame, text="Current Z-Offset:", bg=self.bg_color,
                fg=self.fg_color).pack(pady=5)

        self.value_var = tk.StringVar(value="0.000")
        value_entry = tk.Entry(adjust_frame, textvariable=self.value_var,
                              font=("Arial", 12), justify=tk.CENTER, width=15)
        value_entry.pack(pady=5)
        value_entry.bind('<Return>', lambda e: self.update_point_value())

        # Slider for fine adjustment
        tk.Label(adjust_frame, text="Fine Adjustment (±0.5mm):", bg=self.bg_color,
                fg=self.fg_color, font=("Arial", 9)).pack(pady=(10, 5))

        self.slider_var = tk.DoubleVar(value=0)
        slider = tk.Scale(adjust_frame, from_=-0.5, to=0.5, resolution=0.001,
                         orient=tk.HORIZONTAL, variable=self.slider_var,
                         command=self.on_slider_change, bg=self.bg_color,
                         fg=self.fg_color, highlightbackground=self.bg_color,
                         troughcolor=self.highlight_color, length=250)
        slider.pack(pady=5)

        # Quick adjustment buttons
        quick_frame = tk.Frame(adjust_frame, bg=self.bg_color)
        quick_frame.pack(pady=10)

        adjustments = [("++", 0.1), ("+", 0.01), ("-", -0.01), ("--", -0.1)]
        for label, value in adjustments:
            tk.Button(quick_frame, text=label, command=lambda v=value: self.quick_adjust(v),
                     bg=self.highlight_color, fg=self.fg_color, width=4, pady=2).pack(side=tk.LEFT, padx=2)

        tk.Button(adjust_frame, text="Update Point", command=self.update_point_value,
                 bg="#27ae60", fg=self.fg_color, padx=20, pady=8, font=("Arial", 10, "bold")).pack(pady=10)

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

    def load_mesh_data(self):
        """Load mesh data from printer.cfg"""
        try:
            if not os.path.exists(self.config_file):
                messagebox.showerror("Error", f"Config file not found: {self.config_file}")
                return

            with open(self.config_file, 'r') as f:
                content = f.read()

            # Find the bed_mesh section
            mesh_match = re.search(r'\[bed_mesh default\].*?points =\s*(.*?)(?=\n#\*#|\nz_count|$)',
                                  content, re.DOTALL)

            if not mesh_match:
                messagebox.showerror("Error", "Could not find bed_mesh default section")
                return

            points_text = mesh_match.group(1)

            # Extract all points
            points = []
            for line in points_text.split('\n'):
                line = line.strip()
                if line.startswith('#*#') and ',' in line:
                    # Remove the #*# prefix and split by comma
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

            if x_count_match:
                self.x_count = int(x_count_match.group(1))
            if y_count_match:
                self.y_count = int(y_count_match.group(1))

            self.update_plot()
            self.update_statistics()
            messagebox.showinfo("Success", f"Loaded {self.x_count}x{self.y_count} mesh ({self.x_count * self.y_count} points)")

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

            # Find the bed_mesh points section
            mesh_pattern = r'(\[bed_mesh default\].*?points =\s*).*?(?=#\*#\s*x_count)'

            # Generate new points string
            points_str = ""
            for row in self.mesh_data:
                points_str += "#*# \t  "
                points_str += ", ".join([f"{val:.6f}" for val in row])
                points_str += "\n"

            # Replace the points section
            new_content = re.sub(mesh_pattern, r'\1\n' + points_str, content, flags=re.DOTALL)

            # Backup original file
            backup_file = self.config_file + ".backup"
            with open(backup_file, 'w') as f:
                f.write(content)

            # Write new content
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
            self.update_plot()
            self.update_statistics()
            messagebox.showinfo("Reset", "Mesh data reset to original values")

    def update_plot(self):
        """Update the heatmap visualization"""
        if self.mesh_data is None:
            return

        self.ax.clear()

        # Create heatmap
        im = self.ax.imshow(self.mesh_data, cmap='RdYlGn_r', aspect='auto', interpolation='bilinear')

        # Add colorbar
        if hasattr(self, 'cbar'):
            self.cbar.remove()
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

        # Highlight selected point
        if self.selected_point is not None:
            y, x = self.selected_point
            self.ax.plot(x, y, 'w*', markersize=20, markeredgecolor='black', markeredgewidth=2)

        # Style
        self.ax.tick_params(colors='white')
        self.fig.patch.set_facecolor(self.bg_color)
        self.ax.set_facecolor('#1a1a1a')

        self.canvas.draw()

    def on_click(self, event):
        """Handle click on heatmap"""
        if event.inaxes != self.ax or self.mesh_data is None:
            return

        x = int(round(event.xdata))
        y = int(round(event.ydata))

        if 0 <= x < self.x_count and 0 <= y < self.y_count:
            self.selected_point = (y, x)
            value = self.mesh_data[y, x]

            self.value_var.set(f"{value:.6f}")
            self.slider_var.set(0)

            # Calculate approximate physical coordinates
            x_phys = self.mesh_min[0] + (x / (self.x_count - 1)) * (self.mesh_max[0] - self.mesh_min[0])
            y_phys = self.mesh_min[1] + (y / (self.y_count - 1)) * (self.mesh_max[1] - self.mesh_min[1])

            self.point_label.config(text=f"Point [{x}, {y}]")
            self.coord_label.config(text=f"~X:{x_phys:.1f} Y:{y_phys:.1f} Z:{value:.3f}")

            self.update_plot()

    def on_slider_change(self, value):
        """Handle slider change"""
        if self.selected_point is None:
            return

        y, x = self.selected_point
        base_value = self.mesh_data[y, x] - self.slider_var.get()
        new_value = base_value + float(value)
        self.value_var.set(f"{new_value:.6f}")

    def quick_adjust(self, delta):
        """Quick adjustment buttons"""
        if self.selected_point is None:
            messagebox.showwarning("Warning", "Please select a point first")
            return

        try:
            current = float(self.value_var.get())
            new_value = current + delta
            self.value_var.set(f"{new_value:.6f}")
            self.update_point_value()
        except ValueError:
            pass

    def update_point_value(self):
        """Update the selected point value"""
        if self.selected_point is None:
            messagebox.showwarning("Warning", "Please select a point first")
            return

        try:
            new_value = float(self.value_var.get())
            y, x = self.selected_point
            self.mesh_data[y, x] = new_value
            self.slider_var.set(0)
            self.update_plot()
            self.update_statistics()
        except ValueError:
            messagebox.showerror("Error", "Invalid value entered")

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
    app = BedLevelEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
