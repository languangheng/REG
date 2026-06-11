# BrowserAct 安装与使用指南

## 目标
安装 BrowserAct skill 及其 CLI，并整理使用方法。

## 安装结果
- **uv**: 0.11.19 — 通过 `irm https://astral.sh/uv/install.ps1 | iex` 安装到 `C:\Users\languangheng\.local\bin`
- **browser-act-cli**: 0.1.27 — 通过 `uv tool install browser-act-cli --python 3.12` 安装（uv 自动下载 Python 3.12.13）
- **Skill**: browser-act 已安装到 `C:\Users\languangheng\.qclaw\skills\browser-act`
- **注意**: uv 安装路径 `%USERPROFILE%\.local\bin` 需在 PATH 中，每次新终端需 `$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"` 或将其永久加入用户 PATH

## 核心用法
1. `browser-act browser create` 创建浏览器
2. `browser-act browser open <id> <url>` 打开网页
3. `browser-act state/click/input/screenshot` 等交互命令需 `--session` 参数
4. 三大特色：solve-captcha（验证码）、remote-assist（远程协助）、stealth-extract（隐身提取）
5. 网络捕获：network requests / HAR 录制 / Cookie 管理

## 约束
- Python 3.12 由 uv 管理，系统 Python 3.14 不受影响
- 所有数据本地存储，仅 solve-captcha 会外发验证码图片
