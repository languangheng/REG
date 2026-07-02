# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

class EmptySetEmergence:
    def __init__(self, max_steps=500000, p_contain=0.5, depth_penalty=0.12):
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
print("ESE 大样本验证：50万步，penalty=0.12，5次独立运行")
print("=" * 70)

all_results = []
all_prime_sigs = []

for run_id in range(5):
    seed = 42 + run_id * 100
    np.random.seed(seed)

    ese = EmptySetEmergence(max_steps=500000, p_contain=0.5, depth_penalty=0.12)
    ese.run()

    class_sizes = list(ese.sig_count.values())
    class_sizes_sorted = sorted(class_sizes, reverse=True)

    ranks = np.arange(1, min(101, len(class_sizes_sorted)+1))
    sizes = class_sizes_sorted[:100]
    slope, _ = np.polyfit(np.log(ranks), np.log(sizes), 1)

    prime_sigs = [sig for sig, count in ese.sig_count.items() if count == 1]
    prime_hashes = [hash(str(sig)) % 10000 for sig in prime_sigs]
    prime_hashes_sorted = sorted(set(prime_hashes))

    all_results.append({
        'run': run_id + 1,
        'slope': slope,
        'max_depth': max(ese.depths),
        'unique_sigs': len(ese.signatures),
        'prime_count': len(prime_sigs),
        'prime_hashes': prime_hashes_sorted,
        'prime_sigs': prime_sigs,
    })

    all_prime_sigs.extend(prime_hashes_sorted)

    print(f"Run {run_id+1}: alpha={slope:.4f}  dev={abs(slope+2.0):.4f}  "
          f"max_d={max(ese.depths)}  unique={len(ese.signatures)}  irreducible={len(prime_sigs)}")

# Statistics
slopes = [r['slope'] for r in all_results]
mean_slope = np.mean(slopes)
std_slope = np.std(slopes)

print("\n" + "=" * 70)
print("Stability Statistics (50K steps, penalty=0.12)")
print("=" * 70)
print(f"Mean alpha = {mean_slope:.4f}")
print(f"Std dev    = {std_slope:.4f}")
print(f"Dev from -2.0 = {abs(mean_slope + 2.0):.4f}")
if std_slope < 0.1 and abs(mean_slope + 2.0) < 0.1:
    print("[CONFIRMED] alpha=-2.0 is stable across 5 independent runs!")
elif std_slope < 0.2:
    print("[OK] alpha=-2.0 is reasonably stable (std < 0.2)")
else:
    print("[NOTE] alpha shows significant variation across runs")

# Irreducible structure analysis
print("\n" + "=" * 70)
print("Irreducible Structure Analysis")
print("=" * 70)

# Count irreducible by run
for r in all_results:
    print(f"  Run {r['run']}: {r['prime_count']} irreducible signatures out of {r['unique_sigs']} unique")

total_prime = sum(r['prime_count'] for r in all_results)
print(f"\nTotal irreducible across all runs: {total_prime}")

# Detailed irreducible signatures from first run
print("\nIrreducible signatures (Run 1, first 20):")
r1 = all_results[0]
for i, sig in enumerate(sorted(r1['prime_sigs'], key=lambda s: len(str(s)))):
    depth = 0
    s = sig
    while isinstance(s, tuple) and len(s) > 0:
        depth += 1
        s = s[0]
    print(f"  {i+1:2d}. sig={str(sig):<30s} depth={depth}")

# Prime number comparison
real_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
               73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
               157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229]
real_prime_mod = [p % 10000 for p in real_primes]

all_hashes = []
for r in all_results:
    all_hashes.extend(r['prime_hashes'])
hash_counter = Counter(all_hashes)
common_hashes = hash_counter.most_common(50)

print(f"\nAll irreducible hash values: {len(all_hashes)} total, {len(hash_counter)} unique")
print(f"\nTop 20 most common irreducible hashes:")
for h, c in common_hashes[:20]:
    print(f"  {h:5d}: appears {c} times")

# Intersection with primes mod 10000
ese_set = set([h for h, c in common_hashes[:50]])
prime_set = set(real_prime_mod)
intersection = ese_set & prime_set
print(f"\nESE irreducible hashes (top 50) vs real primes mod 10000:")
print(f"  Intersection size: {len(intersection)}")
if intersection:
    print(f"  Intersection: {sorted(intersection)}")
    print(f"  [MATCH] Found overlap between ESE irreducible and prime numbers!")
else:
    # Try different modulus
    print(f"  [NOTE] No direct intersection. Trying mod 1000...")
    real_pm = [p % 1000 for p in real_primes]
    ese_pm = set([h % 1000 for h, c in common_hashes[:50]])
    inter_pm = ese_pm & set(real_pm)
    print(f"  Intersection size (mod 1000): {len(inter_pm)}")
    if inter_pm:
        print(f"  Intersection: {sorted(inter_pm)}")

# Depth distribution of irreducible structures
print(f"\nIrreducible structure depth distribution (Run 1):")
depth_irred = {}
for sig in r1['prime_sigs']:
    depth = 0
    s = sig
    while isinstance(s, tuple) and len(s) > 0:
        depth += 1
        s = s[0]
    depth_irred[depth] = depth_irred.get(depth, 0) + 1
for d in sorted(depth_irred.keys()):
    print(f"  depth={d}: {depth_irred[d]} irreducible structures")

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Alpha stability
axes[0,0].bar(range(1, 6), slopes, color='steelblue', edgecolor='white', alpha=0.8)
axes[0,0].axhline(mean_slope, color='blue', linestyle='-', linewidth=2, label=f'Mean={mean_slope:.4f}')
axes[0,0].axhline(-2.0, color='green', linestyle='--', linewidth=2, label='Target (-2.0)')
axes[0,0].fill_between([0, 6], mean_slope-std_slope, mean_slope+std_slope, alpha=0.2, color='blue')
axes[0,0].set_xlabel('Run')
axes[0,0].set_ylabel('alpha')
axes[0,0].set_title('Alpha Stability: 5 runs, 500K steps, penalty=0.12')
axes[0,0].legend()
axes[0,0].set_xticks(range(1, 6))
axes[0,0].set_ylim(-2.3, -1.5)

# Plot 2: Class size distribution
r_best = all_results[np.argmin([abs(s+2.0) for s in slopes])]
ese_best = EmptySetEmergence(max_steps=500000, p_contain=0.5, depth_penalty=0.12)
np.random.seed(42)
ese_best.run()
cs_sorted = sorted(ese_best.sig_count.values(), reverse=True)
ranks = np.arange(1, len(cs_sorted)+1)
axes[0,1].loglog(ranks, cs_sorted, 'b-', linewidth=1, alpha=0.7, label='ESE class sizes')
axes[0,1].loglog(ranks, cs_sorted[0]/ranks, 'r--', linewidth=2, label='Zipf (1/r)')
axes[0,1].set_xlabel('Rank')
axes[0,1].set_ylabel('Class Size')
axes[0,1].set_title(f'Class Size Distribution (alpha~{mean_slope:.3f})')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)

# Plot 3: Depth distribution of all nodes
depth_dist = Counter(ese_best.depths)
max_d = max(depth_dist.keys())
d_vals = list(range(max_d+1))
d_counts = [depth_dist.get(d, 0) for d in d_vals]
axes[1,0].bar(d_vals, d_counts, color='coral', edgecolor='white', alpha=0.7)
axes[1,0].set_xlabel('Depth')
axes[1,0].set_ylabel('Node Count')
axes[1,0].set_title('Depth Distribution (50K steps, penalty=0.12)')
axes[1,0].set_yscale('log')

# Plot 4: Irreducible by depth
depth_irred_vals = list(depth_irred.keys())
depth_irred_counts = list(depth_irred.values())
axes[1,1].bar(depth_irred_vals, depth_irred_counts, color='darkgreen', edgecolor='white')
axes[1,1].set_xlabel('Depth')
axes[1,1].set_ylabel('Irreducible Count')
axes[1,1].set_title('Irreducible Structures by Depth (Run 1)')

plt.tight_layout()
plt.savefig('ese_large_sample_verify.png', dpi=150)
print("\nChart saved: ese_large_sample_verify.png")
