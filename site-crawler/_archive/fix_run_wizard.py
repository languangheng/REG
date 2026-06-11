path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_text = '''        print("[wizard] Overlay injected. Use the browser panel to complete setup.")
        print("[wizard] Waiting for user to finish (window close or __cw_result)...")

        # Step 3: poll window.__cw_result
        max_wait = 600  # 10 min max
        start = time.time()
        result = None
        while time.time() - start < max_wait:
            try:
                val = client.evaluate_js("JSON.stringify(window.__cw_result || null)")
                if val and val != "null":
                    result = json.loads(val)
                    print(f"[wizard] Got config result")
                    break
            except Exception:
                pass
            time.sleep(3)

        if not result:
            print("[wizard] Timeout, no result received")
            return

        # Step 4: generate config and write sites.yaml
        print("[wizard] Generating config file...")
        config = build_config(key, name, base_url, entry_url, result)
        write_config(key, config)
        print(f"[wizard] Config written to sites.yaml")'''

new_text = '''        print("[wizard] Overlay injected. Use the browser panel to complete setup.")
        print("[wizard] Waiting for user to finish (window close or __cw_result)...")

        # Track URL for navigation detection
        def get_url():
            try:
                return client.evaluate_js("window.location.href")
            except Exception:
                return None

        last_url = get_url()

        # Step 3: poll window.__cw_result
        max_wait = 600  # 10 min max
        start = time.time()
        result = None
        while time.time() - start < max_wait:
            # Check for result
            try:
                val = client.evaluate_js("JSON.stringify(window.__cw_result || null)")
                if val and val != "null":
                    result = json.loads(val)
                    print(f"[wizard] Got config result")
                    break
            except Exception:
                pass

            # Check for URL change (navigation)
            current_url = get_url()
            if current_url and last_url and current_url != last_url:
                print(f"[wizard] Navigation detected: {current_url}")
                print("[wizard] Waiting for page load...")
                client.wait(5)
                print("[wizard] Re-injecting overlay...")
                try:
                    client.evaluate_js(OVERLAY_JS)
                    client.wait(2)
                    print("[wizard] Re-injection complete. Continue using the panel.")
                except Exception as e:
                    print(f"[wizard] Re-injection failed: {e}")
                last_url = current_url
            elif current_url and not last_url:
                last_url = current_url

            time.sleep(3)

        if not result:
            print("[wizard] Timeout, no result received")
            return

        # Step 4: generate config and write sites.yaml
        print("[wizard] Generating config file...")
        config = build_config(key, name, base_url, entry_url, result)
        write_config(key, config)
        print(f"[wizard] Config written to sites.yaml")'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed run_wizard: added URL tracking and re-injection")
else:
    print("ERROR: old_text not found!")
    idx = content.find('Overlay injected')
    if idx >= 0:
        print("Found 'Overlay injected' at index", idx)
        print("Context:", repr(content[idx:idx+300]))
    else:
        print("'Overlay injected' not found at all")
