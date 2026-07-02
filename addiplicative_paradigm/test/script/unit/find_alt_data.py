# -*- coding: utf-8 -*-
"""Try alternative LIGO data sources"""
import urllib.request, urllib.error, socket

# Test connectivity first
hosts_to_test = [
    ("gwosc.org", 443),
    ("zenodo.org", 443),
    ("www.gwosc.org", 443),
    ("data.gwpsh.com", 443),  # possible China mirror
    ("ligometadata.dcc.ligo.org", 443),
]

print("Testing network connectivity to various LIGO data hosts:")
for host, port in hosts_to_test:
    try:
        socket.setdefaulttimeout(8)
        sock = socket.create_connection((host, port), timeout=8)
        sock.close()
        print(f"  {host}:{port}  -->  OK")
    except Exception as e:
        print(f"  {host}:{port}  -->  FAIL: {e}")

# Try specific LIGO data files
print("\nTrying specific data file URLs:")
test_urls = [
    ("Zenodo (Zenodo ID 13993902)", "https://zenodo.org/records/13993902/files/L-L1_GWOSC_O4KHZ_R1-1126257411-4096.hdf5"),
    ("Zenodo (redirect check)", "https://zenodo.org/record/13993902/files/L-L1_GWOSC_O4KHZ_R1-1126257411-4096.hdf5"),
    ("LIGO DCC (old format)", "https://www.ligo.org/science/Publication-GW150914/data/L-L1_GWOSC_O4KHZ_R1-1126257411-4096.hdf5"),
]

for name, url in test_urls:
    print(f"\n  {name}:")
    print(f"  URL: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=15)
        size = response.headers.get('Content-Length', 'unknown')
        print(f"  --> Status: {response.status}, Size: {size}")
        if int(size) if size != 'unknown' else 0 > 1000:
            print(f"  --> DATA FILE FOUND! Ready to download.")
    except urllib.error.HTTPError as e:
        print(f"  --> HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        print(f"  --> URL Error: {e.reason}")
    except Exception as e:
        print(f"  --> Error: {e}")

# Check if any local hdf5 files exist anywhere on the system
print("\nSearching for existing LIGO HDF5 files on the system...")
import os
for search_path in ['C:\\Users\\languangheng', 'D:\\', 'E:\\', 'F:']:
    if os.path.exists(search_path):
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if 'gwosc' in f.lower() or 'ligo' in f.lower() or 'hdf5' in f.lower():
                    fpath = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fpath)
                        if size > 1000000:  # > 1MB
                            print(f"  Found: {fpath} ({size/1024/1024:.1f} MB)")
                    except:
                        pass
