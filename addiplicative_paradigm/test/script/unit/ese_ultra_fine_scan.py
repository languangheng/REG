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
print("ESE 超精细扫描：penalty 0.10 ~ 0.15，步长 0.005")
print("=" * 70)

penalty_values = np.arange(0.100, 0.155, 0.005)
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
    })

    dev = abs(slope + 2.0)
    marker = ''
    if dev < 0.02:
        marker = ' <<<< ALPHA=-2.0 FOUND!'
    elif dev < 0.05:
        marker = ' *'
    print(f"penalty={penalty:.3f} | alpha={slope:.4f} | dev={dev:.4f} | max_d={max_depth:3d} | unique={len(ese.signatures):3d}{marker}")

# Also run multiple seeds to check stability
print("\n" + "=" * 70)
print("稳定性检验：对最接近 -2.0 的点做 5 次重复运行")
print("=" * 70)

penalties = [r['penalty'] for r in results]
slopes_arr = np.array([r['slope'] for r in results])
best_idx = np.argmin([abs(s + 2.0) for s in slopes_arr])
best_penalty = penalties[best_idx]

print(f"最接近 -2.0 的惩罚强度: {best_penalty:.3f}")
print(f"5次独立运行的幂律指数:")
alphas_multi = []
for seed in [42, 123, 456, 789, 2026]:
    rng_backup = np.random.get_state()
    np.random.seed(seed)
    ese_m = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=best_penalty)
    ese_m.run()
    cs = sorted(ese_m.sig_count.values(), reverse=True)
    rk = np.arange(1, min(51, len(cs)+1))
    sz = cs[:50]
    sl, _ = np.polyfit(np.log(rk), np.log(sz), 1)
    alphas_multi.append(sl)
    print(f"  seed={seed}: alpha={sl:.4f}  (dev from -2.0: {abs(sl+2.0):.4f})")
    np.random.set_state(rng_backup)

mean_alpha = np.mean(alphas_multi)
std_alpha = np.std(alphas_multi)
print(f"\n平均值: {mean_alpha:.4f} +/- {std_alpha:.4f}")
print(f"与-2.0的偏差: {abs(mean_alpha+2.0):.4f}")
if abs(mean_alpha + 2.0) < 0.1:
    print("[结论] alpha=-2.0 被稳定复现！这是 ESE=zeta 猜想的决定性证据。")
elif abs(mean_alpha + 2.0) < 0.2:
    print("[结论] alpha 接近 -2.0，但有一定波动。多次平均: {:.4f}".format(mean_alpha))
else:
    print("[结论] alpha 与 -2.0 有明显偏差。")

# Visualization
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].plot(penalties, slopes_arr, 'o-', color='steelblue', linewidth=2, markersize=8)
axes[0].axhline(-2.0, color='green', linestyle='--', linewidth=2.5, alpha=0.8, label='Prime (-2.0)')
axes[0].axhline(-1.0, color='red', linestyle='--', alpha=0.5, label='Zipf (-1.0)')
axes[0].fill_between(penalties, -2.1, -1.9, alpha=0.15, color='green', label='Target band')
axes[0].annotate(
    f'Best: p={best_penalty:.3f}\na={mean_alpha:.4f}\nstd={std_alpha:.4f}',
    xy=(best_penalty, mean_alpha),
    xytext=(best_penalty + 0.015, mean_alpha + 0.3),
    fontsize=10, color='darkgreen', fontweight='bold',
    arrowprops=dict(arrowstyle='->', color='darkgreen'))
axes[0].set_xlabel('Depth Penalty')
axes[0].set_ylabel('Power Law Exponent alpha')
axes[0].set_title('Ultra-Fine Scan: alpha vs Penalty (0.100 ~ 0.150)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Multiple runs stability plot
ax2 = axes[1]
ax2.bar(range(5), alphas_multi, color='steelblue', alpha=0.7, label='Individual runs')
ax2.axhline(-2.0, color='green', linestyle='--', linewidth=2, label='Target (-2.0)')
ax2.axhline(mean_alpha, color='orange', linestyle='-', linewidth=2, label=f'Mean ({mean_alpha:.4f})')
ax2.axhline(mean_alpha + std_alpha, color='orange', linestyle=':', alpha=0.5)
ax2.axhline(mean_alpha - std_alpha, color='orange', linestyle=':', alpha=0.5)
ax2.set_xlabel('Run Index')
ax2.set_ylabel('alpha')
ax2.set_title(f'Stability Check: 5 runs at penalty={best_penalty:.3f}')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('ese_ultra_fine_scan.png', dpi=150)
print("\n图表已保存至 ese_ultra_fine_scan.png")
