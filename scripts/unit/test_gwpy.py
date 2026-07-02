# -*- coding: utf-8 -*-
from gwpy.timeseries import TimeSeries
print('Testing LIGO data download...')
# GW150914: GPS 1126259462
# Get 16 seconds around merger
data = TimeSeries.fetch_open_data('L1', 1126259454, 1126259470)
print(f'Downloaded: {len(data)} samples, duration={data.duration:.1f}s, fs={data.sample_rate:.0f}Hz')
print(f'Data range: {data.min():.6e} to {data.max():.6e}')
