"""
REG Turbulence - Run all 5 simulations and capture full logs
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os
import sys
from io import StringIO

os.chdir(r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\github\scripts\task1")

# Redirect stdout to capture all prints
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()

logger = Logger('simulation_logs.txt')

# ============ Script 1: 1D Turbulence ============
print("=" * 70)
print("SCRIPT 1: 1D TURBULENCE TRANSITION")
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
transitions1 = []

print(f"Grid: {net1.n} layers")
print(f"Initial flow_drive: {net1.flow_drive}")
print(f"Dependence strength: {net1.dep_strength}")
print("\n--- Running 400 steps ---\n")

last_regime = 'Laminar'
for frame in range(400):
    net1.step()
    if frame % 8 == 0 and frame > 0:
        net1.increase_flow(0.012)
    turb = np.std(net1.depths[1:-1])
    if turb < 0.2: regime = 'Laminar'
    elif turb < 0.5: regime = 'Transition'
    else: regime = 'Turbulent'
    
    if regime != last_regime:
        print(f"[Step {net1.step_count:>4d}] Flow={net1.flow_drive:.3f} sigma={turb:.4f} *** {last_regime} -> {regime} ***")
        transitions1.append((net1.step_count, net1.flow_drive, turb, last_regime, regime))
        last_regime = regime

print(f"\n--- Summary ---")
print(f"Total steps: {net1.step_count}")
print(f"State transitions: {len(transitions1)}")
for i, t in enumerate(transitions1, 1):
    print(f"  Transition {i}: Step {t[0]}, Flow={t[1]:.3f}, sigma={t[2]:.4f}, {t[3]} -> {t[4]}")

# Save figure
plt.figure(figsize=(16, 10))
plt.style.use('dark_background')
fig1, axes1 = plt.subplots(2, 2, figsize=(16, 10))
fig1.suptitle('REG 1D Turbulence | Laminar -> Transition -> Turbulent', fontsize=16, fontweight='bold', color='white')
axes1[0, 0].plot(net1.positions, net1.depths, 'cyan', linewidth=1.5)
axes1[0, 0].axhline(1.0, color='gray', linestyle='--', alpha=0.5)
axes1[0, 0].set_ylim(0, 4); axes1[0, 0].set_title('Dependency Depth Profile', color='white')
axes1[0, 1].imshow(net1.history, aspect='auto', cmap='RdBu_r', vmin=0, vmax=2.5, origin='lower')
axes1[0, 1].set_title('Spatiotemporal Evolution', color='white')
plt.close()
fig1.savefig('turbulence_1d_results.png', dpi=150, bbox_inches='tight')

# ============ Script 2: Parameter Scan ============
print("\n" + "=" * 70)
print("SCRIPT 2: PARAMETER SCAN")
print("=" * 70)

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

    def increase_flow(self, increment=0.015):
        self.flow_drive = min(0.8, self.flow_drive + increment)

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

dep_strengths = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
first_vals, locked_vals = [], []
scan_results = []

print("Scanning dependence strength vs critical flow velocity...\n")
print(f"{'Dep.Strength':>12} | {'First Transition':>16} | {'Locked Turbulence':>16}")
print("-" * 50)

for ds in dep_strengths:
    net = FluidREG_Scan(n_layers=80, dep_strength=ds, seed=42)
    ft, lt = net.run(total_steps=500)
    first_vals.append(ft if ft else 0.8)
    locked_vals.append(lt if lt else 0.8)
    scan_results.append({'dep_strength': ds, 'first_transition': ft, 'locked_turbulence': lt})
    
    ft_str = f"{ft:.3f}" if ft is not None else "N/A"
    lt_str = f"{lt:.3f}" if lt is not None else "N/A"
    print(f"{ds:>12.1f} | {ft_str:>16} | {lt_str:>16}")

print("\n--- Summary ---")
for r in scan_results:
    ft_str = f"{r['first_transition']:.3f}" if r['first_transition'] is not None else "N/A"
    lt_str = f"{r['locked_turbulence']:.3f}" if r['locked_turbulence'] is not None else "N/A"
    print(f"Dep.Strength={r['dep_strength']:.1f}: First Transition={ft_str}, Locked Turbulence={lt_str}")

# Save figure
plt.figure(figsize=(10, 6))
plt.plot(dep_strengths, first_vals, 'o-', color='orange', lw=2, ms=10, label='First Transition')
plt.plot(dep_strengths, locked_vals, 's-', color='red', lw=2, ms=10, label='Locked Turbulence')
plt.xlabel('Dependence Strength')
plt.ylabel('Critical Flow Velocity')
plt.legend(); plt.grid(alpha=0.3)
plt.title('REG: Dependence Strength vs Critical Flow Velocity')
plt.tight_layout()
plt.savefig('turbulence_scan_results.png', dpi=150, bbox_inches='tight')
plt.close()

# ============ Script 3: 2D Turbulence ============
print("\n" + "=" * 70)
print("SCRIPT 3: 2D VORTEX EMERGENCE")
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
transitions2 = []

print(f"Grid: {size2}x{size2} = {size2*size2} nodes")
print(f"Initial flow_drive: {net2.flow_drive}")
print(f"Dependence strength: {net2.dep_strength}")
print("\n--- Running 400 steps ---\n")

last_regime = 'Laminar'
for frame in range(400):
    net2.step()
    if frame % 8 == 0 and frame > 0:
        net2.increase_flow(0.012)
    turb = np.std(net2.depths[1:-1,1:-1])
    if turb < 0.15: regime = 'Laminar'
    elif turb < 0.4: regime = 'Transition'
    else: regime = 'Turbulent'
    
    if regime != last_regime:
        print(f"[Step {net2.step_count:>4d}] Flow={net2.flow_drive:.3f} sigma={turb:.4f} *** {last_regime} -> {regime} ***")
        transitions2.append((net2.step_count, net2.flow_drive, turb, last_regime, regime))
        last_regime = regime

print(f"\n--- Summary ---")
print(f"Total steps: {net2.step_count}")
print(f"State transitions: {len(transitions2)}")
for i, t in enumerate(transitions2, 1):
    print(f"  Transition {i}: Step {t[0]}, Flow={t[1]:.3f}, sigma={t[2]:.4f}, {t[3]} -> {t[4]}")

# Save figure
plt.figure(figsize=(14, 12))
plt.style.use('dark_background')
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 12))
fig2.suptitle('REG 2D Turbulence | Vortex Emergence', fontsize=16, fontweight='bold', color='white')
axes2[0,0].imshow(net2.depths, cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes2[0,0].set_title('Dependency Depth (Blue=Laminar, Red=Collapse)', color='white')
axes2[0,1].imshow(np.sqrt(net2.vx**2+net2.vy**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes2[0,1].set_title('Vortex Intensity', color='white')
axes2[1,0].imshow(net2.history, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes2[1,0].set_title('Vortex Activity History', color='white')
plt.close()
fig2.savefig('turbulence_2d_results.png', dpi=150, bbox_inches='tight')

# ============ Script 4: 3D Turbulence ============
print("\n" + "=" * 70)
print("SCRIPT 4: 3D VORTEX TUBE STRUCTURE")
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
transitions3 = []

print(f"Grid: {SIZE3}x{SIZE3}x{SIZE3} = {SIZE3**3} nodes")
print(f"Initial flow_drive: {net3.flow_drive}")
print(f"Dependence strength: {net3.dep_strength}")
print("\n--- Running 400 steps ---\n")

last_regime = 'Laminar'
for frame in range(400):
    net3.step()
    if frame % 8 == 0 and frame > 0:
        net3.increase_flow(0.012)
    turb = np.std(net3.depths[1:-1,1:-1,1:-1])
    if turb < 0.15: regime = 'Laminar'
    elif turb < 0.4: regime = 'Transition'
    else: regime = 'Turbulent'
    
    if regime != last_regime:
        print(f"[Step {net3.step_count:>4d}] Flow={net3.flow_drive:.3f} sigma={turb:.4f} *** {last_regime} -> {regime} ***")
        transitions3.append((net3.step_count, net3.flow_drive, turb, last_regime, regime))
        last_regime = regime

print(f"\n--- Summary ---")
print(f"Total steps: {net3.step_count}")
print(f"State transitions: {len(transitions3)}")
for i, t in enumerate(transitions3, 1):
    print(f"  Transition {i}: Step {t[0]}, Flow={t[1]:.3f}, sigma={t[2]:.4f}, {t[3]} -> {t[4]}")

# Save figure
plt.figure(figsize=(14, 12))
plt.style.use('dark_background')
fig3, axes3 = plt.subplots(2, 2, figsize=(14, 12))
fig3.suptitle('REG 3D Turbulence | Vortex Tube Structure', fontsize=16, fontweight='bold', color='white')
mid = SIZE3 // 2
axes3[0,0].imshow(net3.depths[:,:,mid], cmap='RdBu_r', vmin=0, vmax=2, origin='lower')
axes3[0,0].set_title(f'Dependency Depth XY Slice (Z={mid})', color='white')
axes3[0,1].imshow(np.sqrt(net3.vx[:,:,mid]**2+net3.vy[:,:,mid]**2+net3.vz[:,:,mid]**2), cmap='hot', vmin=0, vmax=0.1, origin='lower')
axes3[0,1].set_title(f'Vortex Intensity XY Slice (Z={mid})', color='white')
axes3[1,0].imshow(net3.history_slice, cmap='plasma', vmin=0, vmax=3, origin='lower')
axes3[1,0].set_title('Vortex Tube History', color='white')
plt.close()
fig3.savefig('turbulence_3d_results.png', dpi=150, bbox_inches='tight')

# ============ Script 5: Multi-Fluid Comparison ============
print("\n" + "=" * 70)
print("SCRIPT 5: MULTI-FLUID COMPARISON")
print("=" * 70)

class FluidREG_Compare:
    def __init__(self, n_layers=80, dep_strength=1.0, label='Fluid', seed=42):
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

    def increase_flow(self, increment=0.01):
        self.flow_drive = min(0.8, self.flow_drive + increment)

    def run(self, total_steps=400):
        for step in range(total_steps):
            self.step()
            if step % 8 == 0 and step > 0: self.increase_flow(0.01)
            self.history.append(np.std(self.depths[1:-1]))

fluids = [
    {'label': 'Water (Low Viscosity)', 'dep_strength': 0.5, 'seed': 42},
    {'label': 'Oil (Medium Viscosity)', 'dep_strength': 1.0, 'seed': 42},
    {'label': 'Honey (High Viscosity)', 'dep_strength': 1.5, 'seed': 42},
]

print("Comparing turbulence transition in different fluids...\n")
print(f"{'Fluid Type':<30} | {'First Transition Step':>20} | {'Turbulence Lock Step':>18}")
print("-" * 75)

fluid_results = []
for fluid in fluids:
    net = FluidREG_Compare(n_layers=80, dep_strength=fluid['dep_strength'], label=fluid['label'], seed=fluid['seed'])
    net.run(total_steps=400)
    hist = np.array(net.history)
    
    first_trans_step = next((j for j, v in enumerate(hist) if v > 0.2), None)
    locked_turb_step = next((j for j, v in enumerate(hist) if v > 0.5), None)
    
    fluid_results.append({
        'label': fluid['label'],
        'dep_strength': fluid['dep_strength'],
        'first_trans_step': first_trans_step,
        'locked_turb_step': locked_turb_step
    })
    
    ft_str = str(first_trans_step) if first_trans_step is not None else "N/A"
    lt_str = str(locked_turb_step) if locked_turb_step is not None else "N/A"
    print(f"{fluid['label']:<30} | {ft_str:>20} | {lt_str:>18}")

print("\n--- Summary ---")
for r in fluid_results:
    ft_str = str(r['first_trans_step']) if r['first_trans_step'] is not None else "N/A"
    lt_str = str(r['locked_turb_step']) if r['locked_turb_step'] is not None else "N/A"
    print(f"{r['label']}: First Transition Step={ft_str}, Turbulence Lock Step={lt_str}")

# Save figure
plt.figure(figsize=(14, 6))
colors = ['blue', 'orange', 'red']
for fluid, r in zip(fluids, fluid_results):
    net = FluidREG_Compare(n_layers=80, dep_strength=fluid['dep_strength'], label=fluid['label'], seed=fluid['seed'])
    net.run(total_steps=400)
    plt.plot(net.history, color=colors[len(fluid_results)-1-fluid_results.index(r)], linewidth=2, label=fluid['label'])

plt.axhline(0.2, color='gray', linestyle='--', alpha=0.5, label='Transition Threshold')
plt.axhline(0.5, color='black', linestyle='--', alpha=0.5, label='Turbulence Threshold')
plt.xlabel('Time Step', fontsize=13)
plt.ylabel('Turbulence Intensity', fontsize=13)
plt.title('REG: Turbulence Transition Comparison for Different Fluids', fontsize=14, fontweight='bold')
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fluid_comparison_results.png', dpi=150, bbox_inches='tight')
plt.close()

# ============ Final Summary ============
print("\n" + "=" * 70)
print("ALL SIMULATIONS COMPLETE!")
print("=" * 70)
print("\nGenerated files:")
for f in ['turbulence_1d_results.png', 'turbulence_scan_results.png', 
          'turbulence_2d_results.png', 'turbulence_3d_results.png', 
          'fluid_comparison_results.png']:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f"  [OK] {f} ({size:.1f} KB)")

print("\nLogs saved to: simulation_logs.txt")
print("\n" + "=" * 70)
print("LOG SUMMARY")
print("=" * 70)
print(f"\n1D Turbulence: {len(transitions1)} state transitions")
print(f"Parameter Scan: {len(scan_results)} data points")
print(f"2D Turbulence: {len(transitions2)} state transitions")
print(f"3D Turbulence: {len(transitions3)} state transitions")
print(f"Multi-Fluid: {len(fluid_results)} fluids compared")

logger.close()
