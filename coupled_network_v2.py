import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import time


class CoupledNetworkV2:
    """
    优化版乘-加网络：降低耦合强度，提高度惩罚，目标平均度=3.0，目标Phi=2.0
    """

    def __init__(self, n_nodes=300, seed=42, d0=3.0,
                 phi_target=2.0, penalty_phi=0.4, penalty_deg=0.5,
                 p_curv=0.3):
        np.random.seed(seed)
        self.n = n_nodes
        self.d0 = d0
        self.phi_target = phi_target
        self.lamb_phi = penalty_phi
        self.lamb_deg = penalty_deg
        self.p_curv = p_curv

        self.add_edges = [[] for _ in range(n_nodes)]
        self.mult_edges = [[] for _ in range(n_nodes)]
        self.mult_depth = np.zeros(n_nodes)

        self.gamma_a = 0.8
        self.gamma_m = 1.0

        self.total_add = 0
        self.total_mult = 0
        self.total_energy = 0.0

        self._initialize_network()
        self._update_energy()

    def _initialize_network(self):
        for i in range(self.n):
            degree = len(self.add_edges[i])
            n_needed = np.random.randint(2, 5) - degree
            candidates = list(set(range(self.n)) - {i} - set(self.add_edges[i]))
            if n_needed > 0 and len(candidates) >= n_needed:
                neighbors = np.random.choice(candidates, min(n_needed, len(candidates)), replace=False)
                for j in neighbors:
                    self.add_edges[i].append(j)
                    self.add_edges[j].append(i)
                    self.total_add += 1

        for i in range(self.n):
            if np.random.random() < 0.2:
                target = np.random.randint(self.n)
                if target != i:
                    self.mult_edges[i].append(target)
                    self.mult_depth[i] += 1
                    self.total_mult += 1

    def _degree_penalty(self):
        return self.lamb_deg * sum((len(adj) - self.d0) ** 2 for adj in self.add_edges)

    def _phi_penalty(self):
        return self.lamb_phi * sum((d - self.phi_target) ** 2 for d in self.mult_depth)

    def _update_energy(self):
        self.total_energy = (self.gamma_a * self.total_add +
                             self.gamma_m * self.total_mult +
                             self._degree_penalty() +
                             self._phi_penalty())

    def _backup_state(self):
        return (
            [[*adj] for adj in self.add_edges],
            [[*adj] for adj in self.mult_edges],
            self.mult_depth.copy(),
            self.total_add,
            self.total_mult,
            self.total_energy,
        )

    def _restore_state(self, state):
        (self.add_edges, self.mult_edges, self.mult_depth,
         self.total_add, self.total_mult, self.total_energy) = state

    def metropolis_step(self):
        node = np.random.randint(self.n)
        r = np.random.random()

        old_state = self._backup_state()

        if r < 0.35:  # 加 ⊕ 边
            target = np.random.randint(self.n)
            if target != node and target not in self.add_edges[node]:
                self.add_edges[node].append(target)
                self.add_edges[target].append(node)
                self.total_add += 1

        elif r < 0.65:  # 加 ⊗ 边（含耦合）
            target = np.random.randint(self.n)
            if target != node:
                self.mult_edges[node].append(target)
                self.mult_depth[node] += 1
                self.total_mult += 1

                if np.random.random() < self.p_curv:
                    candidates = [i for i in range(self.n)
                                 if i != node and i not in self.add_edges[node]]
                    if candidates:
                        nb = np.random.choice(candidates)
                        self.add_edges[node].append(nb)
                        self.add_edges[nb].append(node)
                        self.total_add += 1

        else:  # 乘转加
            if self.mult_depth[node] > 0 and self.mult_edges[node]:
                candidates = [i for i in range(self.n)
                             if i != node and i not in self.add_edges[node]]
                if len(candidates) >= 2:
                    new_neighbors = np.random.choice(candidates, 2, replace=False)
                    self.mult_edges[node].pop()
                    self.mult_depth[node] -= 1
                    self.total_mult -= 1
                    for nb in new_neighbors:
                        self.add_edges[node].append(nb)
                        self.add_edges[nb].append(node)
                        self.total_add += 1

        self._update_energy()
        delta_e = self.total_energy - old_state[5]

        if delta_e > 0 and np.random.random() >= np.exp(-delta_e):
            self._restore_state(old_state)

    def get_local_mult_density(self, node, radius=1):
        visited = {node}
        frontier = [node]
        for _ in range(radius):
            new_frontier = []
            for v in frontier:
                for nb in self.add_edges[v]:
                    if nb not in visited:
                        visited.add(nb)
                        new_frontier.append(nb)
            frontier = new_frontier
        depths = [self.mult_depth[v] for v in visited]
        return np.mean(depths) if depths else 0.0

    def get_local_curvature(self, node, radius=1):
        visited = {node}
        frontier = [node]
        for _ in range(radius):
            new_frontier = []
            for v in frontier:
                for nb in self.add_edges[v]:
                    if nb not in visited:
                        visited.add(nb)
                        new_frontier.append(nb)
            frontier = new_frontier
        n_visited = len(visited)
        if n_visited == 0:
            return 0.0
        total_edges = sum(len(self.add_edges[v]) for v in visited) // 2
        avg_deg = total_edges / n_visited
        return avg_deg - self.d0


# ================= 运行参数 =================
n_nodes = 300
burn_in = 20000
n_total = 40000

print("=" * 60)
print("Add-Mult Network (Tuned V2): Lower Coupling, Higher Degree Penalty")
print(f"Nodes:{n_nodes}, Target degree:3.0, Target Phi:2.0")
print("=" * 60)

start = time.time()
net = CoupledNetworkV2(n_nodes=n_nodes, seed=42, d0=3.0,
                       phi_target=2.0, penalty_phi=0.4, penalty_deg=0.5,
                       p_curv=0.3)

print(f"Burning in {burn_in} steps...")
for step in range(burn_in):
    net.metropolis_step()
    if (step + 1) % 10000 == 0:
        print(f"  Burn: {step + 1}/{burn_in}")

print(f"Sampling {n_total - burn_in} steps...")
phi_vals = []
curv_vals = []

for step in range(burn_in, n_total):
    net.metropolis_step()
    if step % 100 == 0:
        i = np.random.randint(net.n)
        phi_vals.append(net.get_local_mult_density(i))
        curv_vals.append(net.get_local_curvature(i))

elapsed = time.time() - start
avg_degree = 2 * net.total_add / net.n
print(f"Complete, elapsed: {elapsed:.1f} seconds")
print(f"Total (+) edges: {net.total_add} | Total (x) nestings: {net.total_mult}")
print(f"Final total energy: {net.total_energy:.1f}")
print(f"Average degree: {avg_degree:.2f}")

# ================= 数据分析 =================
phi_arr = np.array(phi_vals)
curv_arr = np.array(curv_vals)

hist, bin_edges = np.histogram(phi_arr, bins=25, density=True)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
prob = hist / hist.sum()
prob = np.clip(prob, 1e-10, None)
V_measured = -np.log(prob)
V_measured -= V_measured.min()


def power_law(phi, v0, n):
    return v0 * np.abs(phi) ** n


mask = bin_centers > 0.01
popt = None
if mask.sum() > 3:
    try:
        popt, _ = curve_fit(power_law, bin_centers[mask], V_measured[mask], p0=[1.0, 2.0])
        v0_fit, n_fit = popt
        print(f"Power law fit V(Phi) = {v0_fit:.3f} * Phi^{n_fit:.3f}")
    except Exception:
        v0_fit, n_fit = 1.0, 2.0
else:
    v0_fit, n_fit = 1.0, 2.0

if np.std(phi_arr) > 1e-10 and np.std(curv_arr) > 1e-10:
    corr = np.corrcoef(phi_arr, curv_arr)[0, 1]
    alpha = corr * np.std(curv_arr) / np.std(phi_arr)
    print(f"Coupling constant alpha = {alpha:.4f}")
else:
    alpha = 0.0

print(f"Phi stats: mean={np.mean(phi_arr):.3f}, std={np.std(phi_arr):.3f}")
print(f"Curvature stats: mean={np.mean(curv_arr):.3f}, std={np.std(curv_arr):.3f}")

# ================= 可视化 =================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('Add-Mult Network (Tuned V2): Lower Coupling, Higher Degree Penalty', fontsize=14, fontweight='bold')

axes[0, 0].plot(phi_vals, alpha=0.7, linewidth=0.8, color='blue')
axes[0, 0].set_xlabel('Sample Index')
axes[0, 0].set_ylabel('Phi')
axes[0, 0].set_title('Phi Time Series')
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].plot(curv_vals, alpha=0.7, linewidth=0.8, color='red')
axes[0, 1].set_xlabel('Sample Index')
axes[0, 1].set_ylabel('Curvature')
axes[0, 1].set_title('Curvature Time Series')
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].scatter(bin_centers, V_measured, c='blue', s=25, label='Measured', zorder=5)
x_sm = np.linspace(max(1e-3, bin_centers[0]), bin_centers[-1], 100)
axes[1, 0].plot(x_sm, power_law(x_sm, v0_fit, n_fit), 'r-', lw=2, label=f'Fit n={n_fit:.2f}')
axes[1, 0].set_xlabel('Phi')
axes[1, 0].set_ylabel('V(Phi)')
axes[1, 0].set_title('Effective Potential V(Phi)')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].scatter(phi_arr, curv_arr, alpha=0.5, c='purple', s=10)
if abs(alpha) > 1e-9:
    x_fit = np.linspace(phi_arr.min(), phi_arr.max(), 100)
    y_fit = alpha * (x_fit - np.mean(phi_arr)) + np.mean(curv_arr)
    axes[1, 1].plot(x_fit, y_fit, 'r-', lw=2, label=f'alpha={alpha:.3f}')
axes[1, 1].set_xlabel('Phi')
axes[1, 1].set_ylabel('Curvature')
axes[1, 1].set_title('Phi-Curvature Coupling')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
output_path = 'tuned_network_results.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nFigure saved to {output_path}")
plt.close('all')

print("=" * 60)
print("Run complete.")
print("=" * 60)
