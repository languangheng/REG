# -*- coding: utf-8 -*-
import numpy as np
from collections import Counter

class ESE:
    def __init__(self, max_steps=50000, p_contain=0.5, depth_penalty=0.0):
        self.max_steps = max_steps
        self.p_contain = p_contain
        self.depth_penalty = depth_penalty
        self.signatures = [()]
        self.depths = [0]
        self.sig_to_id = {(): 0}
        self.sig_count = Counter()
        self.sig_count[()] = 1

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


target = 1.0 / 137.0
print("=" * 60)
print("Fine Structure Constant Stability (penalty=0.0, N=50K)")
print("=" * 60)
print(f"Target: 1/137 = {target:.6f}")
print()

rank50_ratios = []
rank50_sizes = []
for run in range(10):
    np.random.seed(42 + run * 100)
    ese = ESE(max_steps=50000, p_contain=0.5, depth_penalty=0.0)
    ese.run()
    cs = sorted(ese.sig_count.values(), reverse=True)
    total = sum(cs)
    n_uniq = len(cs)
    if n_uniq >= 50:
        r50 = cs[49] / total
        rank50_ratios.append(r50)
        rank50_sizes.append(cs[49])
        dev = abs(r50 - target) / target * 100
        print(f"Run {run+1}: unique={n_uniq:3d}, size50={cs[49]:5d}, ratio={r50:.6f}, dev={dev:.2f}%")
    else:
        print(f"Run {run+1}: unique={n_uniq:3d}, rank50 NOT AVAILABLE")

if rank50_ratios:
    mean = np.mean(rank50_ratios)
    std = np.std(rank50_ratios)
    mean_size = np.mean(rank50_sizes)
    print()
    print(f"Mean rank50 ratio: {mean:.6f} +/- {std:.6f}")
    print(f"Mean class size: {mean_size:.1f}")
    print(f"Mean dev from 1/137: {abs(mean-target)/target*100:.2f}%")
    print(f"Range: [{min(rank50_ratios):.6f}, {max(rank50_ratios):.6f}]")
    print(f"Range of sizes: [{min(rank50_sizes)}, {max(rank50_sizes)}]")

    # Also check: does 50^2 relate?
    print(f"\n50^2 = {50**2}")
    print(f"total/137 = {sum(rank50_sizes)/137:.1f} (total instances / 137)")
    print(f"mean_size50 * 137 = {mean_size * 137:.1f} (size50 * 137)")
