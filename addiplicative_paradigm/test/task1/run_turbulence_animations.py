"""
REG湍流动态模拟 - 批量执行脚本
运行三个动态可视化模拟并保存关键帧
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import os

os.chdir(r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\github\scripts\task1")

print("=" * 70)
print("REG湍流动态模拟 - 批量执行")
print("=" * 70)
print("\n提示：每个模拟会显示动态窗口，观察完后关闭窗口继续下一个模拟。\n")

# ============ 脚本1: 一维湍流转捩 ============
print("\n" + "=" * 70)
print("[1/3] 一维湍流转捩模拟")
print("=" * 70)

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
            left_pull = 0; right_pull = 0
            if i > 0: left_pull = self.dep_strength * (self.depths[i-1] - self.depths[i])
            if i < self.n-1: right_pull = self.dep_strength * (self.depths[i+1] - self.depths[i])
            new_depths[i] += 0.3 * (left_pull + right_pull)
            if np.random.random() < self.flow_drive:
                new_depths[i] += np.random.normal(0, 0.5 * self.flow_drive / np.sqrt(self.dep_strength))
        new_depths[0] = 1.0; new_depths[-1] = 1.0
        self.depths = np.clip(new_depths, 0, None)
        self.step_count += 1
        self.history = np.roll(self.history, -1, axis=1)
        self.history[:, -1] = self.depths

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)

net1 = FluidREG_1D(n_layers=100, dep_strength=1.0, flow_drive=0.02, seed=42)

plt.style.use('dark_background')
fig1, axes1 = plt.subplots(2, 2, figsize=(16, 10))
fig1.suptitle('REG 一维湍流转捩 | 层流 -> 转捩 -> 湍流', fontsize=16, fontweight='bold', color='white')

ax1 = axes1[0, 0]; ax1.set_ylim(0, 4)
ax1.set_title('依赖深度分布', color='white'); ax1.axhline(1.0, color='gray', linestyle='--')
line1, = ax1.plot(net1.positions, net1.depths, 'cyan', linewidth=1.5)

ax2 = axes1[0, 1]
im1 = ax2.imshow(net1.history, aspect='auto', cmap='RdBu_r', vmin=0, vmax=2.5, origin='lower')
ax2.set_title('时空演化 (红=崩溃)', color='white')

ax3 = axes1[1, 0]; ax3.set_xlim(0, 500); ax3.set_ylim(0, 1.5)
ax3.set_title('湍流强度', color='white'); ax3.axhline(0.3, color='gray', linestyle='--')
turb_hist1 = []; line3, = ax3.plot([], [], 'r-', linewidth=2)

ax4 = axes1[1, 1]; ax4.axis('off'); ax4.set_facecolor('#111111')
status_text1 = ax4.text(0.1, 0.5, '', fontsize=14, color='white', verticalalignment='center', fontfamily='monospace')

last_regime1 = '层流'
transition_log1 = []

def update1(frame):
    global last_regime1
    net1.step()
    if frame % 8 == 0 and frame > 0: net1.increase_flow(0.012)
    turb = np.std(net1.depths[1:-1])
    if turb < 0.2: regime, color = '层流', 'cyan'
    elif turb < 0.5: regime, color = '转捩', 'yellow'
    else: regime, color = '湍流', 'red'
    if regime != last_regime1:
        msg = f"[步{net1.step_count:>4d}] 流速={net1.flow_drive:.3f} sigma={turb:.4f} *** {last_regime1} -> {regime} ***"
        print(msg)
        transition_log1.append(msg)
        last_regime1 = regime
    line1.set_ydata(net1.depths); line1.set_color(color)
    im1.set_array(net1.history)
    turb_hist1.append(turb)
    if len(turb_hist1) > 500: turb_hist1.pop(0)
    line3.set_data(range(len(turb_hist1)), turb_hist1)
    status_str = f"步: {net1.step_count}\n流速: {net1.flow_drive:.3f}\n湍流强度: {turb:.4f}\n状态: {regime}"
    status_text1.set_text(status_str); status_text1.set_color(color)
    fig1.suptitle(f'REG 一维湍流 | 步{net1.step_count} | 流速{net1.flow_drive:.2f} | {regime}', fontsize=16, fontweight='bold', color='white')
    return line1, im1, line3, status_text1

ani1 = FuncAnimation(fig1, update1, frames=400, interval=60, repeat=False)
plt.tight_layout()
plt.show()

# 保存一维模拟结果
fig1.savefig('turbulence_1d_final.png', dpi=150, bbox_inches='tight')
print("\n[完成] 一维湍流模拟完成，结果保存至 turbulence_1d_final.png")
print(f"状态转换次数: {len(transition_log1)}")

# ============ 脚本2: 二维涡旋涌现 ============
print("\n" + "=" * 70)
print("[2/3] 二维涡旋涌现模拟")
print("=" * 70)

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

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)

size2 = 60
net2 = FluidREG_2D(size=size2, dep_strength=1.0, flow_drive=0.03, seed=42)
print(f"网格: {size2}x{size2}")

plt.style.use('dark_background')
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 12))
fig2.suptitle('REG 二维湍流 | 涡旋涌现', fontsize=16, fontweight='bold', color='white')

im1_2 = axes2[0,0].imshow(net2.depths, cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes2[0,0].set_title('依赖深度 (蓝=层流, 红=崩溃)', color='white')
cbar1 = plt.colorbar(im1_2, ax=axes2[0,0]); cbar1.set_label('依赖深度', color='white')

im2_2 = axes2[0,1].imshow(np.sqrt(net2.vx**2+net2.vy**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes2[0,1].set_title('涡旋强度 (速度幅值)', color='white')
cbar2 = plt.colorbar(im2_2, ax=axes2[0,1]); cbar2.set_label('速度', color='white')

im3_2 = axes2[1,0].imshow(net2.history, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes2[1,0].set_title('涡旋活动历史 (亮=频繁涡旋区)', color='white')
cbar3 = plt.colorbar(im3_2, ax=axes2[1,0]); cbar3.set_label('累积扰动', color='white')

axes2[1,1].axis('off'); axes2[1,1].set_facecolor('#111111')
status_text2 = axes2[1,1].text(0.1,0.5,'',fontsize=14,color='white',verticalalignment='center',fontfamily='monospace')

last_regime2 = '层流'
transition_log2 = []

def update2(frame):
    global last_regime2
    net2.step()
    if frame % 8 == 0 and frame > 0: net2.increase_flow(0.012)
    turb = np.std(net2.depths[1:-1,1:-1])
    if turb < 0.15: regime, color = '层流', 'cyan'
    elif turb < 0.4: regime, color = '转捩', 'yellow'
    else: regime, color = '湍流', 'red'
    if regime != last_regime2:
        msg = f"[步{net2.step_count:>4d}] 流速={net2.flow_drive:.3f} sigma={turb:.4f} *** {last_regime2} -> {regime} ***"
        print(msg)
        transition_log2.append(msg)
        last_regime2 = regime
    im1_2.set_array(net2.depths); im2_2.set_array(np.sqrt(net2.vx**2+net2.vy**2)); im3_2.set_array(net2.history)
    status_text2.set_text(f"步: {net2.step_count}\n流速: {net2.flow_drive:.3f}\n湍流强度: {turb:.4f}\n状态: {regime}")
    status_text2.set_color(color)
    fig2.suptitle(f'REG 二维湍流 | 步{net2.step_count} | 流速{net2.flow_drive:.2f} | {regime}', fontsize=16, fontweight='bold', color='white')
    return im1_2, im2_2, im3_2, status_text2

ani2 = FuncAnimation(fig2, update2, frames=400, interval=80, repeat=False)
plt.tight_layout()
plt.show()

# 保存二维模拟结果
fig2.savefig('turbulence_2d_final.png', dpi=150, bbox_inches='tight')
print("\n[完成] 二维湍流模拟完成，结果保存至 turbulence_2d_final.png")
print(f"状态转换次数: {len(transition_log2)}")

# ============ 脚本3: 三维涡管结构 ============
print("\n" + "=" * 70)
print("[3/3] 三维涡管结构模拟")
print("=" * 70)

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
        new_vx = self.vx.copy(); new_vy = self.vy.copy(); new_vz = self.vz.copy()
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
                        theta = np.random.random()*2*np.pi; phi = np.random.random()*np.pi
                        new_vx[i,j,k] += perturbation*np.sin(phi)*np.cos(theta)*0.15
                        new_vy[i,j,k] += perturbation*np.sin(phi)*np.sin(theta)*0.15
                        new_vz[i,j,k] += perturbation*np.cos(phi)*0.15
        self.depths = np.clip(new_depths, 0, 3); self.vx, self.vy, self.vz = new_vx, new_vy, new_vz
        mid = self.size // 2
        self.history_slice += np.abs(self.depths[:,:,mid] - 1.0) * 0.15
        self.step_count += 1

    def increase_flow(self, increment=0.012):
        self.flow_drive = min(0.6, self.flow_drive + increment)

SIZE3 = 30
net3 = FluidREG_3D(size=SIZE3, dep_strength=1.0, flow_drive=0.03, seed=42)
print(f"网格: {SIZE3}x{SIZE3}x{SIZE3} ({SIZE3**3:,}节点)")

plt.style.use('dark_background')
fig3, axes3 = plt.subplots(2, 2, figsize=(14, 12))
fig3.suptitle('REG 三维湍流 | 涡管结构涌现', fontsize=16, fontweight='bold', color='white')

mid = SIZE3 // 2
im1_3 = axes3[0,0].imshow(net3.depths[:,:,mid], cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes3[0,0].set_title(f'依赖深度 XY切片 (Z={mid})', color='white')
cbar1_3 = plt.colorbar(im1_3, ax=axes3[0,0]); cbar1_3.set_label('依赖深度', color='white')

im2_3 = axes3[0,1].imshow(np.sqrt(net3.vx[:,:,mid]**2+net3.vy[:,:,mid]**2+net3.vz[:,:,mid]**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes3[0,1].set_title(f'涡旋强度 XY切片 (Z={mid})', color='white')
cbar2_3 = plt.colorbar(im2_3, ax=axes3[0,1]); cbar2_3.set_label('速度', color='white')

im3_3 = axes3[1,0].imshow(net3.history_slice, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes3[1,0].set_title('涡管活动历史 (亮=频繁涡旋区)', color='white')
cbar3_3 = plt.colorbar(im3_3, ax=axes3[1,0]); cbar3_3.set_label('累积扰动', color='white')

axes3[1,1].axis('off'); axes3[1,1].set_facecolor('#111111')
status_text3 = axes3[1,1].text(0.1,0.5,'',fontsize=14,color='white',verticalalignment='center',fontfamily='monospace')

last_regime3 = '层流'
transition_log3 = []

def update3(frame):
    global last_regime3
    net3.step()
    if frame % 8 == 0 and frame > 0: net3.increase_flow(0.012)
    turb = np.std(net3.depths[1:-1,1:-1,1:-1])
    if turb < 0.15: regime, color = '层流', 'cyan'
    elif turb < 0.4: regime, color = '转捩', 'yellow'
    else: regime, color = '湍流', 'red'
    if regime != last_regime3:
        msg = f"[步{net3.step_count:>4d}] 流速={net3.flow_drive:.3f} sigma={turb:.4f} *** {last_regime3} -> {regime} ***"
        print(msg)
        transition_log3.append(msg)
        last_regime3 = regime
    mid = SIZE3 // 2
    im1_3.set_array(net3.depths[:,:,mid])
    im2_3.set_array(np.sqrt(net3.vx[:,:,mid]**2+net3.vy[:,:,mid]**2+net3.vz[:,:,mid]**2))
    im3_3.set_array(net3.history_slice)
    status_text3.set_text(f"步: {net3.step_count}\n流速: {net3.flow_drive:.3f}\n湍流强度: {turb:.4f}\n状态: {regime}")
    status_text3.set_color(color)
    fig3.suptitle(f'REG 三维湍流 | 步{net3.step_count} | 流速{net3.flow_drive:.2f} | {regime}', fontsize=16, fontweight='bold', color='white')
    return im1_3, im2_3, im3_3, status_text3

ani3 = FuncAnimation(fig3, update3, frames=400, interval=80, repeat=False)
plt.tight_layout()
plt.show()

# 保存三维模拟结果
fig3.savefig('turbulence_3d_final.png', dpi=150, bbox_inches='tight')
print("\n[完成] 三维湍流模拟完成，结果保存至 turbulence_3d_final.png")
print(f"状态转换次数: {len(transition_log3)}")

# ============ 汇总报告 ============
print("\n" + "=" * 70)
print("所有模拟完成！")
print("=" * 70)
print("\n生成的文件:")
for f in ['turbulence_1d_final.png', 'turbulence_2d_final.png', 'turbulence_3d_final.png']:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f"  [OK] {f} ({size:.1f} KB)")
    else:
        print(f"  [FAIL] {f} (未生成)")

print("\n模拟统计:")
print(f"  一维湍流: {len(transition_log1)} 次状态转换")
print(f"  二维湍流: {len(transition_log2)} 次状态转换")
print(f"  三维湍流: {len(transition_log3)} 次状态转换")
print("\n所有动态模拟已完成！")
