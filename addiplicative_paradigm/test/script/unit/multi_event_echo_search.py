# -*- coding: utf-8 -*-
"""
验证一（升级版）：多事件引力波回声联合搜索
"""
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import correlate, find_peaks, butter, filtfilt
import os, time

DATA_DIR = r"C:\Users\languangheng\Downloads"

# 已知引力波事件（GPS 并合时刻）
EVENTS = {
    "GW150914":  {"gps": 1126259462.423, "mass": 65,  "f_echo": 75},
    "GW151226":  {"gps": 1135136350.647, "mass": 22,  "f_echo": 220},
    "GW170104":  {"gps": 1167559936.605, "mass": 51,  "f_echo": 95},
    "GW170608":  {"gps": 1180922494.490, "mass": 18,  "f_echo": 270},
    "GW170814":  {"gps": 1186741861.670, "mass": 53,  "f_echo": 90},
    "GW190521":  {"gps": 1242442967.406, "mass": 150, "f_echo": 33},
}

# 事件 → 文件路径（优先用 H1 数据）
EVENT_FILES = {
    "GW150914": os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1126259447-32.hdf5"),
    "GW151226": os.path.join(DATA_DIR, "H-H1_LOSC_4_V2-1135136334-32.hdf5"),
    "GW170104": os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1167559921-32.hdf5"),
    "GW170608": os.path.join(DATA_DIR, "H-H1_LOSC_CLN_16_V1-1180922478-32.hdf5"),
    "GW170814": os.path.join(DATA_DIR, "H-H1_LOSC_CLN_16_V1-1186741845-32.hdf5"),
    "GW190521": os.path.join(DATA_DIR, "H-H1_GWOSC_16KHZ_R1-1242442952-32.hdf5"),
}

# ---- 读取文件元数据 ----
print("=" * 70)
print("Multi-Event GW Echo Joint Search")
print("=" * 70)
print("\nFile metadata:")
for evt, fpath in EVENT_FILES.items():
    if os.path.exists(fpath):
        with h5py.File(fpath, 'r') as f:
            gps_start = float(f['strain']['Strain'].attrs.get('Xstart', 0))
            spacing = float(f['strain']['Strain'].attrs.get('Xspacing', 0))
            sr = int(1.0 / spacing) if spacing > 0 else 0
            n = len(f['strain']['Strain'][:])
            dur = n / sr if sr else 0
            gps_end = gps_start + dur
        gps_evt = EVENTS[evt]['gps']
        in_file = "YES" if gps_start <= gps_evt <= gps_end else "NO"
        print(f"  {evt}: GPS {gps_start:.0f}-{gps_end:.0f} ({dur:.0f}s @ {sr}Hz)  "
              f"event={'IN FILE' if in_file=='YES' else 'OUT OF FILE'}  "
              f"f_echo={EVENTS[evt]['f_echo']}Hz")
    else:
        print(f"  {evt}: FILE NOT FOUND - {os.path.basename(fpath)}")


# ---- 带通滤波 + 白化 ----
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

def load_and_prep(fpath, gps_merger, window_sec=2.0):
    """加载数据，提取并合前后 window_sec 秒，滤波+白化"""
    with h5py.File(fpath, 'r') as f:
        strain = f['strain']['Strain'][:]
        gps_start = float(f['strain']['Strain'].attrs.get('Xstart', 0))
        spacing = float(f['strain']['Strain'].attrs.get('Xspacing', 1))
        fs = int(round(1.0 / spacing))
    times = gps_start + np.arange(len(strain)) / fs

    # 清理 NaN
    nan_mask = np.isnan(strain)
    if np.any(nan_mask):
        x = np.arange(len(strain))
        strain = np.interp(x, x[~nan_mask], strain[~nan_mask])

    # 并合时刻在文件中的索引
    merger_idx = np.argmin(np.abs(times - gps_merger))
    win = int(window_sec * fs)
    s = max(0, merger_idx - win)
    e = min(len(strain), merger_idx + win)
    strain_win = strain[s:e]
    t_win = times[s:e]
    merger_rel = gps_merger - t_win[0]

    return strain_win, t_win, merger_rel, fs

def search_echo(strain_win, t_win, merger_rel, fs, f_echo, tau=0.05):
    """对一个事件做回声匹配滤波搜索"""
    # 带通（回声频率 ±40Hz，留宽一些避免信号损失）
    lo, hi = max(20, f_echo-40), min(fs/2-1, f_echo+40)
    try:
        sf = bandpass(strain_win, lo, hi, fs)
    except:
        sf = strain_win
    sw = whiten(sf, fs)

    # 模板
    t_tmpl = np.arange(0, 0.15, 1/fs)
    tmpl = np.sin(2*np.pi*f_echo*t_tmpl) * np.exp(-t_tmpl/tau)
    tmpl = tmpl / np.max(np.abs(tmpl))

    # 匹配滤波
    corr = correlate(sw, tmpl, mode='valid')
    corr_t = t_win[:len(corr)]
    noise_std = np.std(corr[:int(0.5*fs)])
    snr = corr / noise_std if noise_std > 0 else corr
    snr_abs = np.abs(snr)

    # 并合后搜索窗口（0.02s ~ 1.5s）
    t_search = corr_t - merger_rel  # 相对并合时刻
    post_mask = (t_search >= 0.02) & (t_search <= 1.5)
    post_snr = snr_abs[post_mask]
    post_t = corr_t[post_mask]

    max_snr_post = np.max(post_snr) if len(post_snr) > 0 else 0
    max_idx_post = np.argmax(post_snr) if len(post_snr) > 0 else -1
    max_t_post = post_t[max_idx_post] if max_idx_post >= 0 else 0

    # 全局峰值
    peaks_all, _ = find_peaks(snr_abs, height=2.5, distance=int(0.03*fs))
    peaks_post = [p for p in peaks_all if 0.02 <= t_search[p] <= 1.5]

    return {
        'snr': snr,
        'snr_abs': snr_abs,
        'corr_t': corr_t,
        't_search': t_search,
        'merger_rel': merger_rel,
        'max_snr_post': max_snr_post,
        'max_t_post': max_t_post,
        'n_peaks_post': len(peaks_post),
        'f_echo': f_echo,
    }

# ---- 逐事件搜索 ----
print("\n" + "=" * 70)
print("Per-Event Echo Search")
print("=" * 70)

results = []
for evt, fpath in EVENT_FILES.items():
    if not os.path.exists(fpath):
        print(f"\n  {evt}: FILE NOT FOUND, skipping")
        continue
    info = EVENTS[evt]
    gps_merger = info['gps']
    f_echo = info['f_echo']

    print(f"\n  [{evt}] f_echo={f_echo}Hz, GPS={gps_merger:.3f}")
    t0 = time.time()

    try:
        strain_win, t_win, merger_rel, fs = load_and_prep(fpath, gps_merger, window_sec=2.0)
        r = search_echo(strain_win, t_win, merger_rel, fs, f_echo)
        r['event'] = evt
        r['fs'] = fs
        results.append(r)

        print(f"    FS={fs}Hz, merger_rel={merger_rel:.3f}s in window")
        print(f"    Post-merger max|SNR|={r['max_snr_post']:.3f} at t={r['max_t_post']:.3f}s")
        print(f"    Post-merger peaks(>2.5sig)={r['n_peaks_post']}")
        print(f"    Time: {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

# ---- 联合分析 ----
print("\n" + "=" * 70)
print("Joint Multi-Event Analysis")
print("=" * 70)

if len(results) < 2:
    print("Not enough events with data. Abort joint analysis.")
else:
    snr_vals = [r['max_snr_post'] for r in results]
    n = len(snr_vals)
    joint_snr = np.sqrt(np.sum(np.array(snr_vals)**2))
    joint_snr_norm = joint_snr / np.sqrt(n)
    alpha_joint = joint_snr_norm / 24.0

    print(f"\n  Events analyzed: {n}")
    print(f"\n  {'Event':<12} | {'f_echo(Hz)':<10} | {'Max SNR post-merger':<18} | {'Alpha_ul':<10}")
    print(f"  {'-'*12} | {'-'*10} | {'-'*18} | {'-'*10}")
    for r in results:
        alpha = r['max_snr_post'] / 24.0
        sig = "***" if r['max_snr_post'] > 4.0 else ("**" if r['max_snr_post'] > 3.0 else ("*" if r['max_snr_post'] > 2.5 else ""))
        print(f"  {r['event']:<12} | {r['f_echo']:<10} | {r['max_snr_post']:<18.3f} {sig:<4} | {alpha:<10.4f}")

    print(f"\n  Joint SNR (sqrt(sum SNR_i^2)) = {joint_snr:.3f}")
    print(f"  Normalized joint SNR = {joint_snr_norm:.3f}")
    print(f"  Alpha joint upper limit = {alpha_joint:.4f}")
    print(f"\n  Theory prediction: alpha ~ 0.1")
    if alpha_joint > 0.1:
        print(f"  [OK] alpha_joint={alpha_joint:.4f} > 0.1: NOT RULED OUT")
    else:
        print(f"  [!!] alpha_joint={alpha_joint:.4f} < 0.1: THEORY CHALLENGED")

    # Significance assessment
    sig_events = [r for r in results if r['max_snr_post'] > 3.0]
    print(f"\n  Events with post-merger SNR > 3sigma: {len(sig_events)}")
    if len(sig_events) == 0:
        print(f"  --> No significant echo candidates found.")
    else:
        for r in sig_events:
            print(f"  --> {r['event']}: SNR={r['max_snr_post']:.3f} (need confirmation)")

    # Noise expectation: for N events, max post-merger SNR in noise should be ~3.3 for 99% CL
    # If observed > expected, it's a hint of signal
    expected_max_snr = np.sqrt(2 * np.log(n))  # Gumbel approx for max of n noise peaks
    print(f"\n  Expected max SNR in pure noise (Gumbel, n={n}): ~{expected_max_snr:.2f}")
    obs_max = max(snr_vals)
    print(f"  Observed max post-merger SNR: {obs_max:.3f}")
    if obs_max > expected_max_snr * 1.5:
        print(f"  --> Excess above noise expectation: possible signal hint (needs confirmation)")
    else:
        print(f"  --> Consistent with noise expectation (no excess)")

# ---- Visualization ----
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
axes = axes.flatten()
colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b']

for i, r in enumerate(results[:6]):
    ax = axes[i]
    ts = r['t_search']
    mask = (ts >= -0.5) & (ts <= 1.5)
    ax.plot(ts[mask], r['snr_abs'][mask], color=colors[i % len(colors)], linewidth=0.6)
    ax.axvline(0, color='red', linestyle='--', lw=1.5, alpha=0.7, label='Merger')
    ax.axvspan(0.02, 1.5, alpha=0.12, color='yellow', label='Echo window')
    ax.axhline(2.5, color='orange', linestyle=':', lw=1, label='2.5sig')
    ax.axhline(3.0, color='red', linestyle=':', lw=1, label='3sig')
    ax.set_xlabel('Time since merger (s)', fontsize=9)
    ax.set_ylabel('|SNR|', fontsize=9)
    max_s = r['max_snr_post']
    marker = '*' if max_s > 3.0 else ''
    ax.set_title(f"{r['event']} (f={r['f_echo']}Hz)\nmax|SNR|={max_s:.2f}{marker}", fontsize=10)
    ax.legend(fontsize=7, loc='upper right')
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(0, min(10, max(r['snr_abs']) * 1.1))
    ax.grid(alpha=0.25)

for i in range(len(results), 6):
    axes[i].axis('off')

fig.suptitle('Multi-Event GW Echo Joint Search\n'
             f'Joint normalized SNR = {joint_snr_norm:.3f} | Alpha <= {alpha_joint:.4f}',
             fontsize=13, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.96])
out_png = os.path.join(os.path.dirname(__file__), 'multi_event_echo_search.png')
plt.savefig(out_png, dpi=150, bbox_inches='tight')
print(f"\nFigure saved: {out_png}")
plt.close()
