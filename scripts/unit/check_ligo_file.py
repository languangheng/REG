# -*- coding: utf-8 -*-
import h5py, numpy as np, os

fname = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit\L-L1_GWOSC_16KHZ_R1-1126259447-32.hdf5"
print(f"File: {fname}")
print(f"Size: {os.path.getsize(fname) / 1024 / 1024:.1f} MB")

with h5py.File(fname, 'r') as f:
    print(f"Keys: {list(f.keys())}")
    for k in f.keys():
        print(f"  {k}: {type(f[k])}")
        if hasattr(f[k], 'keys'):
            for sk in f[k].keys():
                print(f"    {sk}")
    
    strain = f['strain/Strain'][:]
    print(f"\nStrain: shape={strain.shape}, dtype={strain.dtype}")
    print(f"Duration: {len(strain)/16384:.1f} s at 16384 Hz")
    print(f"NaN count: {np.sum(np.isnan(strain))}")
    print(f"Min: {np.nanmin(strain):.4e}, Max: {np.nanmax(strain):.4e}")
    print(f"GPS start: 1126259447, end: ~{1126259447 + len(strain)/16384:.0f}")
    # GW150914 merger time: GPS 1126259462.423
    merger_gps = 1126259462.423
    start_gps = 1126259447
    merger_sample = int((merger_gps - start_gps) * 16384)
    print(f"\nGW150914 merger at GPS {merger_gps}")
    print(f"Merger is at sample ~{merger_sample} / {len(strain)} ({merger_sample/len(strain)*100:.1f}% into file)")
