# -*- coding: utf-8 -*-
import numpy as np
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
print("ESE Multi-Constant Exploration")
print("=" * 70)

np.random.seed(42)
ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
ese.run()

cs = sorted(ese.sig_count.values(), reverse=True)
total = sum(cs)
unique = len(cs)

print(f"Total: {total}, Unique signatures: {unique}")
print(f"Top-10 class sizes: {cs[:10]}")

# ============================================================
# Exploration 1: Rank 1-100 ratio scan (known constants)
# ============================================================
print("\n" + "=" * 70)
print("Exploration 1: Rank 1-100 Scan (Known Physics Constants)")
print("=" * 70)

known_constants = [
    (1/137, "1/137 (Fine Structure)"),
    (1/128, "1/128 (Approx Coupling)"),
    (1/100, "1/100 (Century)"),
    (1/50, "1/50 (Approx)"),
    (1/20, "1/20"),
    (1/10, "1/10 (Decade)"),
    (1/3, "1/3 (Charge Ratio)"),
    (1/7, "1/7 (Musical/Approx)"),
    (1/6, "1/6 (Dice)"),
    (1/np.e, "1/e (Euler)"),
    (np.pi/100, "pi/100"),
    (np.sqrt(2)/10, "sqrt(2)/10"),
]

best_matches = []
for rank in range(1, min(101, unique+1)):
    size = cs[rank-1]
    ratio = size / total
    for const_val, const_name in known_constants:
        dev = abs(ratio - const_val) / const_val * 100
        if dev < 12:
            best_matches.append((rank, ratio, const_val, const_name, dev))

best_matches.sort(key=lambda x: x[4])

print(f"\nMatches (dev < 12%):")
if best_matches:
    seen = set()
    count = 0
    for rank, ratio, const_val, const_name, dev in best_matches:
        key = (const_name, int(ratio*10000))
        if key in seen:
            continue
        seen.add(key)
        print(f"  rank={rank:3d}: ratio={ratio:.6f} ~= {const_name} (dev={dev:.1f}%)")
        count += 1
        if count >= 20:
            break
else:
    print("  No matches found. Reference ratios:")
    for rank in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        if rank <= unique:
            print(f"  rank={rank:3d}: ratio={cs[rank-1]/total:.6f}")

# ============================================================
# Exploration 2: Optimal N for 1/137
# ============================================================
print("\n" + "=" * 70)
print("Exploration 2: Optimal N for 1/137")
print("=" * 70)

target = 1.0 / 137.0
print(f"Target: 1/137 = {target:.6f}")
print(f"\n{'N':>8} {'rank50_ratio':>14} {'dev%':>8} {'unique':>8}")
print("-" * 45)

results_n = []
for n_steps in [5000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 80000, 100000]:
    np.random.seed(42)
    ese_n = EmptySetEmergence(max_steps=n_steps, p_contain=0.5, depth_penalty=0.0)
    ese_n.run()
    cs_n = sorted(ese_n.sig_count.values(), reverse=True)
    tot_n = sum(cs_n)
    uniq_n = len(cs_n)
    if uniq_n >= 50:
        r = cs_n[49] / tot_n
        dev = abs(r - target) / target * 100
        results_n.append((n_steps, r, dev, uniq_n))
        print(f"{n_steps:>8} {r:>14.6f} {dev:>8.2f} {uniq_n:>8d}")
    else:
        print(f"{n_steps:>8} {'N/A':>14} {'N/A':>8} {uniq_n:>8d}")

best = min(results_n, key=lambda x: x[2])
print(f"\n** Optimal N = {best[0]}, ratio={best[1]:.6f}, dev={best[2]:.2f}%")

# Also check: rank where ratio = 1/137 approximately
print(f"\n** Rank where ratio closest to 1/137 = {target:.6f}:")
devs = [(rank, cs[rank-1]/total, abs(cs[rank-1]/total - target)/target*100) for rank in range(1, min(101, unique+1))]
devs.sort(key=lambda x: x[2])
for rank, ratio, dev in devs[:5]:
    print(f"  rank={rank:3d}: ratio={ratio:.6f}, dev={dev:.2f}%")

# ============================================================
# Exploration 3: Three-generation fermion log-spacing (improved)
# ============================================================
print("\n" + "=" * 70)
print("Exploration 3: Three-Generation Fermion Log-Spacing")
print("=" * 70)

# Real lepton masses
e_mass = 0.511
mu_mass = 105.66
tau_mass = 1776.86
real_masses = np.array([e_mass, mu_mass, tau_mass])
real_logs = np.log(real_masses)
real_log_diff = np.diff(real_logs)

print(f"Real lepton masses: e={e_mass}, mu={mu_mass}, tau={tau_mass} MeV")
print(f"ln(masses): {real_logs[0]:.4f}, {real_logs[1]:.4f}, {real_logs[2]:.4f}")
print(f"Delta ln(12) = {real_log_diff[0]:.4f}  [mu/e = {mu_mass/e_mass:.1f}x]")
print(f"Delta ln(23) = {real_log_diff[1]:.4f}  [tau/mu = {tau_mass/mu_mass:.1f}x]")

# ESE class size log-spacings
mid = unique // 2
size_top = cs[0]
size_mid = cs[mid-1]
size_end = cs[-1]

ese_logs = np.log(np.array([size_top, size_mid, size_end]))
ese_log_diff = np.diff(ese_logs)

print(f"\nESE class sizes: top={size_top}, mid={size_mid}, end={size_end}")
print(f"ESE ln(sizes): {ese_logs[0]:.4f}, {ese_logs[1]:.4f}, {ese_logs[2]:.4f}")
print(f"ESE Delta ln(12) = {ese_log_diff[0]:.4f}")
print(f"ESE Delta ln(23) = {ese_log_diff[1]:.4f}")

# Scale ESE to match real Delta12
scale = real_log_diff[0] / ese_log_diff[0]
scaled_ese_d23 = ese_log_diff[1] * scale
print(f"\n[Scale factor: {scale:.3f}]")
print(f"Scaled ESE Delta ln(23) = {scaled_ese_d23:.4f}")
print(f"Real Delta ln(23)      = {real_log_diff[1]:.4f}")
print(f"Deviation: {abs(scaled_ese_d23 - real_log_diff[1])/real_log_diff[1]*100:.1f}%")

# Alternative: use top, 1/3, 2/3 positions
p1 = 0
p2 = unique // 3
p3 = 2 * unique // 3
if unique >= 3:
    size_p1 = cs[p1]
    size_p2 = cs[p2-1]
    size_p3 = cs[p3-1]
    ese_logs2 = np.log(np.array([size_p1, size_p2, size_p3]))
    ese_log_diff2 = np.diff(ese_logs2)
    scale2 = real_log_diff[0] / ese_log_diff2[0]
    scaled2 = ese_log_diff2[1] * scale2
    print(f"\n[Using positions {p1},{p2},{p3}]")
    print(f"ESE sizes: {size_p1}, {size_p2}, {size_p3}")
    print(f"ESE Delta ln(12) = {ese_log_diff2[0]:.4f}, Delta ln(23) = {ese_log_diff2[1]:.4f}")
    print(f"Scaled Delta ln(23) = {scaled2:.4f} (scale={scale2:.3f})")
    print(f"Real Delta ln(23)   = {real_log_diff[1]:.4f}")
    print(f"Deviation: {abs(scaled2 - real_log_diff[1])/real_log_diff[1]*100:.1f}%")

# Direct ratio comparison
print(f"\n[Direct ratio comparison]")
print(f"Real mu/e     = {mu_mass/e_mass:.2f}  -> ln = {np.log(mu_mass/e_mass):.4f}")
print(f"Real tau/mu   = {tau_mass/mu_mass:.2f} -> ln = {np.log(tau_mass/mu_mass):.4f}")
print(f"ESE top/mid   = {size_top/size_mid:.2f} -> ln = {np.log(size_top/size_mid):.4f}")
print(f"ESE mid/bot   = {size_mid/size_end:.2f} -> ln = {np.log(size_mid/size_end):.4f}")
print(f"\nRatio ratio:")
print(f"  Real:    ln(mu/e) / ln(tau/mu) = {np.log(mu_mass/e_mass)/np.log(tau_mass/mu_mass):.4f}")
print(f"  ESE:     ln(top/mid) / ln(mid/bot) = {np.log(size_top/size_mid)/np.log(size_mid/size_end):.4f}")
