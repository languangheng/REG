# -*- coding: utf-8 -*-
"""
验证五：精细结构常数稳定性（50次独立运行）
"""
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt

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
print("Verify 5: Fine-Structure Constant Stability (50 Independent Runs)")
print("=" * 70)

fine_struct_const = 1.0 / 137.0  # = 0.00729927
target_rank = 48

all_ratios = []
all_size_at_48 = []
all_unique = []
all_ranks_around = []  # store rank-40 to rank-56 for each run

print("\nRunning 50 independent ESE simulations (N=50000, penalty=0.0)...")
print("-" * 60)

for run_id in range(50):
    seed = 42 + run_id * 100
    np.random.seed(seed)

    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
    ese.run()

    class_sizes_sorted = sorted(ese.sig_count.values(), reverse=True)
    total = sum(class_sizes_sorted)
    unique = len(class_sizes_sorted)

    if unique >= target_rank:
        size_at_48 = class_sizes_sorted[target_rank - 1]
        ratio = size_at_48 / total
        all_ratios.append(ratio)
        all_size_at_48.append(size_at_48)
        all_unique.append(unique)

        # Store nearby ranks for analysis
        rank_min = max(1, target_rank - 10)
        rank_max = min(len(class_sizes_sorted), target_rank + 10)
        nearby = [class_sizes_sorted[r - 1] / total for r in range(rank_min, rank_max + 1)]
        all_ranks_around.append((rank_min, rank_max, nearby))

    if (run_id + 1) % 10 == 0:
        print(f"  Completed {run_id + 1}/50 runs...")

print(f"  Completed 50/50 runs.")

# Statistics
ratios_arr = np.array(all_ratios)
mean_ratio = np.mean(ratios_arr)
std_ratio = np.std(ratios_arr)
cv = std_ratio / mean_ratio * 100.0

deviation_pct = abs(mean_ratio - fine_struct_const) / fine_struct_const * 100.0

ci_low = np.percentile(ratios_arr, 16)
ci_high = np.percentile(ratios_arr, 84)

se = std_ratio / np.sqrt(len(ratios_arr))
z_score = abs(mean_ratio - fine_struct_const) / se if se > 0 else 0

best_idx = np.argmin(np.abs(ratios_arr - fine_struct_const))

print(f"\nSuccessful runs: {len(ratios_arr)}/50")
print(f"Total instances per run: 50001")
print(f"Unique signatures per run: {np.mean(all_unique):.0f} +/- {np.std(all_unique):.0f}")

print(f"\n" + "=" * 70)
print("Statistical Results: Rank-48 Proportion")
print("=" * 70)
print(f"  Mean proportion: {mean_ratio:.8f} +/- {std_ratio:.8f}")
print(f"  Std deviation:   {std_ratio:.8f}")
print(f"  CV (Coefficient of Variation): {cv:.2f}%")
print(f"  68% CI (1-sigma): [{ci_low:.8f}, {ci_high:.8f}]")
print(f"  1/137         =   {fine_struct_const:.8f}")
print(f"  Mean deviation from 1/137: {deviation_pct:.4f}%")
print(f"  Z-score (mean vs 1/137): {z_score:.4f} sigma")

best_run_ratio = ratios_arr[best_idx]
best_dev = abs(best_run_ratio - fine_struct_const) / fine_struct_const * 100.0
print(f"\n  Best run:  #{best_idx+1}")
print(f"    Proportion: {best_run_ratio:.8f}")
print(f"    Deviation from 1/137: {best_dev:.4f}%")
print(f"    Size@rank-48: {all_size_at_48[best_idx]}")

# Check where 1/137 falls in the rank-40 to 56 range (best run)
b_r, b_r_max, b_nearby = all_ranks_around[best_idx]
print(f"\n  Best run: rank-40 to rank-56 proportions:")
for r_idx, r in enumerate(range(b_r, b_r_max + 1)):
    val = b_nearby[r_idx]
    dev = abs(val - fine_struct_const) / fine_struct_const * 100.0
    mark = " <<<" if dev < 0.5 else ""
    print(f"    rank-{r:2d}: {val:.6f} (dev={dev:+.2f}%){mark}")

# Stability verdict
print(f"\n" + "=" * 70)
print("Stability Verdict")
print("=" * 70)

verdicts = []
if cv < 5:
    verdicts.append(f"[PASS] CV = {cv:.2f}% < 5%  ->  Highly stable")
elif cv < 10:
    verdicts.append(f"[MARGINAL] CV = {cv:.2f}% (5-10%)  ->  Moderately stable")
else:
    verdicts.append(f"[FAIL] CV = {cv:.2f}% > 10%  ->  Unstable")

if z_score < 2:
    verdicts.append(f"[PASS] Z-score = {z_score:.2f} < 2 sigma  ->  No significant difference from 1/137")
elif z_score < 3:
    verdicts.append(f"[MARGINAL] Z-score = {z_score:.2f} (2-3 sigma)  ->  Marginally significant")
else:
    verdicts.append(f"[FAIL] Z-score = {z_score:.2f} > 3 sigma  ->  Significant difference from 1/137")

in_ci = fine_struct_const >= ci_low and fine_struct_const <= ci_high
if in_ci:
    verdicts.append(f"[PASS] 1/137 = {fine_struct_const:.6f} within 68% CI [{ci_low:.6f}, {ci_high:.6f}]")
else:
    verdicts.append(f"[MARGINAL] 1/137 = {fine_struct_const:.6f} outside 68% CI [{ci_low:.6f}, {ci_high:.6f}]")

for v in verdicts:
    print(" ", v)

# Fraction of runs with dev < 1%
devs_all = np.abs(ratios_arr - fine_struct_const) / fine_struct_const * 100.0
frac_1pct = np.mean(devs_all < 1.0) * 100
frac_2pct = np.mean(devs_all < 2.0) * 100
frac_5pct = np.mean(devs_all < 5.0) * 100

print(f"\n  Runs with deviation < 1%: {frac_1pct:.0f}%")
print(f"  Runs with deviation < 2%: {frac_2pct:.0f}%")
print(f"  Runs with deviation < 5%: {frac_5pct:.0f}%")

# Visualization
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# Fig 1: 50 runs bar chart
ax1 = axes[0]
colors = ['red' if abs(r - fine_struct_const)/fine_struct_const < 0.01 
          else 'steelblue' for r in ratios_arr]
ax1.bar(np.arange(1, len(ratios_arr)+1), ratios_arr, color=colors, edgecolor='white', alpha=0.8)
ax1.axhline(fine_struct_const, color='red', linestyle='--', linewidth=2, 
            label=f'1/137 = {fine_struct_const:.6f}')
ax1.axhline(mean_ratio, color='blue', linestyle='-', linewidth=2, 
            label=f'Mean = {mean_ratio:.6f}')
ax1.fill_between([0, len(ratios_arr)+1], ci_low, ci_high, 
                 alpha=0.15, color='blue', label='68% CI')
ax1.set_xlabel('Run ID', fontsize=12)
ax1.set_ylabel('Rank-48 Proportion', fontsize=12)
ax1.set_title(f'50 Runs Stability (CV={cv:.1f}%, Z={z_score:.2f}sigma)', fontsize=12)
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

# Fig 2: Histogram
ax2 = axes[1]
ax2.hist(ratios_arr, bins=15, color='steelblue', edgecolor='white', alpha=0.7)
ax2.axvline(fine_struct_const, color='red', linestyle='--', linewidth=2, label='1/137')
ax2.axvline(mean_ratio, color='blue', linestyle='-', linewidth=2, label=f'Mean')
ax2.axvline(ci_low, color='blue', linestyle=':', linewidth=1.5, label='68% CI bounds')
ax2.axvline(ci_high, color='blue', linestyle=':', linewidth=1.5)
ax2.set_xlabel('Rank-48 Proportion', fontsize=12)
ax2.set_ylabel('Count', fontsize=12)
ax2.set_title('Proportion Distribution (50 runs)', fontsize=12)
ax2.legend(fontsize=10)

# Fig 3: Deviation from 1/137 for each run
ax3 = axes[2]
ax3.bar(np.arange(1, len(devs_all)+1), devs_all, 
         color=['green' if d < 1.0 else 'orange' if d < 2.0 else 'red' for d in devs_all],
         edgecolor='white', alpha=0.8)
ax3.axhline(1.0, color='green', linestyle='--', linewidth=1.5, label='1% threshold')
ax3.axhline(2.0, color='orange', linestyle='--', linewidth=1.5, label='2% threshold')
ax3.axhline(5.0, color='red', linestyle='--', linewidth=1.5, label='5% threshold')
ax3.set_xlabel('Run ID', fontsize=12)
ax3.set_ylabel('Deviation from 1/137 (%)', fontsize=12)
ax3.set_title('Per-Run Deviation from Fine-Structure Constant', fontsize=12)
ax3.legend(fontsize=9)
ax3.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('verify_fine_structure_50runs.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nFigure saved to verify_fine_structure_50runs.png")

# Summary table
print(f"\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Target: rank-48 proportion vs 1/137 = {fine_struct_const:.8f}")
print(f"50-run mean: {mean_ratio:.8f} (deviation: {deviation_pct:.4f}%)")
print(f"Stability: CV={cv:.2f}%, Z-score={z_score:.2f}sigma")
print(f"1sigma CI: [{ci_low:.8f}, {ci_high:.8f}]")
print(f"Runs within 1% of 1/137: {frac_1pct:.0f}%")
print(f"Runs within 2% of 1/137: {frac_2pct:.0f}%")
print(f"Runs within 5% of 1/137: {frac_5pct:.0f}%")
