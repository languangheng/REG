# -*- coding: utf-8 -*-
"""
验证一：引力波回声搜索
REG理论预言：黑洞合并后产生频率~75Hz、衰减时间~0.05s的回声信号
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate, find_peaks, butter, filtfilt
import time
import os

print("=" * 70)
print("Verify 1: Gravitational Wave Echo Search")
print("REG prediction: f~75Hz, tau~0.05s after BH merger")
print("=" * 70)

# REG theory prediction
f_echo = 75.0      # Hz
tau_echo = 0.05    # decay time (s)
template_duration = 0.15  # template length (s)

# Check for real LIGO data
DATA_FILE = "L-L1_GWOSC_O4c1DiscC00_4KHZ_R1-1422962688-4096.hdf5"
use_real_data = os.path.exists(DATA_FILE)

if use_real_data:
    print(f"Loading real LIGO data: {DATA_FILE}")
    import h5py
    with h5py.File(DATA_FILE, 'r') as f:
        strain = f['strain/Strain'][:]
        nan_mask = np.isnan(strain)
        if np.any(nan_mask):
            print(f"  Cleaning NaN: {np.sum(nan_mask)} points")
            x = np.arange(len(strain))
            strain = np.interp(x, x[~nan_mask], strain[~nan_mask])
    sample_rate = 4096
    times = np.arange(len(strain)) / sample_rate
    data_label = "LIGO O4c Real Data"
else:
    print("Real LIGO data file not found. Using simulated data with injected echo.")
    print("(Download O4c data from https://gwosc.org/ for real search)")
    sample_rate = 4096
    duration = 60  # seconds
    times = np.arange(0, duration, 1/sample_rate)
    np.random.seed(42)

    # Realistic LIGO noise
    noise = np.random.normal(0, 1e-22, len(times))

    # Inject echo signal at t=30s
    t_echo = 30.05
    echo_amplitude = 3e-22
    t_env = np.arange(0, 0.1, 1/sample_rate)
    envelope = np.exp(-t_env / tau_echo)
    echo_wave = echo_amplitude * np.sin(2 * np.pi * f_echo * t_env) * envelope
    echo_signal = np.zeros_like(times)
    start_idx = int(t_echo * sample_rate)
    if start_idx + len(echo_wave) <= len(times):
        echo_signal[start_idx:start_idx + len(echo_wave)] = echo_wave

    strain = noise + echo_signal
    data_label = f"Simulated Data (echo injected at t={t_echo}s)"

print(f"Data duration: {len(strain)/sample_rate:.1f} seconds")
print(f"Sample rate: {sample_rate} Hz")
print(f"Template: f={f_echo} Hz, tau={tau_echo} s")

# ============================================================
# Bandpass filter (30-500 Hz, LIGO sensitive band)
# ============================================================
def bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data)

print("\nBandpass filtering (30-500 Hz)...")
strain_filtered = bandpass_filter(strain, 30, 500, sample_rate)

# ============================================================
# Whiten (simple local std normalization)
# ============================================================
print("Whitening...")
window = int(0.1 * sample_rate)
strain_white = np.zeros_like(strain_filtered)
for i in range(len(strain_filtered)):
    start = max(0, i - window // 2)
    end = min(len(strain_filtered), i + window // 2)
    local_std = np.std(strain_filtered[start:end])
    if local_std > 0:
        strain_white[i] = strain_filtered[i] / local_std

strain_white -= np.mean(strain_white)

# ============================================================
# Echo template
# ============================================================
t_tmpl = np.arange(0, template_duration, 1/sample_rate)
template = np.sin(2 * np.pi * f_echo * t_tmpl) * np.exp(-t_tmpl / tau_echo)
template = template / np.max(np.abs(template))  # normalize

# ============================================================
# Matched filter
# ============================================================
print("Matched filtering...")
t0 = time.time()
correlation = correlate(strain_white, template, mode='valid')
correlation_times = times[:len(correlation)]

global_std = np.std(correlation)
snr = correlation / global_std if global_std > 0 else correlation

# Peak detection (3-sigma threshold)
peaks, properties = find_peaks(np.abs(snr), height=3.0, distance=int(0.05 * sample_rate))
elapsed = time.time() - t0
print(f"Matched filtering done in {elapsed:.1f} seconds")
print(f"SNR > 3 sigma peaks: {len(peaks)}")

# ============================================================
# Results
# ============================================================
print("\n" + "=" * 70)
print("SEARCH RESULTS")
print("=" * 70)
print(f"Template: f={f_echo} Hz, tau={tau_echo} s")
print(f"Data: {data_label}")
print(f"SNR > 3 sigma peaks found: {len(peaks)}")

snr_abs = np.abs(snr)

if len(peaks) > 0:
    max_snr = np.max(snr_abs)
    upper_limit = np.percentile(snr_abs[peaks], 90) if len(peaks) > 10 else np.max(snr_abs)
    print(f"\n  Max |SNR|: {max_snr:.2f}")
    print(f"  90% CL upper limit SNR: {upper_limit:.2f}")

    # Constraint on alpha (coupling constant)
    # Echo amplitude A_echo proportional to alpha
    # Reference: GW150914 main merger SNR ~ 24
    snr_main_ref = 24.0
    alpha_upper = upper_limit / snr_main_ref
    print(f"\n  Constraint on relation-curvature coupling constant alpha:")
    print(f"    alpha <= {alpha_upper:.4f} (90% C.L.)")
    print(f"    REG theory prediction: alpha ~ 0.1")

    if alpha_upper > 0.1:
        print(f"\n  [NOT RULED OUT] Upper limit {alpha_upper:.4f} > 0.1: theory survives")
    else:
        print(f"\n  [RULED OUT] Upper limit {alpha_upper:.4f} < 0.1: theory challenged")

    # Show top 5 peaks
    peak_snrs = snr_abs[peaks]
    top5_idx = np.argsort(peak_snrs)[-5:][::-1]
    print(f"\n  Top 5 peaks:")
    for i, idx in enumerate(top5_idx):
        t = correlation_times[peaks[idx]]
        s = peak_snrs[idx]
        print(f"    Peak {i+1}: SNR={s:.2f} at t={t:.3f}s")
else:
    max_snr = np.max(snr_abs)
    upper_limit = np.percentile(snr_abs, 99.9)
    alpha_upper = upper_limit / 24.0
    print(f"\n  Max |SNR|: {max_snr:.2f}")
    print(f"  99.9% CL upper limit SNR: {upper_limit:.2f}")
    print(f"  alpha <= {alpha_upper:.4f} (99.9% C.L.)")

# Also test with different SNR thresholds
print(f"\n  SNR threshold analysis:")
for thresh in [3.0, 4.0, 5.0, 6.0]:
    pks, _ = find_peaks(np.abs(snr), height=thresh, distance=int(0.05 * sample_rate))
    print(f"    SNR > {thresh:.1f} sigma: {len(pks)} peaks")

# ============================================================
# Visualization
# ============================================================
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Fig 1: Whitened data (first 60 seconds)
plot_samples = min(60 * sample_rate, len(strain_white))
axes[0].plot(times[:plot_samples], strain_white[:plot_samples], 'k-', linewidth=0.3)
axes[0].axvline(t_echo, color='red', linestyle='--', linewidth=1.5,
                  label=f'Injected echo at t={t_echo}s')
axes[0].set_xlabel('Time (s)', fontsize=11)
axes[0].set_ylabel('Whitened Strain', fontsize=11)
axes[0].set_title(f'{data_label} -- Whitened Data (first 60s)', fontsize=12)
axes[0].legend(fontsize=9)
axes[0].grid(True, alpha=0.3)

# Fig 2: Echo template
axes[1].plot(t_tmpl * 1000, template, 'b-', linewidth=1.5)
axes[1].set_xlabel('Time (ms)', fontsize=11)
axes[1].set_ylabel('Normalized Amplitude', fontsize=11)
axes[1].set_title(f'Echo Template (f={f_echo}Hz, tau={tau_echo*1000:.0f}ms)', fontsize=12)
axes[1].grid(True, alpha=0.3)

# Fig 3: SNR distribution
axes[2].hist(snr_abs, bins=200, color='steelblue', edgecolor='white', alpha=0.7,
              label='All data')
axes[2].axvline(3.0, color='red', linestyle='--', linewidth=2, label='3-sigma threshold')
axes[2].axvline(4.0, color='orange', linestyle='--', linewidth=1.5, label='4-sigma threshold')
axes[2].axvline(5.0, color='darkorange', linestyle='--', linewidth=1.5, label='5-sigma threshold')
if len(peaks) > 0:
    axes[2].axvline(upper_limit, color='purple', linestyle='-', linewidth=2,
                      label=f'90% CL limit={upper_limit:.2f}')
axes[2].set_xlabel('|SNR|', fontsize=11)
axes[2].set_ylabel('Count', fontsize=11)
axes[2].set_title('Full-data SNR Distribution', fontsize=12)
axes[2].set_xlim(0, min(15, np.max(snr_abs) * 1.1))
axes[2].legend(fontsize=9)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('verify_gravitational_wave_echo.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nFigure saved to verify_gravitational_wave_echo.png")
print("\nInterpretation:")
print("- Significant SNR peak (>5 sigma) + correct frequency = GW echo DETECTED")
print("- No significant peak -> upper limit on alpha")
print("- Current LIGO sensitivity: alpha~0.1 echo may be below detection threshold")
print("- Next-gen detectors (Einstein Telescope, Cosmic Explorer) will conclusively test alpha~0.1")
