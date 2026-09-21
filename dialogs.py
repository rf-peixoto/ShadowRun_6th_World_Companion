"""Shared Toplevel dialogs used across tabs."""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from character import ShadowrunCharacter
import theme


class DescriptionViewer(tk.Toplevel):
    """Read-only popup for showing an item's full description."""

    def __init__(self, parent, title, content):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.configure(bg=theme.BG)

        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text_area = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD, bg=theme.ENTRY_BG, fg=theme.FG, font=("Arial", 10)
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.text_area.insert(tk.END, content)
        self.text_area.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack()


class EditGearDialog(tk.Toplevel):
    """Add/edit dialog for gear, spells, powers, and foci alike."""

    GEAR_ATTRIBUTES = {
        "Weapons": ["Damage", "Accuracy", "AP", "Mode", "RC", "Ammo", "Type", "Price"],
        "Armor": ["Rating", "Social", "Capacity", "Type", "Price"],
        "Cyberware": ["Essence Cost", "Capacity", "Rating", "Type", "Price"],
        "Bioware": ["Essence Cost", "Rating", "Capacity", "Type", "Price"],
        "Magic Items": ["Force", "Type", "Binding", "Price"],
        "Medkits": ["Rating", "Quantity", "Type", "Price"],
        "Electronics": ["Rating", "Capacity", "Function", "Price"],
        "Other": ["Effect", "Duration", "Potency", "Price"],
        "Spell": ["Type", "Drain", "Price"],
        "Power": ["Activation", "Effect", "Cost", "Price"],
        "Focus": ["Type", "Force", "Price"],
        "Complex Form": ["Target", "Fade", "Price"],
    }

    # Categories that get an "Equipped" checkbox: only equipped Armor/Weapons
    # count toward Armor Rating / Weapon Accuracy (see character.recalculate).
    EQUIPPABLE_CATEGORIES = ("Weapons", "Armor")

    GEAR_OPTIONS = {
        ("Weapons", "Type"): ShadowrunCharacter.WEAPON_TYPES,
        ("Armor", "Type"): ShadowrunCharacter.ARMOR_TYPES,
        ("Cyberware", "Type"): ShadowrunCharacter.CYBERWARE_TYPES,
        ("Medkits", "Type"): ShadowrunCharacter.MEDKIT_TYPES,
        ("Spell", "Type"): ["Combat", "Health", "Illusion", "Manipulation", "Ritual"],
        ("Power", "Activation"): ["Passive", "Simple Action", "Complex Action"],
        ("Focus", "Type"): ["Power", "Sustaining", "Weapon", "Spell", "Adept", "Binding"],
        ("Complex Form", "Target"): ["Device", "File", "Persona", "Sprite", "Self"],
    }

    PREDEFINED_SOURCES = {
        # Rituals are recorded the same way as Spells (same Add/Edit form,
        # same Karma-buy-off flow) -- just tagged Type "Ritual" -- so they're
        # offered from the same "Use Predefined" picker.
        "Spell": ShadowrunCharacter.PREDEFINED_SPELLS + ShadowrunCharacter.PREDEFINED_RITUALS,
        "Power": ShadowrunCharacter.PREDEFINED_POWERS,
        "Focus": ShadowrunCharacter.PREDEFINED_FOCI,
        "Weapons": ShadowrunCharacter.PREDEFINED_GEAR["Weapons"],
        "Armor": ShadowrunCharacter.PREDEFINED_GEAR["Armor"],
        "Cyberware": ShadowrunCharacter.PREDEFINED_GEAR["Cyberware"],
        "Bioware": ShadowrunCharacter.PREDEFINED_GEAR["Bioware"],
        "Magic Items": ShadowrunCharacter.PREDEFINED_GEAR["Magic Items"],
        "Electronics": ShadowrunCharacter.PREDEFINED_GEAR["Electronics"],
        "Medkits": ShadowrunCharacter.PREDEFINED_GEAR["Medkits"],
        "Other": ShadowrunCharacter.PREDEFINED_GEAR["Other"],
        "Complex Form": ShadowrunCharacter.PREDEFINED_COMPLEX_FORMS,
    }

    def __init__(self, parent, category, item=None):
        super().__init__(parent)
        self.parent = parent
        self.category = category
        self.item = item or {}
        self.result = None

        self.title(f"Edit {category}")
        self.geometry("420x520")
        self.configure(bg=theme.BG)
        self.resizable(True, True)

        self.create_widgets()
        self.grab_set()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_row = ttk.Frame(main_frame)
        top_row.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=5)

        if self.category in self.PREDEFINED_SOURCES:
            ttk.Button(top_row, text="Use Predefined", command=self.use_predefined).pack(side=tk.LEFT)

        # Equipped (Weapons/Armor) / Bonded (Focus) toggle -- feeds directly
        # into Armor Rating, Weapon Accuracy, or Magic in recalculate().
        self.equipped_var = None
        self.bonded_var = None
        if self.category in self.EQUIPPABLE_CATEGORIES:
            self.equipped_var = tk.BooleanVar(value=str(self.item.get("Equipped", "Yes")).lower() != "no")
            ttk.Checkbutton(top_row, text="Equipped (counts toward Armor/Accuracy)",
                            variable=self.equipped_var).pack(side=tk.LEFT, padx=10)
        elif self.category == "Focus":
            self.bonded_var = tk.BooleanVar(value=str(self.item.get("Bonded", "No")).lower() in ("yes", "true", "1"))
            ttk.Checkbutton(top_row, text="Bonded (Power Focus adds Force to Magic)",
                            variable=self.bonded_var).pack(side=tk.LEFT, padx=10)

        ttk.Label(main_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=30)
        self.name_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.name_entry.insert(0, self.item.get("name", ""))

        ttk.Label(main_frame, text="Description:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        self.desc_text = scrolledtext.ScrolledText(main_frame, width=30, height=4,
                                                    bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG)
        self.desc_text.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.desc_text.insert(tk.END, self.item.get("description", ""))

        row = 3
        self.attr_entries = {}
        for attr in self.GEAR_ATTRIBUTES.get(self.category, []):
            ttk.Label(main_frame, text=f"{attr}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

            options = self.GEAR_OPTIONS.get((self.category, attr))
            if options:
                entry = ttk.Combobox(main_frame, values=options, width=15)
                entry.set(self.item.get(attr, options[0] if options else ""))
            elif attr in ("Quantity", "Rating", "Force"):
                entry = ttk.Spinbox(main_frame, from_=1, to=100, width=15)
                entry.set(str(self.item.get(attr, "1")))
            else:
                entry = ttk.Entry(main_frame, width=15)
                entry.insert(0, str(self.item.get(attr, "")))

            entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            self.attr_entries[attr] = entry
            row += 1

        ttk.Label(main_frame, text="Custom Attributes:").grid(row=row, column=0, sticky=tk.NW, padx=5, pady=5)
        self.attr_text = scrolledtext.ScrolledText(main_frame, width=30, height=4,
                                                    bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG)
        self.attr_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        if self.item:
            custom_attrs = [
                f"{key}: {value}" for key, value in self.item.items()
                if key not in ("name", "description") and key not in self.GEAR_ATTRIBUTES.get(self.category, [])
            ]
            self.attr_text.insert(tk.END, "\n".join(custom_attrs))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def use_predefined(self):
        predefined = self.PREDEFINED_SOURCES.get(self.category)
        if not predefined:
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Select {self.category}")
        dialog.geometry("400x300")
        dialog.configure(bg=theme.BG)

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        listbox = tk.Listbox(list_frame, bg=theme.ENTRY_BG, fg=theme.FG, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for item in predefined:
            listbox.insert(tk.END, item["name"])

        def select_item():
            selected = listbox.curselection()
            if not selected:
                return
            item = predefined[selected[0]]
            # Predefined data (PREDEFINED_SPELLS/POWERS/FOCI) uses lowercase keys
            # ("type", "drain", ...) while the dialog's fields are capitalized
            # ("Type", "Drain", ...) to match GEAR_ATTRIBUTES -- match case
            # insensitively so predefined items actually populate the form.
            item_lower = {k.lower(): v for k, v in item.items()}

            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, item.get("name", ""))
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert(tk.END, item.get("description", ""))

            for attr, widget in self.attr_entries.items():
                value = item.get(attr, item_lower.get(attr.lower()))
                if value is None:
                    continue
                if isinstance(widget, ttk.Combobox):
                    widget.set(value)
                else:
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Select", command=select_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return

        description = self.desc_text.get("1.0", tk.END).strip()

        attributes = {}
        for attr, widget in self.attr_entries.items():
            value = widget.get().strip()
            if value:
                attributes[attr] = value

        text = self.attr_text.get("1.0", tk.END)
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key:
                    attributes[key] = value

        self.result = {"name": name, "description": description}
        self.result.update(attributes)
        if self.equipped_var is not None:
            self.result["Equipped"] = "Yes" if self.equipped_var.get() else "No"
        if self.bonded_var is not None:
            self.result["Bonded"] = "Yes" if self.bonded_var.get() else "No"
        self.destroy()


class EditContactDialog(tk.Toplevel):
    def __init__(self, parent, contact=None):
        super().__init__(parent)
        self.parent = parent
        self.contact = contact or {}
        self.result = None

        self.title("Edit Contact")
        self.geometry("400x320")
        self.configure(bg=theme.BG)
        self.resizable(False, False)

        self.create_widgets()
        self.grab_set()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fields = [
            ("Name:", "name", "entry"),
            ("Type:", "type", "combo"),
            ("Loyalty:", "loyalty", "loyalty_combo"),
            ("Connection:", "connection", "entry"),
            ("Notes:", "notes", "text")
        ]

        self.entries = {}
        for i, (label, key, field_type) in enumerate(fields):
            ttk.Label(main_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)

            if field_type == "text":
                entry = scrolledtext.ScrolledText(main_frame, width=30, height=4,
                                                   bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG)
                entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
                if self.contact.get(key):
                    entry.insert(tk.END, self.contact[key])
            elif field_type == "loyalty_combo":
                entry = ttk.Combobox(main_frame, width=27, values=ShadowrunCharacter.LOYALTY_LEVELS)
                entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
                if self.contact.get(key):
                    entry.set(self.contact[key])
            elif field_type == "combo":
                values = ShadowrunCharacter.CONTACT_TYPES if key == "type" else []
                entry = ttk.Combobox(main_frame, width=27, values=values)
                entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
                if self.contact.get(key):
                    entry.set(self.contact[key])
            else:
                entry = ttk.Entry(main_frame, width=30)
                entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
                if self.contact.get(key):
                    entry.insert(0, self.contact[key])

            self.entries[key] = entry

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        result = {}
        for key, widget in self.entries.items():
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox)):
                result[key] = widget.get()
            else:
                result[key] = widget.get("1.0", tk.END).strip()

        if not result.get("name", "").strip():
            messagebox.showerror("Error", "Name is required")
            return

        self.result = result
        self.destroy()


class RunDialog(tk.Toplevel):
    """Create (or edit) a run/mission."""

    def __init__(self, parent, run=None):
        super().__init__(parent)
        self.title("Edit Run" if run else "Create New Run")
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self.grab_set()
        self.parent = parent
        self.run = None
        self.editing = run
        self.tasks = [dict(t) for t in run.tasks] if run else []
        self._build_ui()
        if run:
            self._load(run)

    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(padx=10, pady=10)

        ttk.Label(main, text="Run Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = ttk.Entry(main, width=40)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.name_entry.focus_set()

        ttk.Label(main, text="Reward (¥):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.reward_entry = ttk.Spinbox(main, from_=0, to=1000000, width=10)
        self.reward_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.reward_entry.set(0)

        ttk.Label(main, text="Description:").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
        self.desc_text = scrolledtext.ScrolledText(
            main, width=40, height=5, bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG, wrap="word"
        )
        self.desc_text.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(main, text="Task Description:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.task_desc_entry = ttk.Entry(main, width=40)
        self.task_desc_entry.grid(row=3, column=1, padx=5, pady=5)

        self.mand_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Mandatory", variable=self.mand_var).grid(row=4, column=1, sticky="w", padx=5)
        ttk.Button(main, text="Add Task", command=self._add_task).grid(row=4, column=1, sticky="e", padx=5, pady=5)

        ttk.Label(main, text="Tasks:").grid(row=5, column=0, sticky="nw", padx=5, pady=5)
        tasks_frame = ttk.Frame(main)
        tasks_frame.grid(row=5, column=1, padx=5, pady=5, sticky="nsew")

        self.tasks_listbox = tk.Listbox(
            tasks_frame, width=50, height=6, bg=theme.ENTRY_BG, fg=theme.FG,
            selectbackground=theme.SELECTED_BG, activestyle="none"
        )
        self.tasks_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=self.tasks_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.tasks_listbox.config(yscrollcommand=scrollbar.set)

        ttk.Button(main, text="Remove Selected Task", command=self._remove_task).grid(
            row=6, column=1, sticky="e", padx=5, pady=5
        )

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save Run", command=self._on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side="left", padx=5)

        for task in self.tasks:
            self._render_task_row(task)

    def _load(self, run):
        self.name_entry.insert(0, run.name)
        self.reward_entry.set(run.reward)
        self.desc_text.insert("1.0", run.description)

    def _render_task_row(self, task):
        label = f"{task['description']} [{'M' if task.get('mandatory') else 'O'}]"
        self.tasks_listbox.insert("end", label)

    def _add_task(self):
        desc = self.task_desc_entry.get().strip()
        if not desc:
            messagebox.showwarning("Warning", "Task description cannot be empty")
            return
        task = {"description": desc, "mandatory": self.mand_var.get(), "completed": False}
        self.tasks.append(task)
        self._render_task_row(task)
        self.task_desc_entry.delete(0, "end")

    def _remove_task(self):
        sel = self.tasks_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.tasks_listbox.delete(idx)
        del self.tasks[idx]

    def _on_ok(self):
        from runs import ShadowrunRun

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Run name cannot be empty")
            return
        try:
            reward = int(self.reward_entry.get())
        except ValueError:
            messagebox.showwarning("Warning", "Invalid reward value")
            return

        description = self.desc_text.get("1.0", "end").strip()
        run = self.editing or ShadowrunRun()
        run.name = name
        run.description = description
        run.reward = reward
        run.tasks = [dict(t) for t in self.tasks]
        self.run = run
        self.destroy()

    def _on_cancel(self):
        self.destroy()
