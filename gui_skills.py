"""Skills and Qualities tabs."""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from character import ShadowrunCharacter
import theme


class SkillsQualitiesTabMixin:
    # -- Skills -------------------------------------------------------

    def setup_skills_tab(self):
        tab = self.tabs["Skills"]

        left_frame = ttk.Frame(tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        skill_frame = ttk.LabelFrame(left_frame, text="Skills")
        skill_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.skill_tree = ttk.Treeview(skill_frame, columns=("Skill", "Specialization", "Rank"), show="headings", height=15)
        self.skill_tree.heading("Skill", text="Skill")
        self.skill_tree.heading("Specialization", text="Specialization")
        self.skill_tree.heading("Rank", text="Rank")
        self.skill_tree.column("Skill", width=150)
        self.skill_tree.column("Specialization", width=150)
        self.skill_tree.column("Rank", width=50)
        self.skill_tree.pack(fill=tk.BOTH, expand=True)
        self.skill_tree.bind("<<TreeviewSelect>>", self.update_specialization_list)

        ctrl_frame = ttk.Frame(skill_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ctrl_frame, text="Rank:").pack(side=tk.LEFT, padx=2)
        self.skill_rank_spin = ttk.Spinbox(ctrl_frame, from_=0, to=12, width=3)
        self.skill_rank_spin.pack(side=tk.LEFT, padx=2)

        ttk.Label(ctrl_frame, text="Specialization:").pack(side=tk.LEFT, padx=2)
        self.skill_spec_combo = ttk.Combobox(ctrl_frame, width=20, state="readonly")
        self.skill_spec_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl_frame, text="Update Skill", command=self.update_skill).pack(side=tk.LEFT, padx=5)

        desc_frame = ttk.LabelFrame(left_frame, text="Skill Description")
        desc_frame.pack(fill=tk.X, padx=5, pady=5)

        self.skill_desc_text = scrolledtext.ScrolledText(desc_frame, height=5, wrap=tk.WORD,
                                                          bg=theme.ENTRY_BG, fg=theme.FG)
        self.skill_desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.skill_desc_text.config(state=tk.DISABLED)

    def update_specialization_list(self, event=None):
        selected = self.skill_tree.selection()
        if not selected:
            return

        values = self.skill_tree.item(selected[0])["values"]
        skill = values[0]
        specializations = ShadowrunCharacter.SKILL_SPECIALIZATIONS.get(skill, [])

        options = ["None"] + specializations
        self.skill_spec_combo["values"] = options
        current_spec = self.character.specializations.get(skill, "")
        self.skill_spec_combo.set(current_spec or "None")

        self.skill_rank_spin.delete(0, tk.END)
        self.skill_rank_spin.insert(0, str(self.character.skills[skill]))

        self.skill_desc_text.config(state=tk.NORMAL)
        self.skill_desc_text.delete("1.0", tk.END)
        self.skill_desc_text.insert(tk.END, f"Skill: {skill}\n")
        self.skill_desc_text.insert(tk.END, f"Rank: {self.character.skills[skill]}\n")
        self.skill_desc_text.insert(tk.END, f"Specialization: {current_spec or 'None'}\n")
        self.skill_desc_text.config(state=tk.DISABLED)

    def update_skill(self):
        selected = self.skill_tree.selection()
        if not selected:
            return
        values = self.skill_tree.item(selected[0])["values"]
        skill = values[0]
        try:
            rank = int(self.skill_rank_spin.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid rank value")
            return
        spec = self.skill_spec_combo.get()

        self.character.skills[skill] = rank
        if spec and spec != "None":
            self.character.specializations[skill] = spec
        else:
            self.character.specializations.pop(skill, None)

        self.skill_tree.item(selected[0], values=(skill, spec if spec != "None" else "", rank))
        self.update_specialization_list()
        self.on_character_changed()

    def refresh_skills(self):
        for item in self.skill_tree.get_children():
            self.skill_tree.delete(item)
        for skill, rank in self.character.skills.items():
            spec = self.character.specializations.get(skill, "")
            self.skill_tree.insert("", "end", values=(skill, spec, rank))

    # -- Qualities ------------------------------------------------------

    def setup_qualities_tab(self):
        tab = self.tabs["Qualities"]

        pos_frame = ttk.LabelFrame(tab, text="Positive Qualities")
        pos_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.pos_quality_list = tk.Listbox(pos_frame, selectmode=tk.MULTIPLE, height=15,
                                            bg=theme.ENTRY_BG, fg=theme.FG)
        for quality in ShadowrunCharacter.QUALITIES["Positive"]:
            self.pos_quality_list.insert(tk.END, quality)
        self.pos_quality_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Button(pos_frame, text="Add Selected", command=self.add_pos_quality).pack(pady=5)

        neg_frame = ttk.LabelFrame(tab, text="Negative Qualities")
        neg_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.neg_quality_list = tk.Listbox(neg_frame, selectmode=tk.MULTIPLE, height=15,
                                            bg=theme.ENTRY_BG, fg=theme.FG)
        for quality in ShadowrunCharacter.QUALITIES["Negative"]:
            self.neg_quality_list.insert(tk.END, quality)
        self.neg_quality_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Button(neg_frame, text="Add Selected", command=self.add_neg_quality).pack(pady=5)

        cur_frame = ttk.LabelFrame(tab, text="Current Qualities")
        cur_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.cur_quality_list = tk.Listbox(cur_frame, height=8, bg=theme.ENTRY_BG, fg=theme.FG)
        self.cur_quality_list.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(cur_frame, text="Remove Selected", command=self.remove_quality).pack(pady=5)

    def add_pos_quality(self):
        selected = self.pos_quality_list.curselection()
        for index in selected:
            quality = self.pos_quality_list.get(index)
            if quality in self.character.qualities:
                continue
            karma_cost = ShadowrunCharacter.QUALITY_EFFECTS.get(quality, {}).get("karma", 0)
            if self.character.karma >= karma_cost:
                self.character.qualities.append(quality)
                self.character.karma -= karma_cost
            else:
                messagebox.showerror("Error", f"Not enough karma for {quality}! Cost: {karma_cost}")
        self.refresh_qualities()
        self.on_character_changed()

    def add_neg_quality(self):
        selected = self.neg_quality_list.curselection()
        for index in selected:
            quality = self.neg_quality_list.get(index)
            if quality in self.character.qualities:
                continue
            karma_gain = -ShadowrunCharacter.QUALITY_EFFECTS.get(quality, {}).get("karma", 0)
            self.character.qualities.append(quality)
            self.character.karma += karma_gain
        self.refresh_qualities()
        self.on_character_changed()

    def remove_quality(self):
        selected = self.cur_quality_list.curselection()
        if not selected:
            return
        index = selected[0]
        quality_str = self.cur_quality_list.get(index)
        quality = quality_str[4:]
        if quality in self.character.qualities:
            if quality_str.startswith("[+]"):
                karma_cost = ShadowrunCharacter.QUALITY_EFFECTS.get(quality, {}).get("karma", 0)
                self.character.karma += karma_cost
            else:
                karma_gain = -ShadowrunCharacter.QUALITY_EFFECTS.get(quality, {}).get("karma", 0)
                self.character.karma -= karma_gain
            self.character.qualities.remove(quality)
        self.refresh_qualities()
        self.on_character_changed()

    def refresh_qualities(self):
        self.cur_quality_list.delete(0, tk.END)
        for quality in self.character.qualities:
            prefix = "[+]" if quality in ShadowrunCharacter.QUALITIES["Positive"] else "[-]"
            self.cur_quality_list.insert(tk.END, f"{prefix} {quality}")
