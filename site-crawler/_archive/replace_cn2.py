path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find OVERLAY_JS
start_marker = 'OVERLAY_JS = r"""'
i = content.find(start_marker)
js_start = i + len(start_marker)

# Find end of raw string (next """)
js_end = content.find('"""', js_start)

before = content[:i]
after = content[js_end + 3:]  # after the closing """
js = content[js_start:js_end]

print(f"JS length: {len(js)} chars")
# Check for remaining Chinese
cn_chars = [ch for ch in js if ord(ch) > 0x4e00 and ord(ch) < 0x9fff]
print(f"Chinese chars remaining: {len(cn_chars)}")
if cn_chars:
    # Show unique Chinese strings
    import re
    cn_strings = re.findall(r'[\u4e00-\u9fff]+', js)
    print(f"Chinese strings: {set(cn_strings)}")

replacements = {
    "Config Wizard": "Config Wizard",  # already replaced? keep as is
    "Initializing...": "Initializing...",
    "Click a content link on the page (video or image)": "Click a content link on the page (video or image)",
    "Cancel": "Cancel",
    "Cancelled": "Cancelled",
    "Selection mode active, click a link...": "Selection mode active, click a link...",
    "Selected:": "Selected:",
    "What type of content?": "What type of content?",
    "Video": "Video",
    "Image": "Image",
    "Reselect": "Reselect",
    "Navigating to detail page...": "Navigating to detail page...",
    "Navigate to:": "Navigate to:",
    "Click Play / Watch Now button on this page": "Click Play / Watch Now button on this page",
    "Clicked Play": "Clicked Play",
    "Skip": "Skip",
    "Detail page loaded, click play link": "Detail page loaded, click play link",
    "Extracting image links...": "Extracting image links...",
    "Navigating to player page...": "Navigating to player page...",
    "If redirected, waiting for player to load...": "If redirected, waiting for player to load...",
    "Player page:": "Player page:",
    "Skipped play selection": "Skipped play selection",
    "Detecting video stream URL...": "Detecting video stream URL...",
    "Found": "Found",
    "iframe(s)": "iframe(s)",
    "Found stream:": "Found stream:",
    "Video stream found!": "Video stream found!",
    "Confirm & Save Config": "Confirm & Save Config",
    "Auto-detect failed, confirm player is loaded": "Auto-detect failed, confirm player is loaded",
    "Refresh & Retry": "Refresh & Retry",
    "image(s)": "image(s)",
    "Config generated, saving...": "Config generated, saving...",
    "Config saved to window.__cw_result": "Config saved to window.__cw_result",
    "You can close this window now.": "You can close this window now.",
    "Config complete! You can close this window.": "Config complete! You can close this window.",
    "Close Window": "Close Window",
    "Ready. Click Start to begin.": "Ready. Click Start to begin.",
    "Start Select": "Start Select",
    "Wizard ready": "Wizard ready",
}

for cn, en in replacements.items():
    if cn in js:
        js = js.replace(cn, en)

# Check again
cn_chars2 = [ch for ch in js if ord(ch) > 0x4e00 and ord(ch) < 0x9fff]
print(f"After replacement - Chinese chars: {len(cn_chars2)}")
if cn_chars2:
    cn_strings2 = re.findall(r'[\u4e00-\u9fff]+', js)
    print(f"Remaining Chinese: {set(cn_strings2)}")

new_content = before + start_marker + js + '"""' + after

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done. File written.")
