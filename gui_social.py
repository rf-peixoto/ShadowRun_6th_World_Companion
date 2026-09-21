"""Contacts and Background tabs.

The portrait editor lives here (not Character Info) -- see gui_basic.py's
module docstring for why: a non-square photo used to grow the "Portrait"
box to its own pixel dimensions and break the Character Info grid next to
it. character.py now force-crops every portrait to a square before it's
ever stored, so the display box here is always the same fixed size.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

import theme
from dialogs import EditContactDialog, DescriptionViewer

try:
    from PIL import ImageTk
except ImportError:
    ImageTk = None

# Displayed thumbnail size. The stored portrait itself is capped separately,
# at a larger square size, by character.set_portrait_from_file.
PORTRAIT_DISPLAY_SIZE = (150, 150)


class SocialTabMixin:
    # -- Contacts -----------------------------------------------------------

    def setup_contacts_tab(self):
        tab = self.tabs["Contacts"]

        list_frame = ttk.LabelFrame(tab, text="Contacts")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Name", "Type", "Loyalty", "Connection")
        self.contact_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.contact_tree.heading(col, text=col)
            self.contact_tree.column(col, width=100)
        self.contact_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.contact_tree.bind("<Double-1>", self.edit_contact)
        self.contact_tree.bind("<<TreeviewSelect>>", self.show_contact_description)

        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(ctrl_frame, text="Add Contact", command=self.add_contact).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Edit Contact", command=self.edit_contact).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Remove Contact", command=self.remove_contact).pack(side=tk.LEFT, padx=5)

    def show_contact_description(self, event=None):
        selected = self.contact_tree.selection()
        if not selected:
            return
        index = self.contact_tree.index(selected[0])
        contact = self.character.contacts[index]
        content = (f"Name: {contact.get('name', '')}\n"
                   f"Type: {contact.get('type', '')}\n"
                   f"Loyalty: {contact.get('loyalty', '')}\n"
                   f"Connection: {contact.get('connection', '')}\n\n"
                   f"Notes:\n{contact.get('notes', '')}")
        DescriptionViewer(self.root, "Contact Details", content)

    def add_contact(self):
        dialog = EditContactDialog(self.root)
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        self.character.contacts.append(dialog.result)
        self.contact_tree.insert("", "end", values=(
            dialog.result["name"], dialog.result.get("type", ""),
            dialog.result.get("loyalty", ""), dialog.result.get("connection", "")
        ))
        self.on_character_changed()

    def edit_contact(self, event=None):
        selected = self.contact_tree.selection()
        if not selected:
            return
        index = self.contact_tree.index(selected[0])
        contact = self.character.contacts[index]

        dialog = EditContactDialog(self.root, contact)
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        contact.update(dialog.result)
        self.contact_tree.item(selected[0], values=(
            dialog.result["name"], dialog.result.get("type", ""),
            dialog.result.get("loyalty", ""), dialog.result.get("connection", "")
        ))
        self.on_character_changed()

    def remove_contact(self):
        selected = self.contact_tree.selection()
        if not selected:
            return
        index = self.contact_tree.index(selected[0])
        del self.character.contacts[index]
        self.contact_tree.delete(selected[0])
        self.on_character_changed()

    def refresh_contacts(self):
        for item in self.contact_tree.get_children():
            self.contact_tree.delete(item)
        for contact in self.character.contacts:
            self.contact_tree.insert("", "end", values=(
                contact.get("name", "Unknown"), contact.get("type", ""),
                contact.get("loyalty", ""), contact.get("connection", "")
            ))

    # -- Background -----------------------------------------------------------

    def setup_background_tab(self):
        tab = self.tabs["Background"]

        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        age_rep_frame = ttk.Frame(top_frame)
        age_rep_frame.pack(side=tk.LEFT, fill=tk.Y, anchor="n")

        ttk.Label(age_rep_frame, text="Age:").pack(side=tk.LEFT, padx=5)
        self.age_spin = ttk.Spinbox(age_rep_frame, from_=0, to=200, width=5)
        self.age_spin.pack(side=tk.LEFT, padx=5)
        self.age_spin.bind("<FocusOut>", self.on_character_changed)

        ttk.Label(age_rep_frame, text="Reputation:").pack(side=tk.LEFT, padx=5)
        self.reputation_spin = ttk.Spinbox(age_rep_frame, from_=0, to=20, width=5)
        self.reputation_spin.pack(side=tk.LEFT, padx=5)
        self.reputation_spin.bind("<FocusOut>", self.on_character_changed)

        # Portrait: a fixed PORTRAIT_DISPLAY_SIZE pixel box regardless of the
        # source photo. A tk.Label's width/height option is in *characters*
        # while showing text but silently switches to *pixels* once an image
        # is assigned -- using a Label for both the "No Portrait" placeholder
        # and the actual image meant the same width/height value produced
        # two very different box sizes (this was tried and visibly broke:
        # the placeholder was a reasonable size but the image shrank to a
        # sliver). A Canvas has no such ambiguity: it's always exactly
        # PORTRAIT_DISPLAY_SIZE pixels, whether it's showing the placeholder
        # text or the (already square-cropped) portrait image.
        portrait_frame = ttk.LabelFrame(top_frame, text="Portrait")
        portrait_frame.pack(side=tk.RIGHT, padx=(20, 0))
        self.portrait_canvas = tk.Canvas(
            portrait_frame, bg=theme.ENTRY_BG,
            width=PORTRAIT_DISPLAY_SIZE[0], height=PORTRAIT_DISPLAY_SIZE[1],
            highlightthickness=0
        )
        self.portrait_canvas.pack(padx=5, pady=5)
        pbtns = ttk.Frame(portrait_frame)
        pbtns.pack(pady=(0, 5))
        ttk.Button(pbtns, text="Load", command=self.load_portrait).pack(side=tk.LEFT, padx=2)
        ttk.Button(pbtns, text="Clear", command=self.clear_portrait).pack(side=tk.LEFT, padx=2)

        frame = ttk.LabelFrame(tab, text="Character Background")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.background_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20,
                                                          bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG)
        self.background_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.background_text.bind("<FocusOut>", self.on_character_changed)

    # -- Portrait -------------------------------------------------------

    def load_portrait(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            self.character.set_portrait_from_file(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load portrait: {e}")
            return
        self.refresh_portrait()

    def clear_portrait(self):
        self.character.clear_portrait()
        self.refresh_portrait()

    def refresh_portrait(self):
        cx = PORTRAIT_DISPLAY_SIZE[0] / 2
        cy = PORTRAIT_DISPLAY_SIZE[1] / 2
        self.portrait_canvas.delete("all")
        img = self.character.get_portrait_image(PORTRAIT_DISPLAY_SIZE)
        if img is None or ImageTk is None:
            self._portrait_photo = None
            self.portrait_canvas.create_text(cx, cy, text="No Portrait", fill=theme.FG)
            return
        self._portrait_photo = ImageTk.PhotoImage(img)
        self.portrait_canvas.create_image(cx, cy, image=self._portrait_photo)

    def commit_background(self):
        try:
            self.character.age = int(self.age_spin.get() or "0")
        except ValueError:
            pass
        try:
            self.character.reputation = int(self.reputation_spin.get() or "0")
        except ValueError:
            pass
        self.character.background = self.background_text.get("1.0", tk.END).strip()

    def refresh_background(self):
        self.age_spin.delete(0, tk.END)
        self.age_spin.insert(0, str(self.character.age))
        self.reputation_spin.delete(0, tk.END)
        self.reputation_spin.insert(0, str(self.character.reputation))
        self.background_text.delete("1.0", tk.END)
        self.background_text.insert(tk.END, self.character.background)
        self.refresh_portrait()
