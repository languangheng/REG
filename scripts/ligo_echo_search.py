import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

t = np.linspace(0, 0.1, 10000)
f = 75  # Hz
tau = 0.05  # 衰减时间
main_signal = np.sin(2 * np.pi * 150 * t) * np.exp(-t / 0.02)  # 主并合信号
echo = 0.3 * np.sin(2 * np.pi * f * (t - 0.04)) * np.exp(-(t - 0.04) / tau)
echo[t < 0.04] = 0
signal = main_signal + echo

plt.figure(figsize=(10, 4))
plt.plot(t, signal, 'k-', linewidth=0.5)
plt.axvline(0.04, color='red', linestyle='--', label='Echo start')
plt.xlabel('Time (s)')
plt.ylabel('Strain')
plt.title('Gravitational wave with echo (conceptual)')
plt.legend()
plt.tight_layout()
plt.savefig('gw_echo.png', dpi=150, bbox_inches='tight')
print("Figure saved to gw_echo.png")
plt.close('all')
