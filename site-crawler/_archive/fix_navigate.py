path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\browser_act.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_navigate = '''    def navigate(self, url: str) -> str:
        """导航到 URL。若 session 不存在则先打开浏览器。"""
        try:
            return self._run("navigate", url, timeout=30)
        except RuntimeError:
            return self.open(url)'''

new_navigate = '''    def navigate(self, url: str) -> str:
        """导航到 URL。若 session 不存在则先打开浏览器。"""
        try:
            return self._run("navigate", url, timeout=30)
        except RuntimeError:
            # Fallback: open browser first
            bid = self.browser_id or self.get_first_browser_id()
            if not bid:
                # Create new browser
                import subprocess
                env = os.environ.copy()
                env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")
                result = subprocess.run(
                    [self._cmd, "browser", "create", "--type=chrome-direct"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                output = result.stdout + result.stderr
                # Parse browser id from output like "id=xxx"
                m = re.search(r'id=(\S+)', output)
                if m:
                    self.browser_id = m.group(1)
                    bid = self.browser_id
                else:
                    raise RuntimeError(f"Failed to create browser: {output}")
            return self._run("browser", "open", bid, url, timeout=30)'''

if old_navigate in content:
    content = content.replace(old_navigate, new_navigate)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed navigate: auto-create browser on fallback")
else:
    print("ERROR: old_navigate not found")
    idx = content.find('def navigate')
    if idx >= 0:
        print("Found 'def navigate' at", idx)
        print(repr(content[idx:idx+300]))
