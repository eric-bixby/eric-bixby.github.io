#!/usr/bin/env python3

# pip install Pillow

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
import webbrowser
import html
from html.parser import HTMLParser
from PIL import Image, ImageTk
import io
import base64
import urllib.request
import urllib.error


class NetscapeBookmarkParser(HTMLParser):
    """Parser for Netscape Bookmark HTML format (with nested folders)"""

    def __init__(self):
        super().__init__()
        # Root is an implicit container with children (top-level folders)
        self.root = {
            "name": "ROOT",
            "children": [],
            "bookmarks": []
        }
        self.folder_stack = [self.root]
        self.next_is_folder = False
        self.next_is_bookmark = False
        self.current_bookmark_attrs = {}
        self.current_folder_attrs = {}

    @property
    def folders(self):
        # Top-level folders are children of root
        return self.root["children"]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if tag == "h3":
            # Folder name will be in next data; store attributes for that folder
            self.next_is_folder = True
            self.current_folder_attrs = attrs_dict

        elif tag == "a":
            # Bookmark title will be in next data
            self.next_is_bookmark = True
            self.current_bookmark_attrs = attrs_dict

        elif tag == "dl":
            # New level in the folder tree starts after a H3/DT
            pass

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "dl":
            # End of a folder level; pop if not root
            if len(self.folder_stack) > 1:
                self.folder_stack.pop()

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.next_is_folder:
            folder_name = data
            new_folder = {
                "name": folder_name,
                "children": [],
                "bookmarks": []
            }

            # Preserve folder-level Netscape attributes
            if "add_date" in self.current_folder_attrs:
                new_folder["add_date"] = self.current_folder_attrs["add_date"]
            if "last_modified" in self.current_folder_attrs:
                new_folder["last_modified"] = self.current_folder_attrs["last_modified"]
            if "personal_toolbar_folder" in self.current_folder_attrs:
                new_folder["personal_toolbar_folder"] = (
                    self.current_folder_attrs["personal_toolbar_folder"]
                )

            # Add to current folder
            self.folder_stack[-1]["children"].append(new_folder)
            # This folder becomes current for subsequent DL
            self.folder_stack.append(new_folder)

            self.next_is_folder = False
            self.current_folder_attrs = {}

        elif self.next_is_bookmark:
            current_folder = self.folder_stack[-1]

            bookmark = {
                "title": data,
                "url": self.current_bookmark_attrs.get("href", ""),
                "description": "",
                "date": datetime.now().strftime("%Y-%m-%d")
            }

            # Preserve Netscape attributes
            if "add_date" in self.current_bookmark_attrs:
                bookmark["add_date"] = self.current_bookmark_attrs["add_date"]
                try:
                    ts = int(self.current_bookmark_attrs["add_date"])
                    bookmark["date"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                except Exception:
                    pass

            if "last_modified" in self.current_bookmark_attrs:
                bookmark["last_modified"] = self.current_bookmark_attrs["last_modified"]

            if "icon" in self.current_bookmark_attrs:
                bookmark["icon"] = self.current_bookmark_attrs["icon"]

            if "icon_uri" in self.current_bookmark_attrs:
                bookmark["icon_uri"] = self.current_bookmark_attrs["icon_uri"]

            if "tags" in self.current_bookmark_attrs:
                bookmark["tags"] = self.current_bookmark_attrs["tags"]

            current_folder["bookmarks"].append(bookmark)
            self.next_is_bookmark = False


class BookmarkManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Bookmark Manager")
        self.root.geometry("900x600")

        # In-memory structure: {"folders": [ {name, children, bookmarks}, ... ]}
        self.data = {"folders": []}

        # Icon cache: {icon_key: PhotoImage}
        self.icon_cache = {}

        # Default icons
        self.default_icon = None
        self.folder_icon = None

        self.create_default_icons()
        self.create_widgets()
        self.populate_tree()

    # ---------- Icon Management ----------

    def create_default_icons(self):
        """Create default placeholder icons"""
        from PIL import ImageDraw

        # Default bookmark icon (gray circle with dot)
        default_img = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
        draw = ImageDraw.Draw(default_img)
        draw.ellipse([2, 2, 14, 14], fill=(200, 200, 200, 255), outline=(150, 150, 150, 255))
        draw.ellipse([6, 6, 10, 10], fill=(150, 150, 150, 255))
        self.default_icon = ImageTk.PhotoImage(default_img)

        # Folder icon (yellow folder)
        folder_img = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
        draw = ImageDraw.Draw(folder_img)
        draw.rectangle([1, 5, 15, 14], fill=(255, 200, 50, 255), outline=(200, 150, 0, 255))
        draw.polygon(
            [1, 5, 5, 5, 7, 3, 10, 3, 12, 5, 15, 5],
            fill=(255, 220, 100, 255),
            outline=(200, 150, 0, 255),
        )
        self.folder_icon = ImageTk.PhotoImage(folder_img)

    def get_icon_for_bookmark(self, bookmark):
        """Get icon for a bookmark, loading from ICON or ICON_URI if available"""
        icon_key = bookmark.get("icon") or bookmark.get("icon_uri")

        if not icon_key:
            return self.default_icon

        if icon_key in self.icon_cache:
            return self.icon_cache[icon_key]

        try:
            img = None

            # ICON as data URI
            if "icon" in bookmark:
                icon_data = bookmark["icon"]
                if icon_data.startswith("data:image") and "base64," in icon_data:
                    base64_data = icon_data.split("base64,", 1)[1]
                    img_data = base64.b64decode(base64_data)
                    img = Image.open(io.BytesIO(img_data))

            # ICON_URI as URL
            if img is None and "icon_uri" in bookmark:
                icon_uri = bookmark["icon_uri"]
                try:
                    with urllib.request.urlopen(icon_uri, timeout=2) as response:
                        img_data = response.read()
                        img = Image.open(io.BytesIO(img_data))
                except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
                    pass

            if img:
                img = img.resize((16, 16), Image.Resampling.LANCZOS)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                photo = ImageTk.PhotoImage(img)
                self.icon_cache[icon_key] = photo
                return photo

        except Exception:
            pass

        self.icon_cache[icon_key] = self.default_icon
        return self.default_icon

    # ---------- GUI Setup ----------

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        title_label = ttk.Label(
            main_frame,
            text="📚 Bookmark Manager",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Tree frame (no search row)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Columns: URL, Date (no Folder column)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("URL", "Date"),
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading("#0", text="Title")
        self.tree.heading("URL", text="URL")
        self.tree.heading("Date", text="Date Added")

        self.tree.column("#0", width=260, minwidth=180)
        self.tree.column("URL", width=360, minwidth=240)
        self.tree.column("Date", width=120, minwidth=100)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self.on_double_click)

        # Right-side buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=1, sticky="n")

        ttk.Button(
            button_frame, text="➕ Add Folder", command=self.add_folder, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Button(
            button_frame, text="🔖 Add Bookmark", command=self.add_bookmark, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Button(
            button_frame, text="✏️ Edit", command=self.edit_item, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Button(
            button_frame, text="🗑️ Delete", command=self.delete_item, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(pady=8, fill=tk.X)

        ttk.Button(
            button_frame, text="⬇️ Expand All", command=self.expand_all, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Button(
            button_frame, text="⬆️ Collapse All", command=self.collapse_all, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(pady=8, fill=tk.X)

        ttk.Button(
            button_frame, text="📂 Load HTML", command=self.load_html, width=20
        ).pack(pady=4, fill=tk.X)

        ttk.Button(
            button_frame, text="💾 Save HTML", command=self.save_html, width=20
        ).pack(pady=4, fill=tk.X)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, textvariable=self.status_var, anchor=tk.W
        )
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    # ---------- Tree Population (no search) ----------

    def populate_tree(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        def add_folder_recursive(folder, parent_id=""):
            folder_name = folder.get("name", "Untitled Folder")
            is_toolbar = bool(folder.get("personal_toolbar_folder"))
            tags = ("folder", "toolbar") if is_toolbar else ("folder",)

            folder_id = self.tree.insert(
                parent_id,
                "end",
                text=folder_name,
                values=("", ""),
                tags=tags,
                image=self.folder_icon
            )

            # Bookmarks
            for bm in folder.get("bookmarks", []):
                icon = self.get_icon_for_bookmark(bm)
                self.tree.insert(
                    folder_id,
                    "end",
                    text=bm.get("title", "Untitled"),
                    values=(bm.get("url", ""), bm.get("date", "")),
                    tags=("bookmark",),
                    image=icon
                )

            # Child folders
            for child in folder.get("children", []):
                add_folder_recursive(child, folder_id)

        def count_bookmarks_recursive(folder):
            c = len(folder.get("bookmarks", []))
            for ch in folder.get("children", []):
                c += count_bookmarks_recursive(ch)
            return c

        total_bookmarks = 0
        toolbar_folder = None
        other_folders = []
        for top_folder in self.data.get("folders", []):
            if top_folder.get("personal_toolbar_folder"):
                toolbar_folder = top_folder
            else:
                other_folders.append(top_folder)

        if toolbar_folder:
            add_folder_recursive(toolbar_folder, "")
            total_bookmarks += count_bookmarks_recursive(toolbar_folder)

        self.other_bookmarks_node = self.tree.insert(
            "", "end",
            text="Other Bookmarks",
            values=("", ""),
            tags=("folder", "other_bookmarks"),
            image=self.folder_icon
        )
        for top_folder in other_folders:
            add_folder_recursive(top_folder, self.other_bookmarks_node)
            total_bookmarks += count_bookmarks_recursive(top_folder)

        self.status_var.set(
            f"Total: {len(self.data.get('folders', []))} top-level folders, {total_bookmarks} bookmarks"
        )

    # ---------- Folder/Bookmark Lookup Helpers ----------

    def find_folder_and_parent(self, folder_name, parent=None, folders=None):
        """Find first folder with given name; returns (folder, parent_folder)."""
        if folders is None:
            folders = self.data.get("folders", [])
            parent = None

        for f in folders:
            if f.get("name") == folder_name:
                return f, parent
            child_result = self.find_folder_and_parent(
                folder_name, parent=f, folders=f.get("children", [])
            )
            if child_result[0] is not None:
                return child_result
        return None, None

    def find_bookmark(self, title, url, folder):
        """Find bookmark dict in given folder."""
        for bm in folder.get("bookmarks", []):
            if bm.get("title") == title and bm.get("url") == url:
                return bm
        return None

    def find_folder_for_item(self, item_id):
        """Given a Treeview item id that is a folder, find its folder dict."""
        name = self.tree.item(item_id, "text")
        folder, _ = self.find_folder_and_parent(name)
        return folder

    # ---------- Folder & Bookmark Operations ----------

    def add_folder(self):
        """Add a new folder as a child of the selected folder."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a folder row first.")
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")
        if "folder" not in tags:
            messagebox.showwarning("Warning", "Add Folder requires a folder row to be selected.")
            return

        folder_name = simpledialog.askstring("Add Folder", "Enter folder name:")
        if not folder_name:
            return
        folder_name = folder_name.strip()
        if not folder_name:
            return

        # "Other Bookmarks" is virtual — add a new top-level folder directly
        if "other_bookmarks" in tags:
            for f in self.data.get("folders", []):
                if f.get("name") == folder_name:
                    messagebox.showwarning("Warning", "A folder with that name already exists.")
                    return
            new_folder = {"name": folder_name, "children": [], "bookmarks": []}
            self.data.setdefault("folders", []).append(new_folder)
            self.populate_tree()
            return

        parent_folder = self.find_folder_for_item(item)
        if parent_folder is None:
            messagebox.showerror("Error", "Internal folder lookup failed.")
            return

        # Optional: duplicate name check at this level
        for ch in parent_folder.get("children", []):
            if ch.get("name") == folder_name:
                messagebox.showwarning(
                    "Warning", "A folder with that name already exists here."
                )
                return

        new_folder = {"name": folder_name, "children": [], "bookmarks": []}
        parent_folder.setdefault("children", []).append(new_folder)

        self.populate_tree()

    def add_bookmark(self):
        """Add a bookmark as a child of the selected folder."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a folder row first.")
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")
        if "folder" not in tags:
            messagebox.showwarning("Warning", "Add Bookmark requires a folder row to be selected.")
            return

        if "other_bookmarks" in tags or "toolbar" in tags:
            messagebox.showwarning("Warning", "Select a folder inside to add a bookmark.")
            return

        folder = self.find_folder_for_item(item)
        if folder is None:
            messagebox.showerror("Error", "Internal folder lookup failed.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Bookmark")
        dialog.geometry("460x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Title
        ttk.Label(dialog, text="Title:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        title_entry = ttk.Entry(dialog, width=40)
        title_entry.grid(row=0, column=1, padx=10, pady=5)

        # URL
        ttk.Label(dialog, text="URL:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        url_entry = ttk.Entry(dialog, width=40)
        url_entry.grid(row=1, column=1, padx=10, pady=5)

        # Description
        ttk.Label(dialog, text="Description:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        desc_text = tk.Text(dialog, width=30, height=3)
        desc_text.grid(row=2, column=1, padx=10, pady=5)

        # Icon URI
        ttk.Label(dialog, text="Icon URI:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        icon_entry = ttk.Entry(dialog, width=40)
        icon_entry.grid(row=3, column=1, padx=10, pady=5)

        # Tags
        ttk.Label(dialog, text="Tags:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        tags_entry = ttk.Entry(dialog, width=40)
        tags_entry.grid(row=4, column=1, padx=10, pady=5)

        def on_save():
            title = title_entry.get().strip()
            url = url_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            icon_uri = icon_entry.get().strip()
            tags = tags_entry.get().strip()

            if not title or not url:
                messagebox.showwarning("Warning", "Title and URL are required!")
                return

            ts = int(datetime.now().timestamp())
            bm = {
                "title": title,
                "url": url,
                "description": description,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "add_date": str(ts),
                "last_modified": str(ts),
            }
            if icon_uri:
                bm["icon_uri"] = icon_uri
            if tags:
                bm["tags"] = tags

            folder.setdefault("bookmarks", []).append(bm)
            self.populate_tree()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        title_entry.focus()

    def edit_item(self):
        """Edit selected folder or bookmark."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to edit!")
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")
        if "toolbar" in tags or "other_bookmarks" in tags:
            messagebox.showwarning("Warning", "This folder cannot be edited.")
            return

        text = self.tree.item(item, "text")
        tags = self.tree.item(item, "tags")

        # Folder
        if "folder" in tags:
            self.edit_folder(text)
        else:
            self.edit_bookmark(item)

    def edit_folder(self, folder_name):
        folder, parent = self.find_folder_and_parent(folder_name)
        if not folder:
            return
        new_name = simpledialog.askstring(
            "Edit Folder", "Enter new folder name:", initialvalue=folder_name
        )
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == folder_name:
            return

        folder["name"] = new_name
        self.populate_tree()

    def edit_bookmark(self, item):
        text = self.tree.item(item, "text")
        values = self.tree.item(item, "values")
        url = values[0]

        # Find parent folder of this bookmark
        parent_item = self.tree.parent(item)
        if not parent_item:
            return
        folder_name = self.tree.item(parent_item, "text")
        folder, _ = self.find_folder_and_parent(folder_name)
        if not folder:
            return

        bm = self.find_bookmark(text, url, folder)
        if not bm:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Bookmark")
        dialog.geometry("460x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Title
        ttk.Label(dialog, text="Title:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        title_entry = ttk.Entry(dialog, width=40)
        title_entry.insert(0, bm.get("title", ""))
        title_entry.grid(row=0, column=1, padx=10, pady=5)

        # URL
        ttk.Label(dialog, text="URL:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        url_entry = ttk.Entry(dialog, width=40)
        url_entry.insert(0, bm.get("url", ""))
        url_entry.grid(row=1, column=1, padx=10, pady=5)

        # Description
        ttk.Label(dialog, text="Description:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        desc_text = tk.Text(dialog, width=30, height=3)
        if bm.get("description"):
            desc_text.insert("1.0", bm["description"])
        desc_text.grid(row=2, column=1, padx=10, pady=5)

        # Icon URI
        ttk.Label(dialog, text="Icon URI:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        icon_entry = ttk.Entry(dialog, width=40)
        if bm.get("icon_uri"):
            icon_entry.insert(0, bm["icon_uri"])
        icon_entry.grid(row=3, column=1, padx=10, pady=5)

        # Tags
        ttk.Label(dialog, text="Tags:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        tags_entry = ttk.Entry(dialog, width=40)
        if bm.get("tags"):
            tags_entry.insert(0, bm["tags"])
        tags_entry.grid(row=4, column=1, padx=10, pady=5)

        def on_update():
            new_title = title_entry.get().strip()
            new_url = url_entry.get().strip()
            new_desc = desc_text.get("1.0", tk.END).strip()
            new_icon_uri = icon_entry.get().strip()
            new_tags = tags_entry.get().strip()

            if not new_title or not new_url:
                messagebox.showwarning("Warning", "Title and URL are required!")
                return

            # Update bookmark in-place
            bm["title"] = new_title
            bm["url"] = new_url
            bm["description"] = new_desc
            if "add_date" not in bm:
                bm["add_date"] = str(int(datetime.now().timestamp()))
            bm["last_modified"] = str(int(datetime.now().timestamp()))
            if new_icon_uri:
                bm["icon_uri"] = new_icon_uri
            else:
                bm.pop("icon_uri", None)
            if new_tags:
                bm["tags"] = new_tags
            else:
                bm.pop("tags", None)

            self.populate_tree()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Update", command=on_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def delete_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to delete!")
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")
        if "toolbar" in tags or "other_bookmarks" in tags:
            messagebox.showwarning("Warning", "This folder cannot be deleted.")
            return

        text = self.tree.item(item, "text")
        values = self.tree.item(item, "values")
        tags = self.tree.item(item, "tags")

        if not messagebox.askyesno("Confirm Delete", f"Delete '{text}'?"):
            return

        # Folder
        if "folder" in tags:
            folder_name = text
            folder, parent = self.find_folder_and_parent(folder_name)
            if not folder:
                return
            if parent is None:
                self.data["folders"].remove(folder)
            else:
                parent["children"].remove(folder)
        else:
            # Bookmark
            title = text
            url = values[0]

            parent_item = self.tree.parent(item)
            if not parent_item:
                return
            folder_name = self.tree.item(parent_item, "text")
            folder, _ = self.find_folder_and_parent(folder_name)
            if folder:
                bm = self.find_bookmark(title, url, folder)
                if bm:
                    folder["bookmarks"].remove(bm)

        self.populate_tree()

    # ---------- Netscape HTML Load/Save ----------

    def load_html(self):
        fname = filedialog.askopenfilename(
            title="Load Bookmarks (Netscape HTML)",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")]
        )
        if not fname:
            return
        try:
            with open(fname, "r", encoding="utf-8") as f:
                content = f.read()
            parser = NetscapeBookmarkParser()
            parser.feed(content)

            # Replace current data with loaded folders
            self.data["folders"] = parser.folders

            # Clear icon cache when loading new data
            self.icon_cache.clear()

            self.populate_tree()
            messagebox.showinfo("Success", "Loaded bookmarks from HTML.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load HTML: {e}")

    def save_html(self):
        fname = filedialog.asksaveasfilename(
            title="Save Bookmarks (Netscape HTML)",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if not fname:
            return
        try:
            html_content = self.generate_netscape_html()
            with open(fname, "w", encoding="utf-8") as f:
                f.write(html_content)
            messagebox.showinfo("Success", "Saved bookmarks to HTML.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save HTML: {e}")

    def generate_netscape_html(self):
        lines = []
        lines.append("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
        lines.append("<!-- This is an automatically generated file.")
        lines.append("     It will be read and overwritten.")
        lines.append("     DO NOT EDIT! -->")
        lines.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
        lines.append("<TITLE>Bookmarks</TITLE>")
        lines.append("<H1>Bookmarks</H1>")
        lines.append("<DL><p>")

        def write_folder(folder, indent="    "):
            name = html.escape(folder.get("name", "Folder"))

            # Folder attributes
            f_attrs = []
            if "add_date" in folder:
                f_attrs.append(f'ADD_DATE="{folder["add_date"]}"')
            if "last_modified" in folder:
                f_attrs.append(f'LAST_MODIFIED="{folder["last_modified"]}"')
            if "personal_toolbar_folder" in folder:
                f_attrs.append(
                    f'PERSONAL_TOOLBAR_FOLDER="{folder["personal_toolbar_folder"]}"'
                )

            f_attr_str = (" " + " ".join(f_attrs)) if f_attrs else ""

            # Folder header line with attributes
            lines.append(f'{indent}<DT><H3{f_attr_str}>{name}</H3>')
            lines.append(f"{indent}<DL><p>")

            # Bookmarks
            for bm in folder.get("bookmarks", []):
                title = html.escape(bm.get("title", "Untitled"))
                # DO NOT HTML-ESCAPE THE URL ITSELF
                url = bm.get("url", "") # <--- CHANGE IS HERE

                attrs = [f'HREF="{url}"'] # <--- AND HERE
                if "add_date" in bm:
                    attrs.append(f'ADD_DATE="{bm["add_date"]}"')
                else:
                    try:
                        ds = bm.get("date", "")
                        if ds:
                            dt = datetime.strptime(ds, "%Y-%m-%d")
                            attrs.append(f'ADD_DATE="{int(dt.timestamp())}"')
                    except Exception:
                        pass

                if "last_modified" in bm:
                    attrs.append(f'LAST_MODIFIED="{bm["last_modified"]}"')

                if "icon" in bm:
                    attrs.append(f'ICON="{bm["icon"]}"')

                if "icon_uri" in bm:
                    attrs.append(f'ICON_URI="{bm["icon_uri"]}"')

                if "tags" in bm:
                    attrs.append(f'TAGS="{bm["tags"]}"')

                attr_str = " ".join(attrs)
                lines.append(f'{indent}    <DT><A {attr_str}>{title}</A>')
                if bm.get("description"):
                    lines.append(
                        f'{indent}    <DD>{html.escape(bm["description"])}'
                    )

            # Child folders
            for ch in folder.get("children", []):
                write_folder(ch, indent + "    ")

            lines.append(f"{indent}</DL><p>")

        for f in self.data.get("folders", []):
            write_folder(f, "    ")

        lines.append("</DL><p>")
        return "\n".join(lines)

    # ---------- Misc GUI Handlers ----------

    def expand_all(self):
        def recurse(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                recurse(child)

        for i in self.tree.get_children():
            recurse(i)

    def collapse_all(self):
        def recurse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                recurse(child)

        for i in self.tree.get_children():
            recurse(i)

    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item, "values")
        tags = self.tree.item(item, "tags")
        if "bookmark" in tags and values and values[0]:
            webbrowser.open(values[0])


def main():
    root = tk.Tk()
    app = BookmarkManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
