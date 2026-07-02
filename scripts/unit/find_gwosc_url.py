# -*- coding: utf-8 -*-
"""Try multiple GWOSC URLs to find correct GW150914 data"""
import urllib.request
import urllib.error

urls_to_try = [
    # GWTC-1 catalog
    "https://www.gwosc.org/eventapi/html/GWTC-1/GW150914/",
    # Single event
    "https://www.gwosc.org/eventapi/html/event/GW150914/",
    # O3a sensitive data
    "https://www.gwosc.org/eventapi/html/GWTC-2.1/GW150914/",
    # 4kHz data
    "https://www.gwosc.org/eventapi/html/GW150914/L-L1_GWOSC_O4khz_R1-1126257411-4096.hdf5",
    # 16kHz data
    "https://www.gwosc.org/eventapi/html/GW150914/L-L1_GWOSC_O3RawR1-1126257411-16384.hdf5",
    # Try gwpy's known URL pattern
    "https://www.gwosc.org/static/media/L-L1_GWOSC_O4khz_R1-1126257411-4096.hdf5",
]

for url in urls_to_try:
    print(f"Trying: {url}", end=" ... ", flush=True)
    try:
        req = urllib.request.Request(url, method='HEAD')
        response = urllib.request.urlopen(req, timeout=10)
        print(f"OK! Status: {response.status}")
        print(f"  Content-Length: {response.headers.get('Content-Length', 'unknown')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
    except Exception as e:
        print(f"Error: {e}")
