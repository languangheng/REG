"""Simplify OVERLAY_JS: remove type selection, auto-detect from URL."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the onLinkClick function (remove choose_type step)
old_onlinkclick = '''  function onLinkClick(e) {
    if (state.stage !== 'select_link') return;
    e.preventDefault();
    e.stopPropagation();

    const a = e.currentTarget;
    state.selected_link = { href: a.href, text: a.textContent.trim().substring(0,80), selector: getSelector(a) };
    log(`Selected: ${a.textContent.trim().substring(0,40)}`);
    log(`URL: ${a.href}`);
    // Clear highlights
    document.querySelectorAll('.cw-highlight').forEach(el => {
      el.classList.remove('cw-highlight');
      el.removeEventListener('click', onLinkClick, true);
    });
    // Ask type
    state.stage = 'choose_type';
    setStep('What type of content?');
    setActions([
      { label: 'Video', cls: 'btn-primary', fn: () => chooseType('video') },
      { label: 'Image', cls: 'btn-primary', fn: () => chooseType('image') },
      { label: 'Reselect', cls: 'btn-ghost', fn: startSelectLink },
    ]);
  }'''

new_onlinkclick = '''  function onLinkClick(e) {
    if (state.stage !== 'select_link') return;
    e.preventDefault();
    e.stopPropagation();

    const a = e.currentTarget;
    state.selected_link = { href: a.href, text: a.textContent.trim().substring(0,80), selector: getSelector(a) };
    log(`Selected: ${a.textContent.trim().substring(0,40)}`);
    log(`URL: ${a.href}`);
    // Clear highlights
    document.querySelectorAll('.cw-highlight').forEach(el => {
      el.classList.remove('cw-highlight');
      el.removeEventListener('click', onLinkClick, true);
    });

    // Auto-detect type from URL
    const href = a.href;
    if (href.includes('/vodplay/') || href.includes('/play/') || href.includes('/video/')) {
      state.link_type = 'video';
      log('Auto-detected: video content');
    } else if (href.includes('/voddetail/') || href.includes('/detail/') || href.includes('/art/')) {
      state.link_type = 'video';  // Detail page, still video flow
      log('Auto-detected: video detail page');
    } else if (/\\.(jpg|png|gif|webp)/i.test(href)) {
      state.link_type = 'image';
      log('Auto-detected: image content');
    } else {
      state.link_type = 'video';  // Default to video
      log('Default: video content');
    }

    // Navigate directly
    proceedToDetail();
  }

  function proceedToDetail() {
    const type = state.link_type;
    const pattern = urlToPattern(state.selected_link.href);
    if (type === 'video') {
      state.config.link_patterns.video_detail.push(pattern);
    } else {
      state.config.link_patterns.art_detail.push(pattern);
    }
    state.link_selector = state.selected_link.selector;
    log(`CSS selector: ${state.link_selector}`);
    log(`URL regex: ${pattern}`);

    state.stage = 'navigating';
    setStep(`Navigating to detail page...`);
    setActions([]);
    log(`Navigate to: ${state.selected_link.href}`);
    window.location.href = state.selected_link.href;
  }'''

if old_onlinkclick in content:
    content = content.replace(old_onlinkclick, new_onlinkclick)
    # Remove chooseType function since it's no longer needed
    content = content.replace(
        '''  function chooseType(type) {
    state.link_type = type;
    log(`type: ${type}`);
    // Generate link_pattern
    const pattern = urlToPattern(state.selected_link.href);
    if (type === 'video') {
      state.config.link_patterns.video_detail.push(pattern);
    } else {
      state.config.link_patterns.art_detail.push(pattern);
    }
    // Generate CSS selector for similar links
    state.link_selector = state.selected_link.selector;
    log(`CSS selector: ${state.link_selector}`);
    log(`URL regex: ${pattern}`);

    // Navigate to detail page
    state.stage = 'navigating';
    setStep(`Navigating to detail page...`);
    setActions([]);
    log(`Navigate to: ${state.selected_link.href}`);
    window.location.href = state.selected_link.href;
  }''',
        ''
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Simplified: removed choose_type step, auto-detect from URL")
else:
    print("ERROR: old_onlinkclick not found!")
    # Debug: show what we're looking for
    idx = content.find('function onLinkClick')
    if idx >= 0:
        print(f"Found 'function onLinkClick' at index {idx}")
        print("Snippet:", repr(content[idx:idx+200]))
