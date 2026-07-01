import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

xi = 0.5
M_P = 2.435e18  # GeV, 仅用于标度，不影响 gamma-1 的形状
Phi = np.logspace(15, 20, 500)  # 从 GUT 尺度到普朗克尺度
x = Phi / M_P

# gamma-1 近似公式
gamma_minus_1 = -4 * xi**2 * x**2

plt.figure(figsize=(8, 5))
plt.loglog(Phi, np.abs(gamma_minus_1), 'b-', linewidth=2)
plt.axhline(2.3e-5, color='red', linestyle='--', label='Cassini bound (2.3e-5)')
plt.xlabel('Scalar field Phi (GeV)')
plt.ylabel('|gamma - 1|')
plt.title('Post-Newtonian deviation vs scalar field')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('post_newtonian_gamma.png', dpi=150, bbox_inches='tight')
print("Figure saved to post_newtonian_gamma.png")
plt.close('all')
