import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# 理论预测
n_s_pred = 0.967
r_pred = 0.0044

# Planck 2018 约束椭圆 (近似: 中心, 宽度, 相关系数)
ellipse_center = [0.9649, 0.0]
ellipse_width = 0.0042 * 2   # 1σ 宽度
ellipse_height = 0.02        # r 的 1σ 上界

ellipse = Ellipse(
    ellipse_center,
    ellipse_width,
    ellipse_height,
    edgecolor='darkblue',
    facecolor='lightblue',
    alpha=0.5,
    linewidth=2,
)

fig, ax = plt.subplots(figsize=(8, 6))
ax.add_patch(ellipse)
ax.plot(n_s_pred, r_pred, 'r*', markersize=20, markeredgecolor='darkred', label='Our theory')
ax.axhline(0.036, color='gray', linestyle='--', label='BICEP/Keck 95% upper limit (r<0.036)')
ax.set_xlabel('Spectral index n_s')
ax.set_ylabel('Tensor-to-scalar ratio r')
ax.set_xlim(0.94, 0.98)
ax.set_ylim(-0.01, 0.12)
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_title('Planck 2018 constraints + our prediction')
plt.tight_layout()
plt.savefig('inflation_ns_r.png', dpi=150, bbox_inches='tight')
print("Figure saved to inflation_ns_r.png")
plt.close('all')
