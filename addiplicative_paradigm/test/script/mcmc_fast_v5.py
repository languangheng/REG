"""
MCMC v5: REG Cosmological Fitting  (Pantheon+ SNe + Planck CMB)
Relational Emergent Gravity: w(z) = w0 + wa*z/(1+z) parameter estimation
Grid-accelerated MCMC: bilinear interpolation on precomputed 40x40 w0-wa grid
"""
import numpy as np
from scipy.integrate import quad
import emcee
import corner
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time, os, sys

BASE = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test"
OUT = os.path.join(BASE, 'out')
os.makedirs(OUT, exist_ok=True)
os.chdir(BASE)

# ======================================================================
# 1. Load Pantheon+ data
# ======================================================================
fname = os.path.join(BASE, "pantheon_data.txt")
z_list, mu_list, mu_err_list = [], [], []
with open(fname, 'r') as f:
    f.readline()
    for line in f:
        parts = line.strip().split()
        if len(parts) < 12: continue
        try:
            z = float(parts[2])
            if z <= 0: z = float(parts[4])
            if z <= 0: z = float(parts[6])
            if z <= 0: continue
            mu = float(parts[10]); mu_err = float(parts[11])
            if mu > 0 and mu_err > 0:
                z_list.append(z); mu_list.append(mu); mu_err_list.append(mu_err)
        except: continue

Z_SN   = np.array(z_list, dtype=np.float64)
MU_OBS = np.array(mu_list, dtype=np.float64)
MU_ERR = np.array(mu_err_list, dtype=np.float64)
N_SN   = len(Z_SN)
N_WALKERS, N_STEPS, NDIM = 64, 6000, 5

print("=" * 60)
print("  Pantheon+ SNe + Planck CMB MCMC  (v5)")
print("=" * 60)
print(f"  Pantheon+ SNe: {N_SN}  |  z=[{Z_SN.min():.4f}, {Z_SN.max():.4f}]")
print(f"  Walkers={N_WALKERS}, Steps={N_STEPS}, Dim={NDIM}")
print("")

# ======================================================================
# 2. Pre-compute grid: mu(z_n, w0_i, wa_j)
# ======================================================================
c_km_s = 299792.458
OM_REF, H0_REF = 0.30, 70.0

print("[Grid] Building distance-modulus lookup table...")
t0 = time.time()

W0_GRID = np.linspace(-1.8, 0.0, 40)
WA_GRID  = np.linspace(-2.5, 2.5, 40)
N_W0, N_WA = len(W0_GRID), len(WA_GRID)
dw0 = W0_GRID[1] - W0_GRID[0]
dwa = WA_GRID[1] - WA_GRID[0]

def Hz(z, w0, wa):
    ODE = 1.0 - OM_REF
    f   = (1+z)**(3*(1+w0+wa)) * np.exp(-3*wa*z/(1+z))
    return H0_REF * np.sqrt(OM_REF*(1+z)**3 + ODE*f)

def dL(z, w0, wa):
    return (1+z) * quad(lambda x: c_km_s/Hz(x,w0,wa), 0, z, limit=30)[0]

MU_GRID = np.zeros((N_SN, N_W0, N_WA), dtype=np.float64)
for i, w0 in enumerate(W0_GRID):
    if (i+1) % 10 == 0 or i == 0: print(f"  w0: {i+1}/{N_W0}")
    for j, wa in enumerate(WA_GRID):
        for n, zn in enumerate(Z_SN):
            try:
                dl = dL(zn, w0, wa)
                MU_GRID[n,i,j] = 5.0*np.log10(max(dl,1e-10))+25.0 if dl>0 else np.nan
            except:
                MU_GRID[n,i,j] = np.nan

for n in range(N_SN):
    col = MU_GRID[n]; valid = np.isfinite(col)
    if valid.any(): col[~valid] = np.mean(col[valid])
    else: col[:] = 0.0

print(f"[Grid] Done in {time.time()-t0:.1f}s  shape={MU_GRID.shape}")
print("")

# ======================================================================
# 3. Bilinear interpolation
# ======================================================================
def interp_mu_vectorized(w0_arr, wa_arr):
    n_w = len(w0_arr)
    mu_all = np.zeros((n_w, N_SN), dtype=np.float64)
    for k in range(n_w):
        w0, wa = w0_arr[k], wa_arr[k]
        i0 = int((w0 - W0_GRID[0]) / dw0); j0 = int((wa - WA_GRID[0]) / dwa)
        i0 = np.clip(i0, 0, N_W0-2); j0 = np.clip(j0, 0, N_WA-2)
        i1, j1 = i0+1, j0+1
        tx = np.clip((w0 - W0_GRID[i0])/max(W0_GRID[i1]-W0_GRID[i0],1e-10), 0, 1)
        ty = np.clip((wa - WA_GRID[j0])/max(WA_GRID[j1]-WA_GRID[j0],1e-10), 0, 1)
        mu_all[k] = (
            (1-tx)*(1-ty)*MU_GRID[:,i0,j0] + tx*(1-ty)*MU_GRID[:,i1,j0] +
            (1-tx)*ty   *MU_GRID[:,i0,j1] + tx*ty   *MU_GRID[:,i1,j1])
    return mu_all

# ======================================================================
# 4. Likelihood
# ======================================================================
PLANCK_OMH2     = 0.1430
PLANCK_OMH2_ERR = 0.0011

def log_likelihood(params):
    params = np.atleast_2d(params)
    n_w = params.shape[0]
    w0_arr = params[:,0]; wa_arr = params[:,1]
    Om_arr = params[:,2]; H0_arr = params[:,3]; M0_arr = params[:,4]

    valid = (
        (w0_arr>-2.0)&(w0_arr<0.0) &
        (wa_arr>-3.0)&(wa_arr<3.0) &
        (Om_arr>0.20)&(Om_arr<0.50) &
        (H0_arr>60.0)&(H0_arr<80.0) &
        (M0_arr>-0.30)&(M0_arr<0.10)
    )
    if not np.any(valid): return np.full(n_w, -np.inf)

    mu_all = interp_mu_vectorized(w0_arr, wa_arr)
    corrections = M0_arr.reshape(-1,1) + 5.0*np.log10(H0_arr.reshape(-1,1)/H0_REF)
    mu_all = mu_all + corrections
    invalid = np.any(~np.isfinite(mu_all), axis=1)
    valid[invalid] = False

    chi2_sn  = np.full(n_w, np.inf)
    chi2_cmb = np.full(n_w, 0.0)
    for k in range(n_w):
        if not valid[k]: continue
        chi2_sn[k]  = np.sum(((MU_OBS - mu_all[k])/MU_ERR)**2)
        chi2_cmb[k] = ((Om_arr[k]*(H0_arr[k]/100.0)**2 - PLANCK_OMH2)/PLANCK_OMH2_ERR)**2

    log_like = -0.5*(chi2_sn + chi2_cmb)
    log_like[~valid] = -np.inf
    return log_like if n_w > 1 else log_like[0]

def log_prob(params):
    lp = log_likelihood(params)
    return lp if np.isfinite(lp) else -np.inf

# ======================================================================
# 5. Run MCMC
# ======================================================================
def main():
    print("[MCMC] Starting...")
    print(f"  Walkers={N_WALKERS}, Steps={N_STEPS}, Dim={NDIM}")
    print(f"  Single-process mode (Windows compatible)")
    print(f"  Expected: ~25-40 min")
    print("")

    # Fixed sigma per parameter
    init = np.array([-0.89, 0.00, 0.306, 68.3, -0.14])
    init_sigma = np.array([0.03, 0.30, 0.010, 1.0, 0.01])
    pos = init + init_sigma * np.random.randn(N_WALKERS, NDIM)

    t_start = time.time()
    sampler = emcee.EnsembleSampler(N_WALKERS, NDIM, log_prob)
    sampler.run_mcmc(pos, N_STEPS, progress=True, skip_initial_state_check=True)
    elapsed = time.time() - t_start

    print(f"\n[MCMC] Done! {elapsed:.0f}s  ({elapsed/60:.1f} min)")

    # ==================================================================
    # 6. Results
    # ==================================================================
    BURN = 1000
    samples = sampler.get_chain(discard=BURN, flat=True)
    LABELS = [r'$w_0$', r'$w_a$', r'$\Omega_m$', r'$H_0$', r'$M_0$']

    print("")
    print("=" * 60)
    print("  POSTERIOR STATISTICS (68% C.L.)")
    print("=" * 60)
    for i, lbl in enumerate(LABELS):
        med = np.median(samples[:, i])
        lo, hi = np.percentile(samples[:, i], [16, 84])
        print(f"  {lbl:>8s}:  {med:+.4f}  [{lo:+.4f}, {hi:+.4f}]")

    w0_lo, w0_hi = np.percentile(samples[:,0], [16, 84])
    wa_lo, wa_hi = np.percentile(samples[:,1], [16, 84])
    w0_med = np.median(samples[:,0])
    wa_med = np.median(samples[:,1])

    print("")
    print("=" * 60)
    print("  THEORY CHECK")
    print("=" * 60)
    w0_ok = "TRUE " if (w0_lo <= -0.98 <= w0_hi) else "FALSE"
    wa_ok = "TRUE " if (wa_lo <= 0.02  <= wa_hi) else "FALSE"
    print(f"  w0 = -0.98 in 68% C.L.?  {w0_ok}  [{w0_lo:.4f}, {w0_hi:.4f}]")
    print(f"  wa = +0.02 in 68% C.L.?  {wa_ok}  [{wa_lo:.4f}, {wa_hi:.4f}]")

    # ==================================================================
    # 7. Plots
    # ==================================================================
    print("")
    print("[Plot] Generating figures...")

    fig = corner.corner(samples[:,:2],
        labels=[r'$w_0$', r'$w_a$'], truths=[-0.98, 0.02],
        quantiles=[0.16, 0.5, 0.84], show_titles=True,
        title_kwargs={"fontsize": 11})
    fig.suptitle("REG DE MCMC: $w_0$ vs $w_a$ Posterior\n"
                 "Pantheon+ SNe + Planck 2018 Prior",
                 fontsize=13, fontweight='bold', y=1.02)
    fig.savefig(os.path.join(OUT, 'fig10_mcmc_corner_w0_wa.png'), dpi=150, bbox_inches='tight')
    print("  Saved: fig10_mcmc_corner_w0_wa.png"); plt.close()

    fig2 = corner.corner(samples, labels=LABELS,
        quantiles=[0.16, 0.5, 0.84], show_titles=True,
        title_kwargs={"fontsize": 9})
    fig2.suptitle("REG DE MCMC: All Parameters\nPantheon+ + Planck 2018",
        fontsize=12, fontweight='bold')
    fig2.savefig(os.path.join(OUT, 'fig11_mcmc_corner_all.png'), dpi=150, bbox_inches='tight')
    print("  Saved: fig11_mcmc_corner_all.png"); plt.close()

    z_fine = np.linspace(0.001, 2.3, 200)
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    ax3.fill_between(z_fine,
        w0_lo+wa_lo*z_fine/(1+z_fine),
        w0_hi+wa_hi*z_fine/(1+z_fine),
        alpha=0.25, color='steelblue', label='68% C.L.')
    ax3.plot(z_fine, w0_med+wa_med*z_fine/(1+z_fine),
        'steelblue', lw=2.5, label='Best-fit: w0={:.2f}, wa={:.2f}'.format(w0_med, wa_med))
    ax3.axhline(-1.0, color='green', lw=1.5, ls='--', label='Lambda-CDM (w=-1)')
    ax3.axhline(-0.98, color='red', lw=1.5, ls=':', label='Theory: w0=-0.98')
    ax3.scatter([0],[-0.98], color='red', s=60, zorder=5)
    ax3.set_xlabel('Redshift z', fontsize=12)
    ax3.set_ylabel('Dark Energy EoS w(z)', fontsize=12)
    ax3.set_title("REG DE: w(z) Evolution  (Pantheon+ + Planck 2018)",
        fontsize=13, fontweight='bold')
    ax3.legend(fontsize=9); ax3.grid(alpha=0.3)
    ax3.set_xlim(0, 2.3); ax3.set_ylim(-1.5, -0.5)
    plt.tight_layout()
    fig3.savefig(os.path.join(OUT, 'fig13_mcmc_wz_evolution.png'), dpi=150, bbox_inches='tight')
    print("  Saved: fig13_mcmc_wz_evolution.png"); plt.close()

    print("")
    print("=" * 60)
    print("  ALL DONE!")
    print(f"  Total time: {elapsed:.0f}s  ({elapsed/60:.1f} min)")
    print("=" * 60)

if __name__ == '__main__':
    main()
