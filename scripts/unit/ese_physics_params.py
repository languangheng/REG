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


print("=" * 60)
print("Parameter Exploration: Physics Tests Feasibility")
print("=" * 60)

configs = [
    (50000, 0.5, 0.0),
    (50000, 0.5, 0.02),
    (50000, 0.5, 0.05),
]

for max_steps, p, pen in configs:
    np.random.seed(42)
    ese = EmptySetEmergence(max_steps=max_steps, p_contain=p, depth_penalty=pen)
    ese.run()
    cs = sorted(ese.sig_count.values(), reverse=True)
    dd = Counter(ese.depths)
    total = sum(cs)

    rank137_ok = len(cs) >= 137
    d123_ok = dd.get(1, 0) > 0 and dd.get(2, 0) > 0 and dd.get(3, 0) > 0

    print(f"\npenalty={pen:.2f}: unique={len(ese.signatures)}, max_depth={max(ese.depths)}")
    print(f"  Depth top-5: {dict(list(sorted(dd.items()))[:5])}")
    print(f"  Rank-137: {'OK' if rank137_ok else 'N/A'} (size={cs[136] if rank137_ok else 0}, ratio={cs[136]/total if rank137_ok else 0:.6f})")
    print(f"  Depth 1/2/3: {dd.get(1,0)}/{dd.get(2,0)}/{dd.get(3,0)} -> {'OK' if d123_ok else 'NOT OK'}")

# Best config for physics tests
print("\n" + "=" * 60)
print("Best Config for Physics Tests")
print("=" * 60)

# Use penalty=0.0 (max unique sigs) for physics tests
np.random.seed(42)
ese_best = EmptySetEmergence(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
ese_best.run()
cs = sorted(ese_best.sig_count.values(), reverse=True)
dd = Counter(ese_best.depths)
total = sum(cs)

print(f"\n[Using penalty=0.0 for physics tests]")
print(f"Total instances: {total:,}")
print(f"Unique signatures: {len(cs)}")
print(f"Max depth: {max(ese_best.depths)}")

# Test 1: Fine structure constant 1/137
print(f"\n[Test 1: Fine Structure Constant ~ 1/137 = {1/137:.6f}]")
target = 1.0 / 137.0
# Find rank where ratio matches
for rank in [1, 10, 50, 100, 137, 150, 200]:
    if rank <= len(cs):
        ratio = cs[rank-1] / total
        dev = abs(ratio - target) / target * 100
        marker = ' <-- BEST!' if dev < 5 else ''
        print(f"  Rank {rank:3d}: size={cs[rank-1]:6.0f}, ratio={ratio:.6f}, dev={dev:6.2f}%{marker}")

# Test 2: Three-generation fermion mass ratios
print(f"\n[Test 2: Three-Generation Fermion Mass Ratios]")
real_masses = np.array([0.511, 105.66, 1776.86])  # e, mu, tau in MeV
real_ratio = real_masses / real_masses[0]
print(f"Real lepton mass ratio (e=1): 1 : {real_ratio[1]:.2f} : {real_ratio[2]:.2f}")

# ESE depth-based mass
# Hypothesis: mass ~ 1 / (node_count at depth) * depth
# Or: mass ~ depth * ln(total / node_count_at_depth)
print(f"\nESE depth distribution:")
for d in range(5):
    nd = dd.get(d, 0)
    print(f"  depth={d}: {nd} nodes")

# Try mass ~ depth * log(1/fraction)
if dd.get(1, 0) > 0 and dd.get(2, 0) > 0 and dd.get(3, 0) > 0:
    f1 = dd.get(1, 0) / total
    f2 = dd.get(2, 0) / total
    f3 = dd.get(3, 0) / total
    # Mass estimate 1: proportional to depth, inverse to count
    m1 = 1 * (-np.log(f1 + 1e-10))
    m2 = 2 * (-np.log(f2 + 1e-10))
    m3 = 3 * (-np.log(f3 + 1e-10))
    m_norm = np.array([m1, m2, m3]) / m1
    print(f"\nMass estimate (depth * |ln(fraction)|):")
    print(f"  depth1: {1} * {abs(np.log(f1)):.2f} = {m1:.2f}")
    print(f"  depth2: {2} * {abs(np.log(f2)):.2f} = {m2:.2f}")
    print(f"  depth3: {3} * {abs(np.log(f3)):.2f} = {m3:.2f}")
    print(f"  ESE ratio (depth1=1): 1 : {m_norm[1]:.2f} : {m_norm[2]:.2f}")
    print(f"  Real ratio:          1 : {real_ratio[1]:.2f} : {real_ratio[2]:.2f}")

# Alternative: mass from class size at each depth
print(f"\nAlternative: mass ~ 1/class_size at each depth")
sig_to_depth = {sig: ese_best.depths[ese_best.sig_to_id[sig]] for sig in ese_best.sig_to_id}
depth_to_sizes = {}
for sig, cnt in ese_best.sig_count.items():
    d = sig_to_depth.get(sig, 0)
    if d not in depth_to_sizes:
        depth_to_sizes[d] = []
    depth_to_sizes[d].append(cnt)

for d in [1, 2, 3]:
    if d in depth_to_sizes:
        sizes = sorted(depth_to_sizes[d], reverse=True)
        top_size = sizes[0] if sizes else 0
        print(f"  depth={d}: top class size = {top_size}")

# Look at ln(class_size) as 'energy levels'
print(f"\n'Energy levels' from ln(class_size):")
for rank in [1, 2, 3]:
    if rank <= len(cs):
        e = np.log(cs[rank-1])
        print(f"  rank {rank}: ln(size) = {e:.4f}  (size = {cs[rank-1]})")
