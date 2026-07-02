# -*- coding: utf-8 -*-
"""Download LIGO GW150914 data from GWOSC using urllib"""
import urllib.request
import os

url = "https://www.gwosc.org/eventapi/html/GW150914/L-L1_GWOSC_O4khz_R1-1126257411-4096.hdf5"
output = "GW150914_L1_4khz.hdf5"

print(f"Downloading GW150914 data from GWOSC...")
print(f"URL: {url}")
print(f"Output: {output}")

try:
    # Set a proxy if needed
    # urllib.request.install_opener(...)
    
    def report(count, block_size, total_size):
        percent = min(100, count * block_size * 100 // total_size)
        if count % 500 == 0 or percent == 100:
            print(f"  {percent}% ({count * block_size / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)", flush=True)
    
    urllib.request.urlretrieve(url, output, reporthook=report)
    size = os.path.getsize(output)
    print(f"\nDownload complete! File size: {size / 1024 / 1024:.1f} MB")
    
    # Quick verify it's a valid HDF5 file
    import h5py
    with h5py.File(output, 'r') as f:
        print(f"HDF5 file valid. Keys: {list(f.keys())}")
        if 'strain' in f:
            strain = f['strain/Strain'][:]
            print(f"Strain data: {len(strain)} samples")
    
except Exception as e:
    print(f"Download failed: {e}")
    import traceback
    traceback.print_exc()
