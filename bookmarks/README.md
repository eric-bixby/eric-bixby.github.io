# Eric Bixby's Bookmarks

## Requirements

* Need Python 3.12 or newer
* Do "pip3 install -r requirements.txt"

## Known Issues

* When trying to run bookmarks_manager.py on RHEL, get the following error:
```
X Error of failed request:  BadLength (poly request too large or internal Xlib length error)
  Major opcode of failed request:  139 (RENDER)
  Minor opcode of failed request:  20 (RenderAddGlyphs)
  Serial number of failed request:  790
  Current serial number in output stream:  854
```

## View Page without Style

1. Open the developer tools (usually by pressing F12 or right-clicking and selecting Inspect).
2. Go to the Console tab.
3. Paste and run the following JavaScript snippet to disable all stylesheets and inline styles

```javascript
var d = document;
for (var s in S = d.styleSheets) S[s].disabled = true;
for (var i in I = d.querySelectorAll("[style]")) I[i].style = "";
```

## Sync Procedure

1. Rename the sync-folder in the toolbar-folder to the current date and time (for example, "20260407:1358") to track when synced
2. Export local bookmarks to bookmarks-local.html (same folder as bookmarks.html in repo)
3. Use diff-tool to compare diffs between bookmarks.html and bookmarks-local.html
4. Remove existing local bookmarks from the browser to prevent duplicates from the imported bookmarks
5. Import the updated bookmarks.html into the browser
6. Relocate the imported bookmarks as needed (changes needed vary by browser)

## How to Ignore Text with Regex in Meld

1. Open Preferences: Go to Edit > Preferences.
2. Navigate to Text Filters: Select the Text Filters tab in the Preferences dialog.
3. Add a New Filter:

   1. Click the Add button (often a + sign) to create a new filter.
   2. Give your filter a descriptive name (e.g., "Ignore Timestamps" or "SVN Keywords").
   3. Enter your regular expression in the provided field.
   4. Ensure the Active checkbox for the new filter is enabled.

4. Apply and View: The text matching the pattern will still be visible in the comparison
   view but will not be highlighted as a difference. You may need to refresh or restart
   Meld for the changes to take effect.

## Diff-Tool Rules

* Select the "Minor" button to treat unimportant text as the same

Unimportant text:

```
<H1>.*</H1>
PERSONAL_TOOLBAR_FOLDER="true">.*</H3>
ADD_DATE=".*"
LAST_MODIFIED=".*"
ICON=".*"
<meta .*
.*</meta>
```
