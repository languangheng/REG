# -*- coding: utf-8 -*-
"""Multi-event GW echo search - DEBUGGED"""
import numpy as np, h5py, matplotlib, os, time
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import correlate, find_peaks, butter, filtfilt

DATA_DIR = r"C:\Users\languangheng\Downloads"
EVENTS = {
    "GW150914":  {"gps": 1126259462.423, "mass": 65,  "f_echo": 75},
    "GW151226":  {"gps": 1135136350.647, "mass": 22,  "f_echo": 220},
    "GW170104":  {"gps": 1167559936.605, "mass": 51,  "f_echo": 95},
    "GW170608":  {"gps": 1180922494.490, "mass": 18,  "f_echo": 270},
    "GW170814":  {"gps": 1186741861.670, "mass": 53,  "f_echo": 90},
    "GW190521":  {"gps": 1242442967.406, "mass": 150, "f_echo": 33},
}
EVENT_FILES = {
    "GW150914":  os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1126259447-32.hdf5"),
    "GW151226":  os.path.join(DATA_DIR, "H-H1_LOSC_4_V2-1135136334-32.hdf5"),
    "GW170104":  os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1167559921-32.hdf5"),
    "GW170608":  os.path.join(DATA_DIR, "H-H1_LOSC_CLN_16_V1-1180922478-32.hdf5"),
    "GW170814":  os.path.join(DATA_DIR, "H-H1_LOSC_CLN_16_V1-1186741845-32.hdf5"),
    "GW190521":  os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1242442952-32.hdf5"),
}

def bandpass(data, lo, hi, fs, order=4):
    nyq = 0.5 * fs
    b, a = butter(order, [lo/nyq, hi/nyq], btype='band')
    return filtfilt(b, a, data)

def whiten(data, fs, win_sec=0.05):
    win = int(win_sec * fs)
    out = np.zeros_like(data)
    for i in range(len(data)):
        s, e = max(0, i-win//2), min(len(data), i+win//2)
        std = np.std(data[s:e])
        out[i] = data[i] / std if std > 0 else 0
    return out - np.mean(out)

def process_event(fpath, gps_merger, f_echo, window_sec=2.0):
    """返回：(max_snr_post, peak_times_list, debug_info)"""
    with h5py.File(fpath, 'r') as f:
        strain = f['strain']['Strain'][:]
        gps_start = float(f['strain']['Strain'].attrs.get('Xstart', 0))
        spacing = float(f['strain']['Strain'].attrs.get('Xspacing', 1))
        fs = int(round(1.0 / spacing))
    times_full = gps_start + np.arange(len(strain)) / fs

    # 清理 NaN
    nan_mask = np.isnan(strain)
    if np.any(nan_mask):
        x = np.arange(len(strain))
        strain = np.interp(x, x[~nan_mask], strain[~nan_mask])

    # 并合在文件中的索引
    merger_idx = np.argmin(np.abs(times_full - gps_merger))
    win = int(window_sec * fs)
    s = max(0, merger_idx - win)
    e = min(len(strain), merger_idx + win)
    strain_win = strain[s:e]
    t_win = times_full[s:e]

    # GPS时间：t=0 是文件开头
    # 并合在窗口中的 GPS 时间
    t_merger_gps = gps_merger

    # 滤波 + 白化
    lo, hi = max(20, f_echo-40), min(fs/2-1, f_echo+40)
    try:
        sf = bandpass(strain_win, lo, hi, fs)
    except:
        sf = strain_win
    sw = whiten(sf, fs)

    # 模板
    t_tmpl = np.arange(0, 0.15, 1/fs)
    tmpl = np.sin(2*np.pi*f_echo*t_tmpl) * np.exp(-t_tmpl/0.05)
    tmpl = tmpl / np.max(np.abs(tmpl))

    # 匹配滤波
    corr = correlate(sw, tmpl, mode='valid')
    # corr 的时间：从 sw 的起点 + tmpl 起点（=0）到 sw 终点 - tmpl 终点
    corr_t = t_win[:len(corr)]  # 起始时间与 sw/t_win 相同

    # 噪声估计：只看并合前 0.5s
    merger_in_corr = np.argmin(np.abs(corr_t - t_merger_gps))
    noise_region = corr[max(0, merger_in_corr - int(0.5*fs)):merger_in_corr]
    noise_std = np.std(noise_region) if len(noise_region) > 10 else np.std(corr)
    snr = corr / noise_std if noise_std > 1e-20 else corr
    snr_abs = np.abs(snr)

    # 找峰值（>2.5σ）
    peaks, _ = find_peaks(snr_abs, height=2.5, distance=int(0.03*fs))

    # 转换峰值时间为相对并合时刻
    peak_times = corr_t[peaks] - t_merger_gps  # 相对并合时刻（秒）

    # 并合后窗口搜索（0.02s ~ 1.5s）
    post_mask = (peak_times >= 0.02) & (peak_times <= 1.5)
    post_peaks = peaks[post_mask]
    post_snr_vals = snr_abs[post_peaks]

    max_snr_post = float(np.max(post_snr_vals)) if len(post_snr_vals) > 0 else 0.0
    best_post_time = float(peak_times[post_mask][np.argmax(post_snr_vals)]) if len(post_snr_vals) > 0 else 0.0

    # 全局统计
    max_snr_global = float(np.max(snr_abs))
    max_snr_global_t = float(corr_t[np.argmax(snr_abs)] - t_merger_gps)

    debug = {
        'fs': fs, 'gps_start': gps_start,
        'merger_in_file': times_full[merger_idx],
        't_merger_gps': t_merger_gps,
        'corr_len': len(corr), 'corr_t_start': float(corr_t[0]),
        'corr_t_end': float(corr_t[-1]),
        'merger_in_corr': merger_in_corr,
        'noise_std': float(noise_std),
        'n_peaks_total': len(peaks),
    }

    return {
        'event': '',
        'f_echo': f_echo,
        'max_snr_post': max_snr_post,
        'max_t_post': best_post_time,
        'n_peaks_post': len(post_peaks),
        'max_snr_global': max_snr_global,
        'max_t_global': max_snr_global_t,
        'snr_abs': snr_abs,
        'corr_t': corr_t,
        'peaks': peaks,
        'peak_times': peak_times,
        't_merger_gps': t_merger_gps,
        'fs': fs,
        'debug': debug,
    }

# ---- 运行 ----
print("=" * 70)
print("Multi-Event GW Echo Joint Search v2")
print("=" * 70)

results = []
for evt, fpath in EVENT_FILES.items():
    if not os.path.exists(fpath):
        print(f"\n  [{evt}] FILE NOT FOUND")
        continue
    info = EVENTS[evt]
    gps_merger = info['gps']
    f_echo = info['f_echo']

    print(f"\n  [{evt}] f_echo={f_echo}Hz, GPS={gps_merger:.3f}...", end="", flush=True)
    t0 = time.time()
    try:
        r = process_event(fpath, gps_merger, f_echo)
        r['event'] = evt
        results.append(r)
        dbg = r['debug']
        print(f" done ({time.time()-t0:.1f}s) | "
              f"FS={dbg['fs']}Hz | "
              f"corr=[{dbg['corr_t_start']:.1f},{dbg['corr_t_end']:.1f}]s | "
              f"noise_std={dbg['noise_std']:.4f} | "
              f"global max|SNR|={r['max_snr_global']:.3f} at t={r['max_t_global']:+.3f}s | "
              f"post-merger max|SNR|={r['max_snr_post']:.3f} at t={r['max_t_post']:+.3f}s | "
              f"peaks_post={r['n_peaks_post']}")
    except Exception as e:
        print(f" ERROR: {e}")
        import traceback; traceback.print_exc()

# ---- 联合分析 ----
print("\n" + "=" * 70)
print("Joint Multi-Event Analysis")
print("=" * 70)

n = len(results)
snr_vals = [r['max_snr_post'] for r in results]
joint_snr = np.sqrt(np.sum(np.array(snr_vals)**2))
joint_snr_norm = joint_snr / np.sqrt(n)
alpha_joint = joint_snr_norm / 24.0
expected_noise_max = np.sqrt(2 * np.log(n))

print(f"\n  Events analyzed: {n}")
print(f"\n  {'Event':<12} | {'f_echo':>8} | {'FS(Hz)':>7} | "
      f"{'GlobalMaxSNR':>13} | {'PostMaxSNR':>11} | {'PostT(s)':>8} | {'Npost':>5}")
print(f"  {'-'*12} | {'-'*8} | {'-'*7} | {'-'*13} | {'-'*11} | {'-'*8} | {'-'*5}")
for r in results:
    dbg = r['debug']
    flag = " ***" if r['max_snr_post'] > 4.0 else (" **" if r['max_snr_post'] > 3.0 else (" *" if r['max_snr_post'] > 2.5 else ""))
    print(f"  {r['event']:<12} | {r['f_echo']:>8} | {dbg['fs']:>7} | "
          f"{r['max_snr_global']:>13.3f} | "
          f"{r['max_snr_post']:>11.3f}{flag} | "
          f"{r['max_t_post']:>8.3f} | {r['n_peaks_post']:>5}")

print(f"\n  Joint SNR (sqrt of sum SNR^2) = {joint_snr:.4f}")
print(f"  Normalized joint SNR = {joint_snr_norm:.4f}")
print(f"  Alpha joint upper limit = {alpha_joint:.4f}")
print(f"  Expected max SNR in pure noise (n={n}): ~{expected_noise_max:.2f}")
print(f"\n  Theory prediction: alpha ~ 0.1")
if alpha_joint > 0.1:
    print(f"  [OK] alpha={alpha_joint:.4f} > 0.1: NOT RULED OUT")
elif alpha_joint > 0:
    print(f"  [!!] alpha={alpha_joint:.4f} < 0.1: THEORY CHALLENGED")
else:
    print(f"  [??] alpha={alpha_joint:.4f} (no signal detected)")

sig_events = [r for r in results if r['max_snr_post'] > 3.0]
print(f"\n  Events with post-merger SNR > 3sigma: {len(sig_events)}")
for r in sig_events:
    print(f"    {r['event']}: SNR={r['max_snr_post']:.3f} at t={r['max_t_post']:+.3f}s after merger")

# ---- 可视化 ----
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
axes = axes.flatten()
colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b']

for i, r in enumerate(results[:6]):
    ax = axes[i]
    corr_t = r['corr_t']
    snr_abs = r['snr_abs']
    t_merger_gps = r['t_merger_gps']
    ts = corr_t - t_merger_gps  # 相对并合时刻

    # 画 SNR（只画有意义范围）
    mask = (ts >= -1.0) & (ts <= 2.0)
    ax.plot(ts[mask], snr_abs[mask], color=colors[i%len(colors)], linewidth=0.5, alpha=0.9)
    ax.axvline(0, color='red', linestyle='--', lw=1.5, alpha=0.7, label='Merger')
    ax.axvspan(0.02, 1.5, alpha=0.12, color='yellow', label='Echo window(0.02-1.5s)')
    ax.axhline(2.5, color='orange', linestyle=':', lw=1, label='2.5sig')
    ax.axhline(3.0, color='red', linestyle=':', lw=1, label='3sig')

    # 标记峰值
    peaks = r['peaks']
    peak_times = r['peak_times']
    post_mask = (peak_times >= 0.02) & (peak_times <= 1.5)
    post_peaks = peaks[post_mask]
    if len(post_peaks) > 0:
        ax.scatter(peak_times[post_mask], snr_abs[post_peaks],
                   color='red', s=30, zorder=5, marker='v',
                   label=f'{len(post_peaks)} peaks')

    max_s = r['max_snr_post']
    marker = " ***" if max_s > 4.0 else (" **" if max_s > 3.0 else (" *" if max_s > 2.5 else ""))
    ax.set_xlabel('Time since merger (s)', fontsize=9)
    ax.set_ylabel('|SNR|', fontsize=9)
    ax.set_title(f"{r['event']} (f={r['f_echo']}Hz, FS={r['fs']}Hz)\n"
                 f"max|SNR|_post={max_s:.3f}{marker} at t={r['max_t_post']:+.3f}s",
                 fontsize=10, fontweight='bold' if max_s > 3.0 else 'normal')
    ax.legend(fontsize=7, loc='upper right')
    ax.set_xlim(-1.0, 2.0)
    ymax = min(10, max(snr_abs) * 1.2 if max(snr_abs) > 0 else 5)
    ax.set_ylim(0, ymax)
    ax.grid(alpha=0.25)

for i in range(len(results), 6):
    axes[i].axis('off')

fig.suptitle(
    f"Multi-Event GW Echo Joint Search\n"
    f"n={n} events | Joint normalized SNR={joint_snr_norm:.3f} | "
    f"Alpha_joint<={alpha_joint:.4f}",
    fontsize=13, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.94])
out_png = os.path.join(os.path.dirname(__file__), 'multi_event_echo_search_v2.png')
plt.savefig(out_png, dpi=150, bbox_inches='tight')
print(f"\nFigure saved: {out_png}")
