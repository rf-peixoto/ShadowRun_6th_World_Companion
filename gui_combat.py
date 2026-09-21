"""Combat Stats tab: an "Overview" (derived stats + condition monitors +
combat actions, all visible together) and a "Dice Roller" sub-tab.

The original had four separate sub-tabs (Condition Monitors, Combat Actions,
Dice Roller, Combat Stats) which meant clicking around mid-fight just to see
your Armor Rating while marking damage. Everything you check or touch
constantly during a fight now lives on one "Overview" screen; the dice
roller -- a distinct, focused task -- stays on its own tab.

Bugs fixed here (see character.py for the model-side half of the fix):
- "Battle Hardened" edge action crashed because ``ShadowrunCharacter.roll_dice``
  used to reach into a GUI combobox (``self.roll_combo``) that only exists on
  this class. The model now takes a plain ``roll_type`` string instead.
- Armor Rating / Weapon Accuracy stats always showed 0 because of the
  attribute-dict-wipe bug in the old ``calculate_derived_stats`` -- now reads
  ``character.armor_rating`` / ``character.weapon_accuracy`` directly.
- Spending Edge on a roll never actually deducted it from Current Edge.
"""

import random
import re
import tkinter as tk
from tkinter import ttk, messagebox

from character import ShadowrunCharacter
import theme

# Matches a free-roll dice pool typed as "4d6", "4D6", or "4d" (Shadowrun
# only ever rolls d6s, so the "6" is optional but the "d" is required -- a
# bare number like "4" is handled separately as a plain pool size).
FREE_ROLL_RE = re.compile(r"^\s*(\d+)\s*d\s*6?\s*$", re.IGNORECASE)


class CombatTabMixin:
    def setup_combat_stats_tab(self):
        tab = self.tabs["Combat Stats"]
        notebook = ttk.Notebook(tab)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._setup_overview_subtab(notebook)
        self._setup_dice_roller_subtab(notebook)

    # -- Overview: derived stats + condition monitors + combat actions -----

    def _setup_overview_subtab(self, notebook):
        overview = ttk.Frame(notebook)
        notebook.add(overview, text="Overview")

        # Derived stats strip -- the numbers gear/attributes actually produce.
        stats_frame = ttk.LabelFrame(overview, text="Derived Stats")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        # Note: "damage_penalty" is intentionally prefixed "overview_" here --
        # the Dice Roller sub-tab has its own damage penalty label
        # (self.damage_penalty_label) and reusing the same attribute name
        # would silently overwrite one widget reference with the other.
        stats = [
            ("Initiative", "initiative"), ("Physical Boxes", "physical_boxes"),
            ("Stun Boxes", "stun_boxes"), ("Armor Rating", "armor_rating"),
            ("Weapon Accuracy", "weapon_accuracy"), ("Damage Penalty", "overview_damage_penalty"),
        ]
        for i, (label, attr) in enumerate(stats):
            ttk.Label(stats_frame, text=label + ":").grid(row=i // 3, column=(i % 3) * 2, sticky=tk.W, padx=(10, 2), pady=6)
            value_label = ttk.Label(stats_frame, text="0", font=("Arial", 10, "bold"), foreground=theme.ACCENT)
            value_label.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky=tk.W, padx=(0, 15), pady=6)
            setattr(self, f"{attr}_label", value_label)

        # Condition monitors, side by side so both fit without scrolling.
        monitors_frame = ttk.Frame(overview)
        monitors_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        monitors_frame.columnconfigure(0, weight=1)
        monitors_frame.columnconfigure(1, weight=1)

        phys_frame = ttk.LabelFrame(monitors_frame, text="Physical Condition")
        phys_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ttk.Label(phys_frame, text="Damage:").pack(anchor=tk.W, padx=5, pady=2)
        self.phys_damage_label = tk.Label(phys_frame, text="0", font=("Arial", 10, "bold"), bg=theme.BG, fg="white")
        self.phys_damage_label.pack(anchor=tk.W, padx=5, pady=2)
        self.phys_monitor = tk.Canvas(phys_frame, bg=theme.BG, height=160)
        self.phys_monitor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.phys_monitor.bind("<Button-1>", self.toggle_physical_damage)

        stun_frame = ttk.LabelFrame(monitors_frame, text="Stun Condition")
        stun_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ttk.Label(stun_frame, text="Damage:").pack(anchor=tk.W, padx=5, pady=2)
        self.stun_damage_label = tk.Label(stun_frame, text="0", font=("Arial", 10, "bold"), bg=theme.BG, fg="white")
        self.stun_damage_label.pack(anchor=tk.W, padx=5, pady=2)
        self.stun_monitor = tk.Canvas(stun_frame, bg=theme.BG, height=160)
        self.stun_monitor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.stun_monitor.bind("<Button-1>", self.toggle_stun_damage)

        # Combat actions: initiative, healing, edge -- one row, always visible.
        actions_frame = ttk.Frame(overview)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        init_frame = ttk.LabelFrame(actions_frame, text="Initiative")
        init_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        ttk.Button(init_frame, text="Roll Initiative", command=self.roll_initiative).pack(side=tk.LEFT, padx=5, pady=5)
        self.init_result_label = ttk.Label(init_frame, text="Result: -")
        self.init_result_label.pack(side=tk.LEFT, padx=5)

        heal_frame = ttk.LabelFrame(actions_frame, text="Healing")
        heal_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(heal_frame, text="Use Medkit", command=self.use_medkit).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(heal_frame, text="Rest", command=self.rest).pack(side=tk.LEFT, padx=5, pady=5)

        edge_frame = ttk.LabelFrame(actions_frame, text="Edge")
        edge_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(edge_frame, text="Current Edge:").pack(side=tk.LEFT, padx=5)
        self.edge_label = ttk.Label(edge_frame, text="1", font=("Arial", 10, "bold"))
        self.edge_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(edge_frame, text="Reset Edge", command=self.reset_edge).pack(side=tk.LEFT, padx=5)

    def get_damage_status(self, damage, total_boxes):
        if damage == 0:
            return "Healthy", theme.GOOD
        elif damage <= total_boxes // 3:
            return "Light", "#FFEB3B"
        elif damage <= 2 * total_boxes // 3:
            return "Moderate", theme.WARN
        else:
            return "Serious", theme.BAD

    def draw_condition_monitors(self):
        c = self.character
        phys_status, phys_color = self.get_damage_status(c.physical_damage, c.physical_boxes)
        stun_status, stun_color = self.get_damage_status(c.stun_damage, c.stun_boxes)

        self.phys_damage_label.config(text=f"{c.physical_damage}/{c.physical_boxes} ({phys_status})", fg=phys_color)
        self.stun_damage_label.config(text=f"{c.stun_damage}/{c.stun_boxes} ({stun_status})", fg=stun_color)

        self.draw_single_monitor(self.phys_monitor, c.physical_boxes, c.physical_damage, "#FF5252", "Physical Condition")
        self.draw_single_monitor(self.stun_monitor, c.stun_boxes, c.stun_damage, "#FFC107", "Stun Condition")

        self.damage_penalty_label.config(text=str(c.damage_penalty))
        self.overview_damage_penalty_label.config(text=str(c.damage_penalty))

    def draw_single_monitor(self, canvas, total_boxes, damage, damage_color, title):
        canvas.delete("all")
        width = canvas.winfo_width() or 300
        boxes_per_row = min(5, max(3, width // 35))
        box_size = min(26, (width - 20) // boxes_per_row)
        spacing = 5

        for i in range(total_boxes):
            row = i // boxes_per_row
            col = i % boxes_per_row
            x1 = 10 + col * (box_size + spacing)
            y1 = 10 + row * (box_size + spacing)
            x2, y2 = x1 + box_size, y1 + box_size
            fill_color = damage_color if i < damage else "#444"
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#666")
            if box_size > 15:
                canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=str(i + 1),
                                   fill="white" if i < damage else "#aaa")

        thresholds = [
            (total_boxes // 3, "Light", "#FFEB3B"),
            (2 * total_boxes // 3, "Moderate", theme.WARN),
            (total_boxes, "Serious", theme.BAD)
        ]
        for threshold, label, color in thresholds:
            if threshold < total_boxes:
                row = threshold // boxes_per_row
                y_pos = 10 + row * (box_size + spacing) - 2
                canvas.create_line(5, y_pos, width - 5, y_pos, fill=color, dash=(4, 2), width=2)

    def toggle_physical_damage(self, event):
        self._toggle_damage(event, self.phys_monitor, "physical")

    def toggle_stun_damage(self, event):
        self._toggle_damage(event, self.stun_monitor, "stun")

    def _toggle_damage(self, event, canvas, damage_type):
        box_size = 26
        spacing = 5
        boxes_per_row = min(5, max(3, canvas.winfo_width() // 35))

        row = (event.y - 10) // (box_size + spacing)
        col = (event.x - 10) // (box_size + spacing)
        box_index = row * boxes_per_row + col

        total_boxes = self.character.physical_boxes if damage_type == "physical" else self.character.stun_boxes
        if not (0 <= box_index < total_boxes):
            return

        current = self.character.physical_damage if damage_type == "physical" else self.character.stun_damage
        if damage_type == "physical":
            self.character.physical_damage = current - 1 if box_index < current else current + 1
        else:
            self.character.stun_damage = current - 1 if box_index < current else current + 1

        self.character.recalculate()
        self.draw_condition_monitors()
        self.refresh_quick_stats()

    # -- Combat actions -------------------------------------------------

    def roll_initiative(self):
        result, dice_rolls = self.character.roll_initiative()
        self.init_result_label.config(text=f"Result: {result} (Dice: {dice_rolls})")

    def use_medkit(self):
        if self.character.use_medkit():
            self.draw_condition_monitors()
            self.refresh_gear()
            self.refresh_quick_stats()
            messagebox.showinfo("Medkit Used", "Medkit applied! Physical and stun damage reduced.")
        else:
            messagebox.showwarning("No Medkit", "No medkit found in your gear!")

    def rest(self):
        self.character.rest()
        self.draw_condition_monitors()
        self.refresh_quick_stats()
        messagebox.showinfo("Rest", "Character rested. Stun damage reduced by 1.")

    def reset_edge(self):
        self.character.reset_edge()
        self.edge_label.config(text=str(self.character.current_edge))
        self.refresh_quick_stats()
        messagebox.showinfo("Edge Reset", "Edge points reset to maximum!")

    # -- Dice roller --------------------------------------------------------

    def _setup_dice_roller_subtab(self, notebook):
        dice_frame = ttk.Frame(notebook)
        notebook.add(dice_frame, text="Dice Roller")

        roll_frame = ttk.Frame(dice_frame)
        roll_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(roll_frame, text="Roll Type:").pack(side=tk.LEFT, padx=5)
        self.roll_combo = ttk.Combobox(roll_frame, values=ShadowrunCharacter.DICE_ROLL_OPTIONS, width=25)
        self.roll_combo.pack(side=tk.LEFT, padx=5)
        self.roll_combo.set(ShadowrunCharacter.DICE_ROLL_OPTIONS[0])

        ttk.Label(roll_frame, text="Dice Pool:").pack(side=tk.LEFT, padx=5)
        self.dice_pool_combo = ttk.Combobox(roll_frame, width=25)
        self.dice_pool_combo.pack(side=tk.LEFT, padx=5)

        # Free Roll: for anything that isn't tied to an attribute/skill/gear
        # dice pool -- house rules, GM-called rolls, damage soak dice, etc.
        # Type a count like "4d6" (or just "4") and roll it directly.
        free_roll_frame = ttk.LabelFrame(dice_frame, text="Free Roll")
        free_roll_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(free_roll_frame, text="Dice (e.g. 4d6):").pack(side=tk.LEFT, padx=5, pady=5)
        self.free_roll_entry = ttk.Entry(free_roll_frame, width=12)
        self.free_roll_entry.pack(side=tk.LEFT, padx=5)
        self.free_roll_entry.insert(0, "4d6")
        ttk.Button(free_roll_frame, text="Roll Free Dice", command=self.perform_free_roll).pack(side=tk.LEFT, padx=10)

        edge_action_frame = ttk.Frame(dice_frame)
        edge_action_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(edge_action_frame, text="Edge Action:").pack(side=tk.LEFT, padx=5)
        self.edge_action_combo = ttk.Combobox(
            edge_action_frame, values=["None"] + list(ShadowrunCharacter.EDGE_ACTIONS.keys()), width=30
        )
        self.edge_action_combo.pack(side=tk.LEFT, padx=5)
        self.edge_action_combo.set("None")

        self.wild_die_var = tk.BooleanVar()
        ttk.Checkbutton(edge_action_frame, text="Use Wild Die", variable=self.wild_die_var).pack(side=tk.LEFT, padx=10)

        damage_frame = ttk.Frame(dice_frame)
        damage_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(damage_frame, text="Damage Penalty:", foreground=theme.BAD, font=("Arial", 10)).pack(side=tk.LEFT)
        self.damage_penalty_label = ttk.Label(damage_frame, text="0", foreground=theme.BAD, font=("Arial", 10, "bold"))
        self.damage_penalty_label.pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(dice_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Roll Dice", command=self.perform_dice_roll).pack()

        result_frame = ttk.LabelFrame(dice_frame, text="Results")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.dice_canvas = tk.Canvas(result_frame, bg=theme.ENTRY_BG, height=100)
        self.dice_canvas.pack(fill=tk.X, padx=5, pady=5)

        self.result_frame = ttk.Frame(result_frame)
        self.result_frame.pack(fill=tk.X, padx=5, pady=5)
        self.hits_label = ttk.Label(self.result_frame, text="Hits: 0", font=("Arial", 12, "bold"))
        self.hits_label.pack(side=tk.LEFT, padx=10)
        self.glitch_label = ttk.Label(self.result_frame, text="", font=("Arial", 12))
        self.glitch_label.pack(side=tk.LEFT, padx=10)
        self.success_label = ttk.Label(self.result_frame, text="", font=("Arial", 14, "bold"))
        self.success_label.pack(side=tk.LEFT, padx=10)

    def update_dice_pool_options(self):
        options = []
        for attr in ["Body", "Agility", "Reaction", "Strength", "Willpower",
                    "Logic", "Intuition", "Charisma", "Edge"]:
            value = self.character.attributes[attr]
            if value > 0:
                options.append(f"{attr} ({value})")

        for skill, rank in self.character.skills.items():
            if rank > 0:
                # A specialization grants +2 dice on rolls using it (p.65) --
                # folded straight into the pool size shown/rolled here so it
                # isn't just flavor text on the Skills tab.
                spec = self.character.specializations.get(skill)
                if spec:
                    options.append(f"{skill} [{spec}] ({rank + 2})")
                else:
                    options.append(f"{skill} ({rank})")

        for spell in self.character.spells:
            options.append(f"Spell: {spell.get('name', '')}")
        for power in self.character.powers:
            options.append(f"Power: {power.get('name', '')}")
        for focus in self.character.foci:
            options.append(f"Focus: {focus.get('name', '')}")
        for weapon in self.character.gear["Weapons"]:
            if str(weapon.get("Equipped", "Yes")).strip().lower() != "no":
                options.append(f"Weapon: {weapon.get('name', '')}")

        # Common Matrix actions (p.180+) use Logic + a relevant skill; listed
        # directly as ready-to-roll pools since they aren't tied to any
        # particular piece of gear the way weapon/spell pools are.
        logic = self.character.attributes["Logic"]
        intuition = self.character.attributes["Intuition"]
        cracking = self.character.skills.get("Cracking", 0)
        matrix_pools = {
            "Matrix Perception": logic + intuition,
            "Brute Force (Matrix)": logic + cracking,
            "Hack on the Fly": logic + cracking,
            "Data Spike": logic + cracking,
        }
        for label, pool in matrix_pools.items():
            options.append(f"{label} ({pool})")

        current = self.dice_pool_combo.get()
        self.dice_pool_combo["values"] = options
        if current in options:
            self.dice_pool_combo.set(current)
        elif options:
            self.dice_pool_combo.set(options[0])

    def perform_dice_roll(self):
        edge_action_name = self.edge_action_combo.get()
        requested_edge_action = edge_action_name if edge_action_name != "None" else None
        roll_type = self.roll_combo.get()

        try:
            dice_pool_text = self.dice_pool_combo.get()
            if "(" in dice_pool_text and ")" in dice_pool_text:
                pool_size = int(dice_pool_text.split("(")[1].split(")")[0])
            else:
                pool_size = self.get_special_dice_pool(dice_pool_text)
        except (ValueError, IndexError):
            pool_size = 0

        use_wild_die = self.wild_die_var.get()

        result = self.character.roll_dice(pool_size, requested_edge_action, roll_type, use_wild_die)

        if requested_edge_action and result["edge_action_used"] is None:
            messagebox.showwarning(
                "Not Enough Edge",
                f"Not enough Edge points for {requested_edge_action}! Rolled without an Edge action."
            )

        self.edge_label.config(text=str(self.character.current_edge))
        self.refresh_quick_stats()

        self._display_roll_result(result)

    def parse_free_roll(self, text):
        """Parse a free-roll dice count like "4d6", "4D6", "4d", or a bare
        "4" into a plain dice-pool size. Returns None if it doesn't parse."""
        text = (text or "").strip()
        if not text:
            return None
        match = FREE_ROLL_RE.match(text)
        if match:
            return int(match.group(1))
        if text.isdigit():
            return int(text)
        return None

    def perform_free_roll(self):
        pool_size = self.parse_free_roll(self.free_roll_entry.get())
        if pool_size is None:
            messagebox.showwarning(
                "Invalid Free Roll",
                'Enter a dice count like "4d6" or a plain number of dice, e.g. "4".'
            )
            return

        use_wild_die = self.wild_die_var.get()
        # Free rolls are plain dice pools (house rules, soak tests, GM-called
        # rolls, ...) with no Edge action and no damage-penalty deduction --
        # unlike a named roll, there's no attribute/skill pool to apply it to.
        dice = [random.randint(1, 6) for _ in range(max(0, pool_size))]
        wild_die_result = None
        wild_die_hits = 0
        if use_wild_die and dice:
            current = dice.pop(0)
            wild_die_result = [current]
            while current == 6:
                wild_die_hits += 1
                current = random.randint(1, 6)
                wild_die_result.append(current)
            if current == 1:
                wild_die_hits -= 1
            elif current >= 5:
                wild_die_hits += 1

        hits = sum(1 for r in dice if r >= 5) + wild_die_hits
        ones = sum(1 for r in dice if r == 1)
        total_dice = len(dice)
        glitch = total_dice > 0 and ones > total_dice / 2
        critical_glitch = glitch and hits <= 0

        result = {
            "dice": dice,
            "hits": max(0, hits),
            "glitch": glitch,
            "critical_glitch": critical_glitch,
            "wild_die": wild_die_result,
            "edge_action_used": None,
        }
        self._display_roll_result(result)

    def _display_roll_result(self, result):
        self.dice_canvas.delete("all")
        self.hits_label.config(text=f"Hits: {result['hits']}")

        if result["critical_glitch"]:
            self.glitch_label.config(text="CRITICAL GLITCH!", foreground=theme.BAD)
            self.success_label.config(text="FAILURE", foreground=theme.BAD)
        elif result["glitch"]:
            self.glitch_label.config(text="GLITCH!", foreground=theme.WARN)
            self.success_label.config(text="FAILURE", foreground=theme.BAD)
        else:
            self.glitch_label.config(text="")
            if result["hits"] > 0:
                self.success_label.config(text="SUCCESS!", foreground=theme.GOOD)
            else:
                self.success_label.config(text="FAILURE", foreground=theme.BAD)

        dice_width = 30
        spacing = 5
        canvas_width = self.dice_canvas.winfo_width() or 400
        start_x = max(10, (canvas_width - (dice_width * len(result["dice"]) + spacing * max(0, len(result["dice"]) - 1))) // 2)

        if result.get("wild_die"):
            wild_x = 10
            for die in result["wild_die"]:
                self.draw_die(self.dice_canvas, wild_x, 40, dice_width, die, True)
                wild_x += dice_width + spacing

        for i, die in enumerate(result["dice"]):
            x = start_x + i * (dice_width + spacing)
            self.draw_die(self.dice_canvas, x, 40, dice_width, die)

    def draw_die(self, canvas, x, y, size, value, is_wild=False):
        fill_color = theme.ACCENT if is_wild else "#444"
        canvas.create_rectangle(x, y, x + size, y + size, fill=fill_color, outline="#666")
        canvas.create_text(x + size / 2, y + size / 2, text=str(value), fill="white", font=("Arial", 14, "bold"))
        if value >= 5:
            canvas.create_oval(x + 5, y + 5, x + 10, y + 10, fill=theme.GOOD, outline="")
        elif value == 1:
            canvas.create_oval(x + size - 10, y + 5, x + size - 5, y + 10, fill=theme.BAD, outline="")

    def get_special_dice_pool(self, dice_pool_text):
        pool_size = 0
        if dice_pool_text.startswith("Spell: "):
            pool_size = self.character.attributes["Magic"] + self.character.skills.get("Sorcery", 0)
        elif dice_pool_text.startswith("Power: "):
            pool_size = self.character.attributes["Magic"] + self.character.skills.get("Sorcery", 0)
        elif dice_pool_text.startswith("Focus: "):
            pool_size = self.character.attributes["Magic"] + self.character.skills.get("Sorcery", 0)
        elif dice_pool_text.startswith("Weapon: "):
            pool_size = self.character.attributes["Agility"] + self.character.skills.get("Firearms", 0)
        return pool_size

    # -- Refresh --------------------------------------------------------

    def refresh_combat(self):
        c = self.character
        self.initiative_label.config(text=f"{c.initiative_score} + {c.initiative_dice}d6")
        self.physical_boxes_label.config(text=f"{c.physical_damage}/{c.physical_boxes}")
        self.stun_boxes_label.config(text=f"{c.stun_damage}/{c.stun_boxes}")
        self.armor_rating_label.config(text=str(c.armor_rating))
        self.weapon_accuracy_label.config(text=str(c.weapon_accuracy))
        self.damage_penalty_label.config(text=str(c.damage_penalty))

        self.draw_condition_monitors()
        self.update_dice_pool_options()
        self.edge_label.config(text=str(c.current_edge))
