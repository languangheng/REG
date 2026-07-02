# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

class EmptySetEmergence:
    def __init__(self, max_steps=200000):
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


print("=" * 60)
print("ESE 短期验证：Zipf定律 + 不可约结构详情")
print("=" * 60)

ese = EmptySetEmergence(max_steps=200000)
ese.run()

# ============================================================
# Validation 1: Zipf's Law
# ============================================================
class_sizes = list(ese.sig_count.values())
class_sizes_sorted = sorted(class_sizes, reverse=True)
ranks = np.arange(1, len(class_sizes_sorted) + 1)

print("\n" + "=" * 60)
print("验证一：Zipf定律（类大小 vs 排名）")
print("=" * 60)
print(f"{'排名':<8} {'类大小':<10} {'Zipf预测(1/排名)':<15}")
print("-" * 35)

for i in range(min(15, len(class_sizes_sorted))):
    rank = i + 1
    size = class_sizes_sorted[i]
    zipf_pred = class_sizes_sorted[0] / rank
    print(f"{rank:<8} {size:<10} {zipf_pred:<15.1f}")

log_ranks = np.log(ranks[:100])
log_sizes = np.log(class_sizes_sorted[:100])
slope, intercept = np.polyfit(log_ranks, log_sizes, 1)
print(f"\n幂律指数（前100名）: {slope:.4f}")
print(f"Zipf定律预测值: -1.0000")
print(f"偏差: {abs(slope + 1):.4f}")

# ============================================================
# Validation 2: Irreducible structure details
# ============================================================
prime_sigs = [sig for sig, count in ese.sig_count.items() if count == 1]

print("\n" + "=" * 60)
print("验证二：不可约结构（类大小为1的签名）")
print("=" * 60)
print(f"不可约结构总数: {len(prime_sigs)}")

for i, sig in enumerate(prime_sigs[:10]):
    depth = 0
    s = sig
    while isinstance(s, tuple) and len(s) > 0:
        depth += 1
        s = s[0]
    if depth == 0:
        struct_str = "∅"
    else:
        struct_str = "∅ " + " ".join(["\\u2192 {∅}"] * depth)
    print(f"\n不可约结构 {i+1}:")
    print(f"  签名: {sig}")
    print(f"  深度: {depth}")
    print(f"  结构: {struct_str}")

# ============================================================
# Validation 3: Power law vs prime distribution
# ============================================================
print("\n" + "=" * 60)
print("验证三：ESE幂律 vs 素数分布幂律")
print("=" * 60)

class_size_dist = Counter(class_sizes)
sizes_for_fit = np.array(sorted([s for s in class_size_dist.keys() if s <= 50]))
counts_for_fit = np.array([class_size_dist[s] for s in sizes_for_fit])

log_sizes_fit = np.log(sizes_for_fit[1:])
log_counts_fit = np.log(counts_for_fit[1:])
slope2, _ = np.polyfit(log_sizes_fit, log_counts_fit, 1)

print(f"ESE类大小分布的幂律指数: {slope2:.4f}")
print(f"素数分布近似幂律指数: ~ -2.0 (类大小->类数量)")
print(f"理论说明: 素数的类大小分布(N_x ~ x^(-2))来自数论")
print(f"ESE类大小分布来自: 自包含/自等同操作的随机过程")
if abs(slope2 + 2) < 0.5:
    print(f"结论: 两者接近！ESE遵循与素数相同的幂律结构")
elif abs(slope2 + 1) < 0.3:
    print(f"结论: ESE更接近Zipf定律(α=-1)而非素数(α=-2)")
else:
    print(f"结论: ESE的幂律指数={slope2:.2f}，与素数(-2)和Zipf(-1)都有差异")

# ============================================================
# Visualization
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

axes[0].loglog(ranks, class_sizes_sorted, 'b-', linewidth=1.5, label='Actual')
axes[0].loglog(ranks, class_sizes_sorted[0]/ranks, 'r--', linewidth=1.5, label='Zipf (1/rank)')
axes[0].set_xlabel('Rank')
axes[0].set_ylabel('Class Size')
axes[0].set_title(f'Zipf Law Verification (alpha={slope:.3f})')
axes[0].legend()

axes[1].loglog(sizes_for_fit, counts_for_fit, 'bo', markersize=5, label='Actual')
axes[1].loglog(sizes_for_fit, np.exp(intercept) * sizes_for_fit**slope2, 'r-', linewidth=2, label=f'Fit (alpha={slope2:.2f})')
axes[1].set_xlabel('Class Size')
axes[1].set_ylabel('Class Count')
axes[1].set_title('Class Size Distribution Power Law')
axes[1].legend()

depths_of_sigs = [ese.depths[ese.sig_to_id[sig]] for sig in ese.signatures]
axes[2].scatter(depths_of_sigs, class_sizes, alpha=0.3, s=10)
axes[2].set_xlabel('Depth')
axes[2].set_ylabel('Class Size')
axes[2].set_title('Depth vs Class Size')
axes[2].set_yscale('log')

plt.tight_layout()
plt.savefig('ese_short_term_verify.png', dpi=150)
print("\n图表已保存至 ese_short_term_verify.png")
