# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

class EmptySetEmergence:
    def __init__(self, max_steps=100000, p_contain=0.5, depth_penalty=0.0):
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


# ============================================================
# Experiment 1: Scan p_contain
# ============================================================
print("=" * 60)
print("实验一：自包含概率 vs 幂律指数")
print("=" * 60)
print(f"{'p_contain':<12} {'幂律指数':<12} {'最大深度':<10} {'唯一签名数':<12} {'平均深度':<10}")
print("-" * 56)

p_values = [0.1, 0.3, 0.5, 0.7, 0.9]
power_exponents = []

for p in p_values:
    ese = EmptySetEmergence(max_steps=50000, p_contain=p, depth_penalty=0.0)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)
    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    log_ranks = np.log(ranks)
    log_sizes = np.log(sizes)
    slope, _ = np.polyfit(log_ranks, log_sizes, 1)
    power_exponents.append(slope)

    depths = ese.depths
    max_depth = max(depths) if depths else 0
    mean_depth = np.mean(depths)
    n_sigs = len(ese.signatures)
    print(f"{p:<12.1f} {slope:<12.4f} {max_depth:<10d} {n_sigs:<12d} {mean_depth:<10.4f}")

# ============================================================
# Experiment 2: Scan depth penalty
# ============================================================
print("\n" + "=" * 60)
print("实验二：深度惩罚 vs 幂律指数 (p=0.5)")
print("=" * 60)
print(f"{'惩罚强度':<12} {'幂律指数':<12} {'最大深度':<10} {'唯一签名数':<12} {'平均深度':<10}")
print("-" * 56)

penalty_values = [0.0, 0.5, 1.0, 2.0, 3.0]
penalty_exponents = []

for penalty in penalty_values:
    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=penalty)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)
    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    log_ranks = np.log(ranks)
    log_sizes = np.log(sizes)
    slope, _ = np.polyfit(log_ranks, log_sizes, 1)
    penalty_exponents.append(slope)

    depths = ese.depths
    max_depth = max(depths) if depths else 0
    mean_depth = np.mean(depths)
    n_sigs = len(ese.signatures)
    print(f"{penalty:<12.1f} {slope:<12.4f} {max_depth:<10d} {n_sigs:<12d} {mean_depth:<10.4f}")

# ============================================================
# Additional experiment: deeper penalty scan
# ============================================================
print("\n" + "=" * 60)
print("附加：更深的惩罚扫描 (p=0.5)")
print("=" * 60)
print(f"{'惩罚强度':<12} {'幂律指数':<12} {'最大深度':<10} {'唯一签名数':<12} {'平均深度':<10}")
print("-" * 56)

deep_penalties = [4.0, 5.0, 6.0, 8.0, 10.0]
for penalty in deep_penalties:
    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=penalty)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)
    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    log_ranks = np.log(ranks)
    log_sizes = np.log(sizes)
    slope, _ = np.polyfit(log_ranks, log_sizes, 1)

    depths = ese.depths
    max_depth = max(depths) if depths else 0
    mean_depth = np.mean(depths)
    n_sigs = len(ese.signatures)
    print(f"{penalty:<12.1f} {slope:<12.4f} {max_depth:<10d} {n_sigs:<12d} {mean_depth:<10.4f}")

# ============================================================
# Visualization
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Power exponent vs p_contain
axes[0,0].plot(p_values, power_exponents, 'o-', color='steelblue', linewidth=2, markersize=10)
axes[0,0].axhline(-1.0, color='red', linestyle='--', alpha=0.7, label='Zipf (-1.0)')
axes[0,0].axhline(0.0, color='gray', linestyle='--', alpha=0.5, label='Uniform (0.0)')
axes[0,0].set_xlabel('p_contain (Self-contain probability)')
axes[0,0].set_ylabel('Power law exponent')
axes[0,0].set_title('p_contain vs Power Law Exponent')
axes[0,0].legend()
axes[0,0].grid(True, alpha=0.3)
axes[0,0].set_ylim(-1.5, 0.5)

# Plot 2: Power exponent vs depth penalty
all_penalties = penalty_values + deep_penalties
all_exponents = penalty_exponents + [None] * len(deep_penalties)
axes[0,1].plot(penalty_values, penalty_exponents, 's-', color='coral', linewidth=2, markersize=10, label='penalty 0-3')
axes[0,1].axhline(-1.0, color='red', linestyle='--', alpha=0.7, label='Zipf (-1.0)')
axes[0,1].axhline(0.0, color='gray', linestyle='--', alpha=0.5, label='Uniform (0.0)')
axes[0,1].set_xlabel('Depth Penalty Intensity')
axes[0,1].set_ylabel('Power law exponent')
axes[0,1].set_title('Depth Penalty vs Power Law Exponent (p=0.5)')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)
axes[0,1].set_ylim(-1.5, 0.5)

# Plot 3: Class size distribution at different penalties (representative)
ese0 = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
ese0.run()
ese5 = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=3.0)
ese5.run()

cs0 = sorted(Counter(ese0.sig_count.values()).items())
cs5 = sorted(Counter(ese5.sig_count.values()).items())

axes[1,0].loglog([x[0] for x in cs0], [x[1] for x in cs0], 'o', color='blue', alpha=0.6, label='penalty=0')
axes[1,0].loglog([x[0] for x in cs5], [x[1] for x in cs5], 's', color='red', alpha=0.6, label='penalty=3')
axes[1,0].set_xlabel('Class Size')
axes[1,0].set_ylabel('Class Count')
axes[1,0].set_title('Class Size Distribution: penalty=0 vs penalty=3')
axes[1,0].legend()
axes[1,0].grid(True, alpha=0.3)

# Plot 4: Depth distribution comparison
axes[1,1].bar(range(20), [Counter(ese0.depths).get(d, 0) for d in range(20)], 
              alpha=0.6, label='penalty=0', color='blue', width=0.4)
axes[1,1].bar([d+0.4 for d in range(20)], [Counter(ese5.depths).get(d, 0) for d in range(20)],
              alpha=0.6, label='penalty=3', color='red', width=0.4)
axes[1,1].set_xlabel('Depth')
axes[1,1].set_ylabel('Node Count')
axes[1,1].set_title('Depth Distribution: penalty=0 vs penalty=3')
axes[1,1].legend()
axes[1,1].set_yscale('log')

plt.tight_layout()
plt.savefig('ese_parameter_scan.png', dpi=150)
print("\n图表已保存至 ese_parameter_scan.png")

# ============================================================
# Summary table
# ============================================================
print("\n" + "=" * 60)
print("综合分析结论")
print("=" * 60)
print("\n实验一（p_contain扫描）：")
for p, e in zip(p_values, power_exponents):
    print(f"  p={p:.1f}: alpha={e:+.4f}  ({'接近Zipf' if abs(e+1)<0.3 else '接近均匀' if abs(e)<0.3 else '中间态'})")
print("\n实验二（深度惩罚扫描）：")
for pen, e in zip(penalty_values, penalty_exponents):
    print(f"  penalty={pen:.1f}: alpha={e:+.4f}  ({'接近Zipf' if abs(e+1)<0.3 else '接近均匀' if abs(e)<0.3 else '中间态'})")
print("\n关键发现：")
print(f"  p_contain变化时，幂律指数基本不变（{min(power_exponents):.3f}~{max(power_exponents):.3f}）")
print(f"  深度惩罚增强时，幂律指数从~{penalty_exponents[0]:.3f}变到~{penalty_exponents[-1]:.3f}")
print(f"  {'深度惩罚有效！幂律指数向-1靠拢' if penalty_exponents[-1] < penalty_exponents[0] - 0.3 else '深度惩罚效果有限'}")
