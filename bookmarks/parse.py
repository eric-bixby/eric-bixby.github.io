#!/usr/bin/env python3
"""
Generate **index.html**: a dark‑mode bookmarks page from a Netscape‑format export.

Layout
----
* **Horizontal toolbar** fixed at the top, built from the *Bookmarks Toolbar*
  root. First‑level folders behave like menu buttons; hovering reveals a drop‑down
  list. Bookmarks that aren't inside a folder are collected into a pseudo‑folder
  with the toolbar's title.
* **Index/Main tables** built from *Bookmarks Menu* folders (if any). If the
  menu contains no folders the page still renders—just without the tables.
* Prints clear error messages (✖) and exits with *non‑zero* status on fatal
  problems (parse failure, missing roots, I/O errors).
"""

# pip install bookmarks_parser

from __future__ import annotations

import html
import itertools
import pathlib
import sys
from typing import List, Tuple

import bookmarks_parser

# ────
# Configuration
# ────

DEFAULT_INPUT = "bookmarks.html"
DEFAULT_OUTPUT = "index.html"

Counter = itertools.count  # global counter factory for folder IDs

# ────
# Helper functions
# ────


def _assign_folder_ids(nodes: List[dict], counter: itertools.count) -> None:
    """Recursively assign a unique integer ``_fid`` to every folder node."""
    for node in nodes:
        if node.get("type") == "folder":
            node["_fid"] = next(counter)
            _assign_folder_ids(node.get("children", []), counter)


# ────
# Sorting functions
# ────


def _sort_folders_first_alpha(nodes: List[dict]) -> List[dict]:
    """
    Sort nodes with folders first, then bookmarks, both alphabetically by title.
    This is the default sorting method.
    """
    folders = [n for n in nodes if n.get("type") == "folder"]
    bookmarks = [n for n in nodes if n.get("type") == "bookmark"]

    folders.sort(key=lambda n: (n.get("title") or "").lower())
    bookmarks.sort(key=lambda n: (n.get("title") or "").lower())

    return folders + bookmarks


def _sort_alpha_only(nodes: List[dict]) -> List[dict]:
    """Sort all nodes alphabetically by title, regardless of type."""
    return sorted(nodes, key=lambda n: (n.get("title") or "").lower())


def _sort_none(nodes: List[dict]) -> List[dict]:
    """No sorting - preserve original order."""
    return nodes


# Dictionary of available sorting methods
SORT_METHODS = {
    "folders_first_alpha": _sort_folders_first_alpha,
    "alpha_only": _sort_alpha_only,
    "none": _sort_none,
}

# Default sorting method
DEFAULT_SORT_METHOD = "folders_first_alpha"


def sort_nodes(
    nodes: List[dict],
    method: str = DEFAULT_SORT_METHOD,
    recursive: bool = True,
) -> List[dict]:
    """
    Sort nodes using the specified method.

    Args:
        nodes: List of bookmark/folder nodes to sort
        method: Sorting method name (key from SORT_METHODS)
        recursive: If True, recursively sort children of folders

    Returns:
        Sorted list of nodes
    """
    if method not in SORT_METHODS:
        raise ValueError(
            f"Unknown sort method: {method}. "
            f"Available: {', '.join(SORT_METHODS.keys())}"
        )

    sort_func = SORT_METHODS[method]
    sorted_nodes = sort_func(nodes)

    if recursive:
        for node in sorted_nodes:
            if node.get("type") == "folder" and node.get("children"):
                node["children"] = sort_nodes(
                    node["children"], method=method, recursive=True
                )

    return sorted_nodes


# ────
# Toolbar (horizontal) builder
# ────


def _links_html(nodes: List[dict]) -> str:
    """Return <a> list for the given bookmark *nodes* joined by <br>."""
    links: List[str] = []
    for n in nodes:
        if n.get("type") != "bookmark":
            continue
        title = html.escape(n.get("title", n.get("url", "")))
        url = html.escape(n.get("url", "#"))
        icon = (
            n.get("icon")
            or n.get("icon_uri")
            or n.get("ICON_URI")
            or n.get("ICON")
        )
        icon_html = (
            f'<img src="{html.escape(icon)}" class="favicon" alt="" />'
            if icon
            else ""
        )
        links.append(f'<a href="{url}">{icon_html}{title}</a>')
    return "<br>\n".join(links)


def build_toolbar(
    toolbar_root: dict | None, sort_method: str = DEFAULT_SORT_METHOD
) -> str:
    """Return the HTML markup for the horizontal toolbar."""
    if toolbar_root is None:
        return ""  # nothing to render

    items: List[str] = []
    loose: List[dict] = []  # bookmarks not inside a folder

    # Sort toolbar children (folders + loose bookmarks)
    children = sort_nodes(toolbar_root.get("children", []), sort_method, recursive=True)

    for child in children:
        if child.get("type") == "folder":
            title = html.escape(child.get("title", "(untitled)"))
            sorted_folder_children = sort_nodes(
                child.get("children", []), sort_method, recursive=True
            )
            items.append(
                "<div class='tb-item'>"
                f"<span class='tb-label'>{title}</span>"
                f"<div class='tb-menu'>{_links_html(sorted_folder_children)}</div>"
                "</div>"
            )
        elif child.get("type") == "bookmark":
            loose.append(child)

    if loose:  # add pseudo‑folder first
        label = html.escape(toolbar_root.get("title", "Toolbar"))
        items.insert(
            0,
            "<div class='tb-item'>"
            f"<span class='tb-label'>{label}</span>"
            f"<div class='tb-menu'>{_links_html(sort_nodes(loose, sort_method, recursive=False))}</div>"
            "</div>",
        )

    return "<nav id='toolbar'>" + "\n".join(items) + "</nav>"


# ────
# Bookmarks Menu helpers
# ────


def collect_index_items(nodes: List[dict]) -> List[str]:
    out: List[str] = []
    for n in nodes:
        if n.get("type") == "folder":
            fid = n["_fid"]
            title = html.escape(n.get("title", "(untitled folder)"))
            out.append(
                f'<a id="index{fid}" href="#folder{fid}" class="folder">{title}</a>'
            )
            out.extend(collect_index_items(n.get("children", [])))
    return out


def collect_main_items(nodes: List[dict]) -> List[str]:
    out: List[str] = []
    for n in nodes:
        if n.get("type") == "folder":
            fid = n["_fid"]
            title = html.escape(n.get("title", "(untitled folder)"))
            out.append(
                f'<a id="folder{fid}" href="#top" class="folder">{title}</a>'
            )
            out.extend(collect_main_items(n.get("children", [])))
        elif n.get("type") == "bookmark":
            title = html.escape(n.get("title", "(untitled)") or n.get("url", ""))
            url = html.escape(n.get("url", "#"))
            icon = (
                n.get("icon")
                or n.get("icon_uri")
                or n.get("iconUri")
                or n.get("ICON_URI")
                or n.get("ICON")
            )
            icon_html = (
                f'<img src="{html.escape(icon)}" class="favicon" alt="" />'
                if icon
                else ""
            )
            anchor_cls = "" if icon else " class='no-icon'"
            out.append(f'<a href="{url}"{anchor_cls}>{icon_html}{title}</a>')
    return out


def table_html(cols: List[Tuple[str, List[str]]]) -> str:
    if not cols:
        return ""  # render nothing when list empty
    heads = "".join(f"<th>{hdr}</th>" for hdr, _ in cols)
    cells = []
    for _, items in cols:
        joined = "<br>\n".join(items)
        cells.append(f"<td>{joined}</td>\n")
    return f"<table>\n<tr>{heads}</tr>\n<tr>{''.join(cells)}</tr>\n</table>"


# ────
# Page builder
# ────

"""
**CSS Summary**

- `html{ … }`
  – Due to the toolbar, the scroll offset makes hash links land where you expect them.
- `html,body{ … }`
  – Removes default margins/padding, sets a dark background, light text colour and a system‑font stack for the whole page.
- `#toolbar{ … }`
  – Fixed‑position top bar, full‑width, dark background, flex layout with spacing, padding, bottom border and high z‑index.
- `#toolbar .tb-item{position:relative;}`
  – Makes each toolbar item a positioning context for its dropdown menu.
- `#toolbar .tb-label{color:#ffcb6b;font-weight:bold;cursor:pointer;}`
  – Styles the label inside a toolbar item (bright colour, bold, pointer cursor).
- `#toolbar .tb-menu{display:none;position:absolute;top:100%;left:0;background:#1e1e1e;padding:0.5em;border:1px solid #333;max-width:320px;white-space:nowrap;}`
  – Hidden dropdown menu, positioned just below its parent, with dark background, padding and a max width.
- `#toolbar .tb-item:hover .tb-menu{display:block;}`
  – Shows the dropdown when the parent item is hovered.
- `#toolbar a{color:#4ea3ff;text-decoration:none;line-height:1.3;}`
  – Toolbar links, blue colour, no underline, with a comfortable line height.
- `#toolbar a:hover{text-decoration:underline;}`
  – Underlines a toolbar link on hover.
- `main{margin-top:3rem;padding:1rem;}`
  – Gives the main content area space below the fixed toolbar and inner padding.
- `table{width:1200px;table-layout:fixed;border-collapse:collapse;border:1px solid black;}`
  – Sets a wide fixed‑layout table, collapses borders, and adds an outer black border.
- `th,td{text-align:left;vertical-align:top;padding:2px;border:none}`
  – Left‑aligns text, aligns cell content to the top, minimal padding, removes inner borders.
- `th{background:#1e1e1e;font-weight:600;}`
  – Dark background and semi‑bold font for header cells.
- `td, th{padding:5px;border:1px solid black;}`
  – Overrides previous padding to 5 px and adds a black border around every cell.
- `a{color:#4ea3ff;text-decoration:none;line-height:1.25;}`
  – Global link style: blue, no underline, slightly tighter line height.
- `a:hover{text-decoration:underline;}`
  – Underlines any link on hover.
- `.folder{font-weight:bold;color:#ffcb6b;}`
  – Bold, amber‑coloured folder titles.
- `img.favicon{width:16px;height:16px;vertical-align:middle;margin-right:0.5em;border-radius:2px;}`
  – Small favicons, vertically centered, spaced from text, with rounded corners.
- `.no-icon{padding-left:calc(16px + 0.5em);}`
  – Adds left padding equal to the favicon width plus its margin, used when an icon is absent.
"""

def build_html(
    toolbar: str,
    idx_cols: List[Tuple[str, List[str]]],
    main_cols: List[Tuple[str, List[str]]],
) -> str:
    CSS = """

html{
    scroll-padding-top: 3rem;
}

html,body{
  margin:0;
  padding:0;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;
  background:#121212;
  color:#e0e0e0;
}

#toolbar{position:fixed;top:0;left:0;right:0;background:#1e1e1e;display:flex;gap:1.25em;padding:0.5em 1em;border-bottom:1px solid #333;z-index:1000;}
#toolbar .tb-item{position:relative;}
#toolbar .tb-label{color:#ffcb6b;font-weight:bold;cursor:pointer;}
#toolbar .tb-menu{display:none;position:absolute;top:100%;left:0;background:#1e1e1e;padding:0.5em;border:1px solid #333;max-width:320px;white-space:nowrap;}
#toolbar .tb-item:hover .tb-menu{display:block;}
#toolbar a{color:#4ea3ff;text-decoration:none;line-height:1.3;}
#toolbar a:hover{text-decoration:underline;}

main{margin-top:3rem;padding:1rem;}

table {
  width: 1200px;
  table-layout: fixed;
  border-collapse: collapse;
  border: 1px solid black;
}

th,td{text-align:left;vertical-align:top;padding:2px;border:none}
th{background:#1e1e1e;font-weight:600;}
td, th {
  padding: 5px;
  border: 1px solid black;
}

a{color:#4ea3ff;text-decoration:none;line-height:1.25;}
a:hover{text-decoration:underline;}
.folder{font-weight:bold;color:#ffcb6b;}
img.favicon{width:16px;height:16px;vertical-align:middle;margin-right:0.5em;border-radius:2px;}
.no-icon{padding-left:calc(16px + 0.5em);}

"""

    return "\n".join(
        [
            "<!doctype html><html><head><meta charset='utf-8'><title>Bookmarks</title>",
            f"<style>{CSS}</style></head><body><a id='top'></a>",
            toolbar,
            "<main>",
            table_html(idx_cols),
            table_html(main_cols),
            "</main></body></html>",
        ]
    )


# ────
# Main entry
# ────


def die(msg: str) -> None:
    """Print msg to stderr and exit non‑zero."""
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(1)


def main(
    bookmarks_file: str = DEFAULT_INPUT,
    output_file: str = DEFAULT_OUTPUT,
    sort_method: str = DEFAULT_SORT_METHOD,
) -> None:
    # Parse export ----
    try:
        parsed = bookmarks_parser.parse(bookmarks_file)
    except Exception as exc:
        die(f"Failed to parse '{bookmarks_file}': {exc}")

    menu_root = next((n for n in parsed if n.get("ns_root") == "menu"), None)
    if menu_root is None:
        die("No 'menu' root found in the export.")

    toolbar_root = next((n for n in parsed if n.get("ns_root") == "toolbar"), None)
    toolbar_html = build_toolbar(toolbar_root, sort_method)

    # Build Bookmarks Menu columns ----
    menu_children = menu_root.get("children", [])
    menu_folders = [n for n in menu_children if n.get("type") == "folder"]

    # Sort top-level menu folders (folders-first, alpha by default)
    menu_folders = sort_nodes(menu_folders, sort_method, recursive=False)

    # Prepare columns for index and main tables
    index_cols: List[Tuple[str, List[str]]] = []
    main_cols: List[Tuple[str, List[str]]] = []

    if menu_folders:
        _assign_folder_ids(menu_folders, Counter())
        for folder in menu_folders:
            sorted_children = sort_nodes(
                folder.get("children", []), sort_method, recursive=True
            )
            folder["children"] = sorted_children

            fid = folder["_fid"]
            title = html.escape(folder.get("title", "(untitled)"))

            index_cols.append(
                (
                    f'<a id="index{fid}" href="#folder{fid}" class="folder">{title}</a>',
                    collect_index_items(sorted_children),
                )
            )
            main_cols.append(
                (
                    f'<a id="folder{fid}" href="#top" class="folder">{title}</a>',
                    collect_main_items(sorted_children),
                )
            )

    # Generate full HTML ----
    html_output = build_html(toolbar_html, index_cols, main_cols)

    try:
        pathlib.Path(output_file).write_text(html_output, encoding="utf-8")
        print(f"✔ Wrote {output_file}")
    except Exception as exc:
        die(f"Failed to write '{output_file}': {exc}")


if __name__ == "__main__":
    main()
