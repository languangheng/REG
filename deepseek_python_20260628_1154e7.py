import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import time

class FastNetwork:
    """精简版乘-加网络，用于快速规模扫描"""
    def __init__(self, n_nodes=200, lam_deg=0.3, p_curv=0.5, seed=42):
        np.random.seed(seed)
        self.n = n_nodes
        self.lam_deg = lam_deg
        self.p_curv = p_curv
        self.d0 = 3.0

        self.add = [[] for _ in range(n_nodes)]
        self.mult = [[] for _ in range(n_nodes)]
        self.depth = np.zeros(n_nodes)

        self.ga = 0.8
        self.gm = 1.0
        self.lam_phi = 0.3
        self.phi0 = 2.0

        self.total_add = 0
        self.total_mult = 0
        self._init()

    def _init(self):
        for i in range(self.n):
            for _ in range(np.random.randint(2, 5)):
                j = np.random.randint(self.n)
                if i != j and j not in self.add[i]:
                    self.add[i].append(j)
                    self.add[j].append(i)
                    self.total_add += 1
            if np.random.random() < 0.15:
                j = np.random.randint(self.n)
                if i != j:
                    self.mult[i].append(j)
                    self.depth[i] += 1
                    self.total_mult += 1

    def _energy(self):
        deg_pen = self.lam_deg * sum((len(a)-self.d0)**2 for a in self.add)
        phi_pen = self.lam_phi * sum((d-self.phi0)**2 for d in self.depth)
        return self.ga*self.total_add + self.gm*self.total_mult + deg_pen + phi_pen

    def _backup(self):
        return ([list(a) for a in self.add], [list(m) for m in self.mult],
                self.depth.copy(), self.total_add, self.total_mult, self._energy())

    def _restore(self, state):
        self.add, self.mult, self.depth, self.total_add, self.total_mult, _ = state

    def step(self):
        i = np.random.randint(self.n)
        r = np.random.random()
        old = self._backup()
        if r < 0.35:
            j = np.random.randint(self.n)
            if i!=j and j not in self.add[i]:
                self.add[i].append(j); self.add[j].append(i)
                self.total_add += 1
        elif r < 0.65:
            j = np.random.randint(self.n)
            if i!=j:
                self.mult[i].append(j); self.depth[i] += 1
                self.total_mult += 1
                if np.random.random() < self.p_curv:
                    cand = [k for k in range(self.n) if k!=i and k not in self.add[i]]
                    if cand:
                        k = np.random.choice(cand)
                        self.add[i].append(k); self.add[k].append(i)
                        self.total_add += 1
        else:
            if self.depth[i] > 0 and self.mult[i]:
                self.mult[i].pop(); self.depth[i] -= 1
                self.total_mult -= 1
                cand = [k for k in range(self.n) if k!=i and k not in self.add[i]]
                if len(cand) >= 2:
                    for k in np.random.choice(cand, 2, replace=False):
                        self.add[i].append(k); self.add[k].append(i)
                        self.total_add += 1
        new_e = self._energy()
        delta = new_e - old[5]
        if delta > 0 and np.random.random() >= np.exp(-delta):
            self._restore(old)

    def measure(self, n_samples=40, burn_in=2000):
        """运行模拟并测量 α 和势能指数 n"""
        for _ in range(burn_in): self.step()
        phis = np.zeros(n_samples)
        curvs = np.zeros(n_samples)
        for s in range(n_samples):
            for _ in range(20): self.step()
            i = np.random.randint(self.n)
            seen = {i}; front = [i]
            for _ in range(1):
                nf = []
                for v in front:
                    for nb in self.add[v]:
                        if nb not in seen: seen.add(nb); nf.append(nb)
                front = nf
            phis[s] = np.mean([self.depth[v] for v in seen])
            deg = sum(len(self.add[v]) for v in seen)//2
            curvs[s] = deg/len(seen) - self.d0
        alpha = np.corrcoef(phis, curvs)[0,1] * np.std(curvs)/np.std(phis) if np.std(phis)>0 else 0
        hist, bins = np.histogram(phis, bins=10, density=True)
        centers = (bins[:-1]+bins[1:])/2
        prob = np.clip(hist/hist.sum(), 1e-10, None)
        V = -np.log(prob); V -= V.min()
        mask = centers > 0.01
        try:
            popt, _ = curve_fit(lambda x,v,n: v*np.abs(x)**n, centers[mask], V[mask], p0=[1.0,2.0])
            n_exp = popt[1]
        except:
            n_exp = np.nan
        return alpha, n_exp


# ========================== 规模扫描 ==========================
node_sizes = [100, 200, 300, 500, 800]   # 不同规模
lam_deg_fixed = 0.3
p_curv_fixed = 0.5

print("规模扫描：节点数从 100 到 800")
print("-" * 50)

alpha_vals = []
n_vals = []
times = []

for n_nodes in node_sizes:
    start = time.time()
    net = FastNetwork(n_nodes=n_nodes, lam_deg=lam_deg_fixed, p_curv=p_curv_fixed, seed=42)
    a, n_idx = net.measure(n_samples=40, burn_in=2000)
    elapsed = time.time() - start
    alpha_vals.append(a)
    n_vals.append(n_idx)
    times.append(elapsed)
    print(f"节点数:{n_nodes:>4d}  α={a:+.3f}  n={n_idx:.2f}  耗时:{elapsed:.1f}s")

# ========================== 可视化 ==========================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].plot(node_sizes, alpha_vals, 'o-', color='coral', linewidth=2, markersize=10)
axes[0].axhline(0, color='gray', linestyle='--')
axes[0].set_xlabel('Number of nodes')
axes[0].set_ylabel('Coupling α')
axes[0].set_title('Multiplication–curvature coupling vs network size')

axes[1].plot(node_sizes, n_vals, 's-', color='steelblue', linewidth=2, markersize=10)
axes[1].axhline(4.0, color='gray', linestyle='--', label='Target: V∝Φ⁴')
axes[1].set_xlabel('Number of nodes')
axes[1].set_ylabel('Potential index n')
axes[1].set_title('Effective potential exponent vs network size')
axes[1].legend()

plt.tight_layout()
plt.savefig('scale_scan.png', dpi=150)
plt.show()

# 打印汇总
print("\n===== 汇总 =====")
print(f"α 范围: {min(alpha_vals):+.3f} ~ {max(alpha_vals):+.3f}")
print(f"n 范围: {min(n_vals):.2f} ~ {max(n_vals):.2f}")
print(f"总耗时: {sum(times):.0f} 秒")