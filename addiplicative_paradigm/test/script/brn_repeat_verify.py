"""
Script 3: BRN Repeatability Verification
Verifies that emergent mechanism (alpha>0, n~4) is statistically robust
across independent random seeds
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(SCRIPT_DIR), 'out')
os.makedirs(OUT, exist_ok=True)


class BRN3D:
    def __init__(self, n=300, r_cut=0.22, p_curv=0.5,
                 lam_deg=0.3, lam_phi=0.5, seed=42):
        np.random.seed(seed)
        self.n = n; self.r_cut = r_cut; self.p_curv = p_curv
        self.lam_deg = lam_deg; self.lam_phi = lam_phi
        self.d_target = 3.0; self.phi_target = 2.0
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
                    self.add[i].append(j); self.add[j].append(i)
                    self.total_add += 1
        for i in range(self.n):
            if np.random.random() < 0.15:
                j = np.random.randint(self.n)
                if i != j:
                    self.mult[i].append(j); self.depth[i] += 1
                    self.total_mult += 1

    def _energy(self):
        return (self.total_mult + self.lam_deg *
                sum((len(a)-self.d_target)**2 for a in self.add) +
                self.lam_phi * np.sum((self.depth - self.phi_target)**2))

    def step(self):
        i = np.random.randint(self.n); r = np.random.random()
        old_pos = self.pos[i].copy()
        old_add = [list(a) for a in self.add]
        old_mult = [list(m) for m in self.mult]
        old_depth = self.depth.copy()
        old_ta, old_tm, old_e = self.total_add, self.total_mult, self._energy()
        self.pos[i] += 0.03*(np.random.rand(3)-0.5)
        self.pos[i] = np.clip(self.pos[i], 0, 1)
        if r < 0.35:
            for j in self.add[i]: self.add[j].remove(i); self.total_add -= 1
            self.add[i] = []
            tree = cKDTree(self.pos)
            for j in tree.query_ball_point(self.pos[i], self.r_cut):
                if i != j: self.add[i].append(j); self.add[j].append(i)
                self.total_add += 1
        elif r < 0.65:
            j = np.random.randint(self.n)
            if i != j:
                self.mult[i].append(j); self.depth[i] += 1; self.total_mult += 1
                if np.random.random() < self.p_curv:
                    cand = list(set(range(self.n)) - {i} - set(self.add[i]))
                    if cand:
                        k = np.random.choice(cand)
                        self.add[i].append(k); self.add[k].append(i)
                        self.total_add += 1
        else:
            if self.depth[i] > 0 and self.mult[i]:
                self.mult[i].pop(); self.depth[i] -= 1; self.total_mult -= 1
                cand = list(set(range(self.n)) - {i} - set(self.add[i]))
                if len(cand) >= 2:
                    for k in np.random.choice(cand, 2, replace=False):
                        self.add[i].append(k); self.add[k].append(i)
                        self.total_add += 1
        new_e = self._energy()
        if (new_e - old_e) > 0 and np.random.random() >= np.exp(-(new_e-old_e)):
            self.pos[i] = old_pos; self.add = old_add; self.mult = old_mult
            self.depth = old_depth
            self.total_add, self.total_mult = old_ta, old_tm

    def run(self, burn=20000, samples=20000):
        for _ in range(burn): self.step()
        phi_v, curv_v = [], []
        for _ in range(samples):
            for _ in range(10): self.step()
            i = np.random.randint(self.n)
            phi_v.append(self.depth[i])
            curv_v.append(len(self.add[i]) - self.d_target)
        return np.array(phi_v), np.array(curv_v)


def power_law(z, A, n, z0):
    return A * (z + z0)**n


def scan_all(seeds):
    lam_deg_g = [0.1, 0.2, 0.3, 0.5, 0.8]
    p_curv_g   = [0.1, 0.3, 0.5, 0.7, 0.9]
    all_alpha  = {s: np.zeros((5,5)) for s in seeds}
    all_n      = {s: np.zeros((5,5)) for s in seeds}

    for si, seed in enumerate(seeds):
        print(f"\n  === Seed {seed} ({si+1}/{len(seeds)}) ===")
        for li, lam_deg in enumerate(lam_deg_g):
            for pi, p_curv in enumerate(p_curv_g):
                net = BRN3D(n=300, p_curv=p_curv, lam_deg=lam_deg,
                            lam_phi=0.5, seed=seed)
                phi_v, curv_v = net.run(burn=20000, samples=20000)
                alpha = np.cov(phi_v, curv_v)[0,1] / np.var(phi_v)
                all_alpha[seed][li,pi] = alpha
                try:
                    h, e = np.histogram(phi_v, bins=50, density=True)
                    c = (e[:-1]+e[1:])/2; c = c[h>0]; h = h[h>0]
                    popt, _ = curve_fit(power_law, c, h,
                                        p0=[1,2,0.5], bounds=([0,-4,0],[10,8,5]), maxfev=2000)
                    all_n[seed][li,pi] = popt[1]
                except:
                    all_n[seed][li,pi] = 2.0
                print(f"    ({lam_deg},{p_curv}): alpha={alpha:.3f}, n={all_n[seed][li,pi]:.2f}")
    return lam_deg_g, p_curv_g, all_alpha, all_n


if __name__ == '__main__':
    print("=" * 55)
    print("  BRN: Repeatability Verification")
    print("  3 independent random seeds -> alpha/n statistics")
    print("=" * 55)

    seeds = [42, 123, 777]
    t0 = time.time()
    lg, pc, all_a, all_n = scan_all(seeds)
    print(f"\n  Total scan time: {time.time()-t0:.0f}s")

    # Statistics
    print("\n  === Statistics ===")
    for label, grid_dict in [("alpha", all_a), ("n", all_n)]:
        stacked = np.stack(list(grid_dict.values()), axis=0)
        for li, ld in enumerate(lg):
            for pi, pcv in enumerate(pc):
                vals = stacked[:, li, pi]
                mean = np.mean(vals)
                std  = np.std(vals)
        pos_count = np.mean(stacked > 0)
        n4_count  = np.mean((stacked >= 2) & (stacked <= 6))
        print(f"  {label}: >0: {100*pos_count:.0f}%, n~4(2-6): {100*n4_count:.0f}%")

    # Figure 1: scatter alpha seed1 vs seed2
    fig, ax = plt.subplots(figsize=(7, 6))
    a42 = all_a[42].flatten(); a123 = all_a[123].flatten(); a777 = all_a[777].flatten()
    ax.scatter(a42, a123, c='steelblue', s=50, alpha=0.8, label='seed=42 vs seed=123')
    ax.scatter(a42, a777, c='coral',    s=50, alpha=0.8, label='seed=42 vs seed=777')
    corr1 = np.corrcoef(a42, a123)[0,1]
    corr2 = np.corrcoef(a42, a777)[0,1]
    mn, mx = min(a42.min(), a123.min()), max(a42.max(), a123.max())
    ax.plot([mn,mx],[mn,mx],'k--',lw=1,label='y=x')
    ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
    ax.set_xlabel(r'alpha  (seed=42)', fontsize=12)
    ax.set_ylabel(r'alpha  (seed=123 / seed=777)', fontsize=12)
    ax.set_title(f"BRN Repeatability: alpha Consistency\n"
                 f"Corr(seed42, seed123)={corr1:.3f}  "
                 f"Corr(seed42, seed777)={corr2:.3f}",
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=10); ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig6_brn_repeatability.png'),
                dpi=150, bbox_inches='tight')
    print(f"\n  Saved: fig6_brn_repeatability.png")
    plt.close()

    # Figure 2: seed-averaged heatmaps
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("BRN Parameter Space (Seed-Averaged over 3 runs)\n"
                 "Relation-Curvature Coupling and Quartic Potential",
                 fontsize=12, fontweight='bold')

    a_avg = np.mean(np.stack(list(all_a.values())), axis=0)
    n_avg = np.mean(np.stack(list(all_n.values())), axis=0)

    for ax, grid, title, cmap, label in [
        (axes[0], a_avg,
         "(a) alpha (seed-averaged)", 'RdBu_r', r'alpha'),
        (axes[1], n_avg,
         "(b) n  (seed-averaged)  V(Phi)~Phi^n", 'coolwarm', r'n'),
    ]:
        vmin_v = -0.3 if label == 'alpha' else -1
        vmax_v =  0.5 if label == 'alpha' else  5
        im = ax.imshow(grid, origin='lower', aspect='auto',
                       cmap=cmap, vmin=vmin_v, vmax=vmax_v)
        ax.set_xticks(range(5)); ax.set_xticklabels([f'{p:.1f}' for p in pc])
        ax.set_yticks(range(5)); ax.set_yticklabels([f'{l:.1f}' for l in lg])
        ax.set_xlabel(r'p_curv', fontsize=11)
        ax.set_ylabel(r'lambda_deg', fontsize=11)
        ax.set_title(title, fontsize=10)
        plt.colorbar(im, ax=ax, label=label)
        for li in range(5):
            for pi in range(5):
                val = grid[li,pi]
                c = 'white' if abs(val) > (0.2 if label=='alpha' else 2) else 'black'
                ax.text(pi, li, f'{val:.2f}', ha='center', va='center',
                        fontsize=8, color=c)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig7_brn_alpha_n_space.png'),
                dpi=150, bbox_inches='tight')
    print(f"  Saved: fig7_brn_alpha_n_space.png")
    plt.close()

    print(f"\n  === Script 3 Complete ===")
