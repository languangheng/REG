import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

class FluidREG_1D:
    """REG一维湍流转捩模拟器"""
    def __init__(self, n_layers=100, dep_strength=1.0, flow_drive=0.02, seed=42):
        np.random.seed(seed)
        self.n = n_layers
        self.dep_strength = dep_strength
        self.flow_drive = flow_drive
        self.depths = np.ones(n_layers)
        self.positions = np.linspace(0, 1, n_layers)
        self.history = np.zeros((n_layers, 200))
        self.step_count = 0

    def step(self):
        new_depths = self.depths.copy()
        for i in range(self.n):
            left_pull = 0
            right_pull = 0
            if i > 0:
                left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n - 1:
                right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
        new_depths[0] = 1.0
        new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)
        self.step_count += 1
        self.history = np.roll(self.history, -1, axis=1)
        self.history[:, -1] = self.depths

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)


net = FluidREG_1D(n_layers=100, dep_strength=1.0, flow_drive=0.02, seed=42)

plt.style.use('dark_background')
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('REG 一维湍流转捩', fontsize=16, fontweight='bold', color='white')

ax1 = axes[0, 0]; ax1.set_ylim(0, 4); ax1.set_title('依赖深度分布', color='white')
line1, = ax1.plot(net.positions, net.depths, 'cyan', linewidth=1.5)
ax1.axhline(1.0, color='gray', linestyle='--', alpha=0.5)

ax2 = axes[0, 1]
im = ax2.imshow(net.history, aspect='auto', cmap='RdBu_r', vmin=0, vmax=2.5, origin='lower')
ax2.set_title('时空演化 (红=崩溃)', color='white')

ax3 = axes[1, 0]; ax3.set_xlim(0, 500); ax3.set_ylim(0, 1.5)
ax3.set_title('湍流强度', color='white'); ax3.axhline(0.3, color='gray', linestyle='--')
turb_hist = []
line3, = ax3.plot([], [], 'r-', linewidth=2)

ax4 = axes[1, 1]; ax4.axis('off'); ax4.set_facecolor('#111111')
status_text = ax4.text(0.1, 0.5, '', fontsize=14, color='white', verticalalignment='center', fontfamily='monospace')

last_regime = '层流'
transitions = []

def update(frame):
    global last_regime
    net.step()
    if frame % 8 == 0 and frame > 0: net.increase_flow(0.012)
    turb = np.std(net.depths[1:-1])
    if turb < 0.2: regime, color = '层流', 'cyan'
    elif turb < 0.5: regime, color = '转捩', 'yellow'
    else: regime, color = '湍流', 'red'
    if regime != last_regime:
        transitions.append((net.step_count, net.flow_drive, turb, last_regime, regime))
        print(f"[步{net.step_count:>4d}] 流速={net.flow_drive:.3f} σ={turb:.4f} ★ {last_regime} → {regime} ★")
        last_regime = regime
    line1.set_ydata(net.depths); line1.set_color(color)
    im.set_array(net.history)
    turb_hist.append(turb)
    if len(turb_hist) > 500: turb_hist.pop(0)
    line3.set_data(range(len(turb_hist)), turb_hist)
    status_str = f"步: {net.step_count}\n流速: {net.flow_drive:.3f}\n湍流强度: {turb:.4f}\n状态: {regime}"
    status_text.set_text(status_str); status_text.set_color(color)
    fig.suptitle(f'REG 一维湍流 | 步{net.step_count} | 流速{net.flow_drive:.2f} | {regime}', fontsize=16, fontweight='bold', color='white')
    return line1, im, line3, status_text

ani = FuncAnimation(fig, update, frames=400, interval=60, repeat=False)
plt.tight_layout()
plt.savefig('turbulence_1d_final.png', dpi=150, bbox_inches='tight')
print("最终状态图已保存至 turbulence_1d_final.png")
plt.show()
