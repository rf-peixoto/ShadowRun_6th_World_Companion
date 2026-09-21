"""Basic Info tab: character identity and attributes.

Bug fixed here: "Trade Karma for Nuyen" called ``tk.simpledialog.askinteger``
without ever importing ``tkinter.simpledialog`` -- it crashed with an
AttributeError every time you clicked the button. Fixed by importing it
properly.

The portrait editor used to live on this tab, but a non-square source image
made the "Portrait" LabelFrame grow to match the image's actual (non-square)
pixel dimensions, which pushed and clipped the Name/Metatype/Role/etc. grid
next to it -- effectively breaking this screen's layout. It now lives on the
Background tab (gui_social.py) instead, where it has its own row, and
character.py forces every portrait to a square crop so the display box is
always a fixed, predictable size regardless of the source photo.
"""

import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from character import ShadowrunCharacter
import theme


class BasicInfoTabMixin:
    def setup_basic_info_tab(self):
        tab = self.tabs["Basic Info"]
        notebook = ttk.Notebook(tab)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        char_frame = ttk.Frame(notebook)
        notebook.add(char_frame, text="Character Info")

        ttk.Label(char_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_entry = ttk.Entry(char_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        self.name_entry.bind("<FocusOut>", self.on_character_changed)

        ttk.Label(char_frame, text="Metatype:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.metatype_combo = ttk.Combobox(char_frame, values=ShadowrunCharacter.METATYPES, state="readonly", width=15)
        self.metatype_combo.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        self.metatype_combo.bind("<<ComboboxSelected>>", self.on_character_changed)

        ttk.Label(char_frame, text="Role:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.role_combo = ttk.Combobox(char_frame, values=list(ShadowrunCharacter.ROLES.keys()), state="readonly", width=15)
        self.role_combo.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        self.role_combo.bind("<<ComboboxSelected>>", self.on_character_changed)

        ttk.Label(char_frame, text="Magic/Resonance:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.magic_combo = ttk.Combobox(char_frame, values=ShadowrunCharacter.MAGIC_TYPES, state="readonly", width=15)
        self.magic_combo.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        self.magic_combo.bind("<<ComboboxSelected>>", self.on_character_changed)

        ttk.Label(char_frame, text="Tradition/Mentor:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.tradition_combo = ttk.Combobox(char_frame, values=ShadowrunCharacter.TRADITIONS, state="readonly", width=15)
        self.tradition_combo.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
        self.tradition_combo.bind("<<ComboboxSelected>>", self.on_character_changed)

        ttk.Label(char_frame, text="Initiation Grade:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.init_grade_spin = ttk.Spinbox(char_frame, from_=0, to=10, width=5)
        self.init_grade_spin.grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)
        self.init_grade_spin.bind("<FocusOut>", self.on_character_changed)

        ttk.Label(char_frame, text="Lifestyle:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.lifestyle_combo = ttk.Combobox(char_frame, values=ShadowrunCharacter.LIFESTYLES, state="readonly", width=15)
        self.lifestyle_combo.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
        self.lifestyle_combo.bind("<<ComboboxSelected>>", self.update_lifestyle_nuyen)

        ttk.Label(char_frame, text="Karma:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.karma_spin = ttk.Spinbox(char_frame, from_=0, to=1000, width=5)
        self.karma_spin.grid(row=3, column=3, padx=5, pady=2, sticky=tk.W)
        self.karma_spin.bind("<FocusOut>", self.on_character_changed)

        ttk.Label(char_frame, text="Nuyen:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.nuyen_entry = ttk.Entry(char_frame, width=15)
        self.nuyen_entry.grid(row=4, column=1, padx=5, pady=2, sticky=tk.W)
        self.nuyen_entry.bind("<FocusOut>", self.on_character_changed)

        ttk.Button(char_frame, text="Trade Karma for Nuyen",
                   command=self.trade_karma_for_nuyen).grid(row=4, column=2, padx=5, pady=2, sticky=tk.W)
        ttk.Label(char_frame, text="1 Karma = 2000¥").grid(row=4, column=3, padx=5, pady=2, sticky=tk.W)

        # Quick Stats: the numbers a player checks constantly during a
        # session, visible without leaving the tab you're already on instead
        # of only living on the Combat Stats tab.
        quick_frame = ttk.LabelFrame(char_frame, text="Quick Stats")
        quick_frame.grid(row=5, column=0, columnspan=5, sticky="ew", padx=5, pady=(15, 5))
        self.quick_stat_labels = {}
        quick_stats = ["Physical Boxes", "Stun Boxes", "Initiative", "Armor", "Edge", "Essence"]
        for i, key in enumerate(quick_stats):
            ttk.Label(quick_frame, text=f"{key}:").grid(row=0, column=i * 2, sticky=tk.W, padx=(10, 2), pady=6)
            lbl = ttk.Label(quick_frame, text="-", font=("Arial", 10, "bold"), foreground=theme.ACCENT)
            lbl.grid(row=0, column=i * 2 + 1, sticky=tk.W, padx=(0, 10), pady=6)
            self.quick_stat_labels[key] = lbl

        attr_frame = ttk.Frame(notebook)
        notebook.add(attr_frame, text="Attributes")

        self.attribute_vars = {}
        self.attribute_entries = {}
        row = 0
        for i, attr in enumerate(ShadowrunCharacter.ATTRIBUTES):
            row = i // 3
            col = (i % 3) * 4

            ttk.Label(attr_frame, text=f"{attr}:").grid(row=row, column=col, sticky=tk.W, padx=15, pady=5)

            var = tk.StringVar()
            if attr == "Essence":
                entry = ttk.Entry(attr_frame, width=6, textvariable=var, state="readonly")
            else:
                entry = ttk.Spinbox(attr_frame, from_=1, to=10, width=5, textvariable=var)
                entry.bind("<FocusOut>", self.on_character_changed)

            entry.grid(row=row, column=col + 1, padx=(0, 15), pady=5, sticky=tk.W)
            self.attribute_vars[attr] = var
            self.attribute_entries[attr] = entry

            bonus_label = ttk.Label(attr_frame, text="", foreground=theme.ACCENT)
            bonus_label.grid(row=row, column=col + 2, padx=(0, 10), pady=5, sticky=tk.W)
            setattr(self, f"{attr.lower()}_bonus_label", bonus_label)

            if attr not in ("Edge", "Essence"):
                btn = ttk.Button(attr_frame, text="+", width=2,
                                  command=lambda a=attr: self.increase_attribute(a))
                btn.grid(row=row, column=col + 3, padx=5, pady=5, sticky=tk.W)

        ttk.Button(attr_frame, text="Auto Roll Attributes", command=self.autoroll_attributes).grid(
            row=row + 1, column=0, columnspan=12, pady=15
        )

    # -- Actions ----------------------------------------------------------

    def trade_karma_for_nuyen(self):
        try:
            amount = simpledialog.askinteger(
                "Trade Karma", "How much Karma to trade? (1 Karma = 2000¥)",
                parent=self.root, minvalue=1, maxvalue=max(1, self.character.karma)
            )
        except tk.TclError:
            return
        if not amount:
            return
        if self.character.trade_karma_for_nuyen(amount):
            self.refresh_all()
            messagebox.showinfo("Trade Complete", f"Traded {amount} Karma for {amount * 2000}¥")
        else:
            messagebox.showerror("Error", "Not enough Karma!")

    def increase_attribute(self, attribute):
        self.commit_basic_info()
        current_rating = self.character.base_attributes[attribute]
        karma_cost = (current_rating + 1) * 5
        if self.character.karma < karma_cost:
            messagebox.showerror("Error", f"Not enough Karma! Cost: {karma_cost} Karma")
            return
        if self.character.increase_attribute(attribute):
            self.refresh_all()
            messagebox.showinfo("Attribute Increased",
                                 f"Increased {attribute} to {current_rating + 1} for {karma_cost} Karma")
        else:
            messagebox.showerror("Error", "Failed to increase attribute!")

    def autoroll_attributes(self):
        metatype = self.character.metatype
        base_attrs = {}
        for attr in ShadowrunCharacter.ATTRIBUTES:
            if attr in ("Essence", "Magic", "Resonance"):
                continue
            base_attrs[attr] = random.randint(1, 6)

        if metatype == "Dwarf":
            base_attrs["Body"] = max(3, base_attrs["Body"])
            base_attrs["Willpower"] = max(3, base_attrs["Willpower"])
        elif metatype == "Elf":
            base_attrs["Agility"] = max(2, base_attrs["Agility"])
            base_attrs["Charisma"] = max(3, base_attrs["Charisma"])
        elif metatype == "Ork":
            base_attrs["Body"] = max(3, base_attrs["Body"])
            base_attrs["Strength"] = max(3, base_attrs["Strength"])
        elif metatype == "Troll":
            base_attrs["Body"] = max(5, base_attrs["Body"])
            base_attrs["Strength"] = max(5, base_attrs["Strength"])
            base_attrs["Logic"] = min(5, base_attrs["Logic"])

        self.character.base_attributes.update(base_attrs)
        self.refresh_all()

    def update_lifestyle_nuyen(self, event=None):
        lifestyle = self.lifestyle_combo.get()
        if lifestyle:
            nuyen = ShadowrunCharacter.LIFESTYLE_NUYEN.get(lifestyle, 5000)
            self.nuyen_entry.delete(0, tk.END)
            self.nuyen_entry.insert(0, str(nuyen))
            self.on_character_changed()

    # -- Sync with model ----------------------------------------------------

    def commit_basic_info(self):
        """Write the current widget values into the character object."""
        self.character.name = self.name_entry.get()
        self.character.metatype = self.metatype_combo.get()
        self.character.role = self.role_combo.get()
        self.character.magic_type = self.magic_combo.get()
        self.character.tradition = self.tradition_combo.get()
        self.character.lifestyle = self.lifestyle_combo.get()

        try:
            self.character.initiation_grade = int(self.init_grade_spin.get() or "0")
        except ValueError:
            pass
        try:
            self.character.karma = int(self.karma_spin.get() or "0")
        except ValueError:
            pass
        try:
            self.character.nuyen = int(self.nuyen_entry.get() or "0")
        except ValueError:
            pass

        for attr in ShadowrunCharacter.ATTRIBUTES:
            if attr == "Essence":
                continue
            try:
                self.character.base_attributes[attr] = int(self.attribute_vars[attr].get())
            except (ValueError, tk.TclError):
                pass

    def refresh_basic_info(self):
        c = self.character
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, c.name)
        self.metatype_combo.set(c.metatype)
        self.role_combo.set(c.role)
        self.magic_combo.set(c.magic_type)
        self.tradition_combo.set(c.tradition)
        self.init_grade_spin.delete(0, tk.END)
        self.init_grade_spin.insert(0, str(c.initiation_grade))
        self.lifestyle_combo.set(c.lifestyle)
        self.karma_spin.delete(0, tk.END)
        self.karma_spin.insert(0, str(c.karma))
        self.nuyen_entry.delete(0, tk.END)
        self.nuyen_entry.insert(0, str(c.nuyen))

        for attr in ShadowrunCharacter.ATTRIBUTES:
            if attr == "Essence":
                self.attribute_vars[attr].set(str(c.attributes["Essence"]))
            else:
                self.attribute_vars[attr].set(str(c.base_attributes[attr]))

            bonus = c.attributes[attr] - c.base_attributes[attr]
            bonus_label = getattr(self, f"{attr.lower()}_bonus_label")
            if attr != "Essence" and bonus != 0:
                bonus_text = f"+{bonus}" if bonus > 0 else str(bonus)
                bonus_label.config(text=bonus_text, foreground=theme.BAD if bonus < 0 else theme.ACCENT)
            else:
                bonus_label.config(text="")

        self.refresh_quick_stats()

    def refresh_quick_stats(self):
        if not hasattr(self, "quick_stat_labels"):
            return
        c = self.character
        values = {
            "Physical Boxes": f"{c.physical_damage}/{c.physical_boxes}",
            "Stun Boxes": f"{c.stun_damage}/{c.stun_boxes}",
            "Initiative": f"{c.initiative_score} + {c.initiative_dice}d6",
            "Armor": str(c.armor_rating),
            "Edge": f"{c.current_edge}/{c.attributes['Edge']}",
            "Essence": str(c.attributes["Essence"]),
        }
        for key, text in values.items():
            self.quick_stat_labels[key].config(text=text)
