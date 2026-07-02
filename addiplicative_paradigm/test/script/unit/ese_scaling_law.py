# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
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
print("ESE Scaling Law Study: alpha(N) vs N")
print("=" * 70)

# Step sizes
n_steps_list = [10000, 20000, 50000, 100000, 200000, 500000]
alpha_values = []
depth_values = []
unique_values = []

for n_steps in n_steps_list:
    np.random.seed(42)
    ese = EmptySetEmergence(max_steps=n_steps, p_contain=0.5, depth_penalty=0.12)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)

    ranks = np.arange(1, min(51, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:50]
    if len(sizes) >= 2:
        slope, _ = np.polyfit(np.log(ranks), np.log(sizes), 1)
    else:
        slope = 0.0

    max_depth = max(ese.depths) if ese.depths else 0
    unique_sigs = len(ese.signatures)

    alpha_values.append(slope)
    depth_values.append(max_depth)
    unique_values.append(unique_sigs)

    print(f"N={n_steps:>6} | alpha={slope:.4f}  | max_depth={max_depth:3d} | unique={unique_sigs:4d}")

# Also try different fitting ranges
print("\n" + "=" * 70)
print("Alpha with different fitting ranges")
print("=" * 70)
print(f"{'N':>8} | {'alpha_50':>10} | {'alpha_30':>10} | {'alpha_20':>10}")
print("-" * 50)

alpha_50_all = []
alpha_30_all = []
alpha_20_all = []

for n_steps in n_steps_list:
    np.random.seed(42)
    ese = EmptySetEmergence(max_steps=n_steps, p_contain=0.5, depth_penalty=0.12)
    ese.run()
    cs = sorted(ese.sig_count.values(), reverse=True)

    s50, _ = np.polyfit(np.log(np.arange(1, min(51, len(cs)+1))), np.log(cs[:50]), 1) if len(cs) >= 2 else (0, 0)
    s30, _ = np.polyfit(np.log(np.arange(1, min(31, len(cs)+1))), np.log(cs[:30]), 1) if len(cs) >= 2 else (0, 0)
    s20, _ = np.polyfit(np.log(np.arange(1, min(21, len(cs)+1))), np.log(cs[:20]), 1) if len(cs) >= 2 else (0, 0)

    alpha_50_all.append(s50)
    alpha_30_all.append(s30)
    alpha_20_all.append(s20)

    print(f"{n_steps:>8} | {s50:>10.4f} | {s30:>10.4f} | {s20:>10.4f}")

# Scaling law fitting
log_n = np.log(n_steps_list)
alpha_arr = np.array(alpha_values)
alpha_50_arr = np.array(alpha_50_all)
alpha_30_arr = np.array(alpha_30_all)
alpha_20_arr = np.array(alpha_20_all)

fit_slope, fit_intercept = np.polyfit(log_n, alpha_arr, 1)
fit_slope_50, fit_intercept_50 = np.polyfit(log_n, alpha_50_arr, 1)
fit_slope_30, fit_intercept_30 = np.polyfit(log_n, alpha_30_arr, 1)
fit_slope_20, fit_intercept_20 = np.polyfit(log_n, alpha_20_arr, 1)

r2 = np.corrcoef(log_n, alpha_arr)[0,1]**2

print("\n" + "=" * 70)
print("Scaling Law Fitting Results")
print("=" * 70)
print(f"Fitting range=50:")
print(f"  alpha(N) = {fit_intercept:.4f} + {fit_slope:.4f} * ln(N)")
print(f"  R^2 = {r2:.4f}")
print(f"  Interpretation: {'alpha grows more negative with N' if fit_slope < 0 else 'alpha converges'}")

print(f"\nFitting range=30:")
print(f"  alpha(N) = {fit_intercept_30:.4f} + {fit_slope_30:.4f} * ln(N)")
r2_30 = np.corrcoef(log_n, alpha_30_arr)[0,1]**2
print(f"  R^2 = {r2_30:.4f}")

print(f"\nFitting range=20:")
print(f"  alpha(N) = {fit_intercept_20:.4f} + {fit_slope_20:.4f} * ln(N)")
r2_20 = np.corrcoef(log_n, alpha_20_arr)[0,1]**2
print(f"  R^2 = {r2_20:.4f}")

# Extrapolation
n_extrap = np.array([1000000, 2000000, 5000000, 10000000])
log_n_extrap = np.log(n_extrap)
alpha_extrap_50 = fit_intercept_50 + fit_slope_50 * log_n_extrap
alpha_extrap_30 = fit_intercept_30 + fit_slope_30 * log_n_extrap
alpha_extrap_20 = fit_intercept_20 + fit_slope_20 * log_n_extrap

print(f"\nExtrapolation (fitting range=50):")
for n, a in zip(n_extrap, alpha_extrap_50):
    print(f"  N={n:>8,} -> alpha = {a:.4f}")

print(f"\nExtrapolation (fitting range=30):")
for n, a in zip(n_extrap, alpha_extrap_30):
    print(f"  N={n:>8,} -> alpha = {a:.4f}")

print(f"\nExtrapolation (fitting range=20):")
for n, a in zip(n_extrap, alpha_extrap_20):
    print(f"  N={n:>8,} -> alpha = {a:.4f}")

# Asymptotic analysis
if fit_slope < 0:
    print(f"\nAs N->inf: alpha -> -inf (unbounded)")
else:
    asymptotic = fit_intercept
    print(f"\nAs N->inf: alpha -> {asymptotic:.4f}")

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: alpha vs N (all ranges)
axes[0,0].semilogx(n_steps_list, alpha_20_all, 'o-', color='red', linewidth=2, markersize=8, label=f'range=20 (slope={fit_slope_20:.3f})')
axes[0,0].semilogx(n_steps_list, alpha_30_all, 's-', color='orange', linewidth=2, markersize=8, label=f'range=30 (slope={fit_slope_30:.3f})')
axes[0,0].semilogx(n_steps_list, alpha_50_all, 'o-', color='steelblue', linewidth=2, markersize=10, label=f'range=50 (slope={fit_slope_50:.3f})')
axes[0,0].axhline(-2.0, color='green', linestyle='--', alpha=0.7, label='Prime (-2.0)')
axes[0,0].axhline(-1.0, color='red', linestyle=':', alpha=0.3, label='Zipf (-1.0)')
axes[0,0].set_xlabel('Step count N')
axes[0,0].set_ylabel('Power Law Exponent alpha')
axes[0,0].set_title('Scaling Law: alpha(N) with Different Fitting Ranges')
axes[0,0].legend()
axes[0,0].grid(True, alpha=0.3)

# Plot 2: depth vs N
axes[0,1].loglog(n_steps_list, depth_values, 's-', color='purple', linewidth=2, markersize=10, label='Max depth')
axes[0,1].loglog(n_steps_list, unique_values, 'o-', color='teal', linewidth=2, markersize=10, label='Unique signatures')
# Fit power law for depth
log_d = np.log(depth_values)
log_u = np.log(unique_values)
slope_d, intercept_d = np.polyfit(log_n, log_d, 1)
slope_u, intercept_u = np.polyfit(log_n, log_u, 1)
axes[0,1].loglog(n_steps_list, np.exp(intercept_d + slope_d * log_n), 'r--', linewidth=2, label=f'Depth ~ N^{slope_d:.3f}')
axes[0,1].loglog(n_steps_list, np.exp(intercept_u + slope_u * log_n), 'g--', linewidth=2, label=f'Unique ~ N^{slope_u:.3f}')
axes[0,1].set_xlabel('Step count N')
axes[0,1].set_ylabel('Count')
axes[0,1].set_title(f'Depth & Unique Signatures vs N')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)

# Plot 3: alpha vs ln(N) linear fit (range=50)
axes[1,0].plot(log_n, alpha_50_arr, 'o', color='steelblue', markersize=12, label='Data')
axes[1,0].plot(log_n, fit_intercept_50 + fit_slope_50 * log_n, 'r-', linewidth=2, label=f'Fit: {fit_intercept_50:.3f} + {fit_slope_50:.3f}*ln(N)')
axes[1,0].axhline(-2.0, color='green', linestyle='--', alpha=0.7, label='Prime (-2.0)')
axes[1,0].set_xlabel('ln(N)')
axes[1,0].set_ylabel('alpha (range=50)')
axes[1,0].set_title(f'Linear Fit: alpha vs ln(N) (R^2={r2:.3f})')
axes[1,0].legend()
axes[1,0].grid(True, alpha=0.3)

# Plot 4: Extrapolation
axes[1,1].semilogx(n_steps_list, alpha_50_all, 'o-', color='steelblue', linewidth=2, markersize=10, label='Measured')
axes[1,1].semilogx(n_extrap, alpha_extrap_50, 's-', color='orange', markersize=8, label='Extrapolated')
axes[1,1].axhline(-2.0, color='green', linestyle='--', alpha=0.7, label='Prime (-2.0)')
axes[1,1].axhline(-3.0, color='red', linestyle=':', alpha=0.5, label='Strong concentration (-3.0)')
axes[1,1].set_xlabel('N')
axes[1,1].set_ylabel('alpha')
axes[1,1].set_title('Extrapolation: alpha(N) for larger N')
axes[1,1].legend()
axes[1,1].grid(True, alpha=0.3)
axes[1,1].set_xlim(5000, 20000000)

plt.tight_layout()
plt.savefig('ese_scaling_law.png', dpi=150)
print("\nChart saved: ese_scaling_law.png")

# Summary
print("\n" + "=" * 70)
print("SUMMARY: Scaling Law Interpretation")
print("=" * 70)
print(f"Depth scaling: D ~ N^{slope_d:.4f}  (max_depth / unique ~ N^{slope_u-slope_d:.4f})")
print(f"Alpha scaling (range=50): alpha = {fit_intercept_50:.4f} + {fit_slope_50:.4f} * ln(N)")
print(f"Alpha scaling (range=30): alpha = {fit_intercept_30:.4f} + {fit_slope_30:.4f} * ln(N)")
print(f"Alpha scaling (range=20): alpha = {fit_intercept_20:.4f} + {fit_slope_20:.4f} * ln(N)")
if fit_slope_50 < 0:
    print("\n[PHYSICS] alpha becomes more negative as N grows -> increasing concentration")
    print("[PHYSICS] The system develops stronger hierarchy as it grows larger")
    print("[PHYSICS] At N=1M: alpha ~ {:.2f} (extrapolated)".format(alpha_extrap_50[0]))
else:
    print("\n[PHYSICS] alpha converges to {:.2f} as N grows".format(fit_intercept_50))
