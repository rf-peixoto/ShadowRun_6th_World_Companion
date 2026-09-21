#!/usr/bin/env python3
"""Entry point for the Shadowrun 6E Character & Run Manager.

Run with:
    python main.py
"""

import tkinter as tk

from app import CharacterSheetApp


def main():
    root = tk.Tk()
    app = CharacterSheetApp(root)

    # First paint of the condition monitors needs the canvases to have a
    # real size, which they don't have until the window is actually mapped.
    root.after(100, app.draw_condition_monitors)
    root.bind("<Configure>", lambda e: app.draw_condition_monitors())

    root.mainloop()


if __name__ == "__main__":
    main()
