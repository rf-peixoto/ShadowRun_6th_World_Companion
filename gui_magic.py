"""Magic/Resonance tab: spells, powers, and foci.

Autocalculations wired up here:
- Powers show a running "Power Points used / available" total (available =
  Magic rating, for Adepts/Mystic Adepts) so a player can see at a glance
  whether they've overspent -- it's advisory, not a hard block, since a GM
  may allow it temporarily.
- Bonding a focus (checkbox in the gear dialog) costs Karma once, refunded
  if you un-bond it, and a bonded Power Focus's Force is added straight to
  the character's Magic attribute (see character.recalculate()).
"""

import tkinter as tk
from tkinter import ttk, messagebox

import theme
from dialogs import EditGearDialog, DescriptionViewer

# Karma cost to bond a focus = Force x this multiplier (varies by focus type,
# roughly matching how much a focus does for you).
FOCUS_BOND_MULTIPLIER = {"Power": 2, "Weapon": 1, "Spell": 1, "Sustaining": 1, "Adept": 1, "Binding": 1}


def _is_bonded(item):
    return str(item.get("Bonded", "")).strip().lower() in ("yes", "true", "1")


def _focus_force(item):
    try:
        return int(float(item.get("Force", item.get("force", 0)) or 0))
    except (TypeError, ValueError):
        return 0


def _bond_cost(item):
    focus_type = item.get("Type", item.get("type", ""))
    return _focus_force(item) * FOCUS_BOND_MULTIPLIER.get(focus_type, 1)


class MagicTabMixin:
    def setup_magic_tab(self):
        tab = self.tabs["Magic/Resonance"]
        notebook = ttk.Notebook(tab)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._setup_magic_list(
            notebook, "Spells", "Spell", "spell_tree", ("Type", "Drain"),
            self.add_spell, self.edit_spell, self.remove_spell, self.show_spell_description
        )
        self._setup_powers_tab(notebook)
        self._setup_magic_list(
            notebook, "Focus", "Focus", "foci_tree", ("Type", "Force", "Bonded"),
            self.add_focus, self.edit_focus, self.remove_focus, self.show_focus_description
        )
        # Complex Forms: a Technomancer's Resonance-compiled equivalent of
        # spells. The data model (character.complex_forms, saved/loaded in
        # to_dict/from_dict) already existed, but had no tab at all -- so a
        # Technomancer had nowhere to record what they'd compiled.
        self._setup_magic_list(
            notebook, "Complex Forms", "Complex Form", "complex_form_tree", ("Target", "Fade"),
            self.add_complex_form, self.edit_complex_form, self.remove_complex_form,
            self.show_complex_form_description
        )

    def _setup_magic_list(self, notebook, tab_title, singular, attr_name, columns, add_cmd, edit_cmd, remove_cmd, desc_cmd):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab_title)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        tree.heading("#0", text=singular)
        tree.column("#0", width=150)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<Double-1>", lambda e: edit_cmd(None))
        tree.bind("<<TreeviewSelect>>", desc_cmd)
        setattr(self, attr_name, tree)

        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        ttk.Button(ctrl_frame, text=f"Add {singular}", command=add_cmd).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text=f"Edit {singular}", command=lambda: edit_cmd(None)).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text=f"Remove {singular}", command=remove_cmd).pack(side=tk.LEFT, padx=5)
        return frame

    def _setup_powers_tab(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Powers")

        summary = ttk.Frame(frame)
        summary.pack(fill=tk.X, padx=5, pady=(5, 0))
        ttk.Label(summary, text="Power Points:").pack(side=tk.LEFT)
        self.power_points_label = ttk.Label(summary, text="0 / 0", font=("Arial", 10, "bold"), foreground=theme.ACCENT)
        self.power_points_label.pack(side=tk.LEFT, padx=5)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("Activation", "Effect", "Cost")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        tree.heading("#0", text="Power")
        tree.column("#0", width=200)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100 if col != "Effect" else 220)
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<Double-1>", lambda e: self.edit_power(None))
        tree.bind("<<TreeviewSelect>>", self.show_power_description)
        self.power_tree = tree

        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        ttk.Button(ctrl_frame, text="Add Power", command=self.add_power).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text="Edit Power", command=lambda: self.edit_power(None)).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Remove Power", command=self.remove_power).pack(side=tk.LEFT, padx=5)

    # -- Spells -----------------------------------------------------------

    def show_spell_description(self, event=None):
        selected = self.spell_tree.selection()
        if not selected:
            return
        spell = self.character.spells[self.spell_tree.index(selected[0])]
        content = (f"Name: {spell.get('name', '')}\n\n"
                   f"Type: {spell.get('Type', spell.get('type', ''))}\n"
                   f"Drain: {spell.get('Drain', spell.get('drain', ''))}\n\n"
                   f"Description: {spell.get('description', '')}")
        DescriptionViewer(self.root, "Spell Description", content)

    def add_spell(self):
        dialog = EditGearDialog(self.root, "Spell")
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.spells.append(dialog.result)
        self.spell_tree.insert("", "end", text=dialog.result["name"],
                               values=(dialog.result.get("Type", dialog.result.get("type", "")),
                                       dialog.result.get("Drain", dialog.result.get("drain", ""))))
        self.on_character_changed()

    def edit_spell(self, event):
        selected = self.spell_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.spell_tree.index(item_id)
        dialog = EditGearDialog(self.root, "Spell", self.character.spells[index])
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.spells[index] = dialog.result
        self.spell_tree.item(item_id, text=dialog.result["name"],
                             values=(dialog.result.get("Type", dialog.result.get("type", "")),
                                     dialog.result.get("Drain", dialog.result.get("drain", ""))))
        self.on_character_changed()

    def remove_spell(self):
        selected = self.spell_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.spell_tree.index(item_id)
        self.character.spells.pop(index)
        self.spell_tree.delete(item_id)
        self.on_character_changed()

    # -- Complex Forms ------------------------------------------------------

    def show_complex_form_description(self, event=None):
        selected = self.complex_form_tree.selection()
        if not selected:
            return
        form = self.character.complex_forms[self.complex_form_tree.index(selected[0])]
        content = (f"Name: {form.get('name', '')}\n\n"
                   f"Target: {form.get('Target', form.get('target', ''))}\n"
                   f"Fade: {form.get('Fade', form.get('fade', ''))}\n\n"
                   f"Description: {form.get('description', '')}")
        DescriptionViewer(self.root, "Complex Form Description", content)

    def add_complex_form(self):
        dialog = EditGearDialog(self.root, "Complex Form")
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.complex_forms.append(dialog.result)
        self.complex_form_tree.insert("", "end", text=dialog.result["name"],
                                      values=(dialog.result.get("Target", dialog.result.get("target", "")),
                                              dialog.result.get("Fade", dialog.result.get("fade", ""))))
        self.on_character_changed()

    def edit_complex_form(self, event):
        selected = self.complex_form_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.complex_form_tree.index(item_id)
        dialog = EditGearDialog(self.root, "Complex Form", self.character.complex_forms[index])
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.complex_forms[index] = dialog.result
        self.complex_form_tree.item(item_id, text=dialog.result["name"],
                                    values=(dialog.result.get("Target", dialog.result.get("target", "")),
                                            dialog.result.get("Fade", dialog.result.get("fade", ""))))
        self.on_character_changed()

    def remove_complex_form(self):
        selected = self.complex_form_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.complex_form_tree.index(item_id)
        self.character.complex_forms.pop(index)
        self.complex_form_tree.delete(item_id)
        self.on_character_changed()

    # -- Powers -----------------------------------------------------------

    def show_power_description(self, event=None):
        selected = self.power_tree.selection()
        if not selected:
            return
        power = self.character.powers[self.power_tree.index(selected[0])]
        content = (f"Name: {power.get('name', '')}\n\n"
                   f"Activation: {power.get('activation', '')}\n"
                   f"Effect: {power.get('effect', '')}\n"
                   f"Cost: {power.get('Cost', power.get('cost', 1))} Power Points\n\n"
                   f"Description: {power.get('description', '')}")
        DescriptionViewer(self.root, "Power Description", content)

    def _power_cost_display(self, power):
        try:
            return str(float(power.get("Cost", power.get("cost", 1)) or 1))
        except (TypeError, ValueError):
            return "1"

    def add_power(self):
        dialog = EditGearDialog(self.root, "Power")
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.powers.append(dialog.result)
        self.power_tree.insert("", "end", text=dialog.result["name"],
                               values=(dialog.result.get("Activation", dialog.result.get("activation", "")),
                                       dialog.result.get("Effect", dialog.result.get("effect", "")),
                                       self._power_cost_display(dialog.result)))
        self.on_character_changed()
        self._warn_if_power_points_overspent()

    def edit_power(self, event):
        selected = self.power_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.power_tree.index(item_id)
        dialog = EditGearDialog(self.root, "Power", self.character.powers[index])
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.powers[index] = dialog.result
        self.power_tree.item(item_id, text=dialog.result["name"],
                             values=(dialog.result.get("Activation", dialog.result.get("activation", "")),
                                     dialog.result.get("Effect", dialog.result.get("effect", "")),
                                     self._power_cost_display(dialog.result)))
        self.on_character_changed()
        self._warn_if_power_points_overspent()

    def remove_power(self):
        selected = self.power_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.power_tree.index(item_id)
        self.character.powers.pop(index)
        self.power_tree.delete(item_id)
        self.on_character_changed()

    def _warn_if_power_points_overspent(self):
        c = self.character
        if c.magic_type in ("Adept", "Mystic Adept") and c.power_points_used > c.power_points_available:
            messagebox.showwarning(
                "Power Points",
                f"You've spent {c.power_points_used:g} Power Points but only have "
                f"{c.power_points_available} available (from Magic {c.power_points_available}). "
                "That's fine if your GM allows it, but you may want to remove a power."
            )

    # -- Foci -------------------------------------------------------------

    def show_focus_description(self, event=None):
        selected = self.foci_tree.selection()
        if not selected:
            return
        focus = self.character.foci[self.foci_tree.index(selected[0])]
        bonded = "Yes" if _is_bonded(focus) else "No"
        content = (f"Name: {focus.get('name', '')}\n\n"
                   f"Type: {focus.get('Type', focus.get('type', ''))}\n"
                   f"Force: {focus.get('Force', focus.get('force', ''))}\n"
                   f"Bonded: {bonded} (bonding costs {_bond_cost(focus)} Karma)\n\n"
                   f"Description: {focus.get('description', '')}")
        DescriptionViewer(self.root, "Focus Description", content)

    def _apply_bond_karma_change(self, old_item, new_item):
        """Charge/refund Karma when a focus's Bonded state changes."""
        was_bonded = _is_bonded(old_item) if old_item else False
        now_bonded = _is_bonded(new_item)
        if was_bonded == now_bonded:
            return
        cost = _bond_cost(new_item)
        if now_bonded:
            if self.character.karma < cost:
                messagebox.showwarning(
                    "Not Enough Karma",
                    f"Bonding this focus costs {cost} Karma; you only have {self.character.karma}. "
                    "It's saved as bonded anyway -- adjust Karma manually if your GM wants it enforced."
                )
            self.character.karma -= cost
        else:
            self.character.karma += cost

    def add_focus(self):
        dialog = EditGearDialog(self.root, "Focus")
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self._apply_bond_karma_change(None, dialog.result)
        self.character.foci.append(dialog.result)
        self.foci_tree.insert("", "end", text=dialog.result["name"],
                              values=(dialog.result.get("Type", dialog.result.get("type", "")),
                                      dialog.result.get("Force", dialog.result.get("force", "")),
                                      "Yes" if _is_bonded(dialog.result) else "No"))
        self.on_character_changed()

    def edit_focus(self, event):
        selected = self.foci_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.foci_tree.index(item_id)
        old_item = dict(self.character.foci[index])
        dialog = EditGearDialog(self.root, "Focus", self.character.foci[index])
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self._apply_bond_karma_change(old_item, dialog.result)
        self.character.foci[index] = dialog.result
        self.foci_tree.item(item_id, text=dialog.result["name"],
                            values=(dialog.result.get("Type", dialog.result.get("type", "")),
                                    dialog.result.get("Force", dialog.result.get("force", "")),
                                    "Yes" if _is_bonded(dialog.result) else "No"))
        self.on_character_changed()

    def remove_focus(self):
        selected = self.foci_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        index = self.foci_tree.index(item_id)
        removed = self.character.foci[index]
        if _is_bonded(removed):
            self.character.karma += _bond_cost(removed)  # refund the bond
        self.character.foci.pop(index)
        self.foci_tree.delete(item_id)
        self.on_character_changed()

    # -- Refresh ------------------------------------------------------------

    def refresh_magic(self):
        self.spell_tree.delete(*self.spell_tree.get_children())
        for spell in self.character.spells:
            self.spell_tree.insert("", "end", text=spell.get("name", ""),
                                   values=(spell.get("Type", spell.get("type", "")),
                                           spell.get("Drain", spell.get("drain", ""))))

        self.power_tree.delete(*self.power_tree.get_children())
        for power in self.character.powers:
            self.power_tree.insert("", "end", text=power.get("name", ""),
                                   values=(power.get("Activation", power.get("activation", "")),
                                           power.get("Effect", power.get("effect", "")),
                                           self._power_cost_display(power)))

        self.foci_tree.delete(*self.foci_tree.get_children())
        for focus in self.character.foci:
            self.foci_tree.insert("", "end", text=focus.get("name", ""),
                                  values=(focus.get("Type", focus.get("type", "")),
                                          focus.get("Force", focus.get("force", "")),
                                          "Yes" if _is_bonded(focus) else "No"))

        self.complex_form_tree.delete(*self.complex_form_tree.get_children())
        for form in self.character.complex_forms:
            self.complex_form_tree.insert("", "end", text=form.get("name", ""),
                                          values=(form.get("Target", form.get("target", "")),
                                                  form.get("Fade", form.get("fade", ""))))

        self.refresh_magic_summary()

    def refresh_magic_summary(self):
        if not hasattr(self, "power_points_label"):
            return
        c = self.character
        used = c.power_points_used
        used_display = f"{used:g}" if used != int(used) else str(int(used))
        self.power_points_label.config(
            text=f"{used_display} / {c.power_points_available}",
            foreground=theme.BAD if used > c.power_points_available else theme.ACCENT,
        )
