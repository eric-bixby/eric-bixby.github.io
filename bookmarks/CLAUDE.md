# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repo manages browser bookmarks in Netscape HTML format. It has two main Python tools:

- **`parse.py`** — reads `bookmarks.html` and generates `index.html`, a dark-mode static page with a fixed toolbar and bookmark tables.
- **`bookmark_manager.py`** — a Tkinter GUI for viewing and editing Netscape bookmark HTML files.

## Dependencies

```sh
pip install bookmarks_parser   # required by parse.py
pip install pillow             # required by bookmark_manager.py
```

The CI workflow (`generate-index.yml`) expects a `requirements.txt` in the repo root — it currently exists and lists `bookmarks_parser` and `Pillow`.

## Running the Tools

Generate `index.html` from `bookmarks.html`:
```sh
python parse.py
# or with explicit args:
python parse.py bookmarks.html index.html
```

Launch the GUI bookmark manager:
```sh
python bookmark_manager.py
```

Update bookmarks and push to both repos (`~/git/bookmarks` and `~/git/eric-bixby.github.io`):
```sh
./update.sh
```

## Architecture

### `parse.py`

Parses `bookmarks.html` using the `bookmarks_parser` library (which returns a list of nodes with `type`, `title`, `url`, `children`, `ns_root`, etc.). The script:

1. Finds the `toolbar` root node and builds a fixed horizontal nav with hover dropdowns.
2. Finds the `menu` root node and builds two side-by-side HTML tables — an index table (folder links) and a main table (folder contents with bookmarks).
3. Sorting is configurable via `SORT_METHODS` (`folders_first_alpha`, `alpha_only`, `none`); default is `folders_first_alpha`.
4. Writes the result to `index.html`.

### `bookmark_manager.py`

A standalone Tkinter GUI with two classes:

- **`NetscapeBookmarkParser`** (subclass of `html.parser.HTMLParser`) — hand-written parser for Netscape bookmark HTML. Builds a tree of `{"name", "children", "bookmarks"}` dicts. Does not use the `bookmarks_parser` library.
- **`BookmarkManager`** — the main GUI. Holds the entire bookmark tree in `self.data = {"folders": [...]}`. Operations (add/edit/delete folder or bookmark) mutate this dict and call `populate_tree()` to re-render the Treeview. Load/save via `load_html()` / `save_html()` which use `NetscapeBookmarkParser` and `generate_netscape_html()`.

Icon loading supports base64 data URIs (`ICON=`) and remote URLs (`ICON_URI=`), with a per-session `self.icon_cache` dict.

## CI

`.github/workflows/generate-index.yml` triggers on pushes to `main` when `bookmarks.html` changes. It runs `python parse.py bookmarks.html`, commits the updated `index.html`, and pushes back to the repo.

## Bookmark Sync Workflow

See `README.md` for the manual sync procedure using Meld (diff tool) to compare exported browser bookmarks against `bookmarks.html`.
