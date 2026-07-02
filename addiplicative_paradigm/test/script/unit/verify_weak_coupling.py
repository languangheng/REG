# -*- coding: utf-8 -*-
"""
验证六：弱耦合常数的排名对应
N=100,000，20次独立运行，扫描rank-35~45
"""
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt

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


print("=" * 70)
print("Verify 6: Weak Coupling Constant Rank Correspondence")
print("N=100,000, 20 runs, scanning rank-35 to 45")
print("=" * 70)

weak_coupling = 1.0 / 128.0   # = 0.0078125
fine_structure = 1.0 / 137.0  # = 0.00729927

print(f"\nWeak coupling 1/128 = {weak_coupling:.6f}")
print(f"Fine structure  1/137 = {fine_structure:.6f}")
print(f"Difference: {weak_coupling - fine_structure:.6f}")

# Scan range
n_runs = 20
scan_start = 35
scan_end = 45
all_rank_ratios = {rank: [] for rank in range(scan_start, scan_end + 1)}
all_unique = []

print(f"\n{'='*70}")
print(f"Running {n_runs} independent ESE simulations (N=100,000)...")
print(f"Scan range: rank-{scan_start} to rank-{scan_end}")
print(f"{'='*70}")

import time
t_start = time.time()

for run_id in range(n_runs):
    seed = 42 + run_id * 100
    np.random.seed(seed)

    t0 = time.time()
    ese = EmptySetEmergence(max_steps=100000, p_contain=0.5, depth_penalty=0.0)
    ese.run()
    elapsed = time.time() - t0

    cs_sorted = sorted(ese.sig_count.values(), reverse=True)
    total = sum(cs_sorted)
    unique = len(cs_sorted)
    all_unique.append(unique)

    for rank in range(scan_start, scan_end + 1):
        if unique >= rank:
            ratio = cs_sorted[rank - 1] / total
            all_rank_ratios[rank].append(ratio)

    eta = (time.time() - t_start) / (run_id + 1) * (n_runs - run_id - 1)
    print(f"  Run {run_id+1:2d}/{n_runs} | unique={unique:4d} | "
          f"time={elapsed:.1f}s | ETA={eta:.0f}s | "
          f"rank-40={cs_sorted[39]/total:.6f} | "
          f"rank-48={cs_sorted[47]/total:.6f}")

total_time = time.time() - t_start
print(f"\nTotal time: {total_time:.1f}s ({total_time/60:.1f} min)")

# Statistics
print(f"\n{'='*70}")
print(f"Rank Scan Results ({n_runs} runs, N=100,000)")
print(f"{'='*70}")
print(f"{'Rank':>6} | {'Mean':>10} | {'Std':>10} | {'CV%':>6} | "
      f"{'dev(1/128)':>12} | {'dev(1/137)':>12} | {'in1%':>6}")
print("-" * 80)

best_rank_weak = None
best_dev_weak = float('inf')
best_rank_fine = None
best_dev_fine = float('inf')

for rank in range(scan_start, scan_end + 1):
    ratios = all_rank_ratios[rank]
    if len(ratios) >= 5:
        mean_r = np.mean(ratios)
        std_r = np.std(ratios)
        cv = std_r / mean_r * 100
        dev_weak = abs(mean_r - weak_coupling) / weak_coupling * 100
        dev_fine = abs(mean_r - fine_structure) / fine_structure * 100
        in_1pct = "YES" if dev_weak < 1.0 else ("yes" if dev_weak < 2.0 else "no")

        print(f"{rank:>6} | {mean_r:>10.6f} | {std_r:>10.6f} | {cv:>5.1f}% | "
              f"{dev_weak:>11.2f}% | {dev_fine:>11.2f}% | {in_1pct:>6}")

        if dev_weak < best_dev_weak:
            best_dev_weak = dev_weak
            best_rank_weak = rank
        if dev_fine < best_dev_fine:
            best_dev_fine = dev_fine
            best_rank_fine = rank

print(f"\n{'='*70}")
print(f"Best Matches")
print(f"{'='*70}")
print(f"  Weak coupling (1/128={weak_coupling:.6f}):")
print(f"    Best rank: {best_rank_weak}, deviation: {best_dev_weak:.2f}%")
print(f"  Fine structure (1/137={fine_structure:.6f}):")
print(f"    Best rank: {best_rank_fine}, deviation: {best_dev_fine:.2f}%")

if best_rank_weak and best_rank_fine:
    delta_rank = best_rank_weak - best_rank_fine
    print(f"\n  Rank spacing: delta_rank = {delta_rank}")
    weinberg = 0.223
    print(f"  Weinberg angle: sin^2(theta_W) = {weinberg}")
    print(f"  delta_rank * sin^2(theta_W) = {delta_rank * weinberg:.3f}")
    print(f"  delta_rank / sin^2(theta_W) = {delta_rank / weinberg:.2f}")
    if delta_rank != 0:
        print(f"  1 / delta_rank = {1/delta_rank:.4f}")
    else:
        print(f"  1 / delta_rank = N/A (delta_rank = 0)")

    # Best-run analysis for delta_rank
    print(f"\n  Per-run delta_rank (fine best -> weak best):")
    for run_id in range(min(5, n_runs)):
        ratios = [all_rank_ratios[r][run_id] for r in range(scan_start, scan_end+1)]
        ranks_arr = list(range(scan_start, scan_end+1))
        dev_w = [abs(v - weak_coupling) for v in ratios]
        dev_f = [abs(v - fine_structure) for v in ratios]
        rw = ranks_arr[np.argmin(dev_w)]
        rf = ranks_arr[np.argmin(dev_f)]
        dr = rw - rf
        print(f"    Run {run_id+1}: rank closest to 1/128 = {rw}, "
              f"rank closest to 1/137 = {rf}, delta = {dr}")

# Extended scan: look at rank-45 to 55 too
print(f"\n{'='*70}")
print(f"Extended Scan: rank-45 to 55 (for fine structure reference)")
print(f"{'='*70}")
ext_start, ext_end = 45, 55
ext_results = []
for rank in range(ext_start, ext_end + 1):
    if rank in all_rank_ratios and len(all_rank_ratios[rank]) >= 5:
        mean_r = np.mean(all_rank_ratios[rank])
        dev_f = abs(mean_r - fine_structure) / fine_structure * 100
        dev_w = abs(mean_r - weak_coupling) / weak_coupling * 100
        ext_results.append((rank, mean_r, dev_f, dev_w))
        print(f"  rank-{rank:2d}: mean={mean_r:.6f}, "
              f"dev(1/137)={dev_f:.2f}%, dev(1/128)={dev_w:.2f}%")

# Visualization
fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# Fig 1: Proportion vs rank
ax1 = axes[0]
ranks = list(range(scan_start, scan_end + 1))
means = [np.mean(all_rank_ratios[r]) for r in ranks]
stds = [np.std(all_rank_ratios[r]) for r in ranks]
ax1.errorbar(ranks, means, yerr=stds, fmt='o-', color='steelblue',
             linewidth=2, markersize=8, capsize=4, label='ESE proportion')
ax1.axhline(weak_coupling, color='orange', linestyle='--', linewidth=2,
            label=f'1/128={weak_coupling:.6f}')
ax1.axhline(fine_structure, color='green', linestyle='--', linewidth=2,
            label=f'1/137={fine_structure:.6f}')
# Mark best matches
ax1.axvline(best_rank_weak, color='orange', linestyle=':', alpha=0.5)
ax1.axvline(best_rank_fine, color='green', linestyle=':', alpha=0.5)
ax1.set_xlabel('Rank', fontsize=12)
ax1.set_ylabel('Proportion', fontsize=12)
ax1.set_title(f'Rank-{scan_start} to {scan_end} Proportions (N=100K, {n_runs} runs)', fontsize=12)
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# Fig 2: Deviation from both constants
ax2 = axes[1]
devs_weak = [abs(np.mean(all_rank_ratios[r]) - weak_coupling) / weak_coupling * 100
             for r in ranks]
devs_fine = [abs(np.mean(all_rank_ratios[r]) - fine_structure) / fine_structure * 100
             for r in ranks]
ax2.plot(ranks, devs_weak, 'o-', color='orange', linewidth=2, markersize=8,
         label='Deviation from 1/128')
ax2.plot(ranks, devs_fine, 's-', color='green', linewidth=2, markersize=8,
         label='Deviation from 1/137')
ax2.axhline(1.0, color='red', linestyle=':', linewidth=1.5, label='1% threshold')
ax2.axhline(2.0, color='red', linestyle='--', linewidth=1, label='2% threshold')
ax2.set_xlabel('Rank', fontsize=12)
ax2.set_ylabel('Deviation (%)', fontsize=12)
ax2.set_title('Deviation from Coupling Constants', fontsize=12)
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

# Fig 3: Unique signature count stability
ax3 = axes[2]
ax3.plot(range(1, n_runs+1), all_unique, 'o-', color='steelblue',
         linewidth=2, markersize=6)
ax3.axhline(np.mean(all_unique), color='red', linestyle='--',
            label=f'Mean={np.mean(all_unique):.0f}')
ax3.fill_between(range(1, n_runs+1),
                  np.mean(all_unique) - np.std(all_unique),
                  np.mean(all_unique) + np.std(all_unique),
                  alpha=0.2, color='steelblue')
ax3.set_xlabel('Run ID', fontsize=12)
ax3.set_ylabel('Unique Signatures', fontsize=12)
ax3.set_title(f'Unique Signature Count Stability (CV={np.std(all_unique)/np.mean(all_unique)*100:.1f}%)', fontsize=12)
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('verify_weak_coupling.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nFigure saved to verify_weak_coupling.png")

# Final summary
print(f"\n{'='*70}")
print(f"FINAL SUMMARY")
print(f"{'='*70}")
print(f"  Weak coupling 1/128 = {weak_coupling:.6f}")
print(f"  Fine structure 1/137 = {fine_structure:.6f}")
print(f"  Best rank for 1/128: {best_rank_weak} (dev={best_dev_weak:.2f}%)")
print(f"  Best rank for 1/137: {best_rank_fine} (dev={best_dev_fine:.2f}%)")
if best_rank_weak and best_rank_fine:
    print(f"  Delta rank: {best_rank_weak - best_rank_fine}")
print(f"  Total time: {total_time:.1f}s")
print(f"  Mean unique signatures: {np.mean(all_unique):.0f} +/- {np.std(all_unique):.0f}")
print(f"\nDone! Press Enter to exit...")
