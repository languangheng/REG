# -*- coding: utf-8 -*-
"""
验证一（真实数据版）：引力波回声搜索
使用 LIGO 真实数据 (GW150914, 16kHz, 32秒)
REG 理论预言：f ~ 75 Hz, tau ~ 0.05 s
"""
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import correlate, find_peaks, butter, filtfilt
import time, os

DATA_FILE = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit\L-L1_GWOSC_16KHZ_R1-1126259447-32.hdf5"
OUT_DIR = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit"
MERGER_GPS = 1126259462.423

print("=" * 70)
print("Verify 1: GW Echo Search with REAL LIGO Data")
print("=" * 70)

# ---- Load data ----
print(f"\nLoading: {os.path.basename(DATA_FILE)}")
with h5py.File(DATA_FILE, 'r') as f:
    strain_raw = f['strain/Strain'][:]
    meta = dict(f['meta'].attrs)
    print(f"  GPS start: {meta.get('GPSstart', '?')}")
    print(f"  UTC start:  {meta.get('UTCstart', '?')}")
    print(f"  Detector:  {meta.get('Detector', '?')}")

sample_rate = 16384
duration = len(strain_raw) / sample_rate
times = np.arange(len(strain_raw)) / sample_rate
times_abs = times + meta.get('GPSstart', 1126259447)

print(f"  Duration:  {duration:.1f} s ({len(strain_raw):,} samples)")
print(f"  Merger at: {MERGER_GPS} GPS")
merger_in_file = MERGER_GPS - meta.get('GPSstart', 1126259447)
print(f"  Merger in file: t = {merger_in_file:.3f} s ({merger_in_file/duration*100:.1f}% position)")

# ---- Clean NaN ----
nan_count = np.sum(np.isnan(strain_raw))
if nan_count > 0:
    x = np.arange(len(strain_raw))
    strain_raw = np.interp(x, x[~np.isnan(strain_raw)], strain_raw[~np.isnan(strain_raw)])
    print(f"  Interpolated {nan_count} NaN values")

# ---- Bandpass filter (30-500 Hz) ----
def bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut/nyq, highcut/nyq], btype='band')
    return filtfilt(b, a, data)

print("\nBandpass filtering (30-500 Hz, 4th-order Butterworth)...")
strain_filtered = bandpass_filter(strain_raw, 30, 500, sample_rate)

# ---- Whiten (1-second sliding window RMS) ----
print("Whitening (1-second sliding window)...")
window_samples = sample_rate
strain_white = np.zeros_like(strain_filtered)
for i in range(len(strain_filtered)):
    start = max(0, i - window_samples // 2)
    end = min(len(strain_filtered), i + window_samples // 2)
    local_std = np.std(strain_filtered[start:end])
    strain_white[i] = strain_filtered[i] / local_std if local_std > 0 else 0
strain_white -= np.mean(strain_white)
print(f"  Whitened data: mean={np.mean(strain_white):.4f}, std={np.std(strain_white):.4f}")

# ---- Echo template (REG prediction: f=75Hz, tau=0.05s) ----
f_echo = 75.0
tau_echo = 0.05
template_dur = 0.15
t_tmpl = np.arange(0, template_dur, 1/sample_rate)
template = np.sin(2*np.pi*f_echo*t_tmpl) * np.exp(-t_tmpl/tau_echo)
template = template / np.max(np.abs(template))
print(f"\nEcho template: f={f_echo} Hz, tau={tau_echo*1000:.0f} ms, dur={template_dur}s")

# ---- Matched filter ----
print("Matched filtering...")
t0 = time.time()
correlation = correlate(strain_white, template, mode='valid')
corr_times = times[:len(correlation)]
elapsed = time.time() - t0
print(f"  Done in {elapsed:.1f} s")

# SNR
global_std = np.std(correlation)
snr = correlation / global_std
snr_abs = np.abs(snr)

# ---- Peak detection at multiple thresholds ----
print(f"\n{'='*70}")
print("SEARCH RESULTS (REAL LIGO DATA: GW150914)")
print("="*70)

for thresh in [3.0, 4.0, 5.0, 6.0]:
    peaks, props = find_peaks(snr_abs, height=thresh,
                               distance=int(0.05*sample_rate))
    print(f"  SNR > {thresh:.1f} sigma: {len(peaks)} peak(s)")

# Primary detection at 3-sigma
peaks, _ = find_peaks(snr_abs, height=3.0, distance=int(0.05*sample_rate))

if len(peaks) > 0:
    upper90 = np.percentile(snr_abs[peaks], 90) if len(peaks) > 10 else np.max(snr_abs)
    max_snr = np.max(snr_abs)
    max_idx = np.argmax(snr_abs)
    max_t = corr_times[max_idx]

    print(f"\n  Max |SNR|: {max_snr:.2f} at t={max_t:.3f}s (GPS {times_abs[max_idx]:.1f})")
    print(f"  90% CL upper limit (peak population): {upper90:.2f}")

    # Constraint on alpha
    snr_main_ref = 24.0  # GW150914 main merger SNR ~ 24
    alpha_upper = upper90 / snr_main_ref
    print(f"\n  Alpha constraint (90% CL): alpha <= {alpha_upper:.4f}")
    print(f"  REG theory prediction: alpha ~ 0.1")
    if alpha_upper > 0.1:
        print(f"  [OK] {alpha_upper:.4f} > 0.1: theory NOT ruled out")
    else:
        print(f"  [!!] {alpha_upper:.4f} < 0.1: theory is CHALLENGED")

    # Top peaks near merger
    print(f"\n  Top peaks (near merger at t={merger_in_file:.1f}s):")
    sorted_peaks = peaks[np.argsort(snr_abs[peaks])[::-1]]
    for i, pk in enumerate(sorted_peaks[:8]):
        t_pk = corr_times[pk]
        t_rel = t_pk - merger_in_file
        s = snr_abs[pk]
        flag = " <<< MERGER REGION" if abs(t_rel) < 0.5 else ""
        flag += " <<< INJECTED ECHO WINDOW" if 0 < t_rel < 0.3 else ""
        print(f"    Peak {i+1}: SNR={s:.2f} at t={t_pk:.3f}s "
              f"(GPS {times_abs[pk]:.1f}), Δt={t_rel:+.3f}s from merger{flag}")
else:
    max_snr = np.max(snr_abs)
    upper99 = np.percentile(snr_abs, 99.9)
    alpha_upper = upper99 / 24.0
    print(f"\n  Max |SNR|: {max_snr:.3f}")
    print(f"  99.9% CL upper limit: {upper99:.3f}")
    print(f"  Alpha <= {alpha_upper:.4f} (99.9% CL)")

# ---- Also test nearby frequency templates ----
print(f"\n{'='*70}")
print("Frequency Scan: Testing f=50-150 Hz (template matched filter)")
print("="*70)
print(f"{'Freq (Hz)':>10} | {'Max SNR':>10} | {'N peaks':>8} | {'Alpha_ul':>10}")
print("-" * 50)
freqs_to_test = [50, 60, 70, 75, 80, 90, 100, 110, 120, 130, 140, 150]
for freq in freqs_to_test:
    tmpl = np.sin(2*np.pi*freq*t_tmpl) * np.exp(-t_tmpl/tau_echo)
    tmpl = tmpl / np.max(np.abs(tmpl))
    corr = correlate(strain_white, tmpl, mode='valid')
    s_abs = np.abs(corr) / np.std(corr)
    pks, _ = find_peaks(s_abs, height=3.0, distance=int(0.05*sample_rate))
    max_s = np.max(s_abs)
    alp = np.percentile(s_abs, 90) / snr_main_ref if len(pks) > 10 else max_s / snr_main_ref
    marker = " <-- 75 Hz REG" if freq == 75 else ""
    print(f"{freq:>10.0f} | {max_s:>10.2f} | {len(pks):>8} | {alp:>10.4f}{marker}")

# ---- Visualization ----
fig, axes = plt.subplots(3, 1, figsize=(14, 11))
fig.suptitle(
    f"REG GW Echo Search: Real LIGO Data (GW150914, L1, 16kHz)\n"
    f"Template: f={f_echo} Hz, tau={tau_echo*1000:.0f} ms | "
    f"Max |SNR|={max_snr:.2f}",
    fontsize=13, fontweight='bold')

# Panel 1: Raw strain around merger
idx0 = max(0, int((merger_in_file - 2) * sample_rate))
idx1 = min(len(strain_raw), int((merger_in_file + 2) * sample_rate))
t_plot = times[idx0:idx1] - merger_in_file
s_plot = strain_raw[idx0:idx1] * 1e21
axes[0].plot(t_plot, s_plot, 'k-', linewidth=0.5)
axes[0].axvline(0, color='red', linestyle='--', linewidth=1.5, label='GW150914 merger')
axes[0].set_xlabel('Time relative to merger (s)', fontsize=11)
axes[0].set_ylabel('Strain x10^-21', fontsize=11)
axes[0].set_title('(a) Raw Strain: GW150914 Merger Region (±2s)', fontsize=11)
axes[0].legend(fontsize=9)
axes[0].grid(alpha=0.3)

# Panel 2: SNR time series
axes[1].plot(corr_times, snr_abs, color='steelblue', linewidth=0.3, alpha=0.8)
axes[1].axhline(3.0, color='red', linestyle='--', linewidth=1.5, label='SNR=3 (threshold)')
axes[1].axhline(4.0, color='orange', linestyle=':', linewidth=1, label='SNR=4')
axes[1].axhline(5.0, color='darkorange', linestyle=':', linewidth=1, label='SNR=5')
axes[1].axvline(merger_in_file, color='red', linestyle='--', linewidth=1, alpha=0.5)
if len(peaks) > 0:
    axes[1].scatter(corr_times[peaks], snr_abs[peaks], color='red', s=15, zorder=5,
                       label=f'{len(peaks)} peaks > 3σ')
axes[1].set_xlabel('Time in file (s)', fontsize=11)
axes[1].set_ylabel('|SNR|', fontsize=11)
axes[1].set_title('(b) Matched Filter SNR Time Series (75 Hz template)', fontsize=11)
axes[1].legend(fontsize=9)
axes[1].grid(alpha=0.3)
axes[1].set_ylim(0, min(15, max_snr * 1.1))

# Panel 3: SNR histogram + frequency scan
ax3_twin = axes[2].twinx()
axes[2].hist(snr_abs, bins=200, color='steelblue', edgecolor='white', alpha=0.6, label='SNR distribution')
axes[2].axvline(3.0, color='red', linestyle='--', linewidth=1.5, label='SNR=3 threshold')
axes[2].set_xlabel('|SNR|', fontsize=11)
axes[2].set_ylabel('Count', fontsize=11, color='steelblue')
axes[2].tick_params(axis='y', labelcolor='steelblue')
axes[2].set_xlim(0, min(15, max_snr * 1.1))
axes[2].set_title('(c) SNR Distribution + Frequency Scan', fontsize=11)

# Frequency scan overlay
max_snrs = []
for freq in freqs_to_test:
    tmpl = np.sin(2*np.pi*freq*t_tmpl) * np.exp(-t_tmpl/tau_echo)
    tmpl = tmpl / np.max(np.abs(tmpl))
    corr = correlate(strain_white, tmpl, mode='valid')
    s = np.abs(corr) / np.std(corr)
    max_snrs.append(np.max(s))
ax3_twin.plot(freqs_to_test, max_snrs, 'o-', color='coral', linewidth=2,
              markersize=5, label='Max SNR vs freq')
ax3_twin.set_ylabel('Max |SNR| (frequency scan)', fontsize=11, color='coral')
ax3_twin.tick_params(axis='y', labelcolor='coral')
ax3_twin.axvline(75, color='coral', linestyle=':', alpha=0.5)
ax3_twin.set_xlabel('Template Frequency (Hz)', fontsize=11)

# Combined legend
lines1, labels1 = axes[2].get_legend_handles_labels()
lines2, labels2 = ax3_twin.get_legend_handles_labels()
axes[2].legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc='upper right')
axes[2].grid(alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out_png = os.path.join(OUT_DIR, 'verify1_real_ligo_gw150914.png')
plt.savefig(out_png, dpi=150, bbox_inches='tight')
print(f"\nFigure saved: {out_png}")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("- GW150914 merger is at t=15.4s in this file (15.4/32 = 48.2% position)")
print("- Echoes expected: t = merger + 0.01 to 0.5 seconds (REG prediction)")
print("- SNR > 5sigma near merger region = potential discovery")
print("- Max |SNR| = {:.2f} at 75 Hz template".format(max_snr))
if max_snr >= 5.0:
    print("** STRONG CANDIDATE: SNR {:.1f}sigma exceeds 5-sigma threshold!".format(max_snr))
elif max_snr >= 3.0:
    print("** MARGINAL: SNR {:.1f}sigma exceeds 3-sigma but below 5-sigma".format(max_snr))
else:
    print("** UPPER LIMIT: no significant detection, alpha <= {:.4f}".format(
        np.percentile(snr_abs, 99.9) / 24.0))
