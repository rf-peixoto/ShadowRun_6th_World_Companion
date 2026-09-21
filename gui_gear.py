"""Gear tab: weapons, armor, cyberware, bioware, magic items, electronics,
medkits, and misc gear.

A "Gear Summary" strip at the top shows the numbers this gear actually
produces (Armor Rating, Weapon Accuracy, remaining Essence) so a player can
see the effect of a purchase without flipping to the Combat Stats tab.
"""

import tkinter as tk
from tkinter import ttk

from character import ShadowrunCharacter
import theme
from dialogs import EditGearDialog, DescriptionViewer

EQUIPPABLE_CATEGORIES = ("Weapons", "Armor")


class GearTabMixin:
    def setup_gear_tab(self):
        tab = self.tabs["Gear"]

        summary = ttk.LabelFrame(tab, text="Gear Summary")
        summary.pack(fill=tk.X, padx=10, pady=(5, 0))
        self.gear_summary_labels = {}
        for i, key in enumerate(["Armor Rating", "Weapon Accuracy", "Essence Remaining", "Gear Value"]):
            ttk.Label(summary, text=f"{key}:").grid(row=0, column=i * 2, sticky=tk.W, padx=(10, 2), pady=5)
            lbl = ttk.Label(summary, text="0", font=("Arial", 10, "bold"), foreground=theme.ACCENT)
            lbl.grid(row=0, column=i * 2 + 1, sticky=tk.W, padx=(0, 10), pady=5)
            self.gear_summary_labels[key] = lbl

        notebook = ttk.Notebook(tab)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.gear_frames = {}
        for category in ShadowrunCharacter.GEAR_CATEGORIES:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=category)
            self.gear_frames[category] = frame

            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X, padx=5, pady=5)

            ttk.Button(btn_frame, text=f"Add {category[:-1]}",
                       command=lambda c=category: self.add_gear_item(c)).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Edit Selected",
                       command=lambda c=category: self.edit_gear_item(c)).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Remove Selected",
                       command=lambda c=category: self.remove_gear_item(c)).pack(side=tk.LEFT, padx=2)

            list_frame = ttk.Frame(frame)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            tree = ttk.Treeview(list_frame, columns=("Details",), show="tree", height=10)
            tree.heading("#0", text="Item")
            tree.column("#0", width=200)
            tree.heading("Details", text="Details")
            tree.pack(fill=tk.BOTH, expand=True)

            tree.bind("<Double-1>", lambda e, c=category: self.edit_gear_item(c))
            tree.bind("<<TreeviewSelect>>", lambda e, c=category: self.show_gear_description(c))

            setattr(self, f"{category.lower()}_tree", tree)

    def _gear_tree(self, category):
        return getattr(self, f"{category.lower()}_tree")

    def _format_gear_details(self, item):
        attrs = [f"{k}: {v}" for k, v in item.items() if k not in ("name", "description")]
        return "; ".join(attrs)

    def _gear_item_label(self, category, item):
        name = item.get("name", "Unknown")
        if category in EQUIPPABLE_CATEGORIES:
            equipped = str(item.get("Equipped", "Yes")).strip().lower() != "no"
            return f"{name}" + ("" if equipped else "  (stored)")
        return name

    def update_gear_summary(self):
        if not hasattr(self, "gear_summary_labels"):
            return
        c = self.character
        total_value = 0.0
        for category in ShadowrunCharacter.GEAR_CATEGORIES:
            for item in c.gear[category]:
                try:
                    qty = float(item.get("Quantity", 1) or 1)
                except (TypeError, ValueError):
                    qty = 1
                try:
                    total_value += float(item.get("Price", 0) or 0) * qty
                except (TypeError, ValueError):
                    pass
        self.gear_summary_labels["Armor Rating"].config(text=str(c.armor_rating))
        self.gear_summary_labels["Weapon Accuracy"].config(text=str(c.weapon_accuracy))
        self.gear_summary_labels["Essence Remaining"].config(text=str(c.attributes.get("Essence", 6.0)))
        self.gear_summary_labels["Gear Value"].config(text=f"{int(total_value)}¥")

    def show_gear_description(self, category):
        tree = self._gear_tree(category)
        selected = tree.selection()
        if not selected:
            return
        index = tree.index(selected[0])
        item = self.character.gear[category][index]
        content = f"Name: {item.get('name', '')}\n\n"
        content += f"Description: {item.get('description', '')}\n\n"
        content += "Attributes:\n"
        for key, value in item.items():
            if key not in ("name", "description"):
                content += f"  {key}: {value}\n"
        DescriptionViewer(self.root, "Gear Description", content)

    def add_gear_item(self, category):
        dialog = EditGearDialog(self.root, category)
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.add_gear(category, dialog.result)
        tree = self._gear_tree(category)
        tree.insert("", "end", text=self._gear_item_label(category, dialog.result),
                   values=(self._format_gear_details(dialog.result),))
        self.on_character_changed()

    def edit_gear_item(self, category):
        tree = self._gear_tree(category)
        selected = tree.selection()
        if not selected:
            return
        item_id = selected[0]
        item_index = tree.index(item_id)
        gear_item = self.character.gear[category][item_index]

        dialog = EditGearDialog(self.root, category, gear_item)
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.update_gear(category, item_index, dialog.result)
        tree.item(item_id, text=self._gear_item_label(category, dialog.result),
                 values=(self._format_gear_details(dialog.result),))
        self.on_character_changed()

    def remove_gear_item(self, category):
        tree = self._gear_tree(category)
        selected = tree.selection()
        if not selected:
            return
        item_id = selected[0]
        item_index = tree.index(item_id)
        self.character.remove_gear(category, item_index)
        tree.delete(item_id)
        self.on_character_changed()

    def refresh_gear(self):
        for category in ShadowrunCharacter.GEAR_CATEGORIES:
            tree = self._gear_tree(category)
            for item in tree.get_children():
                tree.delete(item)
            for item in self.character.gear[category]:
                tree.insert("", "end", text=self._gear_item_label(category, item),
                           values=(self._format_gear_details(item),))
        self.update_gear_summary()
