"""
BAO Distance-Ratio Analysis: REG vs Lambda-CDM vs Observations
Data: Alam et al. (2021), MNRAS 505, 767, Table 2 (eBOSS DR16)
"""
import numpy as np
from scipy.integrate import quad
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(SCRIPT_DIR), 'out')
os.makedirs(OUT, exist_ok=True)

c   = 299792.458
rd  = 147.09
H0  = 67.4

def Ez(z, w0, wa, Om):
    ODE = 1.0 - Om
    return np.sqrt(Om*(1+z)**3 + ODE*(1+z)**(3*(1+w0+wa))*np.exp(-3*wa*z/(1+z)))

def DVrd(z, w0, wa, Om, H0):
    integral = quad(lambda x: 1.0/Ez(x,w0,wa,Om), 0.0, z, limit=50)[0]
    dL = (1+z) * (c/H0) * integral
    dA = dL / (1+z)**2
    return (z * dA**2 * c / (H0*Ez(z,w0,wa,Om)))**(1.0/3.0) / rd

bao_z   = np.array([0.38, 0.51, 0.61, 0.70, 0.85, 1.48, 2.33])
obs     = np.array([13.52, 18.33, 22.11, 25.11, 29.78, 39.18, 49.53])
err     = np.array([0.32,  0.41,  0.53,  0.61,  0.72,  0.81,  1.04])
tracers = ['LowZ', 'CMASS', 'BOSS', 'LRG', 'QSO', 'eBOSS', 'LyA']

# REG (Relational Emergent Gravity): w0=-0.98, wa=+0.02
OM_REG = 0.306;   W0_REG = -0.98; WA_REG = 0.02
# Lambda-CDM: w = -1
OM_LCD = 0.315;   W0_LCD = -1.00; WA_LCD = 0.00

dvd_reg = np.array([DVrd(z, W0_REG, WA_REG, OM_REG, H0) for z in bao_z])
dvd_lcd = np.array([DVrd(z, W0_LCD, WA_LCD, OM_LCD, H0) for z in bao_z])

chi2_reg = np.sum(((obs - dvd_reg) / err)**2)
chi2_lcd = np.sum(((obs - dvd_lcd) / err)**2)
n_pts = len(bao_z)

print("=" * 65)
print("  BAO Distance-Ratio: REG vs Lambda-CDM vs SDSS/eBOSS")
print("  Data: Alam et al. (2021), MNRAS 505, 767, Table 2")
print("=" * 65)
print()
print(f"  {'z':>5}  {'Tracer':<8}  {'Observed':>9}  {'REG':>8}  {'LCDM':>8}")
print("  " + "-" * 48)
for i in range(n_pts):
    print(f"  {bao_z[i]:5.2f}  {tracers[i]:<8}  {obs[i]:6.2f} +/- {err[i]:4.2f}  "
          f"{dvd_reg[i]:6.2f}  {dvd_lcd[i]:6.2f}")
print()
print(f"  REG (w0={W0_REG}, wa={WA_REG}, Om={OM_REG}):  chi2/dof = {chi2_reg:.2f}/{n_pts}")
print(f"  Lambda-CDM (w=-1, Om={OM_LCD}):                chi2/dof = {chi2_lcd:.2f}/{n_pts}")
print(f"  Delta chi2  = {chi2_reg - chi2_lcd:.2f}  (REG - LCDM)")
print(f"  npts = {n_pts}")
print()

# Figure
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("BAO Distance Ratio: REG vs Lambda-CDM\n"
             "SDSS/eBOSS Observations (Alam et al. 2021)",
             fontsize=12, fontweight='bold')

axes[0].errorbar(bao_z, obs, yerr=err, fmt='ko', ms=7, capsize=4,
                  label='SDSS/eBOSS (observed)', zorder=5)
axes[0].plot(bao_z, dvd_reg, 'rs--', ms=6, lw=1.8,
             label='REG (w0=-0.98, wa=+0.02)')
axes[0].plot(bao_z, dvd_lcd, 'b^--', ms=6, lw=1.8,
             label=r'$\Lambda$CDM (w=-1)')
axes[0].set_xlabel('Redshift z', fontsize=11)
axes[0].set_ylabel(r'$D_V(z)/r_d$', fontsize=11)
axes[0].set_title('(a) Distance Ratio Comparison', fontsize=10)
axes[0].legend(fontsize=9); axes[0].grid(alpha=0.3)

axes[1].bar(np.arange(n_pts)-0.2, obs-dvd_lcd, width=0.4,
             color='steelblue', alpha=0.7, label=r'$\Lambda$CDM residual')
axes[1].bar(np.arange(n_pts)+0.2, obs-dvd_reg, width=0.4,
             color='coral', alpha=0.7, label='REG residual')
axes[1].axhline(0, color='black', lw=0.8)
axes[1].set_xticks(np.arange(n_pts))
axes[1].set_xticklabels([f'z={bao_z[i]:.2f}' for i in range(n_pts)],
                         rotation=30, ha='right', fontsize=8)
axes[1].set_xlabel('Redshift', fontsize=11)
axes[1].set_ylabel(r'Observed - Theory  $[D_V/r_d]$', fontsize=11)
axes[1].set_title('(b) Residuals: Observed minus Theory', fontsize=10)
axes[1].legend(fontsize=9); axes[1].grid(alpha=0.3, axis='y')

plt.tight_layout()
out_path = os.path.join(OUT, 'fig5_bao_comparison.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"  Saved: fig5_bao_comparison.png")
plt.close()

print("=" * 65)
delta = chi2_reg - chi2_lcd
if delta < 0:
    print(f"  REG is PREFERRED by BAO data (Delta chi2 = {delta:.2f})")
else:
    print(f"  Lambda-CDM is PREFERRED by BAO data (Delta chi2 = {abs(delta):.2f})")
print("=" * 65)
