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


print("=" * 60)
print("ESE Physical Constants: Conceptual Verification")
print("=" * 60)

all_rank137_ratios = []
all_depth_counts = []
all_class_distributions = []

for run_id in range(5):
    seed = 42 + run_id * 100
    np.random.seed(seed)

    ese = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.12)
    ese.run()

    # Class size distribution
    class_sizes_sorted = sorted(ese.sig_count.values(), reverse=True)
    total_instances = sum(class_sizes_sorted)

    # Rank 137
    if len(class_sizes_sorted) >= 137:
        rank137_size = class_sizes_sorted[136]
        rank137_ratio = rank137_size / total_instances
        all_rank137_ratios.append(rank137_ratio)
    else:
        rank137_ratio = None

    # Depth distribution
    depth_dist = Counter(ese.depths)
    n_depth0 = depth_dist.get(0, 0)
    n_depth1 = depth_dist.get(1, 0)
    n_depth2 = depth_dist.get(2, 0)
    n_depth3 = depth_dist.get(3, 0)
    n_depth4 = depth_dist.get(4, 0)

    all_depth_counts.append({
        0: n_depth0, 1: n_depth1, 2: n_depth2,
        3: n_depth3, 4: n_depth4
    })
    all_class_distributions.append({
        'sorted': class_sizes_sorted,
        'total': total_instances,
        'unique': len(class_sizes_sorted)
    })

    print(f"\nRun {run_id+1}: unique sigs={len(class_sizes_sorted)}, total instances={total_instances}")
    if rank137_ratio:
        print(f"  Rank-137 ratio: {rank137_ratio:.6f}  (1/137 = {1/137:.6f}, dev={abs(rank137_ratio-1/137)/(1/137)*100:.1f}%)")
    else:
        print(f"  Rank-137: NOT FOUND (only {len(class_sizes_sorted)} unique signatures)")
    print(f"  Depth 0/1/2/3/4: {n_depth0}/{n_depth1}/{n_depth2}/{n_depth3}/{n_depth4}")
    print(f"  Top-5 class sizes: {class_sizes_sorted[:5]}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

# Verification 1: Fine structure constant
target_137 = 1.0 / 137.0
if all_rank137_ratios:
    avg_ratio = np.mean(all_rank137_ratios)
    print(f"\n[Fine Structure Constant: 1/137 = {target_137:.6f}]")
    print(f"  Run results:")
    for i, r in enumerate(all_rank137_ratios):
        print(f"    Run {i+1}: {r:.6f}  (dev={abs(r-target_137)/target_137*100:.1f}%)")
    print(f"  Average: {avg_ratio:.6f}")
    print(f"  Relative deviation: {abs(avg_ratio-target_137)/target_137*100:.1f}%")
    print(f"  [COMMENT] {'Match found!' if abs(avg_ratio-target_137)/target_137 < 0.1 else 'No match in current simulation'}")
else:
    print(f"\n[Fine Structure Constant] NOT TESTABLE: insufficient unique signatures")

# Verification 2: Three-generation fermion mass ratios
# Lepton masses: electron=0.511MeV, muon=105.66MeV, tau=1776.86MeV
real_masses = np.array([0.511, 105.66, 1776.86])
# In ESE: nodes at deeper levels are "heavier" (less frequent)
# So mass ~ 1/frequency ~ 1/n_depth
# But we need to compare within the same generation level

# Get average depth counts
avg_d = {k: np.mean([dc[k] for dc in all_depth_counts]) for k in [0,1,2,3,4]}
print(f"\n[Three-Generation Fermion Mass Ratios]")
print(f"  Average depth distribution: d0={avg_d[0]:.0f}, d1={avg_d[1]:.0f}, d2={avg_d[2]:.0f}, d3={avg_d[3]:.0f}, d4={avg_d[4]:.0f}")

# ESE depth mass ratio (deeper = heavier)
if avg_d[1] > 0 and avg_d[2] > 0 and avg_d[3] > 0:
    # Define mass ~ 1/depth_count (more nodes = lighter)
    ese_mass_d1 = 1.0 / avg_d[1]
    ese_mass_d2 = 1.0 / avg_d[2]
    ese_mass_d3 = 1.0 / avg_d[3]
    ese_mass_ratio = np.array([ese_mass_d1, ese_mass_d2, ese_mass_d3])
    ese_mass_ratio_norm = ese_mass_ratio / ese_mass_ratio[0]

    # Real mass ratio (electron, muon, tau)
    real_ratio = real_masses / real_masses[0]

    print(f"\n  ESE mass estimate (1/nodes):")
    print(f"    depth1 -> 1/{avg_d[1]:.0f} = {ese_mass_d1:.6f}")
    print(f"    depth2 -> 1/{avg_d[2]:.0f} = {ese_mass_d2:.6f}")
    print(f"    depth3 -> 1/{avg_d[3]:.0f} = {ese_mass_d3:.6f}")
    print(f"  ESE mass ratio (depth1=1): 1 : {ese_mass_ratio_norm[1]:.2f} : {ese_mass_ratio_norm[2]:.2f}")
    print(f"  Real lepton mass ratio (e=1): 1 : {real_ratio[1]:.2f} : {real_ratio[2]:.2f}")

    # Try reversed: deeper = lighter (mass ~ depth_count * depth)
    print(f"\n  Alternative: mass ~ depth * log(nodes)")
    for d in [1, 2, 3]:
        m_est = d * np.log(avg_d[d] + 1)
        print(f"    depth {d}: mass ~ {d} * ln({avg_d[d]:.0f}) = {m_est:.2f}")
    m_est_arr = np.array([d * np.log(avg_d[d] + 1) for d in [1, 2, 3]])
    m_norm = m_est_arr / m_est_arr[0]
    print(f"  Ratio (depth=1): 1 : {m_norm[1]:.2f} : {m_norm[2]:.2f}")
    print(f"  Real ratio:      1 : {real_ratio[1]:.2f} : {real_ratio[2]:.2f}")

# Additional analysis: top-ranked class sizes
print(f"\n[Class Size Distribution Analysis]")
all_sorted = all_class_distributions[0]['sorted']
print(f"  Total instances: {all_class_distributions[0]['total']:,}")
print(f"  Unique signatures: {all_class_distributions[0]['unique']}")
print(f"  Top-10 class sizes: {all_sorted[:10]}")
print(f"  Rank-137 check: ", end="")
if len(all_sorted) >= 137:
    print(f"size={all_sorted[136]}, ratio={all_sorted[136]/all_class_distributions[0]['total']:.6f}")
else:
    print(f"NOT REACHABLE (only {len(all_sorted)} unique sigs)")

# Let's also check what happens if we use natural logarithms of class sizes
print(f"\n[Class Size as 'Energy Levels']")
for rank in [1, 2, 3, 10, 50, 100]:
    if rank <= len(all_sorted):
        size = all_sorted[rank-1]
        ln_size = np.log(size)
        print(f"  Rank {rank:3d}: size={size:6.0f}, ln(size)={ln_size:.4f}")
