"""Headless smoke test: exercise the merged app's main code paths under Xvfb
to catch runtime errors that py_compile can't (Tk widget wiring, cross-mixin
method calls, the specific bugs the merge was supposed to fix)."""
import json
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(__file__))

import tkinter.messagebox as mb
mb.showinfo = lambda *a, **k: None
mb.showwarning = lambda *a, **k: None
mb.showerror = lambda *a, **k: None
mb.askyesno = lambda *a, **k: True

from app import CharacterSheetApp

failures = []


def check(label, fn):
    try:
        fn()
        print(f"OK   {label}")
    except Exception as e:
        import traceback
        print(f"FAIL {label}: {e}")
        traceback.print_exc()
        failures.append(label)


root = tk.Tk()
app = CharacterSheetApp(root)
root.update()

check("draw_condition_monitors (initial)", app.draw_condition_monitors)

def basic_info():
    app.name_entry.delete(0, tk.END)
    app.name_entry.insert(0, "Test Runner")
    app.metatype_combo.set("Troll")
    app.role_combo.set("Street Samurai")
    app.magic_combo.set("Adept")
    app.lifestyle_combo.set("Middle")
    app.karma_spin.delete(0, tk.END)
    app.karma_spin.insert(0, "200")
    app.on_character_changed()
    assert app.character.name == "Test Runner"
    assert app.character.metatype == "Troll"
    assert app.character.attributes["Body"] >= 5  # troll min + samurai bonus

check("basic info commit + recalc", basic_info)


def trade_karma_bug():
    # Directly exercise the model call the button uses, since askinteger needs
    # a real dialog; the important thing is the import doesn't blow up.
    from tkinter import simpledialog
    assert simpledialog is not None
    ok = app.character.trade_karma_for_nuyen(10)
    assert ok
    assert app.character.nuyen >= 5000 + 20000

check("trade karma for nuyen (simpledialog import)", trade_karma_bug)


def attribute_increase():
    karma_before = app.character.karma
    ok = app.increase_attribute_model_only = app.character.increase_attribute("Agility")
    assert ok
    assert app.character.karma < karma_before

check("increase_attribute", attribute_increase)


def find_predefined(category, name):
    from character import ShadowrunCharacter
    for item in ShadowrunCharacter.PREDEFINED_GEAR[category]:
        if item["name"] == name:
            return dict(item)
    raise KeyError(f"{name!r} not found in PREDEFINED_GEAR[{category!r}]")


def gear_and_derived_stats():
    armor_jacket = find_predefined("Armor", "Armor Jacket")  # Rating 4
    pistol = find_predefined("Weapons", "Ares Predator V")  # Accuracy 5
    app.character.add_gear("Armor", armor_jacket)
    app.character.add_gear("Weapons", pistol)
    app.refresh_all()
    assert app.character.armor_rating == 4, app.character.armor_rating
    assert app.character.weapon_accuracy == 5, app.character.weapon_accuracy
    assert app.armor_rating_label.cget("text") == "4"
    assert app.weapon_accuracy_label.cget("text") == "5"

check("gear bonuses stick (armor/weapon accuracy bug)", gear_and_derived_stats)


def cyberware_attribute_and_initiative_bonus():
    wired = find_predefined("Cyberware", "Wired Reflexes (Rating 1)")  # Essence 2.0, Reaction +1, Init Dice +1
    reaction_before = app.character.attributes["Reaction"]
    init_dice_before = app.character.initiative_dice
    app.character.add_gear("Cyberware", wired)
    assert app.character.attributes["Reaction"] == reaction_before + 1, app.character.attributes["Reaction"]
    assert app.character.initiative_dice == init_dice_before + 1, app.character.initiative_dice
    assert abs(app.character.attributes["Essence"] - 4.0) < 0.01, app.character.attributes["Essence"]

check("cyberware attribute/initiative bonus + essence (bonus-wipe bug)", cyberware_attribute_and_initiative_bonus)


def equipped_toggle_excludes_from_totals():
    full_body = find_predefined("Armor", "Full Body Armor")  # Rating 6
    before = app.character.armor_rating
    full_body["Equipped"] = "No"
    app.character.add_gear("Armor", full_body)
    assert app.character.armor_rating == before, (app.character.armor_rating, before)
    # now equip it
    idx = len(app.character.gear["Armor"]) - 1
    equipped_copy = dict(full_body)
    equipped_copy["Equipped"] = "Yes"
    app.character.update_gear("Armor", idx, equipped_copy)
    assert app.character.armor_rating == before + 6, app.character.armor_rating

check("Equipped=No gear excluded from Armor Rating", equipped_toggle_excludes_from_totals)


def bonded_power_focus_boosts_magic():
    magic_before = app.character.attributes["Magic"]
    from character import ShadowrunCharacter
    focus = dict(next(f for f in ShadowrunCharacter.PREDEFINED_FOCI if f["name"] == "Power Focus"))
    focus["Force"] = focus.pop("force")
    focus["Type"] = focus.pop("type")
    focus["Bonded"] = "Yes"
    app.character.foci.append(focus)
    app.character.recalculate()
    assert app.character.attributes["Magic"] == magic_before + 3, app.character.attributes["Magic"]

check("bonded Power Focus adds Force to Magic", bonded_power_focus_boosts_magic)


def power_points_tracking():
    app.character.magic_type = "Adept"
    app.character.recalculate()
    available_before = app.character.power_points_available
    from character import ShadowrunCharacter
    power = dict(next(p for p in ShadowrunCharacter.PREDEFINED_POWERS if p["name"] == "Combat Sense"))
    app.character.powers.append(power)
    app.character.recalculate()
    assert app.character.power_points_used == float(power["Cost"]), app.character.power_points_used
    assert app.character.power_points_available == available_before

check("power points tracked for Adept", power_points_tracking)


def battle_hardened_roll():
    app.character.current_edge = app.character.attributes["Edge"]
    edge_before = app.character.current_edge
    if edge_before < 2:
        app.character.attributes["Edge"] = 3
        app.character.current_edge = 3
        edge_before = 3
    app.dice_pool_combo.set("Body (5)")
    app.roll_combo.set("Defense (Physical)")
    app.edge_action_combo.set("Battle Hardened (2 Edge)")
    app.wild_die_var.set(True)
    app.perform_dice_roll()
    assert app.character.current_edge == edge_before - 2, (app.character.current_edge, edge_before)

check("Battle Hardened edge roll (roll_combo crash bug)", battle_hardened_roll)


def use_predefined_spell():
    from dialogs import EditGearDialog
    dlg = EditGearDialog(root, "Spell")
    dlg.name_entry.insert(0, "")
    # simulate picking the first predefined spell without opening the sub-dialog
    item = EditGearDialog.PREDEFINED_SOURCES["Spell"][0]  # {"name","type","drain","description"}
    item_lower = {k.lower(): v for k, v in item.items()}
    matched = {attr: item.get(attr, item_lower.get(attr.lower())) for attr in dlg.attr_entries}
    assert matched.get("Type") == item["type"]
    assert matched.get("Drain") == item["drain"]
    dlg.destroy()

check("predefined spell case-insensitive match", use_predefined_spell)


def matrix_save_load():
    import tempfile
    app.character.add_matrix_element(1, 2, "Host", "Corp Server")
    app.character.add_matrix_element(3, 4, "IC", "Black IC")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        path = tf.name
    try:
        app.save_matrix.__wrapped__ if hasattr(app.save_matrix, "__wrapped__") else None
        # Call the real save/load using a monkeypatched filedialog
        import dialogs as _d  # noqa
        from unittest import mock
        with mock.patch("gui_matrix.filedialog.asksaveasfilename", return_value=path):
            app.save_matrix()
        with open(path) as f:
            raw = json.load(f)
        assert "1,2" in raw
        app.character.clear_matrix()
        with mock.patch("gui_matrix.filedialog.askopenfilename", return_value=path):
            app.load_matrix()
        assert app.character.get_matrix_element(1, 2)["label"] == "Corp Server"
    finally:
        os.unlink(path)

check("matrix save/load (tuple-key JSON bug)", matrix_save_load)


def runs_flow():
    from runs import ShadowrunRun
    run = ShadowrunRun(name="Milk Run", description="Simple extraction", reward=10000)
    run.tasks = [
        {"description": "Scout the location", "mandatory": True, "completed": False},
        {"description": "Grab the target", "mandatory": True, "completed": False},
        {"description": "Don't get seen", "mandatory": False, "completed": False},
    ]
    app.character.runs.append(run)
    app.refresh_runs()
    app._select_run(run)
    assert app.current_run is run
    for t in run.tasks:
        t["completed"] = True
    app._refresh_run_tasks()
    assert run.mandatory_complete()
    nuyen_before = app.character.nuyen
    app.complete_run()
    assert app.character.nuyen == nuyen_before + 10000
    assert run.status == "Completed"

check("runs tab full flow (create/complete)", runs_flow)


def save_and_load_roundtrip():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".sr6", delete=False) as tf:
        path = tf.name
    try:
        app._write_character(path)
        with open(path) as f:
            data = json.load(f)
        assert data["name"] == "Test Runner"
        assert len(data["runs"]) == 1
        assert "armor_rating" not in data  # derived, recomputed from gear on load, not persisted directly
        from character import ShadowrunCharacter
        fresh = ShadowrunCharacter()
        fresh.from_dict(data)
        assert fresh.armor_rating == app.character.armor_rating
        assert len(fresh.runs) == 1
        assert fresh.runs[0].status == "Completed"
    finally:
        os.unlink(path)

check("save/load roundtrip incl. runs", save_and_load_roundtrip)


def predefined_sources_cover_all_categories():
    from dialogs import EditGearDialog
    for category in ["Medkits", "Magic Items", "Electronics", "Other"]:
        assert category in EditGearDialog.PREDEFINED_SOURCES, category
        assert len(EditGearDialog.PREDEFINED_SOURCES[category]) > 0, category

check("PREDEFINED_SOURCES covers Medkits/Magic Items/Electronics/Other", predefined_sources_cover_all_categories)


def free_roll_parsing():
    assert app.parse_free_roll("4d6") == 4
    assert app.parse_free_roll("4D6") == 4
    assert app.parse_free_roll("4d") == 4
    assert app.parse_free_roll("4") == 4
    assert app.parse_free_roll("") is None
    assert app.parse_free_roll("abc") is None

check("free roll dice-count parsing (4d6 etc.)", free_roll_parsing)


def free_roll_performs():
    app.free_roll_entry.delete(0, tk.END)
    app.free_roll_entry.insert(0, "6d6")
    app.wild_die_var.set(False)
    app.perform_free_roll()
    assert app.hits_label.cget("text").startswith("Hits:")

check("perform_free_roll rolls and displays a result", free_roll_performs)


def matrix_drag_move():
    app.character.clear_matrix()
    app.character.add_matrix_element(1, 1, "Host", "Server")
    app._drag_origin = (1, 1)

    class FakeEvent:
        pass
    ev = FakeEvent()
    ev.x, ev.y = 3 * 50 + 10, 4 * 50 + 10  # cell (3, 4)
    app.canvas_release(ev)
    assert app.character.get_matrix_element(1, 1) is None
    assert app.character.get_matrix_element(3, 4)["label"] == "Server"

check("matrix marker drag-to-move", matrix_drag_move)


def matrix_right_click_delete():
    class FakeEvent:
        pass
    ev = FakeEvent()
    ev.x, ev.y = 3 * 50 + 10, 4 * 50 + 10
    app.canvas_right_click(ev)
    assert app.character.get_matrix_element(3, 4) is None

check("matrix marker right-click delete", matrix_right_click_delete)


def quality_effects_cover_every_quality():
    from character import ShadowrunCharacter
    all_qualities = ShadowrunCharacter.QUALITIES["Positive"] + ShadowrunCharacter.QUALITIES["Negative"]
    missing = [q for q in all_qualities if q not in ShadowrunCharacter.QUALITY_EFFECTS]
    assert not missing, missing

check("every quality has a QUALITY_EFFECTS entry", quality_effects_cover_every_quality)


def quality_box_bonus_and_karma_sign():
    from character import ShadowrunCharacter
    app.character.qualities = ["High Pain Tolerance"]
    app.character.recalculate()
    assert app.character.physical_boxes >= 10  # base 8+ from Body, +2 from quality
    for quality in ShadowrunCharacter.QUALITIES["Positive"]:
        assert ShadowrunCharacter.QUALITY_EFFECTS[quality]["karma"] >= 0, quality
    for quality in ShadowrunCharacter.QUALITIES["Negative"]:
        assert ShadowrunCharacter.QUALITY_EFFECTS[quality]["karma"] <= 0, quality
    app.character.qualities = []
    app.character.recalculate()

check("quality condition-monitor bonus applies + karma sign convention", quality_box_bonus_and_karma_sign)


def mystic_armor_power_grants_armor():
    from character import ShadowrunCharacter
    before = app.character.armor_rating
    power = find_predefined_power = next(p for p in ShadowrunCharacter.PREDEFINED_POWERS if p["name"] == "Mystic Armor")
    app.character.powers.append(dict(power))
    app.character.recalculate()
    assert app.character.armor_rating == before + 3, (app.character.armor_rating, before)
    app.character.powers.pop()
    app.character.recalculate()

check("Mystic Armor power actually adds to Armor Rating (was missing the key)", mystic_armor_power_grants_armor)


def specialization_dice_bonus_in_pool_options():
    app.character.skills["Firearms"] = 4
    app.character.specializations["Firearms"] = "Pistols"
    app.update_dice_pool_options()
    values = list(app.dice_pool_combo["values"])
    assert any("[Pistols] (6)" in v for v in values), values

check("skill specialization adds +2 dice in the dice-pool list", specialization_dice_bonus_in_pool_options)


def export_summary_writes_file():
    import tempfile
    from unittest import mock
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        path = tf.name
    try:
        with mock.patch("app.filedialog.asksaveasfilename", return_value=path):
            app.export_summary()
        with open(path) as f:
            content = f.read()
        assert app.character.name in content
        assert "Attributes:" in content
    finally:
        os.unlink(path)

check("Export Summary writes a readable text file", export_summary_writes_file)


def complex_form_add_edit_remove():
    from dialogs import EditGearDialog
    assert "Complex Form" in EditGearDialog.PREDEFINED_SOURCES
    assert len(EditGearDialog.PREDEFINED_SOURCES["Complex Form"]) > 0

    form = dict(next(f for f in EditGearDialog.PREDEFINED_SOURCES["Complex Form"] if f["name"] == "Resonance Spike"))
    app.character.complex_forms.append(form)
    app.refresh_magic()
    assert len(app.complex_form_tree.get_children()) == 1
    app.character.complex_forms.pop()
    app.refresh_magic()
    assert len(app.complex_form_tree.get_children()) == 0

check("Complex Forms tab: add/refresh/remove (was missing entirely)", complex_form_add_edit_remove)


def complex_forms_survive_save_load():
    import tempfile
    from character import ShadowrunCharacter
    form = dict(next(f for f in ShadowrunCharacter.PREDEFINED_COMPLEX_FORMS if f["name"] == "Editor"))
    app.character.complex_forms.append(form)
    with tempfile.NamedTemporaryFile(suffix=".sr6", delete=False) as tf:
        path = tf.name
    try:
        app._write_character(path)
        fresh = ShadowrunCharacter()
        with open(path) as f:
            fresh.from_dict(json.load(f))
        assert any(f["name"] == "Editor" for f in fresh.complex_forms)
    finally:
        os.unlink(path)
        app.character.complex_forms.pop()

check("complex forms persist through save/load", complex_forms_survive_save_load)


def ritual_and_matrix_content_available():
    from character import ShadowrunCharacter
    from dialogs import EditGearDialog
    assert any(s.get("type") == "Ritual" for s in EditGearDialog.PREDEFINED_SOURCES["Spell"])
    assert len(ShadowrunCharacter.PREDEFINED_ENCHANTMENTS) > 0
    assert all(prep in ShadowrunCharacter.PREDEFINED_GEAR["Magic Items"] for prep in ShadowrunCharacter.PREDEFINED_ENCHANTMENTS)
    assert len(ShadowrunCharacter.MATRIX_ACTIONS) > 0
    app.update_dice_pool_options()
    values = list(app.dice_pool_combo["values"])
    assert any(v.startswith("Matrix Perception (") for v in values), values

check("rituals, enchantments, and matrix actions are wired in", ritual_and_matrix_content_available)


def portrait_roundtrip():
    from PIL import Image
    import tempfile
    img = Image.new("RGB", (800, 600), color=(120, 10, 200))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        path = tf.name
    img.save(path)
    try:
        app.character.set_portrait_from_file(path)
        assert app.character.portrait_data
        got = app.character.get_portrait_image()
        assert got is not None
        app.refresh_portrait()
    finally:
        os.unlink(path)

check("portrait load (new feature)", portrait_roundtrip)


def portrait_forced_square_and_capped():
    from PIL import Image
    import tempfile
    # A wide non-square source (2000x800) -- this used to distort the
    # Character Info layout when the portrait box grew to match it.
    img = Image.new("RGB", (2000, 800), color=(10, 200, 10))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        path = tf.name
    img.save(path)
    try:
        app.character.set_portrait_from_file(path)
        stored = app.character.get_portrait_image()
        assert stored.size[0] == stored.size[1], stored.size  # square
        assert stored.size[0] <= 512, stored.size  # capped
    finally:
        os.unlink(path)

check("portrait forced to a square crop, capped at 512px", portrait_forced_square_and_capped)

root.destroy()

print()
if failures:
    print(f"{len(failures)} FAILURE(S):", failures)
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
