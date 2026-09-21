"""Matrix tab: a simple grid for sketching out hosts/nodes/ICE during a run.

Bug fixed here: "Save Matrix" used ``json.dump(self.character.matrix_grid, f)``
directly, but the grid's keys are ``(x, y)`` tuples -- JSON object keys must be
strings, so this raised a ``TypeError`` (or worse, quietly serialized wrong)
every single time. Now converts to/from ``"x,y"`` string keys, the same
convention used by the character's own save format.
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from character import ShadowrunCharacter


class MatrixTabMixin:
    MATRIX_COLORS = {
        "Player": "#4F9BFF", "Enemy": "#F44336", "Device": "#FFEB3B",
        "Barrier": "#000000", "Data": "#4CAF50", "IC": "#FF9800",
        "Node": "#9C27B0", "Host": "#00BCD4"
    }

    def setup_matrix_tab(self):
        tab = self.tabs["Matrix"]

        left_frame = ttk.Frame(tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=5)
        right_frame = ttk.Frame(tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        element_frame = ttk.LabelFrame(left_frame, text="Matrix Elements")
        element_frame.pack(fill=tk.X, padx=5, pady=5)

        self.selected_element = tk.StringVar(value="Player")
        for element in ShadowrunCharacter.MATRIX_ICONS:
            ttk.Radiobutton(element_frame, text=element, variable=self.selected_element,
                           value=element).pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(element_frame, text="Label:").pack(anchor=tk.W, padx=5, pady=2)
        self.element_label_entry = ttk.Entry(element_frame, width=20)
        self.element_label_entry.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(
            element_frame,
            text="Click an empty cell to place a marker.\nDrag an existing marker to move it.\nRight-click a marker to delete it.",
            justify=tk.LEFT, wraplength=180
        ).pack(anchor=tk.W, padx=5, pady=(6, 2))

        ctrl_frame = ttk.LabelFrame(left_frame, text="Controls")
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="Clear Matrix", command=self.clear_matrix).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(ctrl_frame, text="Save Matrix", command=self.save_matrix).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(ctrl_frame, text="Load Matrix", command=self.load_matrix).pack(fill=tk.X, padx=5, pady=2)

        grid_frame = ttk.LabelFrame(right_frame, text="Matrix Grid")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.matrix_canvas = tk.Canvas(grid_frame, bg="#1c1c1c", width=600, height=400)
        self.matrix_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.matrix_canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(grid_frame, orient=tk.HORIZONTAL, command=self.matrix_canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.matrix_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._drag_origin = None
        self.matrix_canvas.bind("<ButtonPress-1>", self.canvas_press)
        self.matrix_canvas.bind("<B1-Motion>", self.canvas_drag)
        self.matrix_canvas.bind("<ButtonRelease-1>", self.canvas_release)
        self.matrix_canvas.bind("<Button-3>", self.canvas_right_click)
        self.draw_matrix_grid()

    def draw_matrix_grid(self):
        canvas = self.matrix_canvas
        canvas.delete("all")

        cell_size = 50
        for i in range(0, 601, cell_size):
            canvas.create_line(i, 0, i, 400, fill="#333")
        for j in range(0, 401, cell_size):
            canvas.create_line(0, j, 600, j, fill="#333")

        for (x, y), element in self.character.matrix_grid.items():
            self.draw_matrix_element(x, y, element["type"], element.get("label", ""))

    def draw_matrix_element(self, x, y, element_type, label=""):
        size = 40
        x_pixel = x * 50 + 5
        y_pixel = y * 50 + 5
        self.matrix_canvas.create_oval(x_pixel, y_pixel, x_pixel + size, y_pixel + size,
                                       fill=self.MATRIX_COLORS.get(element_type, "#888"), outline="#666")
        self.matrix_canvas.create_text(x_pixel + size / 2, y_pixel + size / 2,
                                       text=label or element_type[0], fill="white", font=("Arial", 10, "bold"))

    def canvas_press(self, event):
        """Left-click: place a new marker on an empty cell, or -- if the
        cell already has one -- pick it up so canvas_drag/canvas_release can
        move it instead of stacking a duplicate on top."""
        cell_size = 50
        x = event.x // cell_size
        y = event.y // cell_size
        if self.character.get_matrix_element(x, y):
            self._drag_origin = (x, y)
        else:
            self._drag_origin = None
            element_type = self.selected_element.get()
            label = self.element_label_entry.get().strip()
            self.character.add_matrix_element(x, y, element_type, label)
            self.draw_matrix_grid()

    def canvas_drag(self, event):
        """While dragging an existing marker, redraw the grid and show the
        marker following the cursor as a floating preview; the model isn't
        updated until the mouse button is released."""
        if not self._drag_origin:
            return
        element = self.character.get_matrix_element(*self._drag_origin)
        if not element:
            return
        self.draw_matrix_grid()
        size = 40
        x_pixel = event.x - size / 2
        y_pixel = event.y - size / 2
        self.matrix_canvas.create_oval(x_pixel, y_pixel, x_pixel + size, y_pixel + size,
                                       fill=self.MATRIX_COLORS.get(element["type"], "#888"),
                                       outline="#FFFFFF", width=2)
        self.matrix_canvas.create_text(event.x, event.y, text=element.get("label") or element["type"][0],
                                       fill="white", font=("Arial", 10, "bold"))

    def canvas_release(self, event):
        origin = self._drag_origin
        self._drag_origin = None
        if not origin:
            return
        cell_size = 50
        new_x = max(0, event.x // cell_size)
        new_y = max(0, event.y // cell_size)
        if (new_x, new_y) != origin:
            element = self.character.matrix_grid.pop(origin, None)
            if element is not None:
                # Dropping onto an occupied cell replaces whatever was there.
                self.character.matrix_grid[(new_x, new_y)] = element
        self.draw_matrix_grid()

    def canvas_right_click(self, event):
        cell_size = 50
        x = event.x // cell_size
        y = event.y // cell_size
        if self.character.get_matrix_element(x, y):
            self.character.remove_matrix_element(x, y)
            self.draw_matrix_grid()

    def clear_matrix(self):
        self.character.clear_matrix()
        self.draw_matrix_grid()

    def save_matrix(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        serializable = {f"{x},{y}": v for (x, y), v in self.character.matrix_grid.items()}
        try:
            with open(file_path, "w") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save matrix: {e}")

    def load_matrix(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                raw = json.load(f)
            self.character.matrix_grid = {}
            for key, value in raw.items():
                x_str, y_str = key.split(",", 1)
                self.character.matrix_grid[(int(x_str), int(y_str))] = value
            self.draw_matrix_grid()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load matrix: {e}")

    def refresh_matrix(self):
        self.draw_matrix_grid()
