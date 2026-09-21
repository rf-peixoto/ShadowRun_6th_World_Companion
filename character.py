"""Character data model for the Shadowrun 6E manager.

This is the merged/fixed version of what used to be ``wip_main.py``'s
``ShadowrunCharacter`` class. Behavior fixes made while merging (see
README.md "Changelog" for the full list):

- ``calculate_derived_stats`` used to blindly overwrite ``self.attributes``
  with a copy of ``base_attributes`` *after* gear bonuses (Essence loss,
  Armor, Weapon Accuracy) had just been computed, silently discarding them
  every time. Everything is now computed in a single ``recalculate()`` pass
  so gear bonuses always stick.
- Armor Rating and Weapon Accuracy are now their own fields
  (``armor_rating`` / ``weapon_accuracy``) instead of being stuffed into the
  ``attributes`` dict, which was never meant to hold anything but the twelve
  core attributes.
- ``roll_dice`` used to reach into a GUI widget (``self.roll_combo``) that
  doesn't exist on this class at all -- using the "Battle Hardened" Edge
  option crashed every time. It now takes an explicit ``roll_type`` string.
- Edge points spent on an Edge action were never actually deducted from
  ``current_edge``. They are now.
- The Wild Die house rule double-counted exploding 6s in some sequences.
  Rewritten to count each 6 once.
- Runs (missions) now live on the character itself (``self.runs``), so a
  character's whole campaign state is one ``.sr6`` file.
- Added portrait support (the code imported PIL but never used it).
"""

import base64
import io
import random

from runs import ShadowrunRun

try:
    from PIL import Image
except ImportError:  # Pillow is optional; portraits just won't be available.
    Image = None


class ShadowrunCharacter:
    METATYPES = ["Human", "Elf", "Dwarf", "Ork", "Troll"]
    ATTRIBUTES = ["Body", "Agility", "Reaction", "Strength", "Willpower",
                  "Logic", "Intuition", "Charisma", "Edge", "Magic",
                  "Resonance", "Essence"]
    SKILLS = ["Astral", "Athletics", "Biotech", "Close Combat", "Con",
              "Conjuring", "Cracking", "Electronics", "Enchanting", "Engineering",
              "Exotic Weapons", "Firearms", "Influence", "Outdoors", "Perception",
              "Piloting", "Sorcery", "Stealth", "Tasking"]

    SKILL_SPECIALIZATIONS = {
        "Firearms": ["Pistols", "Rifles", "Shotguns", "Machine Guns"],
        "Close Combat": ["Blades", "Clubs", "Unarmed Combat"],
        "Stealth": ["Urban", "Wilderness", "Vehicle"],
        "Perception": ["Visual", "Auditory", "Scent"],
        "Con": ["Fast Talk", "Impersonation", "Seduction"],
        "Electronics": ["Cyberdecks", "Commlinks", "Security Systems"],
        "Engineering": ["Aeronautics", "Automotive", "Marine"],
        "Biotech": ["First Aid", "Medicine", "Cybertechnology"],
        "Cracking": ["Hacking", "Cybercombat", "Electronic Warfare"],
        "Tasking": ["Compiling", "Decompiling", "Registering"],
        "Sorcery": ["Combat Spells", "Health Spells", "Illusion Spells"],
        "Conjuring": ["Summoning", "Banishing", "Binding"],
        "Enchanting": ["Alchemy", "Disenchanting", "Artificing"],
        "Influence": ["Leadership", "Negotiation", "Intimidation"],
        "Outdoors": ["Navigation", "Survival", "Tracking"],
        "Piloting": ["Ground Craft", "Aircraft", "Watercraft"],
        "Astral": ["Astral Combat", "Astral Tracking", "Astral Perception"]
    }

    MAGIC_TYPES = ["Mundane", "Magician", "Adept", "Aspected Magician", "Mystic Adept", "Technomancer"]
    LIFESTYLES = ["Street", "Squatter", "Low", "Middle", "High", "Luxury"]
    LIFESTYLE_NUYEN = {
        "Street": 1000,
        "Squatter": 2000,
        "Low": 5000,
        "Middle": 10000,
        "High": 100000,
        "Luxury": 1000000
    }

    ROLES = {
        "Street Samurai": {"Body": 1, "Agility": 1},
        "Decker": {"Logic": 2, "Intuition": 1},
        "Rigger": {"Reaction": 2, "Logic": 1},
        "Face": {"Charisma": 2, "Intuition": 1},
        "Mage": {"Magic": 2, "Willpower": 1},
        "Shaman": {"Magic": 2, "Charisma": 1},
        "Adept": {"Magic": 2, "Agility": 1},
        "Technomancer": {"Resonance": 2, "Logic": 1}
    }

    TRADITIONS = ["None", "Hermetic", "Shamanic", "Christian Theurgy", "Buddhist", "Islamic", "Voodoo"]

    QUALITIES = {
        "Positive": ["Adept", "Ambidextrous", "Analytical Mind", "Astral Chameleon",
                     "Blandness", "Catlike", "Double-Jointed", "Guts", "High Pain Tolerance",
                     "Home Ground", "Human-Looking", "Indomitable", "Juryrigger", "Lucky",
                     "Magical Resistance", "Natural Athlete", "Photographic Memory",
                     "Quick Healer", "Spirit Affinity", "Toughness", "Will to Live"],
        "Negative": ["Addiction", "Allergy", "Astral Beacon", "Bad Luck", "Bad Rep",
                     "Code of Honor", "Dependents", "Gremlins", "Incompetent", "Insomnia",
                     "Magic Sense", "Mild Phobia", "Sensitive System", "Simsense Vertigo",
                     "Social Stress", "Spirit Bane", "Uncouth", "Uneducated"]
    }

    # Every quality's mechanical effect and Karma cost. "karma" is the cost
    # to take a positive quality (paid) or the Karma awarded for a negative
    # one (stored negative -- see add_pos_quality/add_neg_quality in
    # gui_skills.py). Any other key is either an attribute name (applied as
    # a flat bonus in recalculate()) or one of the special keys "Physical
    # Boxes"/"Stun Boxes" (added to the condition monitors). Qualities with
    # no numeric mechanical effect still get a Karma cost so the economy
    # works, even though recalculate() has nothing further to apply.
    QUALITY_EFFECTS = {
        # -- Positive --
        "Adept": {"karma": 5},
        "Ambidextrous": {"Agility": 1, "karma": 6},
        "Analytical Mind": {"Logic": 1, "karma": 7},
        "Astral Chameleon": {"karma": 5},
        "Blandness": {"karma": 8},
        "Catlike": {"Agility": 1, "karma": 9},
        "Double-Jointed": {"karma": 6},
        "Guts": {"karma": 8},
        "High Pain Tolerance": {"Physical Boxes": 2, "Stun Boxes": 2, "karma": 7},
        "Home Ground": {"karma": 5},
        "Human-Looking": {"karma": 7},
        "Indomitable": {"Willpower": 1, "karma": 8},
        "Juryrigger": {"karma": 7},
        "Lucky": {"Edge": 1, "karma": 12},
        "Magical Resistance": {"karma": 10},
        "Natural Athlete": {"Strength": 1, "Agility": 1, "karma": 10},
        "Photographic Memory": {"karma": 7},
        "Quick Healer": {"karma": 8},
        "Spirit Affinity": {"karma": 7},
        "Toughness": {"Body": 1, "karma": 9},
        "Will to Live": {"Physical Boxes": 3, "karma": 7},
        # -- Negative (karma is negative: Karma awarded for taking it) --
        "Addiction": {"karma": -8},
        "Allergy": {"karma": -10},
        "Astral Beacon": {"karma": -5},
        "Bad Luck": {"karma": -12},
        "Bad Rep": {"karma": -7},
        "Code of Honor": {"karma": -8},
        "Dependents": {"karma": -8},
        "Gremlins": {"karma": -8},
        "Incompetent": {"Logic": -1, "Intuition": -1, "karma": -14},
        "Insomnia": {"karma": -8},
        "Magic Sense": {"karma": -5},
        "Mild Phobia": {"karma": -5},
        "Sensitive System": {"karma": -12},
        "Simsense Vertigo": {"karma": -5},
        "Social Stress": {"karma": -8},
        "Spirit Bane": {"karma": -8},
        "Uncouth": {"Charisma": -2, "karma": -12},
        "Uneducated": {"Logic": -2, "karma": -10},
    }

    GEAR_CATEGORIES = ["Weapons", "Armor", "Cyberware", "Bioware", "Magic Items", "Electronics", "Medkits", "Other"]
    WEAPON_TYPES = ["Blades", "Clubs", "Thrown", "Pistols", "Rifles", "Shotguns", "Machine Guns", "Special"]
    ARMOR_TYPES = ["Clothing", "Armor Jacket", "Full Body Armor", "Helmet", "Shield"]
    CYBERWARE_TYPES = ["Headware", "Eyeware", "Earware", "Bodyware", "Cyberlimbs", "Implants"]
    MEDKIT_TYPES = ["Rating 1", "Rating 3", "Rating 6", "Rating 10"]

    CONTACT_TYPES = ["Fixer", "Johnson", "Gang", "Corporate", "Police", "Media", "Talislegger", "Decker", "Street Doc"]
    LOYALTY_LEVELS = ["Unknown", "Known", "Transactional", "Regular", "Professional", "Respectful",
                      "Reliable", "Supportive", "Loyal", "Devoted", "Family"]

    EDGE_ACTIONS = {
        "Reroll Non-Hits (1 Edge)": 1,
        "Seal Fate (1 Edge)": 1,
        "Push the Limit (4 Edge)": 4,
        "Heroic Effort (3 Edge)": 3,
        "Battle Hardened (2 Edge)": 2
    }

    DICE_ROLL_OPTIONS = [
        "Attack (Physical)",
        "Attack (Spell)",
        "Attack (Ranged)",
        "Defense (Physical)",
        "Defense (Astral)",
        "Hacking",
        "Con",
        "Perception",
        "Stealth",
        "First Aid",
        "Piloting",
        "Summoning",
        "Binding",
        "Banishing",
        "Ritual Spellcasting",
        "Alchemy",
        "Matrix Perception",
        "Brute Force (Matrix)",
        "Hack on the Fly",
        "Data Spike",
    ]

    # Matrix combat/hacking actions (p.180+), for the Wiki and as a reference
    # for what to roll -- distinct from the sketch-grid element types in
    # MATRIX_ICONS below.
    MATRIX_ACTIONS = {
        "Matrix Perception": "Simple Action. Logic + Intuition vs. host/icon's Sleaze. Spot a hidden icon, mark, or host.",
        "Brute Force": "Complex Action. Cracking + Logic vs. target's Firewall. Force your way past a target's defenses noisily.",
        "Hack on the Fly": "Complex Action. Cracking + Logic vs. target's Firewall. Quietly gain access, at a dice pool penalty.",
        "Data Spike": "Complex Action. Cracking + Logic vs. target's Firewall. Deal Matrix damage to a device or persona.",
        "Crash Program": "Complex Action. Cracking + Logic vs. target's Firewall. Disable a running program or device function.",
        "Trace Icon": "Complex Action. Reveal an icon's real-world physical location.",
        "Jam Signal": "Complex Action. Electronics + Logic. Disrupt wireless signals in an area.",
        "Reboot Device": "Complex Action. Restart a device, clearing marks and stopping running programs.",
        "Full Matrix Defense": "Complex Action. Add Willpower to all Matrix defense tests until your next turn.",
        "Erase Mark": "Simple Action. Cracking + Logic vs. target's Willpower. Remove one of your marks from an icon.",
    }

    PREDEFINED_SPELLS = [
        {"name": "Power Bolt", "type": "Combat", "drain": "F-3", "description": "Direct combat spell that deals physical damage to a single target."},
        {"name": "Stun Bolt", "type": "Combat", "drain": "F-4", "description": "Direct combat spell that deals stun damage to a single target."},
        {"name": "Fireball", "type": "Combat", "drain": "F-1", "description": "Indirect combat spell dealing physical damage in an area."},
        {"name": "Lightning Bolt", "type": "Combat", "drain": "F-2", "description": "Indirect combat spell dealing physical damage, hard to resist with cover."},
        {"name": "Acid Stream", "type": "Combat", "drain": "F-3", "description": "Direct combat spell that also damages armor and gear."},
        {"name": "Heal", "type": "Health", "drain": "F-4", "description": "Heals physical damage on the target."},
        {"name": "Detox", "type": "Health", "drain": "F-3", "description": "Neutralizes toxins in the target's system."},
        {"name": "Increase Reflexes", "type": "Health", "drain": "F-2", "description": "Temporarily boosts the target's Reaction and initiative."},
        {"name": "Resist Pain", "type": "Health", "drain": "F-3", "description": "Suppresses wound modifiers for the duration."},
        {"name": "Invisibility", "type": "Illusion", "drain": "F-4", "description": "Makes the target very hard to see."},
        {"name": "Silence", "type": "Illusion", "drain": "F-4", "description": "Removes all sound from the area of effect."},
        {"name": "Mask", "type": "Illusion", "drain": "F-3", "description": "Changes the caster's or target's apparent appearance."},
        {"name": "Chaos", "type": "Illusion", "drain": "F-2", "description": "Floods a target's sense with confusing false input."},
        {"name": "Levitate", "type": "Manipulation", "drain": "F-2", "description": "Allows the target to float and move through the air."},
        {"name": "Control Thoughts", "type": "Manipulation", "drain": "F-1", "description": "Lets the caster direct the target's next thought or action."},
        {"name": "Magic Fingers", "type": "Manipulation", "drain": "F-4", "description": "Telekinetically manipulates small objects at a distance."},
        {"name": "Armor", "type": "Manipulation", "drain": "F-3", "description": "Grants the target temporary armor rating."},
        {"name": "Manabolt", "type": "Combat", "drain": "F-2", "description": "Direct combat spell resisted by Willpower alone -- ignores physical armor."},
        {"name": "Stunbolt", "type": "Combat", "drain": "F-3", "description": "Direct combat spell dealing stun damage, resisted by Willpower."},
        {"name": "Deadly Wind", "type": "Combat", "drain": "F+1", "description": "Indirect area combat spell that shreds anything caught in it."},
        {"name": "Antidote", "type": "Health", "drain": "F-2", "description": "Removes a specific toxin from the target's system."},
        {"name": "Cure Disease", "type": "Health", "drain": "F-1", "description": "Cures a disease afflicting the target."},
        {"name": "Trid Phantasm", "type": "Illusion", "drain": "F-3", "description": "Creates a realistic illusion affecting all senses."},
        {"name": "Physical Barrier", "type": "Manipulation", "drain": "F-2", "description": "Creates a solid, physical wall out of nothing."},
        {"name": "Fling", "type": "Manipulation", "drain": "F-3", "description": "Telekinetically hurls an object at a target as a weapon."},
    ]

    PREDEFINED_POWERS = [
        {"name": "Improved Reflexes", "activation": "Passive", "effect": "+1 Reaction, +1D6 Initiative", "Reaction": "1", "Initiative Dice": "1", "Cost": "2.5", "description": "Improves reaction time and initiative."},
        {"name": "Combat Sense", "activation": "Passive", "effect": "+1 Defense Rating", "Cost": "1.5", "description": "Enhances combat awareness, granting a bonus to defense tests."},
        {"name": "Killing Hands", "activation": "Simple Action", "effect": "Unarmed attacks deal physical damage", "Cost": "0.5", "description": "Channels energy into unarmed strikes so they deal physical rather than stun damage."},
        {"name": "Astral Perception", "activation": "Simple Action", "effect": "See into astral space", "Cost": "0.25", "description": "Perceives astral space at will."},
        {"name": "Pain Resistance", "activation": "Passive", "effect": "Ignore wound modifiers", "Cost": "0.5", "description": "Reduces the effect of pain, softening damage penalties."},
        {"name": "Improved Physical Attribute (Body)", "activation": "Passive", "effect": "+1 Body", "Body": "1", "Cost": "1", "description": "Adept training that raises the Body attribute."},
        {"name": "Improved Physical Attribute (Agility)", "activation": "Passive", "effect": "+1 Agility", "Agility": "1", "Cost": "1", "description": "Adept training that raises the Agility attribute."},
        {"name": "Improved Physical Attribute (Strength)", "activation": "Passive", "effect": "+1 Strength", "Strength": "1", "Cost": "1", "description": "Adept training that raises the Strength attribute."},
        {"name": "Mystic Armor", "activation": "Passive", "effect": "+3 Armor", "Armor": "3", "Cost": "1.5", "description": "Wraps the adept in a mystic barrier that adds to their Armor Rating."},
        {"name": "Improved Sense (Low-Light Vision)", "activation": "Passive", "effect": "See in low light", "Cost": "0.5", "description": "Grants low-light vision."},
        {"name": "Rapid Healing", "activation": "Passive", "effect": "Faster natural healing", "Cost": "0.5", "description": "Speeds up the character's natural recovery from damage."},
        {"name": "Enhanced Accuracy (Firearms)", "activation": "Passive", "effect": "+1 Accuracy with a chosen firearm", "Cost": "0.25", "description": "Hones the adept's aim with a specific firearm."},
        {"name": "Improved Physical Attribute (Reaction)", "activation": "Passive", "effect": "+1 Reaction", "Reaction": "1", "Cost": "1", "description": "Adept training that raises the Reaction attribute."},
        {"name": "Improved Reflexes (Rating 2)", "activation": "Passive", "effect": "+2 Reaction, +2D6 Initiative", "Reaction": "2", "Initiative Dice": "2", "Cost": "5", "description": "A stronger version of Improved Reflexes."},
        {"name": "Nerve Strike", "activation": "Simple Action", "effect": "Unarmed strikes can stun on a called shot", "Cost": "0.5", "description": "Focuses ki into pressure-point strikes."},
        {"name": "Traceless Walk", "activation": "Passive", "effect": "Leaves no tracks or scent", "Cost": "0.25", "description": "Adept training in silent, trackless movement."},
        {"name": "Voice Control", "activation": "Passive", "effect": "+2 dice to Con tests using voice", "Cost": "0.5", "description": "Fine control over vocal tone and mimicry."},
        {"name": "Mystic Armor (Rating 2)", "activation": "Passive", "effect": "+6 Armor", "Armor": "6", "Cost": "3", "description": "A stronger mystic barrier."},
    ]

    PREDEFINED_FOCI = [
        {"name": "Power Focus", "type": "Power", "force": 3, "description": "Bonded, adds its Force directly to the caster's Magic attribute."},
        {"name": "Weapon Focus", "type": "Weapon", "force": 2, "description": "Enhances a specific melee weapon with its Force in dice/damage."},
        {"name": "Spellcasting Focus", "type": "Spell", "force": 1, "description": "Adds its Force to a specific spell's casting pool."},
        {"name": "Sustaining Focus", "type": "Sustaining", "force": 2, "description": "Sustains a spell for the caster without an ongoing dice pool penalty."},
        {"name": "Qi Focus", "type": "Adept", "force": 2, "description": "Enhances a specific adept power."},
        {"name": "Binding Focus", "type": "Binding", "force": 3, "description": "Aids in binding a specific type of spirit."},
        {"name": "Centering Focus", "type": "Adept", "force": 2, "description": "Reduces drain when used with a specific linked action."},
        {"name": "Attunement Focus", "type": "Spell", "force": 1, "description": "Improves the caster's connection to their tradition."},
    ]

    # Complex Forms: a Technomancer's equivalent of spells, compiled from
    # Resonance rather than cast from Magic. Added/edited/removed the same
    # way as Spells (own sub-tab under Magic/Resonance, own predefined
    # picker) -- see gui_magic.py and dialogs.PREDEFINED_SOURCES.
    PREDEFINED_COMPLEX_FORMS = [
        {"name": "Resonance Spike", "target": "Persona", "fade": "F-2", "description": "Deals Matrix damage to a target persona, resisted with Resonance."},
        {"name": "Diffusion", "target": "Device", "fade": "F-1", "description": "Reduces a device's Firewall for the duration."},
        {"name": "Editor", "target": "File", "fade": "F-3", "description": "Alters a file undetectably as it's being accessed."},
        {"name": "Cleaner", "target": "Persona", "fade": "F-3", "description": "Erases the technomancer's tracks from a system's logs."},
        {"name": "Puppeteer", "target": "Device", "fade": "F+1", "description": "Takes remote control of a device's actions for the duration."},
        {"name": "Static Veil", "target": "Persona", "fade": "F-2", "description": "Hides the technomancer's icon, granting improved Sleaze."},
        {"name": "Tattletale", "target": "Persona", "fade": "F-1", "description": "Warns the technomancer if a specific icon takes an action."},
    ]

    # Rituals: slower, more powerful group castings (Ritual Spellcasting +
    # Magic, extended test over the ritual's Threshold). Selectable the same
    # way as Spells -- via EditGearDialog's "Use Predefined" for the Spell
    # category (see dialogs.PREDEFINED_SOURCES) -- since they're recorded on
    # a character the same way, just tagged with Type "Ritual".
    PREDEFINED_RITUALS = [
        {"name": "Curse", "type": "Ritual", "drain": "F-1", "description": "A slow-acting ritual that inflicts a lingering run of bad luck on a target the caster has a link to."},
        {"name": "Doom", "type": "Ritual", "drain": "F+2", "description": "An extremely dangerous ritual that deals heavy damage to a target over time; needs a strong material link."},
        {"name": "Circle of Protection", "type": "Ritual", "drain": "F-2", "description": "Wards a warded area against astral and spirit intrusion for the ritual's duration."},
        {"name": "Mindlink", "type": "Ritual", "drain": "F-3", "description": "Links participants' minds together, letting them share thoughts and sensation."},
        {"name": "Remote Viewing", "type": "Ritual", "drain": "F-2", "description": "Lets the caster's consciousness observe a distant location they have a link to."},
        {"name": "Wandering Spirit", "type": "Ritual", "drain": "F-1", "description": "Summons a spirit tied to a specific location, even from far away."},
        {"name": "Hound's Nose", "type": "Ritual", "drain": "F-3", "description": "Grants participants a tracking sense keyed to a specific target."},
    ]

    # Alchemical preparations from the Enchanting skill: single-use items
    # that deliver a spell's effect via triggered container instead of
    # casting it live. Listed as predefined "Magic Items" gear (Type
    # "Preparation") since, like a spell formula, they're something you buy,
    # craft, or find rather than a live-cast action.
    PREDEFINED_ENCHANTMENTS = [
        {"name": "Stun Bolt Preparation (Force 4)", "Force": "4", "Type": "Preparation", "Binding": "Trigger: Contact", "Price": 400},
        {"name": "Armor Preparation (Force 3)", "Force": "3", "Type": "Preparation", "Binding": "Trigger: Command", "Price": 300},
        {"name": "Invisibility Preparation (Force 4)", "Force": "4", "Type": "Preparation", "Binding": "Trigger: Command", "Price": 400},
        {"name": "Detect Enemies Preparation (Force 3)", "Force": "3", "Type": "Preparation", "Binding": "Trigger: Time", "Price": 300},
    ]

    # Cyberware/Bioware/Power items may carry extra keys named after an
    # attribute in ATTRIBUTES (e.g. "Reaction": "1") to grant a flat bonus,
    # and/or an "Initiative Dice" key to add bonus initiative dice. Both are
    # picked up automatically by ``recalculate()`` -- no separate wiring
    # needed to add more predefined (or custom) items like this.
    PREDEFINED_GEAR = {
        "Weapons": [
            {"name": "Ares Predator V", "Damage": "5P", "Accuracy": "5", "AP": "-1", "Mode": "SA", "RC": "0", "Ammo": "15", "Type": "Pistols", "Price": 800},
            {"name": "Colt America L36", "Damage": "4P", "Accuracy": "6", "AP": "0", "Mode": "SA", "RC": "0", "Ammo": "11", "Type": "Pistols", "Price": 320},
            {"name": "Fichetti Security 600", "Damage": "3P", "Accuracy": "7", "AP": "0", "Mode": "SA/BF", "RC": "0", "Ammo": "30", "Type": "Pistols", "Price": 500},
            {"name": "Remington Roomsweeper", "Damage": "4P", "Accuracy": "4", "AP": "-1", "Mode": "SS", "RC": "0", "Ammo": "5", "Type": "Shotguns", "Price": 450},
            {"name": "Defiance EX Shocker", "Damage": "9S(e)", "Accuracy": "4", "AP": "-5", "Mode": "SS", "RC": "0", "Ammo": "4", "Type": "Shotguns", "Price": 700},
            {"name": "AK-97", "Damage": "6P", "Accuracy": "5", "AP": "-2", "Mode": "SA/BF/FA", "RC": "1", "Ammo": "38", "Type": "Rifles", "Price": 1200},
            {"name": "Remington 950", "Damage": "9P", "Accuracy": "6", "AP": "-4", "Mode": "SS", "RC": "0", "Ammo": "6", "Type": "Rifles", "Price": 2600},
            {"name": "Ultimax 100", "Damage": "8P", "Accuracy": "4", "AP": "-4", "Mode": "BF/FA", "RC": "2", "Ammo": "100", "Type": "Machine Guns", "Price": 4000},
            {"name": "Ares MP-LMG", "Damage": "9P", "Accuracy": "5", "AP": "-3", "Mode": "FA", "RC": "3", "Ammo": "50", "Type": "Machine Guns", "Price": 6500},
            {"name": "Combat Knife", "Damage": "3P", "Accuracy": "6", "AP": "-1", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Blades", "Price": 100},
            {"name": "Katana", "Damage": "5P", "Accuracy": "7", "AP": "-2", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Blades", "Price": 900},
            {"name": "Stun Baton", "Damage": "7S(e)", "Accuracy": "5", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Clubs", "Price": 750},
            {"name": "Telescoping Combat Staff", "Damage": "6P", "Accuracy": "6", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Clubs", "Price": 350},
            {"name": "Throwing Knife", "Damage": "2P", "Accuracy": "4", "AP": "-1", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Thrown", "Price": 25},
            {"name": "Fragmentation Grenade", "Damage": "9P", "Accuracy": "4", "AP": "-2", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Thrown", "Price": 100},
            {"name": "Defiance EX Shocker Taser", "Damage": "7S(e)", "Accuracy": "4", "AP": "-5", "Mode": "SS", "RC": "0", "Ammo": "4", "Type": "Special", "Price": 250},
            {"name": "Browning Ultra-Power", "Damage": "6P", "Accuracy": "5", "AP": "-1", "Mode": "SA", "RC": "0", "Ammo": "10", "Type": "Pistols", "Price": 640},
            {"name": "Ruger Super Warhawk", "Damage": "7P", "Accuracy": "5", "AP": "-1", "Mode": "SS", "RC": "0", "Ammo": "6", "Type": "Pistols", "Price": 380},
            {"name": "Enfield AS-7", "Damage": "5P", "Accuracy": "5", "AP": "-1", "Mode": "SA/BF", "RC": "0", "Ammo": "10", "Type": "Shotguns", "Price": 730},
            {"name": "HK XM30", "Damage": "5P", "Accuracy": "6", "AP": "-1", "Mode": "SA/BF/FA", "RC": "2", "Ammo": "40", "Type": "Rifles", "Price": 2600},
            {"name": "Ares Alpha", "Damage": "6P", "Accuracy": "5", "AP": "-1", "Mode": "SA/BF/FA", "RC": "2", "Ammo": "42", "Type": "Rifles", "Price": 3500},
            {"name": "Wakizashi", "Damage": "4P", "Accuracy": "6", "AP": "-1", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Blades", "Price": 400},
            {"name": "Survival Knife", "Damage": "2P", "Accuracy": "5", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Blades", "Price": 220},
            {"name": "Sap", "Damage": "4S", "Accuracy": "4", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Clubs", "Price": 30},
            {"name": "Grapple Gun (Weaponized)", "Damage": "2P", "Accuracy": "4", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Special", "Price": 750},
            {"name": "Flash-Bang Grenade", "Damage": "10S", "Accuracy": "4", "AP": "0", "Mode": "-", "RC": "-", "Ammo": "-", "Type": "Thrown", "Price": 60},
        ],
        "Armor": [
            {"name": "Armor Vest", "Rating": "3", "Social": "0", "Capacity": "4", "Type": "Clothing", "Price": 400},
            {"name": "Lined Coat", "Rating": "6", "Social": "0", "Capacity": "8", "Type": "Clothing", "Price": 1500},
            {"name": "Armor Jacket", "Rating": "4", "Social": "0", "Capacity": "6", "Type": "Armor Jacket", "Price": 1000},
            {"name": "Full Body Armor", "Rating": "6", "Social": "-4", "Capacity": "10", "Type": "Full Body Armor", "Price": 2500},
            {"name": "Ballistic Mask", "Rating": "2", "Social": "-2", "Capacity": "0", "Type": "Helmet", "Price": 300},
            {"name": "Full Helmet", "Rating": "3", "Social": "-2", "Capacity": "2", "Type": "Helmet", "Price": 500},
            {"name": "Riot Shield", "Rating": "3", "Social": "-2", "Capacity": "0", "Type": "Shield", "Price": 2000},
            {"name": "Actioneer Business Clothes", "Rating": "2", "Social": "2", "Capacity": "2", "Type": "Clothing", "Price": 1000},
            {"name": "Urban Explorer Jumpsuit", "Rating": "6", "Social": "0", "Capacity": "8", "Type": "Armor Jacket", "Price": 1250},
            {"name": "Chameleon Suit", "Rating": "5", "Social": "-2", "Capacity": "6", "Type": "Full Body Armor", "Price": 1800},
            {"name": "Forearm Guards", "Rating": "1", "Social": "0", "Capacity": "0", "Type": "Clothing", "Price": 100},
        ],
        "Cyberware": [
            {"name": "Datajack", "Essence Cost": "0.2", "Capacity": "-", "Rating": "-", "Type": "Headware", "Price": 500},
            {"name": "Cybereyes (Rating 3)", "Essence Cost": "0.4", "Capacity": "6", "Rating": "3", "Type": "Eyeware", "Price": 2000},
            {"name": "Cyberears (Rating 3)", "Essence Cost": "0.4", "Capacity": "6", "Rating": "3", "Type": "Earware", "Price": 1500},
            {"name": "Wired Reflexes (Rating 1)", "Essence Cost": "2.0", "Capacity": "-", "Rating": "1", "Type": "Bodyware", "Reaction": "1", "Initiative Dice": "1", "Price": 15000},
            {"name": "Wired Reflexes (Rating 2)", "Essence Cost": "3.0", "Capacity": "-", "Rating": "2", "Type": "Bodyware", "Reaction": "2", "Initiative Dice": "2", "Price": 39000},
            {"name": "Reaction Enhancers (Rating 2)", "Essence Cost": "1.0", "Capacity": "-", "Rating": "2", "Type": "Bodyware", "Reaction": "2", "Price": 26000},
            {"name": "Muscle Replacement (Rating 2)", "Essence Cost": "1.0", "Capacity": "-", "Rating": "2", "Type": "Bodyware", "Strength": "2", "Price": 32000},
            {"name": "Bone Lacing (Plastic)", "Essence Cost": "0.5", "Capacity": "-", "Rating": "-", "Type": "Bodyware", "Body": "1", "Price": 8000},
            {"name": "Move-by-Wire System (Rating 1)", "Essence Cost": "1.5", "Capacity": "-", "Rating": "1", "Type": "Bodyware", "Reaction": "1", "Initiative Dice": "2", "Price": 50000},
            {"name": "Cyberlimb Arm (Standard)", "Essence Cost": "1.0", "Capacity": "10", "Rating": "-", "Type": "Cyberlimbs", "Price": 15000},
            {"name": "Smartlink", "Essence Cost": "0.2", "Capacity": "-", "Rating": "-", "Type": "Implants", "Price": 2000},
            {"name": "Cybereyes (Rating 4)", "Essence Cost": "0.5", "Capacity": "8", "Rating": "4", "Type": "Eyeware", "Price": 4000},
            {"name": "Tactical Computer (Rating 2)", "Essence Cost": "0.4", "Capacity": "-", "Rating": "2", "Type": "Headware", "Price": 16000},
            {"name": "Cyberlimb Leg (Standard)", "Essence Cost": "1.0", "Capacity": "10", "Rating": "-", "Type": "Cyberlimbs", "Price": 15000},
            {"name": "Dermal Plating (Rating 2)", "Essence Cost": "1.0", "Capacity": "-", "Rating": "2", "Type": "Bodyware", "Price": 18000},
            {"name": "Platelet Factory", "Essence Cost": "0.1", "Capacity": "-", "Rating": "-", "Type": "Bodyware", "Price": 15000},
        ],
        "Bioware": [
            {"name": "Muscle Augmentation (Rating 2)", "Essence Cost": "0.6", "Rating": "2", "Capacity": "-", "Type": "Muscle", "Strength": "2", "Price": 12000},
            {"name": "Muscle Toner (Rating 2)", "Essence Cost": "0.4", "Rating": "2", "Capacity": "-", "Type": "Muscle", "Agility": "2", "Price": 32000},
            {"name": "Synaptic Booster (Rating 2)", "Essence Cost": "0.8", "Rating": "2", "Capacity": "-", "Type": "Nervous", "Reaction": "2", "Initiative Dice": "1", "Price": 18000},
            {"name": "Cerebral Booster (Rating 2)", "Essence Cost": "0.4", "Rating": "2", "Capacity": "-", "Type": "Nervous", "Logic": "2", "Price": 31000},
            {"name": "Tailored Pheromones (Rating 3)", "Essence Cost": "0.4", "Rating": "3", "Capacity": "-", "Type": "Endocrine", "Charisma": "1", "Price": 10000},
            {"name": "Trauma Damper", "Essence Cost": "0.3", "Rating": "-", "Capacity": "-", "Type": "Nervous", "Price": 15000},
            {"name": "Orthoskin (Rating 2)", "Essence Cost": "0.5", "Rating": "2", "Capacity": "-", "Type": "Skin", "Price": 20000},
            {"name": "Synthacardium (Rating 2)", "Essence Cost": "0.4", "Rating": "2", "Capacity": "-", "Type": "Muscle", "Body": "1", "Price": 14000},
            {"name": "Sleep Regulator", "Essence Cost": "0.1", "Rating": "-", "Capacity": "-", "Type": "Nervous", "Price": 8000},
            {"name": "Pathogenic Defense (Rating 2)", "Essence Cost": "0.2", "Rating": "2", "Capacity": "-", "Type": "Immune", "Body": "1", "Price": 6000},
        ],
        "Magic Items": [
            {"name": "Reagents (10 units)", "Force": "-", "Type": "Reagent", "Binding": "-", "Price": 100},
            {"name": "Spell Formula", "Force": "-", "Type": "Formula", "Binding": "-", "Price": 500},
            {"name": "Fetish", "Force": "-", "Type": "Fetish", "Binding": "-", "Price": 50},
            {"name": "Sustaining Focus (Force 2)", "Force": "2", "Type": "Sustaining", "Binding": "Karma = Force", "Price": 8000},
            {"name": "Power Focus (Force 3)", "Force": "3", "Type": "Power", "Binding": "Karma = Force x2", "Price": 60000},
            {"name": "Weapon Focus (Force 2)", "Force": "2", "Type": "Weapon", "Binding": "Karma = Force x3", "Price": 40000},
            {"name": "Spirit Fetish", "Force": "-", "Type": "Fetish", "Binding": "-", "Price": 150},
            {"name": "Magical Lodge Materials", "Force": "4", "Type": "Lodge", "Binding": "-", "Price": 2000},
        ] + PREDEFINED_ENCHANTMENTS,
        "Electronics": [
            {"name": "Meta Link Commlink", "Rating": "1", "Capacity": "-", "Function": "Commlink", "Price": 100},
            {"name": "Renraku Sensei Commlink", "Rating": "4", "Capacity": "-", "Function": "Commlink", "Price": 2000},
            {"name": "Microdeck Cyberdeck", "Rating": "3", "Capacity": "-", "Function": "Cyberdeck", "Price": 8500},
            {"name": "Erika Elite Cyberdeck", "Rating": "5", "Capacity": "-", "Function": "Cyberdeck", "Price": 23500},
            {"name": "Subvocal Mic", "Rating": "-", "Capacity": "-", "Function": "Comm Accessory", "Price": 100},
            {"name": "Tag Eraser", "Rating": "-", "Capacity": "-", "Function": "Security Tool", "Price": 800},
            {"name": "AR Gloves", "Rating": "-", "Capacity": "-", "Function": "Comm Accessory", "Price": 50},
            {"name": "Micro-Transceiver", "Rating": "-", "Capacity": "-", "Function": "Comm Accessory", "Price": 100},
            {"name": "Sensor Jammer (Rating 4)", "Rating": "4", "Capacity": "-", "Function": "Security Tool", "Price": 2000},
            {"name": "Drone (Micro)", "Rating": "2", "Capacity": "-", "Function": "Drone", "Price": 1000},
        ],
        "Medkits": [
            {"name": "Basic Medkit", "Rating": "1", "Quantity": "5", "Type": "Rating 1", "Price": 100},
            {"name": "Field Trauma Kit", "Rating": "3", "Quantity": "5", "Type": "Rating 3", "Price": 500},
            {"name": "Professional Medkit", "Rating": "6", "Quantity": "5", "Type": "Rating 6", "Price": 2000},
            {"name": "Hospital-Grade Kit", "Rating": "10", "Quantity": "5", "Type": "Rating 10", "Price": 10000},
            {"name": "Combat Trauma Patch", "Rating": "2", "Quantity": "1", "Type": "Rating 1", "Price": 300},
            {"name": "Auto-Injector Medkit", "Rating": "4", "Quantity": "3", "Type": "Rating 3", "Price": 750},
        ],
        "Other": [
            {"name": "Fake SIN (Rating 4)", "Effect": "Identity cover", "Duration": "Permanent", "Potency": "4", "Price": 4000},
            {"name": "Grapple Gun", "Effect": "Climbing/mobility tool", "Duration": "-", "Potency": "-", "Price": 750},
            {"name": "Survival Kit", "Effect": "Outdoor survival gear", "Duration": "-", "Potency": "-", "Price": 200},
            {"name": "Lockpick Set", "Effect": "+2 dice to physical lock picking", "Duration": "-", "Potency": "2", "Price": 500},
            {"name": "Chemical Suit", "Effect": "Protection from toxins/chemicals", "Duration": "-", "Potency": "6", "Price": 1500},
            {"name": "Fake License (Rating 4)", "Effect": "Legal cover for restricted gear", "Duration": "Permanent", "Potency": "4", "Price": 500},
            {"name": "Climbing Gear", "Effect": "+2 dice to Climbing tests", "Duration": "-", "Potency": "2", "Price": 200},
            {"name": "Gas Mask", "Effect": "Protection from airborne toxins", "Duration": "-", "Potency": "4", "Price": 300},
            {"name": "Zip Ties (10)", "Effect": "Restrain a target", "Duration": "-", "Potency": "-", "Price": 15},
            {"name": "Tag Eraser Spray", "Effect": "Removes RFID tags", "Duration": "-", "Potency": "-", "Price": 40},
        ],
    }

    VEHICLE_TYPES = [
        "Motorcycle", "Sedan", "Sports Car", "Truck", "Helicopter",
        "Drone", "Boat", "VTOL", "Submarine", "Walker"
    ]

    MINOR_ACTIONS = [
        "Free Action", "Simple Action", "Interrupt Action", "Change Gun Mode",
        "Drop Prone", "Stand Up", "Reload Weapon", "Activate Device"
    ]

    MAJOR_ACTIONS = [
        "Complex Action", "Full Attack", "Cast Spell", "Summon Spirit",
        "Hack Device", "Pilot Vehicle", "Full Defense", "Overwatch"
    ]

    MATRIX_ICONS = {
        "Player": "blue_circle",
        "Enemy": "red_triangle",
        "Device": "yellow_square",
        "Barrier": "black_diamond",
        "Data": "green_star",
        "IC": "orange_hexagon",
        "Node": "purple_circle",
        "Host": "cyan_square"
    }

    def __init__(self):
        self.reset_character()

    def reset_character(self):
        self.name = ""
        self.metatype = "Human"
        self.role = ""
        self.background = ""
        self.lifestyle = "Low"
        self.karma = 50
        self.nuyen = 5000
        self.magic_type = "Mundane"
        self.tradition = ""
        self.mentor_spirit = ""
        self.initiation_grade = 0
        self.age = 25
        self.reputation = 0
        self.portrait_data = None  # base64-encoded image bytes, or None

        self.base_attributes = {attr: 1 for attr in self.ATTRIBUTES}
        self.base_attributes["Edge"] = 1
        self.base_attributes["Essence"] = 6.0
        self.attributes = self.base_attributes.copy()
        self.current_edge = self.base_attributes["Edge"]

        self.skills = {skill: 0 for skill in self.SKILLS}
        self.specializations = {}

        self.qualities = []

        self.gear = {category: [] for category in self.GEAR_CATEGORIES}
        self.contacts = []

        self.spells = []
        self.powers = []
        self.complex_forms = []
        self.foci = []

        self.matrix_grid = {}

        self.physical_damage = 0
        self.stun_damage = 0
        self.initiative_passed = 0
        self.damage_penalty = 0

        self.armor_rating = 0
        self.weapon_accuracy = 0
        self.power_points_available = 0
        self.power_points_used = 0.0

        self.runs = []

        self.recalculate()

    def recalculate(self):
        """Recompute every derived value from base_attributes + gear + qualities.

        This replaces the old ``calculate_derived_stats`` / ``calculate_gear_bonuses``
        pair. Doing it in one pass means gear-derived values (Essence loss, Armor,
        Weapon Accuracy) never get clobbered by a later reset to base attributes.
        """
        attributes = self.base_attributes.copy()

        # Metatype minimums (p.53-56)
        if self.metatype == "Dwarf":
            attributes["Body"] = max(3, attributes["Body"])
            attributes["Willpower"] = max(3, attributes["Willpower"])
        elif self.metatype == "Elf":
            attributes["Agility"] = max(2, attributes["Agility"])
            attributes["Charisma"] = max(3, attributes["Charisma"])
        elif self.metatype == "Ork":
            attributes["Body"] = max(3, attributes["Body"])
            attributes["Strength"] = max(3, attributes["Strength"])
        elif self.metatype == "Troll":
            attributes["Body"] = max(5, attributes["Body"])
            attributes["Strength"] = max(5, attributes["Strength"])
            attributes["Logic"] = max(1, min(attributes["Logic"], 5))

        # Role bonuses
        if self.role in self.ROLES:
            for attr, bonus in self.ROLES[self.role].items():
                attributes[attr] = max(1, attributes[attr] + bonus)

        # Quality effects. Most qualities only carry a Karma cost (handled in
        # gui_skills.py when the quality is added/removed), but some also
        # grant a flat attribute bonus (applied here, same convention as
        # gear) or a bonus to a condition monitor (accumulated here and
        # applied below, alongside the derived Body/Willpower boxes).
        quality_physical_box_bonus = 0
        quality_stun_box_bonus = 0
        for quality in self.qualities:
            effect = self.QUALITY_EFFECTS.get(quality)
            if not effect:
                continue
            for key, bonus in effect.items():
                if key == "karma":
                    continue
                elif key == "Physical Boxes":
                    quality_physical_box_bonus += bonus
                elif key == "Stun Boxes":
                    quality_stun_box_bonus += bonus
                elif key in self.ATTRIBUTES:
                    attributes[key] = max(1, attributes[key] + bonus)

        # Essence cost from cyberware/bioware (p.? essence loss)
        essence_cost = 0.0
        for item in self.gear["Cyberware"] + self.gear["Bioware"]:
            try:
                essence_cost += float(item.get("Essence Cost", 0) or 0)
            except (TypeError, ValueError):
                pass
        attributes["Essence"] = round(max(0.0, self.base_attributes.get("Essence", 6.0) - essence_cost), 2)

        # Attribute bonuses from cyberware/bioware/adept powers: any item on
        # those lists may carry an extra key named after an attribute (e.g.
        # "Reaction": "1") to grant a flat bonus. This is what lets predefined
        # (or custom, hand-entered) gear like Wired Reflexes or Muscle
        # Augmentation actually do something instead of being flavor text.
        initiative_dice_bonus = 0
        for item in self.gear["Cyberware"] + self.gear["Bioware"] + self.powers:
            for attr in self.ATTRIBUTES:
                if attr == "Essence" or attr not in item:
                    continue
                try:
                    attributes[attr] += float(item[attr])
                except (TypeError, ValueError):
                    pass
            if "Initiative Dice" in item:
                try:
                    initiative_dice_bonus += float(item["Initiative Dice"])
                except (TypeError, ValueError):
                    pass
        for attr in self.ATTRIBUTES:
            if attr != "Essence":
                attributes[attr] = int(round(attributes[attr]))

        # Armor rating: sum of equipped armor pieces' Rating. Items without an
        # "Equipped" flag (older saves, or items added before this feature)
        # default to equipped so nothing already on a sheet silently stops
        # counting.
        armor_rating = 0
        for item in self.gear["Armor"]:
            if str(item.get("Equipped", "Yes")).strip().lower() == "no":
                continue
            try:
                armor_rating += int(float(item.get("Rating", 0) or 0))
            except (TypeError, ValueError):
                pass

        # Mystic Armor and similar adept powers add straight to Armor Rating.
        for power in self.powers:
            if "Armor" in power:
                try:
                    armor_rating += int(float(power["Armor"]))
                except (TypeError, ValueError):
                    pass
        self.armor_rating = armor_rating

        # Weapon accuracy: highest Accuracy among equipped weapons
        weapon_accuracy = 0
        for item in self.gear["Weapons"]:
            if str(item.get("Equipped", "Yes")).strip().lower() == "no":
                continue
            try:
                weapon_accuracy = max(weapon_accuracy, int(float(item.get("Accuracy", 0) or 0)))
            except (TypeError, ValueError):
                pass
        self.weapon_accuracy = weapon_accuracy

        # Essence affects Magic (p.38) for magically active, non-technomancer types
        if self.magic_type not in ("Mundane", "Technomancer"):
            essence = attributes["Essence"]
            magic = attributes["Magic"]
            for i in range(1, 7):
                if essence < i:
                    magic = min(magic, 6 - i)
            attributes["Magic"] = magic

        # A bonded Power Focus adds its Force straight to Magic (p.? foci rules)
        for focus in self.foci:
            bonded = str(focus.get("Bonded", "")).strip().lower() in ("yes", "true", "1")
            if bonded and focus.get("Type", focus.get("type", "")) == "Power":
                try:
                    attributes["Magic"] += int(float(focus.get("Force", focus.get("force", 0)) or 0))
                except (TypeError, ValueError):
                    pass

        self.attributes = attributes

        # Condition monitors (p.39), plus any bonus boxes from qualities
        # (e.g. High Pain Tolerance, Will to Live).
        body = self.attributes["Body"]
        willpower = self.attributes["Willpower"]
        self.physical_boxes = (body + 1) // 2 + 8 + quality_physical_box_bonus
        self.stun_boxes = (willpower + 1) // 2 + 8 + quality_stun_box_bonus

        # Initiative (p.39)
        self.initiative_score = self.attributes["Reaction"] + self.attributes["Intuition"]
        self.initiative_dice = 1 + int(initiative_dice_bonus)

        # Damage penalty
        self.damage_penalty = -(self.physical_damage // 3 + self.stun_damage // 3)

        # Keep current_edge from exceeding the (possibly changed) max
        self.current_edge = min(self.current_edge, self.attributes["Edge"])

        # Adept/Mystic Adept Power Points: available = Magic rating, used =
        # sum of each known power's Cost (defaults to 1 if unset).
        if self.magic_type in ("Adept", "Mystic Adept"):
            self.power_points_available = self.attributes["Magic"]
        else:
            self.power_points_available = 0
        used = 0.0
        for power in self.powers:
            try:
                used += float(power.get("Cost", power.get("cost", 1)) or 1)
            except (TypeError, ValueError):
                used += 1
        self.power_points_used = used

    def add_gear(self, category, item):
        self.gear[category].append(item)
        self.recalculate()

    def update_gear(self, category, index, item):
        if 0 <= index < len(self.gear[category]):
            self.gear[category][index] = item
            self.recalculate()

    def remove_gear(self, category, index):
        if 0 <= index < len(self.gear[category]):
            del self.gear[category][index]
            self.recalculate()

    def roll_dice(self, pool_size, edge_action=None, roll_type="", use_wild_die=False):
        """Roll dice for the Shadowrun system with Edge options and an optional wild die.

        ``roll_type`` is a plain description of what's being rolled (e.g. one of
        ``DICE_ROLL_OPTIONS``) -- used only to decide whether "Battle Hardened"
        applies (it's a defense-only Edge action). Edge cost is deducted from
        ``current_edge`` here, once, if the action is actually used.
        """
        edge_cost = 0
        edge_action_used = None
        if edge_action:
            edge_cost = self.EDGE_ACTIONS.get(edge_action, 0)
            if self.current_edge >= edge_cost:
                edge_action_used = edge_action
            else:
                edge_cost = 0  # not enough Edge -- roll normally

        if pool_size <= 0 and edge_action_used != "Heroic Effort (3 Edge)":
            return {
                "dice": [], "hits": 0, "glitch": False, "critical_glitch": False,
                "wild_die": None, "edge_action_used": None,
            }

        pool_size += self.damage_penalty

        extra_hits = 0
        reroll_non_hits = False
        seal_fate = False
        battle_hardened = False

        if edge_action_used == "Reroll Non-Hits (1 Edge)":
            reroll_non_hits = True
        elif edge_action_used == "Seal Fate (1 Edge)":
            seal_fate = True
        elif edge_action_used == "Push the Limit (4 Edge)":
            pool_size += self.attributes["Edge"]
        elif edge_action_used == "Heroic Effort (3 Edge)":
            extra_hits = 3
        elif edge_action_used == "Battle Hardened (2 Edge)":
            battle_hardened = True

        dice = []
        wild_die_result = None
        wild_die_hits = 0

        if edge_action_used != "Heroic Effort (3 Edge)":
            pool_size = max(0, pool_size)
            dice = [random.randint(1, 6) for _ in range(pool_size)]

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

            if reroll_non_hits:
                non_hits = [r for r in dice if r < 5]
                rerolled = [random.randint(1, 6) for _ in non_hits]
                dice = [r for r in dice if r >= 5] + rerolled

            if seal_fate:
                to_reroll = [r for r in dice if r < 5 and r != 1]
                rerolled = [random.randint(1, 6) for _ in to_reroll]
                dice = [r for r in dice if r >= 5 or r == 1] + rerolled

        hits = sum(1 for r in dice if r >= 5) + extra_hits + wild_die_hits
        ones = sum(1 for r in dice if r == 1)
        total_dice = len(dice)

        glitch = total_dice > 0 and ones > total_dice / 2
        critical_glitch = glitch and hits <= 0

        if battle_hardened and "Defense" in (roll_type or ""):
            hits += self.attributes["Edge"]

        if edge_cost:
            self.current_edge -= edge_cost

        return {
            "dice": dice,
            "hits": max(0, hits),
            "glitch": glitch,
            "critical_glitch": critical_glitch,
            "wild_die": wild_die_result,
            "edge_action_used": edge_action_used,
        }

    def roll_initiative(self):
        base_score = self.attributes["Reaction"] + self.attributes["Intuition"]
        dice_rolls = [random.randint(1, 6) for _ in range(self.initiative_dice)]
        return base_score + sum(dice_rolls), dice_rolls

    def heal_damage(self, damage_type, amount):
        if damage_type == "physical":
            self.physical_damage = max(0, self.physical_damage - amount)
        elif damage_type == "stun":
            self.stun_damage = max(0, self.stun_damage - amount)
        self.recalculate()

    def use_medkit(self):
        if not self.gear["Medkits"]:
            return False

        medkit = self.gear["Medkits"][0]

        rating = 1
        if "Rating" in medkit:
            try:
                rating_str = str(medkit["Rating"])
                rating = int(rating_str.split()[-1]) if " " in rating_str else int(rating_str)
            except (ValueError, IndexError):
                pass

        self.heal_damage("physical", rating * 2)
        self.heal_damage("stun", rating)

        quantity = 1
        if "Quantity" in medkit:
            try:
                quantity = int(medkit["Quantity"])
            except ValueError:
                pass

        quantity -= 1
        if quantity <= 0:
            self.gear["Medkits"].pop(0)
        else:
            medkit["Quantity"] = str(quantity)

        return True

    def rest(self):
        self.heal_damage("stun", 1)

    def reset_edge(self):
        self.current_edge = self.attributes["Edge"]

    def trade_karma_for_nuyen(self, amount):
        if amount > 0 and self.karma >= amount:
            self.karma -= amount
            self.nuyen += amount * 2000
            return True
        return False

    def increase_attribute(self, attribute):
        current_rating = self.base_attributes[attribute]
        karma_cost = (current_rating + 1) * 5
        if self.karma >= karma_cost:
            self.karma -= karma_cost
            self.base_attributes[attribute] = current_rating + 1
            self.recalculate()
            return True
        return False

    def add_matrix_element(self, x, y, element_type, label=""):
        self.matrix_grid[(x, y)] = {"type": element_type, "label": label}

    def remove_matrix_element(self, x, y):
        self.matrix_grid.pop((x, y), None)

    def get_matrix_element(self, x, y):
        return self.matrix_grid.get((x, y))

    def clear_matrix(self):
        self.matrix_grid = {}

    def set_portrait_from_file(self, path, max_size=512):
        """Load an image file, force it to a centered square crop, downscale
        it to at most ``max_size`` pixels per side, and store it (base64) on
        the character.

        Forcing a square crop here -- rather than just downscaling and
        keeping whatever aspect ratio the source photo had -- is what keeps
        every consumer of this image (the Background tab's portrait box) a
        small, fixed, predictable size. A non-square portrait used to grow
        that box to match the image's real dimensions, which pushed and
        clipped the Character Info tab's layout when the portrait lived
        there.
        """
        if Image is None:
            raise RuntimeError("Pillow is not installed; portraits are unavailable.")
        img = Image.open(path)
        img = img.convert("RGB")
        img = self._crop_to_square(img)
        if img.size[0] > max_size:
            img = img.resize((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        self.portrait_data = base64.b64encode(buf.getvalue()).decode("ascii")

    @staticmethod
    def _crop_to_square(img):
        """Center-crop a PIL Image to a 1:1 square."""
        width, height = img.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        return img.crop((left, top, left + side, top + side))

    def clear_portrait(self):
        self.portrait_data = None

    def get_portrait_image(self, size=None):
        """Return a PIL Image for the stored portrait, or None.

        Also re-crops to square defensively -- a character saved by an
        older version of this app (before portraits were forced square)
        could still have a non-square image stored.
        """
        if not self.portrait_data or Image is None:
            return None
        raw = base64.b64decode(self.portrait_data)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img = self._crop_to_square(img)
        if size:
            img.thumbnail(size)
        return img

    def to_dict(self):
        return {
            "name": self.name,
            "metatype": self.metatype,
            "role": self.role,
            "background": self.background,
            "lifestyle": self.lifestyle,
            "karma": self.karma,
            "nuyen": self.nuyen,
            "magic_type": self.magic_type,
            "tradition": self.tradition,
            "mentor_spirit": self.mentor_spirit,
            "initiation_grade": self.initiation_grade,
            "age": self.age,
            "reputation": self.reputation,
            "portrait_data": self.portrait_data,
            "base_attributes": self.base_attributes,
            "skills": self.skills,
            "specializations": self.specializations,
            "qualities": self.qualities,
            "gear": self.gear,
            "contacts": self.contacts,
            "spells": self.spells,
            "powers": self.powers,
            "complex_forms": self.complex_forms,
            "foci": self.foci,
            "matrix_grid": {f"{x},{y}": v for (x, y), v in self.matrix_grid.items()},
            "physical_damage": self.physical_damage,
            "stun_damage": self.stun_damage,
            "current_edge": self.current_edge,
            "runs": [run.to_dict() for run in self.runs],
        }

    def from_dict(self, data):
        self.name = data.get("name", "")
        self.metatype = data.get("metatype", "Human")
        self.role = data.get("role", "")
        self.background = data.get("background", "")
        self.lifestyle = data.get("lifestyle", "Low")
        self.karma = data.get("karma", 50)
        self.nuyen = data.get("nuyen", 5000)
        self.magic_type = data.get("magic_type", "Mundane")
        self.tradition = data.get("tradition", "")
        self.mentor_spirit = data.get("mentor_spirit", "")
        self.initiation_grade = data.get("initiation_grade", 0)
        self.age = data.get("age", 25)
        self.reputation = data.get("reputation", 0)
        self.portrait_data = data.get("portrait_data")

        self.base_attributes = data.get("base_attributes") or data.get("attributes") or \
            {attr: 1 for attr in self.ATTRIBUTES}
        self.base_attributes.setdefault("Edge", 1)
        self.base_attributes.setdefault("Essence", 6.0)

        self.skills = data.get("skills", {skill: 0 for skill in self.SKILLS})
        self.specializations = data.get("specializations", {})
        self.qualities = data.get("qualities", [])
        self.gear = data.get("gear", {category: [] for category in self.GEAR_CATEGORIES})
        for category in self.GEAR_CATEGORIES:
            self.gear.setdefault(category, [])
        self.contacts = data.get("contacts", [])
        self.spells = data.get("spells", [])
        self.powers = data.get("powers", [])
        self.complex_forms = data.get("complex_forms", [])
        self.foci = data.get("foci", [])

        raw_grid = data.get("matrix_grid", {})
        self.matrix_grid = {}
        for key, value in raw_grid.items():
            if isinstance(key, str) and "," in key:
                x_str, y_str = key.split(",", 1)
                self.matrix_grid[(int(x_str), int(y_str))] = value
            else:
                self.matrix_grid[tuple(key)] = value

        self.physical_damage = data.get("physical_damage", 0)
        self.stun_damage = data.get("stun_damage", 0)

        self.runs = [ShadowrunRun.from_dict(rd) for rd in data.get("runs", [])]

        self.recalculate()
        # current_edge restored after recalculate() so it isn't clobbered by
        # the "clamp to max" step, but still clamped to the (possibly new) max.
        self.current_edge = min(data.get("current_edge", self.attributes["Edge"]), self.attributes["Edge"])
        return self
