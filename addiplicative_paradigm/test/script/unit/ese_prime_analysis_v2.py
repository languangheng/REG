# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

class EmptySetEmergence:
    """空集涌现模拟 - 修正版"""
    def __init__(self, max_steps=100000):
        self.max_steps = max_steps
        self.signatures = [()]
        self.depths = [0]
        self.sig_to_id = {(): 0}
        self.sig_count = Counter()
        self.sig_count[()] = 1
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
        if op_type == 'contain':
            self.edges_contain.append((child, parent))
        else:
            self.edges_equal.append((child, parent))

    def analyze(self):
        total_instances = sum(self.sig_count.values())
        total_classes = len(self.signatures)
        class_sizes = list(self.sig_count.values())
        size_dist = Counter(class_sizes)
        prime_count = size_dist.get(1, 0)
        depth_dist = Counter(self.depths)
        return {
            'total_instances': total_instances,
            'total_classes': total_classes,
            'prime_count': prime_count,
            'prime_ratio': prime_count / total_classes if total_classes > 0 else 0,
            'class_size_distribution': size_dist,
            'depth_distribution': depth_dist,
            'class_sizes': class_sizes,
        }


print("=" * 60)
print("ESE 不可约结构（结构素数）分析 - 修正版")
print("=" * 60)

ese = EmptySetEmergence(max_steps=200000)
ese.run()
results = ese.analyze()

print(f"总实例数（节点总数）: {results['total_instances']:,}")
print(f"唯一结构类型数: {results['total_classes']:,}")
print(f"不可约结构数（类大小=1）: {results['prime_count']:,}")
print(f"不可约类型占比: {results['prime_ratio']:.4f}")

size_dist = results['class_size_distribution']
print(f"\n类大小分布（前15）:")
for s in sorted(size_dist.keys())[:15]:
    print(f"  size={s:4d}: {size_dist[s]:6d} classes")

class_sizes = results['class_sizes']
class_sizes_sorted = np.sort(class_sizes)

max_size = min(100, max(class_sizes))
x_values = list(range(1, max_size + 1))
pi_values = []

for x in x_values:
    total_le_x = np.sum(class_sizes_sorted <= x)
    prime_le_x = results['prime_count'] if x >= 1 else 0
    pi_values.append(prime_le_x / total_le_x if total_le_x > 0 else 0)

print("\n" + "=" * 60)
print("不可约结构占比 vs 素数定理预测")
print("=" * 60)
print(f"{'x':<10} {'不可约占比':<18} {'1/ln(x) 预测':<18} {'偏差%':<10}")
print("-" * 56)
for i, x in enumerate(x_values[:25]):
    pi_val = pi_values[i]
    pred = 1.0 / np.log(x) if x > 1 else 1.0
    dev = (pi_val - pred) / pred * 100 if pred > 0 else 0
    print(f"{x:<10} {pi_val:<18.6f} {pred:<18.6f} {dev:>+.2f}%")

# Correlation
x_plot = [x for x in x_values[2:50]]
pi_plot = pi_values[2:50]
pred_plot = [1.0/np.log(x) for x in x_plot]
if len(x_plot) > 3:
    corr = np.corrcoef(pi_plot, pred_plot)[0, 1]
    print(f"\nPearson相关系数: {corr:.6f}")

# Visualization
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

sizes = sorted([s for s in size_dist.keys() if s <= 50])
counts = [size_dist[s] for s in sizes]
axes[0].bar(sizes, counts, color='steelblue', edgecolor='white')
axes[0].set_xlabel('Class Size')
axes[0].set_ylabel('Class Count')
axes[0].set_title('Structural Class Size Distribution')
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

xp = [x for x in x_values[2:50]]
pip = pi_values[2:50]
prp = [1.0/np.log(x) for x in xp]
axes[2].plot(xp, pip, 'b-', linewidth=2, label='ESE irreducible ratio')
axes[2].plot(xp, prp, 'r--', linewidth=2, label='1/ln(x) prediction')
axes[2].set_xlabel('Class Size Upper Bound x')
axes[2].set_ylabel('Irreducible Ratio')
axes[2].set_title('Irreducible Distribution vs Prime Number Theorem')
axes[2].legend()

plt.tight_layout()
plt.savefig('ese_prime_analysis_v2.png', dpi=150)
print("\n图表已保存至 ese_prime_analysis_v2.png")
