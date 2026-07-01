# Scripts | 脚本说明

This directory contains the core analysis scripts for the Relational Emergent Gravity (REG) framework.

## Scripts

| Script | Description |
|:-------|:------------|
| `brn_simulation.py` | Binary Relation Network (BRN) Monte Carlo simulation in 2D and 3D geometries |
| `mcmc_analysis.py` | Joint MCMC analysis: Pantheon+ SNe + Planck CMB compressed priors |
| `bao_analysis.py` | eBOSS DR16 BAO distance ratio comparison: REG vs ΛCDM |
| `ligo_echo_search.py` | LIGO O4c gravitational wave echo matched-filter search |
| `inflation_calc.py` | ξ-attractor inflation predictions: n_s and r |
| `post_newtonian_constraints.py` | Chameleon screening mechanism and Cassini constraint |
| `download_pantheon.py` | Download Pantheon+ SH0ES Type Ia supernova dataset |

## Quick Start

```bash
# 1. Install dependencies
pip install numpy scipy matplotlib emcee corner tqdm

# 2. Download Pantheon+ data (requires ~5MB download)
python download_pantheon.py

# 3. Run BRN simulation (~5-10 minutes)
python brn_simulation.py

# 4. Run MCMC analysis (~10-30 minutes)
python mcmc_analysis.py

# 5. Run BAO comparison (~1 minute)
python bao_analysis.py
```

## Data Requirements

- `Pantheon+SH0ES.dat` — Pantheon+ Type Ia supernova data (~1700 SNe)
- Download from: https://github.com/dscolnic/Pantheon
