# -*- coding: utf-8 -*-
"""
验证六（扩展版）：弱耦合常数的排名对应
N=100,000，10次运行，扫描 rank-1 到 rank-316（全部唯一签名）
"""
import numpy as np
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


print("=" * 70)
print("Verify 6 (Extended): Full Rank Scan for Coupling Constants")
print("N=100,000, 10 runs, scanning ALL ranks")
print("=" * 70)

weak_coupling = 1.0 / 128.0   # = 0.0078125
fine_structure = 1.0 / 137.0  # = 0.0072993

print(f"\nWeak coupling 1/128  = {weak_coupling:.6f}")
print(f"Fine structure 1/137 = {fine_structure:.6f}")

n_runs = 10
import time
t_start = time.time()

# Run simulations
all_proportions = []
all_unique = []

print(f"\nRunning {n_runs} simulations...")
for run_id in range(n_runs):
    np.random.seed(42 + run_id * 100)
    ese = EmptySetEmergence(max_steps=100000, p_contain=0.5, depth_penalty=0.0)
    ese.run()
    cs_sorted = sorted(ese.sig_count.values(), reverse=True)
    total = sum(cs_sorted)
    props = [s / total for s in cs_sorted]
    all_proportions.append(props)
    all_unique.append(len(cs_sorted))
    elapsed = time.time() - t_start
    eta = elapsed / (run_id + 1) * (n_runs - run_id - 1)
    print(f"  Run {run_id+1}/{n_runs} | unique={len(cs_sorted)} | "
          f"time={elapsed:.1f}s | ETA={eta:.0f}s | "
          f"top={props[0]:.6f} | rank50={props[49]:.6f} | rank100={props[99]:.6f}")

max_unique = max(all_unique)
# Pad to equal length
padded = []
for props in all_proportions:
    arr = list(props) + [float('nan')] * (max_unique - len(props))
    padded.append(arr)
mean_props = np.nanmean(padded, axis=0)
std_props = np.nanstd(padded, axis=0)
print(f"\nMean unique signatures: {max_unique}")

# Find where 1/128 and 1/137 best match
print(f"\n{'='*70}")
print(f"FULL SCAN: Where do 1/128 and 1/137 appear?")
print(f"{'='*70}")

print(f"\n{'Rank':>6} | {'Mean':>10} | {'Std':>10} | {'CV%':>6} | "
      f"{'dev(1/128)':>10} | {'dev(1/137)':>10}")
print("-" * 65)

best_rank_weak = None
best_dev_weak = float('inf')
best_rank_fine = None
best_dev_fine = float('inf')

# Only print ranks with proportion > 0.001 (filter out the tail)
for rank in range(1, max_unique + 1):
    if rank > len(mean_props):
        break
    mean_r = mean_props[rank - 1]
    std_r = std_props[rank - 1]
    if mean_r < 0.001:
        continue
    cv = std_r / mean_r * 100
    dev_weak = abs(mean_r - weak_coupling) / weak_coupling * 100
    dev_fine = abs(mean_r - fine_structure) / fine_structure * 100

    if dev_weak < best_dev_weak:
        best_dev_weak = dev_weak
        best_rank_weak = rank
    if dev_fine < best_dev_fine:
        best_dev_fine = dev_fine
        best_rank_fine = rank

    # Print if within 20% of either constant
    if dev_weak < 20 or dev_fine < 20:
        marker = ""
        if dev_weak < 1.0:
            marker = " <<< 1/128"
        elif dev_fine < 1.0:
            marker = " <<< 1/137"
        print(f"{rank:>6} | {mean_r:>10.6f} | {std_r:>10.6f} | {cv:>5.1f}% | "
              f"{dev_weak:>9.2f}% | {dev_fine:>9.2f}%{marker}")

print(f"\n{'='*70}")
print(f"Best Matches Summary")
print(f"{'='*70}")
print(f"  1/128 = {weak_coupling:.6f}")
print(f"    Best rank: {best_rank_weak}, proportion={mean_props[best_rank_weak-1]:.6f}, deviation={best_dev_weak:.2f}%")
print(f"  1/137 = {fine_structure:.6f}")
print(f"    Best rank: {best_rank_fine}, proportion={mean_props[best_rank_fine-1]:.6f}, deviation={best_dev_fine:.2f}%")

if best_rank_weak and best_rank_fine:
    delta_rank = best_rank_weak - best_rank_fine
    print(f"\n  Delta_rank = {delta_rank}")
    weinberg = 0.223
    print(f"  sin^2(theta_W) = {weinberg}")
    print(f"  delta_rank * sin^2(theta_W) = {delta_rank * weinberg:.3f}")
    print(f"  delta_rank / sin^2(theta_W) = {delta_rank / weinberg:.2f}")

# Also: check ratio between consecutive ranks
print(f"\n{'='*70}")
print(f"Consecutive Rank Ratios (rank_n / rank_(n-1))")
print(f"{'='*70}")
print(f"{'Rank':>8} | {'ratio':>10} | {'target':>10} | {'dev%':>8}")
print("-" * 45)
for rank in [46, 47, 48, 49, 50, 51, 52]:
    if rank <= len(mean_props) and rank - 1 >= 0:
        ratio = mean_props[rank - 1] / mean_props[rank - 2]
        dev_128 = abs(ratio - weak_coupling) / weak_coupling * 100
        dev_137 = abs(ratio - fine_structure) / fine_structure * 100
        dev = min(dev_128, dev_137)
        marker = " <<<" if dev < 5 else ""
        print(f"{rank:>8} | {ratio:>10.6f} | 1/{int(1/ratio) if ratio>0 else 0:>6} | {dev:>7.2f}%{marker}")

# Show the full proportion range
print(f"\n{'='*70}")
print(f"Proportion Range Overview (every 25 ranks)")
print(f"{'='*70}")
for rank in range(1, max_unique + 1, 25):
    mean_r = mean_props[rank - 1]
    print(f"  rank-{rank:3d}: {mean_r:.6f}  (dev from 1/128: {abs(mean_r-weak_coupling)/weak_coupling*100:.1f}%, "
          f"from 1/137: {abs(mean_r-fine_structure)/fine_structure*100:.1f}%)")
