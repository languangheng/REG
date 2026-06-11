"""Replace all Chinese text in OVERLAY_JS with English."""
import re

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find OVERLAY_JS boundaries
start = content.find('OVERLAY_JS = r"""')
end = content.find('"""\n\n# ── Python 端')
if start == -1 or end == -1:
    print("ERROR: Could not find OVERLAY_JS boundaries")
    exit(1)

before = content[:start]
after = content[end + len('"""\n\n# ── Python 端'):]
js = content[start + len('OVERLAY_JS = r"""'):end]

# Replacement map (Chinese -> English)
replacements = {
    "配置向导": "Config Wizard",
    "正在初始化...": "Initializing...",
    "请点击页面上的一个内容链接（视频或图片）": "Click a content link on the page (video or image)",
    "取消": "Cancel",
    "已取消": "Cancelled",
    "选择模式已激活，请点击页面链接...": "Selection mode active, click a link...",
    "已选择:": "Selected:",
    "这个链接指向什么内容？": "What type of content?",
    "视频内容": "Video",
    "图片内容": "Image",
    "重新选择": "Reselect",
    "正在进入详情页...": "Navigating to detail page...",
    "导航到:": "Navigate to:",
    "在详情页中，请点击「播放」或「立即播放」按钮/链接": "Click Play / Watch Now button on this page",
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
    "配置已保存到 window.__cw_result": "Config saved to window.__cw_result",
    "可以关闭此窗口，返回管理界面查看结果。": "You can close this window now.",
    "配置生成完成！可以关闭此窗口。": "Config complete! You can close this window.",
    "关闭窗口": "Close Window",
    "就绪，请点击「开始选择」": "Ready. Click Start to begin.",
    "开始选择": "Start Select",
    "配置向导已就绪": "Wizard ready",
}

for cn, en in replacements.items():
    js = js.replace(cn, en)

new_content = before + 'OVERLAY_JS = r"""' + js + '"""\n\n# ── Python 端' + after

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Done. Replaced {len(replacements)} Chinese strings.")
print(f"File size: {len(new_content)} bytes")
