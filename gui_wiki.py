"""Wiki tab: static in-app reference for gear, magic, vehicles, actions, rules."""

import tkinter as tk
from tkinter import ttk, scrolledtext

from character import ShadowrunCharacter
import theme

WIKI_TOPICS = {
    "Weapons": "**Weapons**\n\nFirearms, blades, and other implements of destruction. Each weapon has:\n- Damage Value (DV)\n- Accuracy (ACC)\n- Armor Penetration (AP)\n- Mode (SA, BF, FA)\n- Recoil Compensation (RC)\n- Ammo Capacity\n\n**Special Rules**\n- Recoil affects burst fire\n- Smartgun systems add +2 ACC",
    "Armor": "**Armor**\n\nProtective gear to reduce damage. Each armor has:\n- Rating (protection value)\n- Social penalty\n- Capacity for modifications\n\n**Special Rules**\n- Stacking armor has diminishing returns\n- Full body armor provides best protection but high social penalty",
    "Cyberware": "**Cyberware**\n\nTechnological implants that enhance abilities but cost Essence. Each cyberware has:\n- Essence Cost\n- Capacity\n- Rating\n\n**Special Rules**\n- Essence loss affects magic users\n- Cyberlimbs can be customized",
    "Bioware": "**Bioware**\n\nBiological enhancements that integrate with the body. Each bioware has:\n- Essence Cost\n- Rating\n- Capacity\n\n**Special Rules**\n- Lower essence cost than cyberware\n- More natural integration",
    "Magic Items": "**Magic Items**\n\nItems with magical properties or that enhance magical abilities. Each item has:\n- Force\n- Type\n- Binding requirements\n\n**Special Rules**\n- Foci must be bound with karma\n- Sustaining foci reduce drain for sustained spells",
    "Electronics": "**Electronics**\n\nDevices and gadgets for the digital age. Each item has:\n- Rating\n- Capacity\n- Function\n\n**Special Rules**\n- Device rating affects functionality\n- Commlinks for communication\n- Cyberdecks for hacking",
    "Medkits": "**Medkits**\n\nMedical supplies for treating injuries. Each medkit has:\n- Rating (effectiveness)\n- Quantity (uses)\n\n**Special Rules**\n- Higher rating provides better healing\n- Each use consumes one charge",
    "Other": "**Other Gear**\n\nMiscellaneous equipment for various purposes. Each item has:\n- Effect\n- Duration\n- Potency\n\n**Special Rules**\n- Includes tools, chemicals, and special items",
    "Spells": "**Spells**\n\nMagical effects created through willpower and tradition. Each spell has:\n- Type (Combat, Health, Illusion, Manipulation)\n- Drain value (cost to cast)\n\n**Casting**\n- Spellcasting + Magic [Force] vs. Drain\n- Drain is Physical for combat spells, Stun for others",
    "Powers": "**Adept Powers**\n\nInnate magical abilities possessed by adepts. Each power has:\n- Activation type (Passive, Simple Action)\n- Effect\n\n**Special Rules**\n- Powered by Magic attribute\n- No drain but limited by power points",
    "Foci": "**Foci**\n\nMagical items that enhance or channel magic. Each focus has:\n- Type (Sustaining, Weapon, Spell, etc.)\n- Force (power level)\n\n**Special Rules**\n- Must be bound with karma\n- Can be overloaded or corrupted",
    "Traditions": "**Magical Traditions**\n\nDifferent approaches to magic:\n- Hermetic (Logic-based)\n- Shamanic (Charisma-based)\n- Christian Theurgy (Willpower-based)\n- Buddhist (Intuition-based)\n\n**Special Rules**\n- Tradition determines drain resistance attribute\n- Affects spirit types that can be summoned",
    "Motorcycle": "**Motorcycle**\n\n- Speed: 4\n- Handling: 5\n- Accel: 3\n- Body: 8\n- Armor: 6\n- Pilot: 1\n- Sensor: 1\n- Seats: 2\n- Price: 15,000¥",
    "Sedan": "**Sedan**\n\n- Speed: 3\n- Handling: 4\n- Accel: 2\n- Body: 12\n- Armor: 10\n- Pilot: 1\n- Sensor: 2\n- Seats: 4\n- Price: 25,000¥",
    "Sports Car": "**Sports Car**\n\n- Speed: 5\n- Handling: 5\n- Accel: 4\n- Body: 10\n- Armor: 8\n- Pilot: 2\n- Sensor: 3\n- Seats: 2\n- Price: 75,000¥",
    "Truck": "**Truck**\n\n- Speed: 2\n- Handling: 3\n- Accel: 1\n- Body: 18\n- Armor: 15\n- Pilot: 1\n- Sensor: 1\n- Seats: 3\n- Price: 40,000¥",
    "Helicopter": "**Helicopter**\n\n- Speed: 4\n- Handling: 4\n- Accel: 2\n- Body: 14\n- Armor: 10\n- Pilot: 3\n- Sensor: 4\n- Seats: 6\n- Price: 200,000¥",
    "Drone": "**Drone**\n\n- Speed: 3\n- Handling: 4\n- Accel: 2\n- Body: 6\n- Armor: 4\n- Pilot: 1\n- Sensor: 2\n- Seats: 0\n- Price: 10,000¥",
    "Free Action": "**Free Action**\n\nCan be performed any time during your turn\n- Speak a few words\n- Drop an item\n- Change gun mode\n- Take a small step",
    "Simple Action": "**Simple Action**\n\nRequires a simple action\n- Fire a weapon (simple)\n- Cast a spell\n- Make a skill test\n- Move up to walking speed",
    "Interrupt Action": "**Interrupt Action**\n\nCan be performed outside your turn\n- Defensive actions\n- Dodging\n- Using Edge",
    "Change Gun Mode": "**Change Gun Mode**\n\nSwitch between firing modes:\n- Single Shot (SS)\n- Semi-Automatic (SA)\n- Burst Fire (BF)\n- Full Automatic (FA)",
    "Complex Action": "**Complex Action**\n\nRequires significant effort\n- Full attack\n- Complex spell casting\n- Hacking attempt\n- Reloading",
    "Full Attack": "**Full Attack**\n\nUnleash a powerful attack\n- Add Edge to attack pool\n- Multiple attacks in one action\n- Requires complex action",
    "Combat": "**Combat Sequence**\n1. Roll initiative\n2. Characters act in initiative order\n3. Repeat for each combat turn\n\n**Actions**\n- Simple Action (1 per turn)\n- Complex Action (1 per turn)\n- Free Action (multiple)",
    "Magic System": "**Magic Rules**\n- Magic Rating determines spell power\n- Drain is physical/stun damage from spellcasting\n- Counterspelling defends against magic\n- Sustaining spells causes penalty",
    "Hacking": "**Matrix Actions**\n- Brute Force (attack)\n- Hack on the Fly (stealth)\n- Matrix Perception (detection)\n\n**Devices**\n- All devices have device rating (1-6)",
    "Vehicles": "**Vehicle Combat**\n- Piloting tests for maneuvers\n- Vehicle stats: Handling, Speed, Accel\n\n**Rigging**\n- Riggers can jump into vehicles directly",
    "Complex Forms": "**Complex Forms**\n\nA Technomancer's Resonance-compiled equivalent of spells. Each has:\n- Target: what it affects (Device, File, Persona, Sprite, Self)\n- Fade value (like Drain, but resisted with Resonance instead of Willpower)\n\n**Compiling**\n- Compiling + Resonance [Level] vs. Fade\n- No reagents or foci needed -- just Resonance and Living Persona",
    "Rituals": "**Rituals**\n\nGroup castings that trade speed for power. Each ritual has:\n- Type: Ritual\n- Drain value\n\n**Casting**\n- Ritual Spellcasting + Magic, extended test vs. the ritual's Threshold\n- Usually needs a material link to the target and takes hours, not seconds\n- Recorded and rolled the same way as a Spell in this app",
    "Enchantments": "**Alchemical Preparations**\n\nSingle-use items created with the Enchanting skill that deliver a spell's effect later, via a trigger, instead of casting it live.\n- Force: sets the preparation's power, same as a spell's Force\n- Binding: the trigger condition (Command, Contact, Time, ...)\n\n**Special Rules**\n- Drain is paid by the enchanter at creation time, not by whoever triggers it\n- Listed under Magic Items -- add one from \"Use Predefined\" in the Gear tab",
    "Qualities": "**Qualities**\n\nPositive qualities cost Karma; negative qualities award it. Both can grant a mechanical effect -- an attribute bonus, extra condition-monitor boxes, or just the Karma itself.\n\nSee the Qualities tab for the full list and to add/remove them on your character; each one's exact Karma cost and effect is shown there.",
}


class WikiTabMixin:
    def setup_wiki_tab(self):
        tab = self.tabs["Wiki"]

        paned_window = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tree_frame = ttk.Frame(paned_window, width=200)
        paned_window.add(tree_frame, weight=1)

        self.wiki_tree = ttk.Treeview(tree_frame, show="tree")
        self.wiki_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        categories = {
            "Gear": ShadowrunCharacter.GEAR_CATEGORIES,
            "Magic": ["Spells", "Rituals", "Powers", "Foci", "Enchantments", "Complex Forms", "Traditions"],
            "Vehicles": ShadowrunCharacter.VEHICLE_TYPES,
            "Actions": ["Minor Actions", "Major Actions", "Matrix Actions"],
            "Qualities": ["Positive Qualities", "Negative Qualities"],
            "Rules": ["Combat", "Magic System", "Hacking", "Vehicles"]
        }

        self.wiki_items = {}
        for category, subcategories in categories.items():
            parent = self.wiki_tree.insert("", "end", text=category, open=True)
            for sub in subcategories:
                self.wiki_items[sub] = self.wiki_tree.insert(parent, "end", text=sub)

        wiki_data = dict(WIKI_TOPICS)

        for category in ShadowrunCharacter.GEAR_CATEGORIES:
            parent_id = self.wiki_items.get(category)
            for item in ShadowrunCharacter.PREDEFINED_GEAR.get(category, []):
                if parent_id:
                    self.wiki_tree.insert(parent_id, "end", text=item["name"])
                content = f"**{item['name']}**\n\n"
                for key, value in item.items():
                    if key not in ("name", "Price"):
                        content += f"- {key}: {value}\n"
                content += f"\nPrice: {item.get('Price', 'N/A')}¥"
                wiki_data[item["name"]] = content

        for spell in ShadowrunCharacter.PREDEFINED_SPELLS:
            parent_id = self.wiki_items.get("Spells")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=spell["name"])
            wiki_data[spell["name"]] = (f"**{spell['name']}**\n\nType: {spell.get('type', '')}\n"
                                        f"Drain: {spell.get('drain', '')}\n\n{spell.get('description', '')}")

        for power in ShadowrunCharacter.PREDEFINED_POWERS:
            parent_id = self.wiki_items.get("Powers")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=power["name"])
            wiki_data[power["name"]] = (f"**{power['name']}**\n\nActivation: {power.get('activation', '')}\n"
                                        f"Effect: {power.get('effect', '')}\n\n{power.get('description', '')}")

        for focus in ShadowrunCharacter.PREDEFINED_FOCI:
            parent_id = self.wiki_items.get("Foci")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=focus["name"])
            wiki_data[focus["name"]] = (f"**{focus['name']}**\n\nType: {focus.get('type', '')}\n"
                                        f"Force: {focus.get('force', '')}\n\n{focus.get('description', '')}")

        for ritual in ShadowrunCharacter.PREDEFINED_RITUALS:
            parent_id = self.wiki_items.get("Rituals")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=ritual["name"])
            wiki_data[ritual["name"]] = (f"**{ritual['name']}**\n\nType: {ritual.get('type', '')}\n"
                                         f"Drain: {ritual.get('drain', '')}\n\n{ritual.get('description', '')}")

        for form in ShadowrunCharacter.PREDEFINED_COMPLEX_FORMS:
            parent_id = self.wiki_items.get("Complex Forms")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=form["name"])
            wiki_data[form["name"]] = (f"**{form['name']}**\n\nTarget: {form.get('target', '')}\n"
                                       f"Fade: {form.get('fade', '')}\n\n{form.get('description', '')}")

        for prep in ShadowrunCharacter.PREDEFINED_ENCHANTMENTS:
            parent_id = self.wiki_items.get("Enchantments")
            if parent_id:
                self.wiki_tree.insert(parent_id, "end", text=prep["name"])
            wiki_data[prep["name"]] = (f"**{prep['name']}**\n\nForce: {prep.get('Force', '')}\n"
                                       f"Trigger: {prep.get('Binding', '')}\n\nPrice: {prep.get('Price', 'N/A')}¥")

        minor_parent = self.wiki_items.get("Minor Actions")
        if minor_parent:
            for action in ShadowrunCharacter.MINOR_ACTIONS:
                self.wiki_tree.insert(minor_parent, "end", text=action)
        major_parent = self.wiki_items.get("Major Actions")
        if major_parent:
            for action in ShadowrunCharacter.MAJOR_ACTIONS:
                self.wiki_tree.insert(major_parent, "end", text=action)

        matrix_parent = self.wiki_items.get("Matrix Actions")
        if matrix_parent:
            for action, description in ShadowrunCharacter.MATRIX_ACTIONS.items():
                self.wiki_tree.insert(matrix_parent, "end", text=action)
                wiki_data[action] = f"**{action}**\n\n{description}"

        pos_parent = self.wiki_items.get("Positive Qualities")
        if pos_parent:
            for quality in ShadowrunCharacter.QUALITIES["Positive"]:
                self.wiki_tree.insert(pos_parent, "end", text=quality)
                wiki_data[quality] = self._quality_wiki_text(quality)
        neg_parent = self.wiki_items.get("Negative Qualities")
        if neg_parent:
            for quality in ShadowrunCharacter.QUALITIES["Negative"]:
                self.wiki_tree.insert(neg_parent, "end", text=quality)
                wiki_data[quality] = self._quality_wiki_text(quality)

        self._wiki_data = wiki_data

        content_frame = ttk.Frame(paned_window)
        paned_window.add(content_frame, weight=3)

        self.wiki_content = scrolledtext.ScrolledText(
            content_frame, wrap=tk.WORD, bg=theme.ENTRY_BG, fg=theme.FG,
            font=("Arial", 10), state=tk.DISABLED
        )
        self.wiki_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.wiki_tree.bind("<<TreeviewSelect>>", self.display_wiki_content)

    def _quality_wiki_text(self, quality):
        effect = ShadowrunCharacter.QUALITY_EFFECTS.get(quality, {})
        karma = effect.get("karma", 0)
        karma_text = f"Costs {karma} Karma" if karma > 0 else (f"Awards {-karma} Karma" if karma < 0 else "No Karma cost")
        mechanical = [f"{k}: {'+' if v > 0 else ''}{v}" for k, v in effect.items() if k != "karma"]
        mechanical_text = ("\n".join(mechanical)) if mechanical else "No numeric mechanical effect -- roleplay only."
        return f"**{quality}**\n\n{karma_text}\n\n{mechanical_text}"

    def display_wiki_content(self, event):
        selected = self.wiki_tree.selection()
        if not selected:
            return

        item = self.wiki_tree.item(selected[0])
        item_text = item["text"]
        parent = self.wiki_tree.parent(selected[0])
        parent_text = self.wiki_tree.item(parent)["text"] if parent else ""

        content = self._wiki_data.get(item_text) or self._wiki_data.get(parent_text) or \
            "No information available for this topic."

        formatted_content = ""
        for line in content.split("\n"):
            formatted_content += ("\n" + line + "\n") if line.startswith("**") else (line + "\n")

        self.wiki_content.config(state=tk.NORMAL)
        self.wiki_content.delete("1.0", tk.END)
        self.wiki_content.insert(tk.END, f"=== {item_text} ===\n\n{formatted_content}")
        self.wiki_content.config(state=tk.DISABLED)
