import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class FluidREG_2D:
    def __init__(self, size=60, dep_strength=1.0, flow_drive=0.03, seed=42):
        np.random.seed(seed)
        self.size = size
        self.dep_strength = dep_strength
        self.flow_drive = flow_drive
        self.depths = np.ones((size, size))
        self.vx = np.zeros((size, size))
        self.vy = np.zeros((size, size))
        self.history = np.zeros((size, size))
        self.step_count = 0

    def step(self):
        new_depths = self.depths.copy()
        new_vx = self.vx.copy(); new_vy = self.vy.copy()
        for i in range(self.size):
            for j in range(self.size):
                neighbor_pull = 0; n_count = 0
                for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ni, nj = i+di, j+dj
                    if 0 <= ni < self.size and 0 <= nj < self.size:
                        neighbor_pull += self.dep_strength * (self.depths[ni,nj] - self.depths[i,j])
                        n_count += 1
                if n_count > 0: new_depths[i,j] += 0.2 * neighbor_pull / n_count
                if np.random.random() < self.flow_drive:
                    perturbation = np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
                    new_depths[i,j] += perturbation
                    angle = np.random.random() * 2 * np.pi
                    new_vx[i,j] += perturbation * np.cos(angle) * 0.15
                    new_vy[i,j] += perturbation * np.sin(angle) * 0.15
        new_depths[0,:]=1; new_depths[-1,:]=1; new_depths[:,0]=1; new_depths[:,-1]=1
        self.depths = np.clip(new_depths, 0, 3); self.vx = new_vx; self.vy = new_vy
        self.history += np.abs(self.depths - 1.0) * 0.15
        self.step_count += 1

    def increase_flow(self, increment=0.012): self.flow_drive = min(0.6, self.flow_drive + increment)


size = 60
net = FluidREG_2D(size=size, dep_strength=1.0, flow_drive=0.03, seed=42)
print("=" * 60); print(f"REG二维湍流 | 网格:{size}x{size}"); print("=" * 60)

plt.style.use('dark_background')
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
fig.suptitle('REG 二维湍流 | 涡旋涌现', fontsize=16, fontweight='bold', color='white')

im1 = axes[0,0].imshow(net.depths, cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes[0,0].set_title('依赖深度 (蓝=层流, 红=崩溃)', color='white')
im2 = axes[0,1].imshow(np.sqrt(net.vx**2+net.vy**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes[0,1].set_title('涡旋强度', color='white')
im3 = axes[1,0].imshow(net.history, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes[1,0].set_title('涡旋活动历史', color='white')
axes[1,1].axis('off')
status_text = axes[1,1].text(0.1,0.5,'',fontsize=14,color='white',verticalalignment='center',fontfamily='monospace')

last_regime = '层流'
def update(frame):
    global last_regime
    net.step()
    if frame % 8 == 0 and frame > 0: net.increase_flow(0.012)
    turb = np.std(net.depths[1:-1,1:-1])
    if turb < 0.15: regime, color = '层流', 'cyan'
    elif turb < 0.4: regime, color = '转捩', 'yellow'
    else: regime, color = '湍流', 'red'
    if regime != last_regime:
        print(f"[步{net.step_count:>4d}] 流速={net.flow_drive:.3f} σ={turb:.4f} ★ {last_regime} → {regime} ★")
        last_regime = regime
    im1.set_array(net.depths); im2.set_array(np.sqrt(net.vx**2+net.vy**2)); im3.set_array(net.history)
    status_text.set_text(f"步: {net.step_count}\n流速: {net.flow_drive:.3f}\n湍流强度: {turb:.4f}\n状态: {regime}")
    status_text.set_color(color)
    fig.suptitle(f'REG 二维湍流 | 步{net.step_count} | 流速{net.flow_drive:.2f} | {regime}', fontsize=16, fontweight='bold', color='white')
    return im1, im2, im3, status_text

ani = FuncAnimation(fig, update, frames=400, interval=80, repeat=False)
plt.tight_layout(); plt.show()
