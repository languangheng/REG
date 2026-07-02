# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import sys

class EmptySetEmergence:
    """ESE模拟：空集的自指涉迭代（带签名追踪）"""
    def __init__(self, max_steps=100000):
        self.max_steps = max_steps
        self.signatures = [()]
        self.depths = [0]
        self.sig_to_id = {(): 0}
        self.edges_contain = []
        self.edges_equal = []
        self.step = 0

    def run(self):
        for _ in range(self.max_steps):
            i = np.random.randint(len(self.signatures))
            if np.random.random() < 0.5:
                new_sig = (self.signatures[i],)
                self._add_node(new_sig, i, 'contain')
            else:
                new_sig = self.signatures[i]
                self._add_node(new_sig, i, 'equal')
            self.step += 1

    def _add_node(self, sig, parent, op_type):
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

        if op_type == 'contain':
            self.edges_contain.append((child, parent))
        else:
            self.edges_equal.append((child, parent))

    def analyze(self):
        n = len(self.signatures)
        sig_counts = Counter(self.signatures)
        class_sizes = list(sig_counts.values())
        size_dist = Counter(class_sizes)
        prime_count = size_dist.get(1, 0)
        total_classes = len(sig_counts)
        depth_dist = Counter(self.depths)
        return {
            'total_signatures': n,
            'total_classes': total_classes,
            'prime_count': prime_count,
            'prime_ratio': prime_count / total_classes if total_classes > 0 else 0,
            'class_size_distribution': size_dist,
            'depth_distribution': depth_dist,
            'sig_counts': sig_counts,
        }


print("=" * 60)
print("ESE 不可约结构（结构素数）分析")
print("=" * 60)

# Run simulation with large N
ese = EmptySetEmergence(max_steps=200000)
ese.run()
results = ese.analyze()

print(f"总节点数: {ese.step + 1:,}")
print(f"唯一签名数（结构类型总数）: {results['total_classes']:,}")
print(f"不可约结构数（类大小=1）: {results['prime_count']:,}")
print(f"不可约比例: {results['prime_ratio']:.4f}")

# Class size distribution summary
size_dist = results['class_size_distribution']
print(f"\n类大小分布（前10）:")
sorted_sizes = sorted(size_dist.keys())
for s in sorted_sizes[:10]:
    cnt = size_dist[s]
    print(f"  size={s:3d}: {cnt:6d} classes")

# Key analysis
class_sizes = list(results['sig_counts'].values())
class_sizes_sorted = np.sort(class_sizes)

max_size = min(100, max(class_sizes))
pi_values = []
x_values = list(range(1, max_size + 1))

for x in x_values:
    total_le_x = np.sum(class_sizes_sorted <= x)
    prime_le_x = results['prime_count'] if x >= 1 else 0
    pi_values.append(prime_le_x / total_le_x if total_le_x > 0 else 0)

print("\n" + "=" * 60)
print("不可约结构占比 vs 素数定理预测")
print("=" * 60)
print(f"{'x':<8} {'不可约占比':<16} {'1/ln(x) 预测':<16} {'偏差%':<10}")
print("-" * 50)
for i, x in enumerate(x_values[:30]):
    pi_val = pi_values[i]
    prime_theorem_pred = 1.0 / np.log(x) if x > 1 else 1.0
    deviation = (pi_val - prime_theorem_pred) / prime_theorem_pred * 100 if prime_theorem_pred > 0 else 0
    print(f"{x:<8} {pi_val:<16.6f} {prime_theorem_pred:<16.6f} {deviation:>+.2f}%")

# Save results to file
with open("ese_prime_table.txt", "w", encoding="utf-8") as f:
    f.write("不可约结构占比 vs 素数定理预测 (N=200000)\n")
    f.write("=" * 60 + "\n")
    f.write(f"{'x':<8} {'不可约占比':<16} {'1/ln(x) 预测':<16} {'偏差%':<10}\n")
    f.write("-" * 50 + "\n")
    for i, x in enumerate(x_values[:30]):
        pi_val = pi_values[i]
        prime_theorem_pred = 1.0 / np.log(x) if x > 1 else 1.0
        deviation = (pi_val - prime_theorem_pred) / prime_theorem_pred * 100 if prime_theorem_pred > 0 else 0
        f.write(f"{x:<8} {pi_val:<16.6f} {prime_theorem_pred:<16.6f} {deviation:>+.2f}%\n")

# Visualization
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

sizes = sorted([s for s in size_dist.keys() if s <= 20])
counts = [size_dist[s] for s in sizes]
axes[0].bar(sizes, counts, color='steelblue', edgecolor='white')
axes[0].set_xlabel('Class Size')
axes[0].set_ylabel('Class Count')
axes[0].set_title('Equal Class Size Distribution')
axes[0].set_yscale('log')

depth_dist = results['depth_distribution']
max_depth = max(depth_dist.keys())
depths = list(range(max_depth + 1))
depth_counts = [depth_dist.get(d, 0) for d in depths]
axes[1].bar(depths, depth_counts, color='coral', edgecolor='white')
axes[1].set_xlabel('Depth')
axes[1].set_ylabel('Node Count')
axes[1].set_title('Structural Depth Distribution')
axes[1].set_yscale('log')

x_plot = [x for x in x_values[1:50]]
pi_plot = pi_values[1:50]
pred_plot = [1.0/np.log(x) for x in x_values[1:50]]
axes[2].plot(x_plot, pi_plot, 'b-', linewidth=2, label='ESE irreducible ratio')
axes[2].plot(x_plot, pred_plot, 'r--', linewidth=2, label='1/ln(x) prediction')
axes[2].set_xlabel('Class Size Upper Bound x')
axes[2].set_ylabel('Irreducible Ratio')
axes[2].set_title('ESE Irreducible vs Prime Number Theorem')
axes[2].legend()

plt.tight_layout()
plt.savefig('ese_prime_analysis.png', dpi=150)
print("\n图表已保存至 ese_prime_analysis.png")
print("对比表已保存至 ese_prime_table.txt")

# Overall correlation
# Pearson correlation between ESE ratio and 1/ln(x)
if len(x_plot) > 3:
    corr = np.corrcoef(pi_plot, pred_plot)[0, 1]
    print(f"\nPearson相关系数 (蓝线 vs 红线): {corr:.6f}")
    if corr > 0.9:
        print("[结论] 高度相关！蓝线与红线趋势一致，支持ESE=zeta的猜想。")
    elif corr > 0.5:
        print("[结论] 中等相关，存在部分一致性，需进一步分析。")
    else:
        print("[结论] 相关性弱，蓝线与红线形态不同，需重新审视定义。")
