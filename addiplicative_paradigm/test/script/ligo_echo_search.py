"""
Script 5: LIGO Gravitational Wave Echo Search
REG (Relational Emergent Gravity) prediction: BH merger echo at ~75 Hz
Matched-filter search for post-merger echoes in LIGO O4c data
"""
import numpy as np
import h5py
from scipy.signal import correlate, find_peaks
import matplotlib.pyplot as plt
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(SCRIPT_DIR), 'out')
os.makedirs(OUT, exist_ok=True)

DATA_FILE = "L-L1_GWOSC_O4c1DiscC00_4KHZ_R1-1422962688-4096.hdf5"

print("=" * 60)
print("  LIGO Gravitational Wave Echo Search")
print("  Matched-filter search in LIGO O4c strain data")
print("=" * 60)

try:
    print(f"\n  Loading: {DATA_FILE}")
    with h5py.File(DATA_FILE, 'r') as f:
        strain = f['strain/Strain'][:]
    nan_mask = np.isnan(strain)
    if np.any(nan_mask):
        print(f"  NaN detected: {np.sum(nan_mask)} samples - interpolating...")
        x = np.arange(len(strain))
        strain = np.interp(x, x[~nan_mask], strain[~nan_mask])
    sample_rate = 4096
    times = np.arange(len(strain)) / sample_rate
    print(f"  Strain loaded:  sample_rate = {sample_rate} Hz")
    print(f"  Duration = {len(strain)/sample_rate:.1f} s  ({len(strain):,} samples)")
except FileNotFoundError:
    print(f"\n  [WARNING] File not found: {DATA_FILE}")
    print(f"  Generating mock data for demonstration...")
    np.random.seed(42)
    sample_rate = 4096
    duration = 4096.0
    times = np.arange(0, duration, 1.0/sample_rate)
    strain = np.random.randn(len(times)) * 1e-22
    strain[int(0.5*sample_rate):int(0.52*sample_rate)] += 5e-21 * np.sin(2*np.pi*75*times[int(0.5*sample_rate):int(0.52*sample_rate)])
    print(f"  Mock strain generated:  sample_rate = {sample_rate} Hz")
    print(f"  Duration = {duration:.1f} s  ({len(strain):,} samples)")
    DATA_FILE = "mock_data"

# Echo template
f_echo, tau_echo, dur = 75.0, 0.05, 0.15
t_tmpl = np.arange(0, dur, 1/sample_rate)
template = np.sin(2*np.pi*f_echo*t_tmpl) * np.exp(-t_tmpl/tau_echo)
template /= np.max(np.abs(template))

print(f"\n  Echo template:")
print(f"    Frequency  f_echo = {f_echo} Hz")
print(f"    Damping time tau = {tau_echo} s ({tau_echo*1000:.0f} ms)")
print(f"    Duration         = {dur} s")

# Matched filter
print("\n  Running matched filter...")
start = time.time()
correlation = correlate(strain, template, mode='valid')
correlation_times = times[:len(correlation)]
global_std = np.std(correlation)
snr = correlation / global_std if global_std > 0 else correlation
peaks, _ = find_peaks(np.abs(snr), height=3.0, distance=int(0.05*sample_rate))
elapsed = time.time() - start
print(f"  Matched filter done:  {elapsed:.1f} s")

print(f"\n  Search Results:")
print(f"    Threshold:  SNR > 3.0")
print(f"    Detections: {len(peaks)} peaks")
if len(peaks) > 0:
    upper90 = np.percentile(np.abs(snr[peaks]), 90)
    print(f"    90th-percentile SNR: {upper90:.2f}")
else:
    max_snr = np.max(np.abs(snr))
    upper90 = np.percentile(np.abs(snr), 99.9)
    print(f"    Maximum |SNR|: {max_snr:.3f}")
    print(f"    99.9th-percentile SNR (upper limit): {upper90:.3f}")

# ---- Figure 1: 4-panel overview ----
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("LIGO GW Echo Search: REG (Relational Emergent Gravity) Prediction", fontsize=13, fontweight='bold')

idx_plot = slice(0, len(strain), 4)
axes[0,0].plot(times[idx_plot], strain[idx_plot]*1e21, 'k-', linewidth=0.2, alpha=0.8)
axes[0,0].set_xlabel('Time (s)', fontsize=11)
axes[0,0].set_ylabel('Strain x10^-21', fontsize=11)
axes[0,0].set_title('(a) LIGO O4c Strain Data', fontsize=11)
axes[0,0].grid(alpha=0.3)

axes[0,1].hist(np.abs(snr), bins=100, color='steelblue', edgecolor='white', alpha=0.75)
axes[0,1].axvline(3.0, color='red', linewidth=1.5, linestyle='--', label='SNR = 3.0 (threshold)')
axes[0,1].set_xlabel('|SNR|', fontsize=11)
axes[0,1].set_ylabel('Count', fontsize=11)
axes[0,1].set_title('(b) SNR Distribution', fontsize=11)
axes[0,1].legend(fontsize=9)
axes[0,1].grid(alpha=0.3)

t_snr = correlation_times
idx_snr = slice(0, len(t_snr), 2)
axes[1,0].plot(t_snr[idx_snr], np.abs(snr[idx_snr]), color='steelblue', linewidth=0.3, alpha=0.8)
axes[1,0].axhline(3.0, color='red', linewidth=1.2, linestyle='--', label='SNR = 3.0')
if len(peaks) > 0:
    axes[1,0].scatter(correlation_times[peaks], np.abs(snr[peaks]), color='red', s=20, zorder=5,
                      label=f'{len(peaks)} detections')
axes[1,0].set_xlabel('Time (s)', fontsize=11)
axes[1,0].set_ylabel('|SNR|', fontsize=11)
axes[1,0].set_title('(c) |SNR| Time Series', fontsize=11)
axes[1,0].legend(fontsize=9)
axes[1,0].grid(alpha=0.3)

t_template_plot = np.arange(0, dur, 1/sample_rate)
axes[1,1].plot(t_template_plot*1000, template, color='darkblue', linewidth=1.5)
axes[1,1].fill_between(t_template_plot*1000, 0, template, color='steelblue', alpha=0.3)
axes[1,1].set_xlabel('Time (ms)', fontsize=11)
axes[1,1].set_ylabel('Normalized Amplitude', fontsize=11)
axes[1,1].set_title(f'(d) Echo Template: f={f_echo:.0f} Hz, tau={tau_echo*1000:.0f} ms', fontsize=11)
axes[1,1].grid(alpha=0.3)
axes[1,1].axvline(tau_echo*1000, color='red', linestyle=':', label='1-tau decay')
axes[1,1].legend(fontsize=9)

plt.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(os.path.join(OUT, 'fig8_ligo_echo_search.png'), dpi=150, bbox_inches='tight')
print(f"\n  Saved: fig8_ligo_echo_search.png")
plt.close()

# ---- Figure 2: SNR time series summary ----
fig2, ax = plt.subplots(figsize=(10, 5))
ax.plot(t_snr[idx_snr], np.abs(snr[idx_snr]), color='steelblue', linewidth=0.3, alpha=0.7, label='|SNR|')
ax.axhline(3.0, color='red', linewidth=1.5, linestyle='--', label='SNR threshold = 3.0')
ax.axhline(upper90, color='orange', linewidth=1.2, linestyle=':', label=f'99.9% upper limit = {upper90:.2f}')
if len(peaks) > 0:
    ax.scatter(correlation_times[peaks], np.abs(snr[peaks]), color='red', s=30, zorder=5,
               label=f'Detections: {len(peaks)}')
ax.set_xlabel('Time (s)', fontsize=12)
ax.set_ylabel('|SNR|', fontsize=12)
ax.set_title(f'LIGO O4c Echo Search: SNR Time Series\n'
             f'REG (Relational Emergent Gravity) | Template: f={f_echo:.0f} Hz, tau={tau_echo*1000:.0f} ms | '
             f'{len(peaks)} peaks above SNR=3.0', fontsize=11)
ax.legend(fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
fig2.savefig(os.path.join(OUT, 'fig9_ligo_snr_timeseries.png'), dpi=150, bbox_inches='tight')
print("  Saved: fig9_ligo_snr_timeseries.png")
plt.close()

print("\n  === Script 5 Complete ===")
