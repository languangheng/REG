path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'OVERLAY_JS = r"""'
i = content.find(start_marker)
js_start = i + len(start_marker)
js_end = content.find('"""', js_start)
before = content[:i]
after = content[js_end + 3:]
js = content[js_start:js_end]

# Comprehensive replacement map
replacements = {
    # UI text
    "配置向导": "Config Wizard",
    "正在初始化...": "Initializing...",
    "就绪，请点击「开始选择」": "Ready. Click Start to begin.",
    "开始选择": "Start Select",
    "取消": "Cancel",
    "已取消": "Cancelled",
    "请点击页面上的一个内容链接（视频或图片）": "Click a content link on the page (video or image)",
    "选择模式已激活，请点击页面链接...": "Selection mode active, click a link...",
    "已选择:": "Selected:",
    "这个链接指向什么内容？": "What type of content?",
    "视频内容": "Video",
    "图片内容": "Image",
    "重新选择": "Reselect",
    "正在进入详情页...": "Navigating to detail page...",
    "导航到:": "Navigate to:",
    "在详情页中，请点击「播放」或「立即播放」按钮": "Click Play / Watch Now button on this page",
    "已点击播放": "Clicked Play",
    "跳过此步": "Skip",
    "详情页已加载，请点击播放链接": "Detail page loaded, click play link",
    "正在提取图片链接...": "Extracting image links...",
    "正在进入播放页...": "Navigating to player page...",
    "如果已跳转，请等待播放页加载...": "If redirected, waiting for player to load...",
    "已进入播放页:": "Player page:",
    "跳过播放链接选择": "Skipped play selection",
    "正在自动检测视频流地址...": "Detecting video stream URL...",
    "发现": "Found",
    "个 iframe": "iframe(s)",
    "找到流地址:": "Found stream:",
    "已找到视频流地址！": "Video stream found!",
    "确认并生成配置": "Confirm & Save Config",
    "未自动找到流地址，请手动确认播放页已加载": "Auto-detect failed, confirm player is loaded",
    "刷新重试": "Refresh & Retry",
    "张图片": "image(s)",
    "配置已生成，正在保存...": "Config generated, saving...",
    "配置已保存到": "Config saved to",
    "可以关闭此窗口，返回管理界面查看结果。": "You can close this window now.",
    "配置生成完成！可以关闭此窗口。": "Config complete! You can close this window.",
    "关闭窗口": "Close Window",
    "配置向导已就绪": "Wizard ready",
    
    # Comments
    "如果已经注入过，跳过": "Already injected, skip",
    "样式": "Styles",
    "面板": "Panel",
    "状态": "State",
    "工具：生成 CSS 选择器": "Util: generate CSS selector",
    "工具：从 URL 生成正则": "Util: URL to regex pattern",
    "把数字部分替换为正则": "Replace numeric parts with regex",
    "Stage: init → 等待用户选择链接": "Stage: init -> wait for user link selection",
    "高亮所有链接": "Highlight all links",
    "询问类型": "Ask type",
    "导航到详情页": "Navigate to detail page",
    "生成同类链接的 CSS 选择器": "Generate CSS selector for similar links",
    "生成 link_pattern": "Generate link_pattern",
    "清除高亮": "Clear highlights",
    "监听页面加载完成（详情页）": "Listen for page load (detail page)",
    "到达详情页": "Arrived at detail page",
    "图片类型：提取图片": "Image type: extract images",
    "高亮所有带播放文字的链接": "Highlight links with play text",
    "用户声称已点击，我们需要找到播放页的 URL": "User clicked play, find player page URL",
    "实际是导航到了播放页，监听下一次 load": "Actually navigated to player, listen for next load",
    "监听是否跳转": "Monitor navigation",
    "提取流地址": "Extract stream URL",
    "扫描": "Scan",
    "提取图片链接": "Extract image links",
    "完成": "Finish",
    "把状态存到 window，让 Python 后端读取": "Save state to window for Python backend",
    "启动": "Start",
    "链接": "link",
    "类型": "type",
    "播放": "play",
    "选择器": "selector",
    "正则": "regex",
    "同类链接的": "similar links'",
    "占位，后面替换": "placeholder, replace later",
    "等待用户选择链接": "Waiting for user to select link",
}

count = 0
for cn, en in replacements.items():
    if cn in js:
        js = js.replace(cn, en)
        count += 1

# Check remaining Chinese
import re
remaining = re.findall(r'[\u4e00-\u9fff]+', js)
if remaining:
    print(f"WARNING: {len(set(remaining))} Chinese strings still remaining:")
    for s in sorted(set(remaining)):
        print(f"  '{s}'")
else:
    print("All Chinese replaced!")

print(f"Replaced {count} strings")

new_content = before + start_marker + js + '"""' + after
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
