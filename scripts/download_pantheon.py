import urllib.request
import os

script_dir = r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju'
out_path = os.path.join(script_dir, 'pantheon_data.txt')

urls = [
    "https://github.com/galacticnebula/pantheon_plus/raw/main/Pantheon%2B_SH0ES.dat",
    "https://raw.githubusercontent.com/galacticnebula/pantheon_plus/main/Pantheon%2B_SH0ES.dat",
    "https://github.com/afitani/PantheonPlus-SHOES-Data/raw/main/Pantheon%2B_SH0ES.dat",
    "https://raw.githubusercontent.com/afitani/PantheonPlus-SHOES-Data/main/Pantheon%2B_SH0ES.dat",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for url in urls:
    try:
        print(f"Trying: {url}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            with open(out_path, 'wb') as f:
                f.write(content)
        print(f"SUCCESS! Downloaded {len(content)} bytes")
        break
    except Exception as e:
        print(f"FAILED: {e}")
else:
    print("All URLs failed.")
