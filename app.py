"""The merged Shadowrun 6E Character & Run Manager.

This used to be two separate Tkinter tools (``wip_main.py`` character sheet
and ``run_tracker.py`` mission tracker). ``CharacterSheetApp`` below combines
them into one notebook: every tab from the character sheet, plus a "Runs"
tab that's the run tracker's functionality, all operating on a single
``ShadowrunCharacter`` (which now also owns the run list, so one .sr6 file
is a character's whole campaign state).

Each tab's widgets and logic live in their own ``gui_*.py`` module as a
mixin class; this file just assembles them and owns the handful of
cross-cutting concerns (loading/saving, and propagating a change in one tab
to the stats that depend on it in another).
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from character import ShadowrunCharacter
import theme

from gui_basic import BasicInfoTabMixin
from gui_skills import SkillsQualitiesTabMixin
from gui_gear import GearTabMixin
from gui_magic import MagicTabMixin
from gui_social import SocialTabMixin
from gui_combat import CombatTabMixin
from gui_matrix import MatrixTabMixin
from gui_wiki import WikiTabMixin
from gui_runs import RunsTabMixin

TAB_NAMES = [
    # Grouped for how a session actually flows: who you are, what you can do,
    # what you're carrying, how you fight, who you know, your campaign, and
    # reference material -- in that order, rather than the original's
    # roughly-alphabetical/whatever-was-coded-first order.
    "Basic Info", "Skills", "Qualities", "Magic/Resonance", "Gear",
    "Combat Stats", "Contacts", "Background", "Runs", "Wiki", "Matrix",
]


class CharacterSheetApp(
    BasicInfoTabMixin,
    SkillsQualitiesTabMixin,
    GearTabMixin,
    MagicTabMixin,
    SocialTabMixin,
    CombatTabMixin,
    MatrixTabMixin,
    WikiTabMixin,
    RunsTabMixin,
):
    def __init__(self, root):
        self.root = root
        self.root.title("Shadowrun 6E Character & Run Manager")
        self.root.geometry("1280x820")
        self.character = ShadowrunCharacter()
        self.current_file_path = None

        theme.apply_theme(self.root)

        self.header_frame = ttk.Frame(self.root)
        self.header_frame.pack(fill=tk.X, padx=10, pady=5)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.footer_frame = ttk.Frame(self.root)
        self.footer_frame.pack(fill=tk.X, padx=10, pady=5)

        self.title_label = ttk.Label(self.header_frame, text="Shadowrun 6E Character Manager",
                                     font=("Arial", 16, "bold"))
        self.title_label.pack(side=tk.LEFT)

        ttk.Button(self.footer_frame, text="New Character", command=self.new_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.footer_frame, text="Save Character", command=self.save_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.footer_frame, text="Save As...", command=self.save_character_as).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.footer_frame, text="Load Character", command=self.load_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.footer_frame, text="Export Summary...", command=self.export_summary).pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tabs = {}
        for name in TAB_NAMES:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=name)
            self.tabs[name] = tab

        self.setup_basic_info_tab()
        self.setup_skills_tab()
        self.setup_qualities_tab()
        self.setup_magic_tab()
        self.setup_gear_tab()
        self.setup_combat_stats_tab()
        self.setup_contacts_tab()
        self.setup_background_tab()
        self.setup_runs_tab()
        self.setup_wiki_tab()
        self.setup_matrix_tab()

        self.refresh_all()

    # -- Cross-tab orchestration ------------------------------------------

    def on_character_changed(self, event=None):
        """Call after any edit that should recompute + redisplay derived stats.

        Basic Info and Background hold free-text/spinbox fields that are only
        written into the character object on demand (not on every keystroke),
        so commit those first, then recompute everything derived from
        attributes/gear/qualities, then refresh the tabs that display derived
        values.
        """
        self.commit_basic_info()
        self.commit_background()
        self.character.recalculate()

        self.refresh_basic_info()
        self.refresh_combat()
        self.update_gear_summary()
        self.refresh_magic_summary()
        self.update_title()

    def refresh_all(self):
        """Full repaint of every tab from the character object. Used after
        New/Load/Import and after anything that changes many fields at once."""
        self.character.recalculate()
        self.refresh_basic_info()
        self.refresh_skills()
        self.refresh_qualities()
        self.refresh_gear()
        self.refresh_magic()
        self.refresh_contacts()
        self.refresh_background()
        self.refresh_combat()
        self.refresh_runs()
        self.refresh_matrix()
        self.update_title()

    def update_title(self):
        name = self.character.name or "Unnamed Runner"
        path = f" — {os.path.basename(self.current_file_path)}" if self.current_file_path else ""
        self.title_label.config(text=f"Shadowrun 6E Character Manager: {name}{path}")

    # -- File operations ----------------------------------------------------

    def new_character(self):
        if not messagebox.askyesno("New Character", "Discard the current character and start a new one?"):
            return
        self.character.reset_character()
        self.current_file_path = None
        self.refresh_all()
        messagebox.showinfo("New Character", "New character created successfully!")

    def save_character(self):
        if self.current_file_path:
            self._write_character(self.current_file_path)
        else:
            self.save_character_as()

    def save_character_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".sr6",
            filetypes=[("Shadowrun 6E Characters", "*.sr6"), ("All Files", "*.*")]
        )
        if file_path:
            self._write_character(file_path)

    def _write_character(self, file_path):
        self.commit_basic_info()
        self.commit_background()
        self.character.recalculate()
        try:
            with open(file_path, "w") as f:
                json.dump(self.character.to_dict(), f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save character: {e}")
            return
        self.current_file_path = file_path
        self.update_title()
        messagebox.showinfo("Save Character", "Character saved successfully!")

    def export_summary(self):
        """Write a plain-text character summary -- handy for a quick print-out
        or to paste into a chat with the GM/party, without handing over the
        full .sr6 JSON file."""
        self.commit_basic_info()
        self.commit_background()
        self.character.recalculate()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"{self.character.name or 'character'}_summary.txt",
        )
        if not file_path:
            return

        c = self.character
        lines = []
        lines.append(f"{c.name or 'Unnamed Runner'} -- {c.metatype} {c.role or ''}".strip())
        lines.append("=" * 60)
        lines.append(f"Magic/Resonance Type: {c.magic_type}    Lifestyle: {c.lifestyle}")
        lines.append(f"Karma: {c.karma}    Nuyen: ¥{c.nuyen}")
        lines.append("")
        lines.append("Attributes:")
        for attr in ShadowrunCharacter.ATTRIBUTES:
            lines.append(f"  {attr}: {c.attributes.get(attr)}")
        lines.append("")
        lines.append(f"Physical Boxes: {c.physical_damage}/{c.physical_boxes}    "
                     f"Stun Boxes: {c.stun_damage}/{c.stun_boxes}")
        lines.append(f"Initiative: {c.initiative_score} + {c.initiative_dice}d6")
        lines.append(f"Armor Rating: {c.armor_rating}    Weapon Accuracy: {c.weapon_accuracy}")
        lines.append(f"Current Edge: {c.current_edge}/{c.attributes.get('Edge')}")
        lines.append("")
        skills_known = {s: r for s, r in c.skills.items() if r > 0}
        if skills_known:
            lines.append("Skills:")
            for skill, rank in sorted(skills_known.items()):
                spec = c.specializations.get(skill)
                lines.append(f"  {skill}: {rank}" + (f" (Specialization: {spec})" if spec else ""))
            lines.append("")
        if c.qualities:
            lines.append("Qualities: " + ", ".join(c.qualities))
            lines.append("")
        for category in ShadowrunCharacter.GEAR_CATEGORIES:
            items = c.gear.get(category, [])
            if items:
                lines.append(f"{category}:")
                for item in items:
                    lines.append(f"  - {item.get('name', '?')}")
                lines.append("")
        if c.spells:
            lines.append("Spells: " + ", ".join(s.get("name", "?") for s in c.spells))
            lines.append("")
        if c.powers:
            lines.append("Adept Powers: " + ", ".join(p.get("name", "?") for p in c.powers))
            lines.append("")
        if c.foci:
            lines.append("Foci: " + ", ".join(f.get("name", "?") for f in c.foci))
            lines.append("")
        if c.contacts:
            lines.append("Contacts:")
            for contact in c.contacts:
                lines.append(f"  - {contact.get('name', '?')} ({contact.get('type', '?')}, "
                             f"Loyalty: {contact.get('loyalty', '?')})")
            lines.append("")
        if c.background:
            lines.append("Background:")
            lines.append(c.background)
            lines.append("")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export summary: {e}")
            return
        messagebox.showinfo("Export Summary", "Character summary exported successfully!")

    def load_character(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Shadowrun 6E Characters", "*.sr6"), ("All Files", "*.*")]
        )
        if not (file_path and os.path.exists(file_path)):
            return
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            self.character.from_dict(data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load character: {e}")
            return
        self.current_file_path = file_path
        self.refresh_all()
        messagebox.showinfo("Load Character", "Character loaded successfully!")
