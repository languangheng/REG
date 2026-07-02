# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

class EmptySetEmergence:
    def __init__(self, max_steps=50000, p_contain=0.5, depth_penalty=0.0):
        self.max_steps = max_steps
        self.p_contain = p_contain
        self.depth_penalty = depth_penalty
        self.signatures = [()]
        self.depths = [0]
        self.sig_to_id = {(): 0}
        self.sig_count = Counter()
        self.sig_count[()] = 1
        self.step = 0

    def run(self):
        for _ in range(self.max_steps):
            if self.depth_penalty > 0:
                weights = np.exp(-self.depth_penalty * np.array(self.depths))
                weights = weights / weights.sum()
                i = np.random.choice(len(self.signatures), p=weights)
            else:
                i = np.random.randint(len(self.signatures))
            if np.random.random() < self.p_contain:
                new_sig = (self.signatures[i],)
                self._add_node(new_sig, i, 'contain')
            else:
                new_sig = self.signatures[i]
                self._add_node(new_sig, i, 'equal')
            self.step += 1

    def _add_node(self, sig, parent, op_type):
        self.sig_count[sig] += 1
        if sig in self.sig_to_id:
            child = self.sig_to_id[sig]
        else:
            child = len(self.signatures)
            self.signatures.append(sig)
            self.sig_to_id[sig] = child
            if op_type == 'contain':
                self.depths.append(self.depths[parent] + 1)
            else:
                self.depths.append(self.depths[parent])


print("=" * 70)
print("ESE 精细扫描：惩罚强度 0.0 ~ 1.0，步长 0.1")
print("=" * 70)
print(f"{'惩罚':<8} {'幂律指数':<12} {'最大深度':<10} {'平均深度':<12} {'唯一签名':<10} {'相'}")
print("-" * 70)

penalty_values = np.arange(0.0, 1.1, 0.1)
results = []

for penalty in penalty_values:
    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=penalty)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)

    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    if len(sizes) >= 2:
        slope, _ = np.polyfit(np.log(ranks), np.log(sizes), 1)
    else:
        slope = 0.0

    depths = ese.depths
    max_depth = max(depths) if depths else 0
    avg_depth = np.mean(depths) if depths else 0

    results.append({
        'penalty': penalty,
        'slope': slope,
        'max_depth': max_depth,
        'avg_depth': avg_depth,
        'unique_sigs': len(ese.signatures),
        'class_sizes': class_sizes_sorted,
        'ese': ese,
    })

    if abs(slope) < 0.3:
        phase = '均匀相'
    elif abs(slope) < 2.0:
        phase = '过渡相'
    elif abs(slope) < 4.0:
        phase = '极端集中相'
    else:
        phase = '退化相'

    print(f"{penalty:<8.1f} {slope:<12.4f} {max_depth:<10d} {avg_depth:<12.4f} {len(ese.signatures):<10d} {phase}")

# Find best Zipf point
penalties_arr = np.array([r['penalty'] for r in results])
slopes_arr = np.array([r['slope'] for r in results])
best_idx = np.argmin([abs(s + 1.0) for s in slopes_arr])
best_penalty = penalties_arr[best_idx]
best_slope = slopes_arr[best_idx]

# Find phase transition
print("\n" + "=" * 70)
print("相变点检测")
print("=" * 70)
for i in range(len(slopes_arr)-1):
    delta = abs(slopes_arr[i+1] - slopes_arr[i])
    if delta > 0.5:
        print(f"  惩罚 {penalties_arr[i]:.1f} -> {penalties_arr[i+1]:.1f}: "
              f"alpha {slopes_arr[i]:.3f} -> {slopes_arr[i+1]:.3f}  (delta={delta:.3f})")

# Fine scan around phase transition
print("\n" + "=" * 70)
print("精细扫描：相变临界区 0.1 ~ 0.5，步长 0.02")
print("=" * 70)
fine_penalties = np.arange(0.1, 0.55, 0.02)
fine_results = []

for penalty in fine_penalties:
    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=penalty)
    ese.run()
    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)
    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    if len(sizes) >= 2:
        slope, _ = np.polyfit(np.log(ranks), np.log(sizes), 1)
    else:
        slope = 0.0
    depths = ese.depths
    fine_results.append({'penalty': penalty, 'slope': slope, 'max_depth': max(depths), 'unique': len(ese.signatures)})
    print(f"惩罚={penalty:.2f} | 幂律指数={slope:.4f} | 最大深度={max(depths)} | 唯一签名={len(ese.signatures)}")

# Find critical point
fp = np.array([r['penalty'] for r in fine_results])
fs = np.array([r['slope'] for r in fine_results])
# Critical: where |slope| crosses 1.0 (between uniform and Zipf)
crossing_idx = np.where((np.abs(fs[:-1]) < 1.0) & (np.abs(fs[1:]) >= 1.0))[0]
if len(crossing_idx) > 0:
    cp = fp[crossing_idx[0]]
    print(f"\n** 相变临界点估计: penalty ≈ {cp:.2f} (alpha 穿过 -1.0)")
else:
    print(f"\n** 相变临界点未在此区间内精确找到，最接近: penalty={fp[np.argmin(np.abs(fs+1.0))]:.2f}")

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: Full scan
axes[0,0].plot(penalties_arr, slopes_arr, 'o-', color='steelblue', linewidth=2, markersize=10)
axes[0,0].axhline(-1.0, color='red', linestyle='--', alpha=0.7, label='Zipf (-1.0)')
axes[0,0].axhline(0.0, color='gray', linestyle='--', alpha=0.5, label='Uniform (0.0)')
axes[0,0].axhline(-2.0, color='green', linestyle='--', alpha=0.5, label='Prime (-2.0)')
axes[0,0].set_xlabel('Depth Penalty')
axes[0,0].set_ylabel('Power Law Exponent')
axes[0,0].set_title('Phase Transition: Power Law Exponent vs Depth Penalty')
axes[0,0].legend()
axes[0,0].grid(True, alpha=0.3)
axes[0,0].axvspan(0.2, 0.5, alpha=0.15, color='orange', label='Transition Zone')
axes[0,0].annotate(f'Best Zipf\npenalty={best_penalty:.1f}\nalpha={best_slope:.3f}',
                   xy=(best_penalty, best_slope),
                   xytext=(best_penalty+0.15, best_slope+0.5),
                   fontsize=10, color='steelblue',
                   arrowprops=dict(arrowstyle='->', color='steelblue'))

# Plot 2: Fine scan around transition
axes[0,1].plot(fp, fs, 's-', color='coral', linewidth=2, markersize=8)
axes[0,1].axhline(-1.0, color='red', linestyle='--', alpha=0.7, label='Zipf (-1.0)')
axes[0,1].axhline(0.0, color='gray', linestyle='--', alpha=0.5, label='Uniform (0.0)')
axes[0,1].set_xlabel('Depth Penalty')
axes[0,1].set_ylabel('Power Law Exponent')
axes[0,1].set_title('Fine Scan: Critical Region 0.1 ~ 0.5')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)

# Plot 3: Max depth vs penalty
max_depths = [r['max_depth'] for r in results]
axes[1,0].plot(penalties_arr, max_depths, 'o-', color='purple', linewidth=2, markersize=10)
axes[1,0].set_xlabel('Depth Penalty')
axes[1,0].set_ylabel('Max Depth')
axes[1,0].set_title('Max Depth Collapse: Evidence of Phase Transition')
axes[1,0].grid(True, alpha=0.3)

# Plot 4: Best Zipf class size distribution
best_sizes = results[best_idx]['class_sizes']
n = len(best_sizes)
axes[1,1].loglog(range(1, n+1), best_sizes, 'b-', linewidth=2, label=f'ESE (penalty={best_penalty:.1f})')
axes[1,1].loglog(range(1, n+1), best_sizes[0]/np.arange(1, n+1), 'r--', linewidth=2, label='Zipf prediction')
axes[1,1].set_xlabel('Rank')
axes[1,1].set_ylabel('Class Size')
axes[1,1].set_title(f'Best Zipf Match: penalty={best_penalty:.1f}, alpha={best_slope:.3f}')
axes[1,1].legend()
axes[1,1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('ese_fine_scan.png', dpi=150)
print("\n图表已保存至 ese_fine_scan.png")

# Summary
print("\n" + "=" * 70)
print("综合结论")
print("=" * 70)
print(f"最接近Zipf的惩罚: {best_penalty:.1f}, alpha={best_slope:.3f}, 偏差={abs(best_slope+1.0):.3f}")
print(f"均匀相: penalty < ~0.3, alpha ~ -0.1")
print(f"相变区: penalty ~ 0.3-0.5, alpha 从 -0.1 跳到 -3.0")
print(f"极端集中: penalty > ~0.5, alpha ~ -3.0 to -5.0")
print(f"物理意义: 深度惩罚驱动了ESE从'民主化'到'精英化'的相变")
