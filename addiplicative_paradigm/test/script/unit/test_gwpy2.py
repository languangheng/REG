# -*- coding: utf-8 -*-
import sys
print('Testing gwpy...', flush=True)
try:
    from gwpy.timeseries import TimeSeries
    print('gwpy imported OK', flush=True)
    # Try a shorter segment first
    print('Downloading 4s of LIGO data around GW150914...', flush=True)
    data = TimeSeries.fetch_open_data('L1', 1126259460, 1126259464)
    print(f'Success! len={len(data)}, duration={data.duration}s', flush=True)
except Exception as e:
    print(f'Error: {e}', flush=True)
    import traceback
    traceback.print_exc()
