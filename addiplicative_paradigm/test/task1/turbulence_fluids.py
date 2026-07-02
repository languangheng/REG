import numpy as np
import matplotlib.pyplot as plt

class FluidREG_Compare:
    def __init__(self, n_layers=80, dep_strength=1.0, label='流体', seed=42):
        np.random.seed(seed)
        self.n = n_layers
        self.dep_strength = dep_strength
        self.label = label
        self.flow_drive = 0.02
        self.depths = np.ones(n_layers)
        self.history = []

    def step(self):
        new_depths = self.depths.copy()
        for i in range(self.n):
            left_pull = right_pull = 0
            if i > 0: left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n-1: right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5*self.flow_drive/np.sqrt(self.dep_strength))
        new_depths[0] = 1.0; new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)

    def increase_flow(self, increment=0.01): self.flow_drive = min(0.8, self.flow_drive + increment)

    def run(self, total_steps=400):
        for step in range(total_steps):
            self.step()
            if step % 8 == 0 and step > 0: self.increase_flow(0.01)
            self.history.append(np.std(self.depths[1:-1]))


fluids = [
    {'label': '水 (低粘性)', 'dep_strength': 0.5, 'seed': 42},
    {'label': '油 (中粘性)', 'dep_strength': 1.0, 'seed': 42},
    {'label': '蜂蜜 (高粘性)', 'dep_strength': 1.5, 'seed': 42},
]

print("=" * 60); print("REG多流体对比：水 vs 油 vs 蜂蜜"); print("=" * 60)
plt.figure(figsize=(14, 6))
colors = ['blue', 'orange', 'red']

for i, fluid in enumerate(fluids):
    net = FluidREG_Compare(n_layers=80, dep_strength=fluid['dep_strength'], label=fluid['label'], seed=fluid['seed'])
    net.run(total_steps=400)
    hist = np.array(net.history)
    plt.plot(hist, color=colors[i], linewidth=2, label=fluid['label'])

plt.axhline(0.2, color='gray', linestyle='--', alpha=0.5, label='转捩阈值')
plt.axhline(0.5, color='black', linestyle='--', alpha=0.5, label='湍流阈值')
plt.xlabel('时间步', fontsize=13); plt.ylabel('湍流强度', fontsize=13)
plt.title('REG: 不同粘性流体的转捩过程对比', fontsize=14, fontweight='bold')
plt.legend(fontsize=12); plt.grid(True, alpha=0.3)
plt.tight_layout(); plt.savefig('fluid_comparison.png', dpi=150); plt.show()
print("图表已保存至 fluid_comparison.png")
