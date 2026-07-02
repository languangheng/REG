# -*- coding: utf-8 -*-
import numpy as np
from collections import Counter

class EmptySetEmergence:
    def __init__(self, max_steps=50000, p_contain=0.5, depth_penalty=0.12):
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
print("ESE Physical Constants Precision Test")
print("=" * 70)

fine_const = 1.0 / 137.0  # 0.00729927
all_rank_ratios = []
all_log_spacings = []

for run_id in range(5):
    seed = 42 + run_id * 100
    np.random.seed(seed)

    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.12)
    ese.run()

    cs_sorted = sorted(ese.sig_count.values(), reverse=True)
    total = sum(cs_sorted)
    n_unique = len(cs_sorted)

    # Scan ranks 40-60
    rank_ratios = {}
    for rank in range(40, min(61, n_unique+1)):
        ratio = cs_sorted[rank-1] / total
        rank_ratios[rank] = ratio
    all_rank_ratios.append(rank_ratios)

    # Log spacings
    if n_unique >= 3:
        log_sizes = np.log(cs_sorted)
        idx_mid = n_unique // 2
        all_log_spacings.append([log_sizes[0], log_sizes[idx_mid], log_sizes[-1]])

    print(f"Run {run_id+1}: unique={n_unique}, total={total}, top3={cs_sorted[:3]}")

# ============================================================
# Test 1: Fine structure constant scan
# ============================================================
print("\n" + "=" * 70)
print("Test 1: Fine Structure Constant Scan (rank 40-60)")
print("=" * 70)
print(f"Target: 1/137 = {fine_const:.6f}")
print(f"\n{'Rank':<6} {'Mean Ratio':<14} {'Std Dev':<12} {'Dev from 1/137':<16} {'Status'}")
print("-" * 65)

results = []
for rank in range(40, 61):
    ratios = [r.get(rank) for r in all_rank_ratios if rank in r]
    if len(ratios) >= 3:
        mean = np.mean(ratios)
        std = np.std(ratios)
        dev_pct = abs(mean - fine_const) / fine_const * 100
        status = "<<< BEST!" if dev_pct < 1.0 else ("*" if dev_pct < 5.0 else "")
        results.append((rank, mean, std, dev_pct, status))
        print(f"{rank:<6} {mean:<14.6f} {std:<12.4f} {dev_pct:<16.2f}% {status}")

if results:
    best = min(results, key=lambda x: x[3])
    print(f"\n** Best match: rank={best[0]}, ratio={best[1]:.6f}, dev={best[3]:.2f}%")

# ============================================================
# Test 2: Log spacing vs lepton masses
# ============================================================
print("\n" + "=" * 70)
print("Test 2: Three-Generation Fermion Mass Log Spacing")
print("=" * 70)

# Real lepton masses (MeV)
e_mass = 0.511
mu_mass = 105.66
tau_mass = 1776.86
real_masses = np.array([e_mass, mu_mass, tau_mass])
real_logs = np.log(real_masses)

print(f"Real lepton masses: e={e_mass}, mu={mu_mass}, tau={tau_mass} MeV")
print(f"ln(masses): {real_logs[0]:.4f}, {real_logs[1]:.4f}, {real_logs[2]:.4f}")
print(f"Delta ln(12) = ln(mu/e) = {real_logs[1]-real_logs[0]:.4f}")
print(f"Delta ln(23) = ln(tau/mu) = {real_logs[2]-real_logs[1]:.4f}")
print(f"Ratio: Delta12 / Delta23 = {(real_logs[1]-real_logs[0])/(real_logs[2]-real_logs[1]):.4f}")

# ESE log spacings
if all_log_spacings:
    avg_logs = np.mean(all_log_spacings, axis=0)
    print(f"\nESE class size log-spacings (mean of 5 runs):")
    print(f"  Top rank:    ln(size_max) = {avg_logs[0]:.4f}  (size ~ {int(np.exp(avg_logs[0]))})")
    print(f"  Mid rank:    ln(size_mid) = {avg_logs[1]:.4f}  (size ~ {int(np.exp(avg_logs[1]))})")
    print(f"  Bottom rank: ln(size_min) = {avg_logs[2]:.4f}  (size ~ {int(np.exp(avg_logs[2]))})")

    ese_d1 = avg_logs[0] - avg_logs[1]  # ln(top/mid)
    ese_d2 = avg_logs[1] - avg_logs[2]  # ln(mid/bottom)
    print(f"\nESE Delta ln(12) = {ese_d1:.4f}")
    print(f"ESE Delta ln(23) = {ese_d2:.4f}")
    print(f"ESE ratio: Delta12 / Delta23 = {ese_d1/ese_d2:.4f}")

    # Scale ESE delta to match real Delta12
    scale = (real_logs[1] - real_logs[0]) / ese_d1
    scaled_d2 = ese_d2 * scale
    print(f"\n[Scaled to match real Delta12]")
    print(f"  Scale factor: {scale:.2f}")
    print(f"  Scaled ESE Delta23: {scaled_d2:.4f}")
    print(f"  Real Delta23:        {real_logs[2]-real_logs[1]:.4f}")
    print(f"  Deviation: {abs(scaled_d2-(real_logs[2]-real_logs[1]))/(real_logs[2]-real_logs[1])*100:.1f}%")

# Alternative: look at the ratio of class sizes across runs
print(f"\n[Alternative: Rank-1 / Rank-N ratio as 'mass hierarchy']")
for n in [2, 3, 5]:
    if len(cs_sorted) >= n:
        ratio = cs_sorted[0] / cs_sorted[n-1]
        print(f"  Rank1/Rank{n} = {cs_sorted[0]}/{cs_sorted[n-1]} = {ratio:.2f}")

# Direct comparison: ESE class size ratios vs lepton mass ratios
if all_log_spacings:
    avg_top = np.exp(avg_logs[0])
    avg_mid = np.exp(avg_logs[1])
    avg_bot = np.exp(avg_logs[2])
    ese_ratio_12 = avg_top / avg_mid
    ese_ratio_23 = avg_mid / avg_bot
    real_ratio_12 = mu_mass / e_mass
    real_ratio_23 = tau_mass / mu_mass

    print(f"\n[Direct Ratio Comparison]")
    print(f"  ESE rank1/rank_mid  = {ese_ratio_12:.2f}")
    print(f"  ESE rank_mid/rank_bottom = {ese_ratio_23:.2f}")
    print(f"  Real mu/e = {real_ratio_12:.2f}")
    print(f"  Real tau/mu = {real_ratio_23:.2f}")

    print(f"\n  ESE ratio12 / ratio23 = {ese_ratio_12/ese_ratio_23:.4f}")
    print(f"  Real ratio12 / ratio23 = {real_ratio_12/real_ratio_23:.4f}")

# Extra: check penalty=0.0 case
print("\n" + "=" * 70)
print("Extra: penalty=0.0, larger N (100K) for more unique signatures")
print("=" * 70)

np.random.seed(42)
ese_large = EmptySetEmergence(max_steps=100000, p_contain=0.5, depth_penalty=0.0)
ese_large.run()
cs_large = sorted(ese_large.sig_count.values(), reverse=True)
total_large = sum(cs_large)
n_unique_large = len(cs_large)

print(f"unique={n_unique_large}, total={total_large}")

# Scan rank 100-200
print(f"\nRank 100-200 scan for 1/137:")
for rank in range(100, min(201, n_unique_large+1), 10):
    ratio = cs_large[rank-1] / total_large
    dev = abs(ratio - fine_const) / fine_const * 100
    marker = " <<<" if dev < 5.0 else ""
    print(f"  Rank {rank:3d}: ratio={ratio:.6f}, dev={dev:6.2f}%{marker}")
