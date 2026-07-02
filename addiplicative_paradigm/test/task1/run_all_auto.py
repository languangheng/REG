"""
REG湍流模拟 - 自动化批量执行版本
不依赖GUI窗口，直接生成结果图片和数据
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import json

print("=" * 70)
print("REG湍流模拟 - 批量执行")
print("=" * 70)

# ============ 脚本1: 一维湍流转捩基础模拟 ============
print("\n[1/5] 一维湍流转捩基础模拟...")

class FluidREG_1D:
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

net1 = FluidREG_1D(n_layers=100, dep_strength=1.0, flow_drive=0.02, seed=42)
transitions_1d = []
turb_history_1d = []

for frame in range(400):
    net1.step()
    if frame % 8 == 0 and frame > 0:
        net1.increase_flow(0.012)
    turb = np.std(net1.depths[1:-1])
    turb_history_1d.append(turb)
    
    if turb < 0.2:
        regime = '层流'
    elif turb < 0.5:
        regime = '转捩'
    else:
        regime = '湍流'
    
    if len(transitions_1d) == 0 or transitions_1d[-1][3] != regime:
        transitions_1d.append((net1.step_count, net1.flow_drive, turb, regime))

# 保存1D结果
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('REG 一维湍流转捩', fontsize=16, fontweight='bold')

axes[0, 0].plot(net1.positions, net1.depths, 'cyan', linewidth=1.5)
axes[0, 0].axhline(1.0, color='gray', linestyle='--', alpha=0.5)
axes[0, 0].set_ylim(0, 4)
axes[0, 0].set_title('依赖深度分布 (最终状态)')

im = axes[0, 1].imshow(net1.history, aspect='auto', cmap='RdBu_r', vmin=0, vmax=2.5, origin='lower')
axes[0, 1].set_title('时空演化 (红=崩溃)')

axes[1, 0].plot(turb_history_1d, 'r-', linewidth=2)
axes[1, 0].axhline(0.2, color='gray', linestyle='--', alpha=0.5, label='转捩阈值')
axes[1, 0].axhline(0.5, color='black', linestyle='--', alpha=0.5, label='湍流阈值')
axes[1, 0].set_xlim(0, 400)
axes[1, 0].set_ylim(0, 1.5)
axes[1, 0].set_title('湍流强度演化')
axes[1, 0].legend()
axes[1, 0].set_xlabel('时间步')

transition_text = "状态转换记录:\n"
for t in transitions_1d[:5]:
    transition_text += f"步{t[0]}: 流速{t[1]:.3f}, σ={t[2]:.4f} → {t[3]}\n"
axes[1, 1].text(0.1, 0.5, transition_text, fontsize=12, verticalalignment='center')
axes[1, 1].axis('off')

plt.tight_layout()
plt.savefig('turbulence_1d_results.png', dpi=150, bbox_inches='tight')
print(f"  [OK] 一维湍流模拟完成，保存至 turbulence_1d_results.png")
print(f"  状态转换: {len(transitions_1d)} 次")
for t in transitions_1d:
    print(f"    步{t[0]:>4d}: 流速={t[1]:.3f}, σ={t[2]:.4f} → {t[3]}")

# ============ 脚本2: 参数扫描 ============
print("\n[2/5] 参数扫描：依赖强度 vs 临界流速...")

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
            if i > 0:
                left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n-1:
                right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
        new_depths[0] = 1.0
        new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)
        self.step_count += 1

    def increase_flow(self, increment=0.015):
        self.flow_drive = min(0.8, self.flow_drive + increment)

    def run(self, total_steps=500):
        first_trans = None
        locked_turb = None
        cons_turb = 0
        for step in range(total_steps):
            self.step()
            if step % 8 == 0 and step > 0:
                self.increase_flow(0.015)
            turb = np.std(self.depths[1:-1])
            if first_trans is None and turb > 0.2:
                first_trans = self.flow_drive
            if turb > 0.5:
                cons_turb += 1
                if cons_turb >= 10 and locked_turb is None:
                    locked_turb = self.flow_drive
            else:
                cons_turb = 0
        return first_trans, locked_turb

dep_strengths = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
first_vals, locked_vals = [], []
scan_results = []

for ds in dep_strengths:
    net = FluidREG_Scan(n_layers=80, dep_strength=ds, seed=42)
    ft, lt = net.run(total_steps=500)
    first_vals.append(ft if ft else 0.8)
    locked_vals.append(lt if lt else 0.8)
    scan_results.append({'dep_strength': ds, 'first_transition': ft, 'locked_turbulence': lt})
    ft_str = f"{ft:.3f}" if ft is not None else "N/A"
    lt_str = f"{lt:.3f}" if lt is not None else "N/A"
    print(f"  依赖={ds:.1f} | 首次转捩={ft_str:>5} | 锁定湍流={lt_str:>5}")

plt.figure(figsize=(10, 6))
plt.plot(dep_strengths, first_vals, 'o-', color='orange', lw=2, ms=10, label='首次转捩')
plt.plot(dep_strengths, locked_vals, 's-', color='red', lw=2, ms=10, label='锁定湍流')
plt.xlabel('依赖强度')
plt.ylabel('临界流速')
plt.legend()
plt.grid(alpha=0.3)
plt.title('REG: 依赖强度 vs 转捩临界流速')
plt.tight_layout()
plt.savefig('turbulence_scan_results.png', dpi=150, bbox_inches='tight')
print(f"  [OK] 参数扫描完成，保存至 turbulence_scan_results.png")

# ============ 脚本3: 二维湍流模拟 ============
print("\n[3/5] 二维湍流涡旋模拟...")

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
        new_vx = self.vx.copy()
        new_vy = self.vy.copy()
        for i in range(self.size):
            for j in range(self.size):
                neighbor_pull = 0
                n_count = 0
                for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ni, nj = i+di, j+dj
                    if 0 <= ni < self.size and 0 <= nj < self.size:
                        neighbor_pull += self.dep_strength * (self.depths[ni,nj] - self.depths[i,j])
                        n_count += 1
                if n_count > 0:
                    new_depths[i,j] += 0.2 * neighbor_pull / n_count
                if np.random.random() < self.flow_drive:
                    perturbation = np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
                    new_depths[i,j] += perturbation
                    angle = np.random.random() * 2 * np.pi
                    new_vx[i,j] += perturbation * np.cos(angle) * 0.15
                    new_vy[i,j] += perturbation * np.sin(angle) * 0.15
        new_depths[0,:]=1; new_depths[-1,:]=1; new_depths[:,0]=1; new_depths[:,-1]=1
        self.depths = np.clip(new_depths, 0, 3)
        self.vx = new_vx
        self.vy = new_vy
        self.history += np.abs(self.depths - 1.0) * 0.15
        self.step_count += 1

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)

size = 60
net2 = FluidREG_2D(size=size, dep_strength=1.0, flow_drive=0.03, seed=42)
transitions_2d = []

for frame in range(400):
    net2.step()
    if frame % 8 == 0 and frame > 0:
        net2.increase_flow(0.012)
    turb = np.std(net2.depths[1:-1,1:-1])
    
    if turb < 0.15:
        regime = '层流'
    elif turb < 0.4:
        regime = '转捩'
    else:
        regime = '湍流'
    
    if len(transitions_2d) == 0 or transitions_2d[-1][3] != regime:
        transitions_2d.append((net2.step_count, net2.flow_drive, turb, regime))

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('REG 二维湍流 | 涡旋涌现', fontsize=16, fontweight='bold')

im1 = axes[0].imshow(net2.depths, cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes[0].set_title('依赖深度 (蓝=层流, 红=崩溃)')
plt.colorbar(im1, ax=axes[0])

im2 = axes[1].imshow(np.sqrt(net2.vx**2+net2.vy**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes[1].set_title('涡旋强度')
plt.colorbar(im2, ax=axes[1])

im3 = axes[2].imshow(net2.history, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes[2].set_title('涡旋活动历史')
plt.colorbar(im3, ax=axes[2])

plt.tight_layout()
plt.savefig('turbulence_2d_results.png', dpi=150, bbox_inches='tight')
print(f"  [OK] 二维湍流模拟完成，保存至 turbulence_2d_results.png")
print(f"  状态转换: {len(transitions_2d)} 次")
for t in transitions_2d:
    print(f"    步{t[0]:>4d}: 流速={t[1]:.3f}, σ={t[2]:.4f} → {t[3]}")

# ============ 脚本4: 三维涡管结构模拟 ============
print("\n[4/5] 三维涡管结构模拟...")

class FluidREG_3D:
    def __init__(self, size=30, dep_strength=1.0, flow_drive=0.03, seed=42):
        np.random.seed(seed)
        self.size = size
        self.dep_strength = dep_strength
        self.flow_drive = flow_drive
        self.depths = np.ones((size, size, size))
        self.vx = np.zeros((size, size, size))
        self.vy = np.zeros((size, size, size))
        self.vz = np.zeros((size, size, size))
        self.history_slice = np.zeros((size, size))
        self.step_count = 0

    def step(self):
        new_depths = self.depths.copy()
        new_vx = self.vx.copy()
        new_vy = self.vy.copy()
        new_vz = self.vz.copy()
        for i in range(1, self.size-1):
            for j in range(1, self.size-1):
                for k in range(1, self.size-1):
                    neighbor_pull = (self.dep_strength*(self.depths[i-1,j,k]-self.depths[i,j,k]) +
                                    self.dep_strength*(self.depths[i+1,j,k]-self.depths[i,j,k]) +
                                    self.dep_strength*(self.depths[i,j-1,k]-self.depths[i,j,k]) +
                                    self.dep_strength*(self.depths[i,j+1,k]-self.depths[i,j,k]) +
                                    self.dep_strength*(self.depths[i,j,k-1]-self.depths[i,j,k]) +
                                    self.dep_strength*(self.depths[i,j,k+1]-self.depths[i,j,k])) / 6.0
                    new_depths[i,j,k] += 0.2 * neighbor_pull
                    if np.random.random() < self.flow_drive:
                        perturbation = np.random.normal(0, 0.5*self.flow_drive/np.sqrt(self.dep_strength))
                        new_depths[i,j,k] += perturbation
                        theta = np.random.random()*2*np.pi
                        phi = np.random.random()*np.pi
                        new_vx[i,j,k] += perturbation*np.sin(phi)*np.cos(theta)*0.15
                        new_vy[i,j,k] += perturbation*np.sin(phi)*np.sin(theta)*0.15
                        new_vz[i,j,k] += perturbation*np.cos(phi)*0.15
        self.depths = np.clip(new_depths, 0, 3)
        self.vx, self.vy, self.vz = new_vx, new_vy, new_vz
        mid = self.size // 2
        self.history_slice += np.abs(self.depths[:,:,mid] - 1.0) * 0.15
        self.step_count += 1

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)

SIZE = 30
net3 = FluidREG_3D(size=SIZE, dep_strength=1.0, flow_drive=0.03, seed=42)
transitions_3d = []

for frame in range(400):
    net3.step()
    if frame % 8 == 0 and frame > 0:
        net3.increase_flow(0.012)
    turb = np.std(net3.depths[1:-1,1:-1,1:-1])
    
    if turb < 0.15:
        regime = '层流'
    elif turb < 0.4:
        regime = '转捩'
    else:
        regime = '湍流'
    
    if len(transitions_3d) == 0 or transitions_3d[-1][3] != regime:
        transitions_3d.append((net3.step_count, net3.flow_drive, turb, regime))

mid = SIZE // 2
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle(f'REG 三维湍流 | 涡管结构 (网格: {SIZE}×{SIZE}×{SIZE})', fontsize=16, fontweight='bold')

im1 = axes[0].imshow(net3.depths[:,:,mid], cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes[0].set_title(f'依赖深度 XY切片 (Z={mid})')
plt.colorbar(im1, ax=axes[0])

im2 = axes[1].imshow(np.sqrt(net3.vx[:,:,mid]**2+net3.vy[:,:,mid]**2+net3.vz[:,:,mid]**2), 
                     cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes[1].set_title('涡旋强度 XY切片')
plt.colorbar(im2, ax=axes[1])

im3 = axes[2].imshow(net3.history_slice, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes[2].set_title('涡管活动历史')
plt.colorbar(im3, ax=axes[2])

plt.tight_layout()
plt.savefig('turbulence_3d_results.png', dpi=150, bbox_inches='tight')
print(f"  [OK] 三维湍流模拟完成，保存至 turbulence_3d_results.png")
print(f"  状态转换: {len(transitions_3d)} 次")
for t in transitions_3d:
    print(f"    步{t[0]:>4d}: 流速={t[1]:.3f}, σ={t[2]:.4f} → {t[3]}")

# ============ 脚本5: 多流体对比 ============
print("\n[5/5] 多流体对比：水 vs 油 vs 蜂蜜...")

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
            if i > 0:
                left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n-1:
                right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5*self.flow_drive/np.sqrt(self.dep_strength))
        new_depths[0] = 1.0
        new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)

    def increase_flow(self, increment=0.01):
        self.flow_drive = min(0.8, self.flow_drive + increment)

    def run(self, total_steps=400):
        for step in range(total_steps):
            self.step()
            if step % 8 == 0 and step > 0:
                self.increase_flow(0.01)
            self.history.append(np.std(self.depths[1:-1]))

fluids = [
    {'label': '水 (低粘性)', 'dep_strength': 0.5, 'seed': 42},
    {'label': '油 (中粘性)', 'dep_strength': 1.0, 'seed': 42},
    {'label': '蜂蜜 (高粘性)', 'dep_strength': 1.5, 'seed': 42},
]

plt.figure(figsize=(14, 6))
colors = ['blue', 'orange', 'red']

for i, fluid in enumerate(fluids):
    net = FluidREG_Compare(n_layers=80, dep_strength=fluid['dep_strength'], 
                          label=fluid['label'], seed=fluid['seed'])
    net.run(total_steps=400)
    hist = np.array(net.history)
    plt.plot(hist, color=colors[i], linewidth=2, label=fluid['label'])
    
    # 计算首次转捩和湍流锁定
    first_trans = next((j for j, v in enumerate(hist) if v > 0.2), len(hist))
    locked_turb = next((j for j, v in enumerate(hist) if v > 0.5), len(hist))
    print(f"  {fluid['label']}: 首次转捩步={first_trans}, 湍流锁定步={locked_turb}")

plt.axhline(0.2, color='gray', linestyle='--', alpha=0.5, label='转捩阈值')
plt.axhline(0.5, color='black', linestyle='--', alpha=0.5, label='湍流阈值')
plt.xlabel('时间步', fontsize=13)
plt.ylabel('湍流强度', fontsize=13)
plt.title('REG: 不同粘性流体的转捩过程对比', fontsize=14, fontweight='bold')
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fluid_comparison_results.png', dpi=150, bbox_inches='tight')
print(f"  [OK] 多流体对比完成，保存至 fluid_comparison_results.png")

# ============ 汇总报告 ============
print("\n" + "=" * 70)
print("模拟完成！生成的文件:")
print("=" * 70)

output_files = [
    'turbulence_1d_results.png',
    'turbulence_scan_results.png',
    'turbulence_2d_results.png',
    'turbulence_3d_results.png',
    'fluid_comparison_results.png'
]

for f in output_files:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f"  [OK] {f} ({size:.1f} KB)")
    else:
        print(f"  [FAIL] {f} (未生成)")

print("\n所有模拟已完成！")
