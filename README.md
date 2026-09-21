![Shadowrun 6th World Logo](https://www.shadowrunsixthworld.com/wp-content/themes/shadowrun/dist/images/shadowrun-logo-totem_bc47c041.png)

##### A desktop tool for managing your Shadowrun 6E characters *and* your campaign's runs (missions), so you don't have to track either by hand. Bugs are still possible — use it *as is*. Want to contribute? Tip me some sats at the address below:

```
bc1q7e3mf5nwmjk9sw8thy35s9r7rq27ta7lzj0d7l
```
##### Happy role playing.

---

## What it is

A single desktop app that covers a full Shadowrun 6th World Edition
character sheet — attributes, skills, qualities, gear, magic, combat,
contacts, background — plus a mission/run tracker for your campaign, all
saved in one `.sr6` file per character. Everything that can be derived from
your build (Armor Rating, Weapon Accuracy, Essence loss, Initiative, Power
Points, condition monitor sizes...) is calculated automatically from your
attributes, gear, and qualities as you edit them, instead of needing to be
worked out and typed in by hand.

## Running it

1. Make sure Python 3.9+ and Tkinter are available. Tkinter ships with most
   Python installs, but on Debian/Ubuntu you may need:
   ```
   sudo apt install python3-tk
   ```
2. Install the one real dependency (Pillow, used for character portraits):
   ```
   pip install -r requirements.txt
   ```
3. Run it:
   ```
   python main.py
   ```

A character (including its runs) is saved as a single `.sr6` file (plain
JSON under the hood) via **Save Character** / **Save As...** / **Load
Character** in the footer. **Export Summary...** writes a plain-text
character sheet you can paste into a chat or print, without handing over
the full save file.

## Tabs

- **Basic Info** — name, metatype, role, magic/resonance type, tradition,
  lifestyle, karma/nuyen (with a Trade Karma for Nuyen helper), your twelve
  core attributes (with an Auto Roll option and per-attribute Karma-cost
  increases), and a Quick Stats strip (condition monitors, Initiative,
  Armor, Edge, Essence) so you don't have to flip to Combat Stats mid-scene.
- **Skills** — all nineteen skills with ranks and, where the skill supports
  one, a specialization; a specialization adds its +2 dice bonus
  automatically wherever that skill is rolled.
- **Qualities** — every quality from the core rules, split into Positive
  and Negative lists. Adding one charges (or, for a negative quality,
  awards) the right amount of Karma automatically, and any quality with a
  mechanical effect (an attribute bonus, extra condition-monitor boxes)
  applies it without further setup.
- **Magic/Resonance** — Spells (including Rituals), Adept Powers (with a
  running Power Points used/available total), Foci (bond a focus for a
  one-time Karma cost — a bonded Power Focus adds its Force straight to
  Magic), and Complex Forms for Technomancers.
- **Gear** — Weapons, Armor, Cyberware, Bioware, Magic Items, Electronics,
  Medkits, and Other, each with a large predefined catalog to pick from via
  "Use Predefined," or add your own. A Gear Summary strip shows Armor
  Rating, Weapon Accuracy, remaining Essence, and total gear value live.
  Weapons/Armor have an Equipped toggle (only equipped gear counts toward
  your totals); Cyberware/Bioware/Adept Powers can carry attribute or
  Initiative Dice bonuses that apply automatically.
- **Combat Stats** — an **Overview** with derived stats, both condition
  monitors (click a box to mark/clear damage), and Initiative/Healing/Edge
  controls all on one screen, plus a **Dice Roller**: pick an
  attribute/skill/spell/power/focus/weapon pool (specializations and Matrix
  actions included), an optional Edge action, and a Wild Die — or use
  **Free Roll** to roll an arbitrary pool by typing something like `4d6`.
- **Contacts** — your contact list with type, loyalty, connection, and
  notes.
- **Background** — age, reputation, a free-text background, and your
  character's portrait (loaded from an image file; always stored as a
  square crop, capped at 512×512, so it stays a small, predictable size no
  matter what photo you load).
- **Runs** — your campaign's mission tracker, living inside the same
  character file: create a run with a reward and a checklist of
  mandatory/optional tasks, track progress, and complete or abandon it
  (reward scales with how much of the checklist got done).
- **Wiki** — an in-app reference covering every predefined gear item, spell,
  ritual, adept power, focus, complex form, alchemical preparation, and
  quality, plus static rules pages for combat, magic, the Matrix, and
  vehicles.
- **Matrix** — a sketch grid for hosts, nodes, ICE, and other Matrix
  elements during a run: click an empty cell to place a marker, drag an
  existing one to move it, right-click to delete it, and save/load a grid
  layout to a file.

## Autocalculation

The character model recomputes everything derived from your build in a
single pass whenever anything changes:

- **Attributes** — metatype minimums, role bonuses, quality bonuses, and
  flat bonuses from Cyberware/Bioware/Adept Powers (any item can carry an
  extra key named after an attribute, e.g. `Reaction: 1`, to grant it).
- **Essence** — reduced by each piece of Cyberware/Bioware's Essence Cost,
  which in turn caps Magic for magically active characters.
- **Armor Rating** / **Weapon Accuracy** — from equipped Armor/Weapons
  (plus Mystic Armor-style adept powers for Armor).
- **Initiative** — Reaction + Intuition, plus bonus dice from Wired
  Reflexes, Move-by-Wire, or similar.
- **Condition monitors** — sized from Body/Willpower, plus any bonus boxes
  from qualities like High Pain Tolerance.
- **Power Points** — available (from Magic, for Adepts/Mystic Adepts) vs.
  used (summed from your powers' Cost).
- **Magic** — boosted by a bonded Power Focus's Force.

## Project layout

- `main.py` — entry point.
- `character.py` — the data model (`ShadowrunCharacter`): all game
  constants and predefined content, the autocalculation engine
  (`recalculate()`), and save/load (`to_dict`/`from_dict`).
- `runs.py` — the `ShadowrunRun` model for the Runs tab.
- `app.py` — assembles the tabs and owns cross-tab concerns (file
  operations, propagating a change on one tab to stats shown on another).
- `theme.py` — the app's single dark theme.
- `dialogs.py` — shared popup dialogs (gear/spell/power/focus editor,
  contact editor, run editor).
- `gui_*.py` — one module per tab (or tab group), each a mixin class that
  `CharacterSheetApp` combines in `app.py`.
- `smoke_test.py` — a headless test suite (run under Xvfb) exercising the
  app's main code paths.

---

*Shadowrun is a trademark of Catalyst Game Labs. This project is not officially affiliated with Catalyst Game Labs or The Topps Company.*
