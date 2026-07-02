"""
Script 2: BRN Nested Depth Distribution
Measures the distribution of multiplicative nesting depth (⊗-generations)
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(SCRIPT_DIR), 'out')
os.makedirs(OUT, exist_ok=True)


class BRN3D:
    def __init__(self, n=500, r_cut=0.22, p_curv=0.5, lam_phi=0.5, seed=42):
        np.random.seed(seed)
        self.n = n
        self.r_cut = r_cut
        self.p_curv = p_curv
        self.lam_phi = lam_phi
        self.phi_target = 2.0
        self.pos = np.random.rand(n, 3)
        self.add = [[] for _ in range(n)]
        self.mult = [[] for _ in range(n)]
        self.depth = np.zeros(n)
        self.total_add, self.total_mult = 0, 0
        self._init_edges()

    def _init_edges(self):
        tree = cKDTree(self.pos)
        for i in range(self.n):
            nbrs = tree.query_ball_point(self.pos[i], self.r_cut)
            for j in nbrs:
                if i < j:
                    self.add[i].append(j)
                    self.add[j].append(i)
                    self.total_add += 1
        for i in range(self.n):
            if np.random.random() < 0.15:
                j = np.random.randint(self.n)
                if i != j:
                    self.mult[i].append(j)
                    self.depth[i] += 1
                    self.total_mult += 1

    def _energy(self):
        return self.total_mult + self.lam_phi * np.sum((self.depth - self.phi_target)**2)

    def step(self):
        i = np.random.randint(self.n)
        r = np.random.random()
        old_pos = self.pos[i].copy()
        old_add = [list(a) for a in self.add]
        old_mult = [list(m) for m in self.mult]
        old_depth = self.depth.copy()
        old_ta, old_tm, old_e = self.total_add, self.total_mult, self._energy()
        self.pos[i] += 0.03 * (np.random.rand(3) - 0.5)
        self.pos[i] = np.clip(self.pos[i], 0, 1)
        if r < 0.35:
            for j in self.add[i]:
                self.add[j].remove(i)
                self.total_add -= 1
            self.add[i] = []
            tree = cKDTree(self.pos)
            for j in tree.query_ball_point(self.pos[i], self.r_cut):
                if i != j:
                    self.add[i].append(j)
                    self.add[j].append(i)
                    self.total_add += 1
        elif r < 0.65:
            j = np.random.randint(self.n)
            if i != j:
                self.mult[i].append(j)
                self.depth[i] += 1
                self.total_mult += 1
                if np.random.random() < self.p_curv:
                    cand = list(set(range(self.n)) - {i} - set(self.add[i]))
                    if cand:
                        k = np.random.choice(cand)
                        self.add[i].append(k)
                        self.add[k].append(i)
                        self.total_add += 1
        else:
            if self.depth[i] > 0 and self.mult[i]:
                self.mult[i].pop()
                self.depth[i] -= 1
                self.total_mult -= 1
                cand = list(set(range(self.n)) - {i} - set(self.add[i]))
                if len(cand) >= 2:
                    for k in np.random.choice(cand, 2, replace=False):
                        self.add[i].append(k)
                        self.add[k].append(i)
                        self.total_add += 1
        new_e = self._energy()
        if (new_e - old_e) > 0 and np.random.random() >= np.exp(-(new_e - old_e)):
            self.pos[i] = old_pos
            self.add = old_add
            self.mult = old_mult
            self.depth = old_depth
            self.total_add, self.total_mult = old_ta, old_tm

    def run(self, burn=3000, samples=200):
        for _ in range(burn):
            self.step()
        depths = []
        for _ in range(samples):
            for _ in range(20):
                self.step()
            depths.extend(self.depth.tolist())
        return np.array(depths)


if __name__ == '__main__':
    print("=" * 55)
    print("  BRN: Multiplicative Nesting Depth Distribution")
    print("  Distribution of dependence-nesting depth (⊗-generations)")
    print("=" * 55)
    start = time.time()
    net = BRN3D(n=500, seed=123)
    depths = net.run(burn=3000, samples=200)
    elapsed = time.time() - start
    print(f"N_samples = {len(depths)},  Wall time = {elapsed:.1f}s")

    unique, counts = np.unique(depths.astype(int), return_counts=True)
    print("\nNesting depth distribution:")
    for d, c in zip(unique, counts):
        print(f"  d = {d:2d}:  count = {c:4d}  ({100.0*c/len(depths):.1f}%)")

    hist, bin_edges = np.histogram(depths, bins=max(10, len(unique)*2))
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    peaks, props = find_peaks(hist, height=max(hist)*0.05, distance=1)
    peak_heights = hist[peaks]
    sorted_idx = np.argsort(peak_heights)[::-1]
    top_peaks = peaks[sorted_idx]
    print(f"\nDetected {len(peaks)} peaks. Top 3:")
    for rank, p in enumerate(top_peaks[:3]):
        print(f"  Rank {rank+1}: depth = {centers[p]:.1f}, height = {hist[p]:.0f}")

    # Figure 1: bar chart with peaks
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(unique, counts, width=0.8, color='steelblue', edgecolor='white', alpha=0.85)
    for p in top_peaks:
        ax.axvline(centers[p], color='red', linestyle='--', linewidth=1.5)
        ax.text(centers[p], hist[p] + 50, f'd={centers[p]:.0f}',
                ha='center', va='bottom', fontsize=9, color='red')
    ax.set_xlabel(r'Multiplicative Nesting Depth $d$', fontsize=12)
    ax.set_ylabel(r'Count', fontsize=12)
    ax.set_title("BRN: Nesting Depth Distribution (Dependence Generations)",
                 fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig3_brn_depth_distribution.png'),
                dpi=150, bbox_inches='tight')
    print(f"\nSaved: fig3_brn_depth_distribution.png")
    plt.close()

    # Figure 2: histogram with CDF overlay
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.suptitle("BRN Depth Statistics", fontsize=13, fontweight='bold')

    axes[0].hist(depths, bins=max(10, len(unique)*2),
                 color='steelblue', edgecolor='white', alpha=0.8, density=True)
    axes[0].set_xlabel(r'Nesting depth $d$', fontsize=11)
    axes[0].set_ylabel(r'Density $P(d)$', fontsize=11)
    axes[0].set_title('(a) Probability Density', fontsize=11)
    axes[0].grid(alpha=0.3)

    sorted_depths = np.sort(depths)
    cdf = np.arange(1, len(sorted_depths) + 1) / len(sorted_depths)
    axes[1].plot(sorted_depths, cdf, 'steelblue', linewidth=2)
    axes[1].axhline(0.5, color='gray', linewidth=0.8, linestyle=':')
    med = np.median(depths)
    axes[1].axvline(med, color='red', linewidth=1.2, linestyle='--',
                    label=f'median = {med:.1f}')
    axes[1].set_xlabel(r'Nesting depth $d$', fontsize=11)
    axes[1].set_ylabel(r'CDF $F(d)$', fontsize=11)
    axes[1].set_title('(b) Cumulative Distribution Function', fontsize=11)
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig4_brn_depth_cdf.png'),
                dpi=150, bbox_inches='tight')
    print(f"Saved: fig4_brn_depth_cdf.png")
    plt.close()

    print(f"\nStatistics:")
    print(f"  mean = {np.mean(depths):.3f}")
    print(f"  median = {np.median(depths):.3f}")
    print(f"  std = {np.std(depths):.3f}")
    print(f"  min = {np.min(depths):.1f},  max = {np.max(depths):.1f}")
    print(f"  P(d=2) = {100.0*np.sum(depths==2)/len(depths):.1f}%")
    print(f"\n  === Script 2 Complete ===")
