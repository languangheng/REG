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
print("ESE Fine Structure Constant Stability + Scaling Law Verification")
print("=" * 70)

fine_const = 1.0 / 137.0

# ============================================================
# Test 1: Stability (20 runs, penalty=0.0, N=50K)
# ============================================================
print("\n" + "=" * 70)
print("Test 1: Stability (20 runs, penalty=0.0, N=50K)")
print("=" * 70)

all_ratios = []
all_sizes_50 = []
all_uniques = []

for run_id in range(20):
    seed = 42 + run_id * 100
    np.random.seed(seed)
    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
    ese.run()
    cs = sorted(ese.sig_count.values(), reverse=True)
    total = sum(cs)
    if len(cs) >= 50:
        ratio = cs[49] / total
        all_ratios.append(ratio)
        all_sizes_50.append(cs[49])
        all_uniques.append(len(cs))
        dev = abs(ratio - fine_const) / fine_const * 100
        print(f"Run {run_id+1:2d}: ratio={ratio:.6f}, size={cs[49]:4d}, unique={len(cs):3d}, dev={dev:.2f}%")

mean_ratio = np.mean(all_ratios)
std_ratio = np.std(all_ratios)
mean_size = np.mean(all_sizes_50)
mean_unique = np.mean(all_uniques)

print(f"\nStatistics:")
print(f"  Mean ratio: {mean_ratio:.6f} +/- {std_ratio:.6f}")
print(f"  Target: 1/137 = {fine_const:.6f}")
print(f"  Mean deviation: {abs(mean_ratio - fine_const)/fine_const*100:.2f}%")
print(f"  Coefficient of variation: {std_ratio/mean_ratio*100:.2f}%")
print(f"  Mean size@50: {mean_size:.1f}")
print(f"  Mean unique: {mean_unique:.1f}")

# ============================================================
# Test 2: Scaling law (different N)
# ============================================================
print("\n" + "=" * 70)
print("Test 2: Scaling Law (penalty=0.0, different N)")
print("=" * 70)

n_list = [10000, 20000, 50000, 100000]
n_ratios = []
n_sizes = []
n_uniques = []

for n_steps in n_list:
    ratios_n = []
    sizes_n = []
    uniqs_n = []
    for run_id in range(5):
        seed = 42 + run_id * 100
        np.random.seed(seed)
        ese = EmptySetEmergence(max_steps=n_steps, p_contain=0.5, depth_penalty=0.0)
        ese.run()
        cs = sorted(ese.sig_count.values(), reverse=True)
        total = sum(cs)
        if len(cs) >= 50:
            ratios_n.append(cs[49] / total)
            sizes_n.append(cs[49])
            uniqs_n.append(len(cs))

    if ratios_n:
        avg_r = np.mean(ratios_n)
        avg_s = np.mean(sizes_n)
        avg_u = np.mean(uniqs_n)
        n_ratios.append(avg_r)
        n_sizes.append(avg_s)
        n_uniques.append(avg_u)
        dev = abs(avg_r - fine_const) / fine_const * 100
        print(f"N={n_steps:>6}: avg_ratio={avg_r:.6f}, avg_size={avg_s:.1f}, avg_unique={avg_u:.1f}, dev={dev:.2f}%")
    else:
        n_ratios.append(None)
        n_sizes.append(None)
        n_uniques.append(None)
        print(f"N={n_steps:>6}: UNABLE (unique < 50)")

# Scaling law fit
valid_idx = [i for i, r in enumerate(n_ratios) if r is not None]
valid_n = [n_list[i] for i in valid_idx]
valid_r = [n_ratios[i] for i in valid_idx]
valid_s = [n_sizes[i] for i in valid_idx]
valid_u = [n_uniques[i] for i in valid_idx]

if len(valid_n) >= 2:
    log_n = np.log(valid_n)
    log_r = np.log(valid_r)
    slope_r, intercept_r = np.polyfit(log_n, log_r, 1)
    print(f"\nScaling law fit: ratio ~ N^{slope_r:.4f}")
    print(f"  Interpretation: {'ratio is SCALE-INVARIANT (slope~0)' if abs(slope_r) < 0.1 else 'ratio depends on N'}")

# ============================================================
# Visualization
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Stability histogram
axes[0,0].hist(all_ratios, bins=12, color='steelblue', edgecolor='white', alpha=0.7)
axes[0,0].axvline(fine_const, color='red', linestyle='--', linewidth=2.5, label=f'1/137={fine_const:.6f}')
axes[0,0].axvline(mean_ratio, color='blue', linestyle='-', linewidth=2.5, label=f'Mean={mean_ratio:.6f}')
axes[0,0].set_xlabel('Rank-50 Ratio')
axes[0,0].set_ylabel('Frequency')
axes[0,0].set_title(f'Fine Structure Constant Stability (20 runs)\nCV={std_ratio/mean_ratio*100:.1f}%, Dev={abs(mean_ratio-fine_const)/fine_const*100:.1f}%')
axes[0,0].legend(fontsize=10)

# Plot 2: Scaling law
axes[0,1].semilogx(valid_n, valid_r, 'o-', color='steelblue', linewidth=2, markersize=10, label='ESE rank-50 ratio')
axes[0,1].axhline(fine_const, color='red', linestyle='--', linewidth=2, label=f'1/137={fine_const:.6f}')
axes[0,1].set_xlabel('Step count N')
axes[0,1].set_ylabel('Rank-50 Ratio')
axes[0,1].set_title(f'Scaling Law: Rank-50 Ratio vs N\nslope={slope_r:.4f} (0=scale-invariant)')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)

# Plot 3: Size@50 vs N
axes[1,0].loglog(valid_n, valid_s, 's-', color='coral', linewidth=2, markersize=10, label='ESE size@50')
log_n_arr = np.log(valid_n)
log_s_arr = np.log(valid_s)
slope_s, intercept_s = np.polyfit(log_n_arr, log_s_arr, 1)
axes[1,0].loglog(valid_n, np.exp(intercept_s + slope_s * log_n_arr), 'r--', linewidth=2, label=f'Fit: ~N^{slope_s:.3f}')
axes[1,0].set_xlabel('Step count N')
axes[1,0].set_ylabel('Class Size at Rank 50')
axes[1,0].set_title(f'Size@50 Scaling: ~N^{slope_s:.3f}')
axes[1,0].legend()
axes[1,0].grid(True, alpha=0.3)

# Plot 4: Unique signatures vs N
axes[1,1].loglog(valid_n, valid_u, 's-', color='purple', linewidth=2, markersize=10, label='ESE unique signatures')
log_u_arr = np.log(valid_u)
slope_u, intercept_u = np.polyfit(log_n_arr, log_u_arr, 1)
axes[1,1].loglog(valid_n, np.exp(intercept_u + slope_u * log_n_arr), 'r--', linewidth=2, label=f'Fit: ~N^{slope_u:.3f}')
axes[1,1].set_xlabel('Step count N')
axes[1,1].set_ylabel('Unique Signature Count')
axes[1,1].set_title(f'Unique Signatures Scaling: ~N^{slope_u:.3f}')
axes[1,1].legend()
axes[1,1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('ese_fine_structure_verify.png', dpi=150)
print("\nChart saved: ese_fine_structure_verify.png")

# ============================================================
# Key conclusions
# ============================================================
print("\n" + "=" * 70)
print("KEY CONCLUSIONS")
print("=" * 70)
print(f"1. Stability: mean_ratio={mean_ratio:.6f}, 1/137={fine_const:.6f}")
print(f"   Deviation: {abs(mean_ratio-fine_const)/fine_const*100:.2f}%")
print(f"   CV: {std_ratio/mean_ratio*100:.2f}%")
print(f"   Verdict: {'STABLE' if std_ratio/mean_ratio < 0.05 else 'UNSTABLE'}")

print(f"\n2. Scaling: ratio ~ N^{slope_r:.4f}")
print(f"   Verdict: {'SCALE-INVARIANT' if abs(slope_r) < 0.1 else 'N-DEPENDENT'}")
print(f"   If scale-invariant: 1/137 is a TRUE emergent constant")
print(f"   If N-dependent: 1/137 is a finite-size approximation")

print(f"\n3. size@50 scaling: ~N^{slope_s:.3f}")
print(f"   unique scaling: ~N^{slope_u:.3f}")
print(f"   Theoretical: size ~ N/unique ~ N^{1-slope_u}")
theo_slope = 1 - slope_u
print(f"   Expected slope from N/unique: {theo_slope:.3f}")
print(f"   Empirical slope: {slope_s:.3f}")
print(f"   Match: {'YES' if abs(slope_s - theo_slope) < 0.1 else 'PARTIAL' if abs(slope_s - theo_slope) < 0.3 else 'NO'}")
