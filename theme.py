"""Single dark theme shared by the whole app.

The two original tools each had their own slightly different dark palette
(``run_tracker.py`` used plain ``tk`` widgets with one set of grays,
``wip_main.py`` used ``ttk`` styles with another). Merged into one so the
Runs tab doesn't look like a different app bolted onto the character sheet.
"""

BG = "#1c1c1c"
BG_ALT = "#2e2e2e"
FG = "#e0e0e0"
ENTRY_BG = "#333333"
SELECTED_BG = "#4a6984"
ACCENT = "#4F9BFF"
GOOD = "#4CAF50"
WARN = "#FF9800"
BAD = "#F44336"


def apply_theme(root):
    """Configure ttk styles for dark mode. Returns the ttk.Style instance."""
    from tkinter import ttk

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=FG, font=("Arial", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabelframe", background=BG, foreground=FG)
    style.configure("TLabelframe.Label", background=BG, foreground=FG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", background="#333", foreground=FG,
                    borderwidth=1, focusthickness=3, focuscolor="#333")
    style.map("TButton",
              background=[("active", "#444")],
              foreground=[("active", FG)])
    style.configure("TCheckbutton", background=BG, foreground=FG)
    style.map("TCheckbutton", background=[("active", BG)])
    style.configure("TRadiobutton", background=BG, foreground=FG)
    style.map("TRadiobutton", background=[("active", BG)])
    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG, insertcolor=FG)
    style.configure("TCombobox", fieldbackground=ENTRY_BG, foreground=FG, background=BG,
                    arrowcolor=FG, selectforeground=FG, selectbackground=ENTRY_BG)
    # ttk.Combobox in "readonly" state (used throughout the app for the
    # Metatype/Role/Magic/Tradition/Lifestyle dropdowns) picks its text and
    # background colors from state-based style.map overrides, not the plain
    # style.configure above -- without this, the "readonly"/"disabled"
    # states fall back to the platform's default light colors, which is why
    # the dropdown text was unreadable (white-on-white).
    style.map("TCombobox",
              fieldbackground=[("readonly", ENTRY_BG), ("disabled", BG_ALT)],
              foreground=[("readonly", FG), ("disabled", "#888888")],
              background=[("readonly", ENTRY_BG), ("disabled", BG_ALT)],
              selectbackground=[("readonly", ENTRY_BG)],
              selectforeground=[("readonly", FG)],
              arrowcolor=[("readonly", FG), ("disabled", "#888888")])
    style.configure("TSpinbox", fieldbackground=ENTRY_BG, foreground=FG, background=BG)
    style.configure("Treeview", background=ENTRY_BG, foreground=FG,
                    fieldbackground=ENTRY_BG, borderwidth=0)
    style.map("Treeview", background=[("selected", SELECTED_BG)])
    style.configure("Treeview.Heading", background="#2d2d2d", foreground=FG)
    style.configure("Vertical.TScrollbar", background="#333", troughcolor=BG)
    style.configure("Horizontal.TScrollbar", background="#333", troughcolor=BG)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background="#2d2d2d", foreground=FG, padding=[10, 5])
    style.map("TNotebook.Tab", background=[("selected", BG)])
    style.configure("TProgressbar", troughcolor=ENTRY_BG, background=GOOD)
    style.configure("TPanedwindow", background=BG)

    # The Combobox's open dropdown list is a separate plain Tk Listbox (not
    # a ttk widget), so it ignores ttk styles entirely and has to be colored
    # through Tk's option database instead.
    root.option_add("*TCombobox*Listbox.background", ENTRY_BG)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECTED_BG)
    root.option_add("*TCombobox*Listbox.selectForeground", FG)

    root.configure(bg=BG)
    return style
