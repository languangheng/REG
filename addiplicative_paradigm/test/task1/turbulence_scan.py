import numpy as np
import matplotlib.pyplot as plt

class FluidREG_Scan:
    def __init__(self, n_layers=80, dep_strength=1.0, seed=42):
        np.random.seed(seed)
        self.n = n_layers
        self.dep_strength = dep_strength
        self.flow_drive = 0.02
        self.depths = np.ones(n_layers)
        self.step_count = 0

    def step(self):
        new_depths = self.depths.copy()
        for i in range(self.n):
            left_pull = right_pull = 0
            if i > 0: left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n-1: right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
        new_depths[0] = 1.0; new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)
        self.step_count += 1

    def increase_flow(self, increment=0.015): self.flow_drive = min(0.8, self.flow_drive + increment)

    def run(self, total_steps=500):
        first_trans = None; locked_turb = None; cons_turb = 0
        for step in range(total_steps):
            self.step()
            if step % 8 == 0 and step > 0: self.increase_flow(0.015)
            turb = np.std(self.depths[1:-1])
            if first_trans is None and turb > 0.2: first_trans = self.flow_drive
            if turb > 0.5:
                cons_turb += 1
                if cons_turb >= 10 and locked_turb is None: locked_turb = self.flow_drive
            else: cons_turb = 0
        return first_trans, locked_turb


print("=" * 60); print("REG湍流参数扫描"); print("=" * 60)
dep_strengths = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
first_vals, locked_vals = [], []
for ds in dep_strengths:
    net = FluidREG_Scan(n_layers=80, dep_strength=ds, seed=42)
    ft, lt = net.run(total_steps=500)
    first_vals.append(ft if ft else 0.8)
    locked_vals.append(lt if lt else 0.8)
    print(f"依赖={ds:.1f} | 首次转捩={ft:.3f} | 锁定湍流={lt:.3f}")

plt.figure(figsize=(10,6))
plt.plot(dep_strengths, first_vals, 'o-', color='orange', lw=2, ms=10, label='首次转捩')
plt.plot(dep_strengths, locked_vals, 's-', color='red', lw=2, ms=10, label='锁定湍流')
plt.xlabel('依赖强度'); plt.ylabel('临界流速'); plt.legend(); plt.grid(alpha=0.3)
plt.title('REG: 依赖强度 vs 转捩临界流速')
plt.tight_layout(); plt.savefig('turbulence_scan.png', dpi=150); plt.show()
print("图表已保存至 turbulence_scan.png")
