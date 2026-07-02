import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import time

class ScanNetwork:
    """参数扫描用乘-加网络（精简版，加快扫描速度）"""
    
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
            for _ in range(np.random.randint(2,5)):
                j = np.random.randint(self.n)
                if i!=j and j not in self.add[i]:
                    self.add[i].append(j)
                    self.add[j].append(i)
                    self.total_add += 1
            if np.random.random() < 0.15:
                j = np.random.randint(self.n)
                if i!=j:
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
    
    def measure(self, n_samples=50):
        """运行模拟并测量α和势能指数"""
        for _ in range(3000): self.step()  # 热化
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
        
        # α：线性耦合强度
        alpha = np.corrcoef(phis, curvs)[0,1] * np.std(curvs)/np.std(phis) if np.std(phis)>0 else 0
        
        # 势能指数：拟合 -ln P(Φ)
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


# ============================================================
# 参数扫描主程序
# ============================================================
print("乘-加网络参数扫描：λ_deg vs p_curv")
print("=" * 50)

lam_range = [0.1, 0.2, 0.3, 0.5, 0.8]
pcurv_range = [0.1, 0.3, 0.5, 0.7, 0.9]

alpha_grid = np.zeros((len(lam_range), len(pcurv_range)))
n_grid = np.zeros((len(lam_range), len(pcurv_range)))

for i, lam in enumerate(lam_range):
    for j, pc in enumerate(pcurv_range):
        print(f"扫描: λ_deg={lam}, p_curv={pc} ...", end=" ")
        net = ScanNetwork(n_nodes=200, lam_deg=lam, p_curv=pc, seed=42)
        a, n = net.measure(n_samples=50)
        alpha_grid[i,j] = a
        n_grid[i,j] = n
        print(f"α={a:.3f}, n={n:.2f}")

# 可视化
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,5))

im1 = ax1.imshow(alpha_grid, origin='lower', cmap='RdBu_r', aspect='auto',
                 extent=[pcurv_range[0], pcurv_range[-1], lam_range[0], lam_range[-1]])
ax1.set_xlabel('p_curv'); ax1.set_ylabel('λ_deg')
ax1.set_title('Coupling α (red=positive, blue=negative)')
plt.colorbar(im1, ax=ax1)

im2 = ax2.imshow(n_grid, origin='lower', cmap='plasma', aspect='auto',
                 extent=[pcurv_range[0], pcurv_range[-1], lam_range[0], lam_range[-1]])
ax2.set_xlabel('p_curv'); ax2.set_ylabel('λ_deg')
ax2.set_title('Potential index n (target: 4.0)')
plt.colorbar(im2, ax=ax2)

plt.tight_layout()
plt.savefig('param_scan_heatmap.png', dpi=150)
plt.show()

# 统计
print(f"\nα>0 的比例: {np.mean(alpha_grid > 0)*100:.1f}%")
print(f"n在[2,6]的比例: {np.mean((n_grid>2) & (n_grid<6))*100:.1f}%")
print("参数扫描完成。热力图已保存。")