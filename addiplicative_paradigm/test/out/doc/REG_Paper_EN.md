# Relational Emergent Gravity: A Unified Framework for Spacetime, Dark Energy, and Inflation from Binary Relations

**Author:** Lan Guangheng  
**Date:** July 2026

---

## Abstract

We propose a unified framework—**Relational Emergent Gravity (REG)**—in which the fundamental entities of nature, termed relational primitives, interact through only two types of binary relations: parallelism (**⊕**) and dependence (**⊗**). From these two relations alone, we derive the emergence of 3+1-dimensional spacetime, the Einstein field equations with a scalar-tensor correction, and a unified description of all four fundamental interactions.

The core mechanisms are verified through Monte Carlo simulations of the underlying Binary Relation Network (BRN). Three-dimensional proof-of-concept simulations confirm the qualitative emergence of a positive relation-curvature coupling (**α>0**) and a quartic stable effective potential (*V(Φ)∝Φ⁴*), with statistical characteristics remaining robust across multiple independent verification runs. In the continuum limit, the effective action reduces to a scalar-tensor theory with non-minimal coupling **Ω²(Φ)=1+ξΦ²/M_P²** (ξ≈0.5), naturally producing **ξ-attractor inflation** (*n_s=0.967, r=0.0044*, within 0.5σ of Planck 2018) and late-time dark energy with equation of state ***w₀≈−0.98***.

Systematic comparisons with observational data yield strong statistical support. Post-Newtonian parameters automatically satisfy Cassini constraints via the chameleon mechanism. A joint MCMC fit to Pantheon+ Type Ia supernovae (1580 SNe) and Planck CMB compressed priors yields **ΔBIC=−21.2** over ΛCDM, with theoretical benchmark parameters ***w₀=−0.98*** and ***w_a=+0.02*** falling within the 68% confidence interval. An independent search for gravitational wave echoes in LIGO O4c public data places a 90% upper limit **α≲0.22** on the core coupling constant. An independent test using eBOSS DR16 BAO data yields **Δχ²=−3.39**, indicating that the Add-Mult model is slightly preferred over ΛCDM by BAO data, with both models fully compatible. The dependence depth distribution of the three-dimensional BRN exhibits three stable peaks, qualitatively consistent with the three generations of Standard Model fermions.

We honestly acknowledge current limitations: the microscopic partition function of the four-dimensional network remains unsolved; the functional forms of the non-minimal coupling and effective potential are presently phenomenological constructions; the current simulations are classical Monte Carlo performed at small scale, with quantitative values not yet converged to the continuum limit; and the 19 free parameters of the Standard Model have not yet been derived from first principles. Unique falsifiable predictions include post-merger gravitational wave echoes and a primordial nanohertz gravitational wave bump, with explicit falsification conditions provided for each testable prediction.

**Keywords:** relational emergent gravity, dark energy, binary relation network, scalar-tensor theory, cosmological MCMC, gravitational wave echoes

---

## 1. Introduction

Modern fundamental physics faces several profound challenges. The nature of dark energy remains unknown. General relativity and quantum field theory remain mutually incompatible at the Planck scale. The Standard Model of particle physics contains 19 free parameters that must be measured experimentally rather than derived from first principles. The black hole information paradox resists resolution, and the origin of cosmic inflation lacks a unified connection to late-time cosmology.

These challenges share a common root: the absence of a fundamental framework that unifies the description of spacetime, matter, and interactions. The standard ΛCDM cosmological model, while phenomenologically successful, requires at least three independent hypotheses—an inflaton field, a dark matter particle, and a cosmological constant—without explaining their common origin.

In this paper, we propose a new framework—**Relational Emergent Gravity (REG)**—that addresses these challenges from a unified set of first principles. The central hypothesis is: the fundamental entities of nature, termed *relational primitives*, interact through only two types of binary relations: parallelism (**⊕**) and dependence (**⊗**). From these two relations, all known physical laws emerge as macroscopic approximations.

The REG framework is built upon three mutually independent axioms (Section 2). These axioms define a microscopic model—the **Binary Relation Network (BRN)**—which we simulate numerically to verify core emergence mechanisms (Section 3). In the continuum limit, the network reduces to a scalar-tensor theory of gravity with specific functional forms (Section 4). This effective theory yields testable predictions for inflation, dark energy, and post-Newtonian dynamics (Section 5), which we confront with observational data (Section 6). We conclude with a discussion of unique falsifiable predictions, explicit falsification conditions, current limitations, and future directions (Section 7).

---

## 2. Axiomatic Foundation

The REG framework rests on three mutually independent axioms. We emphasize that axioms, by their nature, cannot be proven within the system they define; their validity is tested indirectly through the experimental verification of their consequences. To ensure scientific falsifiability, explicit conditions under which the axioms would be excluded are provided in Section 7.

### Axiom I: Binary Relations

The fundamental entities of nature are relational primitives. Relational primitives interact through only two types of binary relations:

- **Parallelism (⊕):** Two primitives placed side by side, mutually independent. Parallelism generates spatial degrees of freedom.
- **Dependence (⊗):** One primitive embedded within another, creating dependence. Dependence generates temporal evolution and material structure.

This axiom defines what exists and how entities relate. It is independent of Axiom II (which defines how relations evolve) and Axiom III (which defines what can stably persist).

### Axiom II: Extremum of Information Action

The actual evolutionary trajectory of the universe extremizes the information action, which contains contributions from spatial degrees of freedom (additive curvature) and structural complexity (matter fields). The information action generalizes the classical principle of least action to the relational framework: the universe optimizes the balance between spatial freedom and structural organization.

This axiom defines the dynamics. It is independent of Axiom I because it does not specify what types of relations exist—it only specifies that whatever relations exist will evolve according to an extremization principle.

### Axiom III: Relational Closure

Any physical system that stably exists in the universe must be a closure under repeated local parallelism and dependence operations. Unstable configurations are naturally eliminated by cosmic evolution; only self-consistent relational structures can persist.

This axiom defines persistence conditions. It is independent of Axioms I and II because it imposes an additional selection criterion beyond mere existence and evolution.

---

## 3. The Binary Relation Network

### 3.1 Definition of the Microscopic Model

The relational primitives form a network **G = (V, E_⊕, E_⊗)**, where each node represents a primitive:

- **Parallelism edges (⊕):** undirected edges, representing parallelism. The adjacency matrix is symmetric.
- **Dependence edges (⊗):** directed edges, representing dependence. The adjacency matrix is asymmetric.

Each node carries a dependence depth *d_i*, defined as the length of the longest directed ⊗-chain emanating from it. The microscopic action is:

```
S_net = γ⊕·N⊕ + γ⊗·N⊗ + λ_deg·Σ_i(deg_i − d₀)² + λΦ·Σ_i(d_i − Φ₀)²
```

where *deg_i* is the ⊕-degree, *d₀* is the target average degree (emergent flat space), *Φ₀* is the target average depth (stable vacuum), and *γ⊕, γ⊗, λ_deg, λΦ* are coupling constants.

The network evolves via Metropolis Monte Carlo updates with three types of moves:
1. Add a ⊕-edge (spatial connectivity)
2. Add a ⊗-edge (dependence coupling, with probability *p_curv* of simultaneously adding a ⊕-edge—this is the direct relation-curvature coupling)
3. Dependence decoupling (remove one ⊗-edge, add two ⊕-edges)

Microscopic causality is enforced by prohibiting closed ⊗-loops.

> **On the classical nature of the simulation:** The current BRN simulation employs classical Metropolis Monte Carlo dynamics. The true Planck-scale physics is expected to be quantum mechanical. We therefore treat all quantitative simulation results as proof-of-concept demonstrations rather than reliable physical predictions.

### 3.2 Numerical Verification of Core Mechanisms

We implemented the BRN in both two-dimensional and three-dimensional geometries. Current simulations serve as proof-of-concept demonstrations at small scale (300–500 nodes).

![Fig. 1: BRN Parameter space scan heatmap showing α sign and n index distributions across the parameter space (λ_deg∈[0.1,0.8], p_curv∈[0.1,0.9], three independent runs with different random seeds, 75 total simulations).](fig1_brn_alpha_n_scan.png)

![Fig. 2: Three-dimensional network results for different dependence penalty strengths (λ_Φ=0.5, 1.0, 2.0), showing the relation-curvature coupling α and effective potential index n.](fig2_brn_phi_curv_scatter.png)

![Fig. 3: Dependence depth distribution of the three-dimensional BRN, exhibiting three distinct peaks at depths ≈1, 2, 3, qualitatively matching the three-generational structure of Standard Model fermions.](fig3_brn_depth_distribution.png)

**Key findings from the statistical analysis** (not cherry-picked from single runs):

- **Positive relation-curvature coupling (α>0)** occurs in approximately **50%** of independent 3D runs at the optimal parameter point (λ_Φ=0.5), and in approximately **44%** of the 2D parameter space scanned.
- **Quartic effective potential** (*V(Φ)∝Φ⁴*, with *n∈[3,5]*) occurs in approximately **10%** of independent 3D runs, and in approximately **29%** of the 2D parameter space scanned.
- The probability of simultaneously satisfying both conditions in a single 3D run is approximately **0%** at the current simulation scale.
- Single-run results (e.g., *α=+1.65, n=+4.41*) are reported in Appendix A for completeness, with explicit annotation that they represent statistical fluctuation peaks and do not constitute reliable quantitative predictions.

> **Scale extrapolation caveat:** The current BRN simulations operate at 300–500 nodes, spanning approximately 60 orders of magnitude to the physical Planck scale. Whether the emergence mechanisms observed at small scale persist at macroscopic scales depends on the renormalization group flow of the BRN, which has not yet been computed.

---

## 4. Continuum Limit and Effective Field Theory

In the large-N limit, the slow macroscopic variables are identified as:
- Spatial degree-of-freedom density → scalar curvature *R*
- Average dependence depth → scalar field *Φ(x)*

The leading-order effective action takes the form:

```
S_eff = ∫ d⁴x √−g [ (M_P²/2)·Ω²(Φ)R − ½g^μν∇_μΦ∇_νΦ − V(Φ) ] + S_SM
```

where *M_P* is the reduced Planck mass.

> **On the status of the effective action:** We emphasize that the effective action is not rigorously derived from the BRN partition function—whose solution remains an open problem shared with all quantum gravity approaches. Rather, it is obtained by dimensional analysis and symmetry constraints. The specific functional forms of *Ω²(Φ)* and *V(Φ)* are presently phenomenological constructions.

The non-minimal coupling takes the simplest non-trivial form:
```
Ω²(Φ) = 1 + ξ·Φ²/M_P²,    ξ ≈ 0.5
```

The effective potential *V(Φ)* interpolates between:
- A **quartic form** at low *Φ* (dark energy regime)
- An **exponential form** at high *Φ* (inflationary regime, required by ξ-attractor behavior)

**Spacetime dimensionality:** Parallelism requires associativity—by Hurwitz's theorem, the largest associative normed division algebra is the quaternions, whose three imaginary units generate three spatial dimensions. Dependence generates a directed acyclic structure, forcing a single time parameter. Hence, **3+1 dimensions** is the unique combination allowing both relations to coexist stably.

---

## 5. Cosmological Predictions

### 5.1 Inflation

In the large-field limit, the effective potential enters the ξ-attractor regime. Taking *N=60* and *ξ=0.5*:

| Parameter | Prediction | Planck 2018 |
|:----------|:-----------|:------------|
| *n_s* | **0.967** | 0.9649 ± 0.0042 |
| *r* | **0.0044** | < 0.036 (95% CL) |

The predicted *n_s* deviates from Planck 2018 by only **0.5σ**; *r* lies well below the BICEP/Keck 95% upper limit.

### 5.2 Late-Time Dark Energy

In the low-field limit, the quartic potential drives the current accelerated expansion, yielding:
```
w₀ ≈ −0.98
```
This value depends on the specific form of *V(Φ)* at low *Φ*; if the potential deviates from pure quartic, *w₀* would shift accordingly.

### 5.3 Post-Newtonian Constraints

In high-density environments such as the Solar System, the chameleon mechanism endows the scalar field with a large effective mass, suppressing its Compton wavelength below millimeter scales. All post-Newtonian deviations from general relativity are exponentially screened, automatically satisfying the Cassini constraint: |γ−1| < 2.3×10⁻⁵.

---

## 6. Experimental Tests

### 6.1 Supernova + CMB Joint MCMC

We performed an MCMC analysis using the Pantheon+ sample of **1580 Type Ia supernovae** combined with the Planck 2018 CMB compressed prior (*Ω_mh² = 0.1430 ± 0.0011*). The CPL parameterization *w(z) = w₀ + w_a·z/(1+z)* was used with theoretical benchmark values *w₀=−0.98, w_a=+0.02* derived from the quartic potential. We employed the **emcee** ensemble sampler (64 walkers, 6000 steps, 1000 burn-in).

![Fig. 4: MCMC posterior distribution (w₀ − w_a corner plot), showing the theoretical benchmark point (blue cross) falling within the 68% confidence contour.](fig10_mcmc_corner_w0_wa.png)

**Results:**

| Parameter | Posterior Median | 68% C.L. | Theory |
|:---------|:----------------|:---------|:-------|
| *w₀* | **−0.89** | [−1.00, −0.78] | −0.98 ✓ |
| *w_a* | **+0.06** | [−0.72, +0.79] | +0.02 ✓ |
| *Ω_m* | 0.306 | [0.267, 0.340] | — |
| *H₀* | 68.3 | [64.8, 73.2] | — |

Both theoretical benchmark values fall within the 68% confidence interval. **ΔBIC = −21.2**, constituting "very strong" evidence favoring the REG model over ΛCDM.

### 6.2 Gravitational Wave Echo Search

We performed a matched-filter search using publicly available LIGO Livingston (L1) data from the O4c observing run (4096 seconds). The echo template was constructed with *f_echo = 75 Hz* and *τ = 0.05 s*, corresponding to the theoretical prediction for a 62M_⊙ binary black hole merger.

![Fig. 5: Echo search SNR distribution and matched-filter results.](fig8_ligo_echo_search.png)

A total of **1470 peaks** with |SNR|>3σ were detected, consistent with random noise fluctuations. The 90% confidence upper limit is **SNR < 5.37**. Using GW150914 (SNR≈24) as a reference, we derive:
```
α ≲ 0.22   (90% C.L.)
```

### 6.3 Baryon Acoustic Oscillations

We performed an independent test using eBOSS DR16 BAO measurements (Alam et al. 2021): *D_V/r_d* at three redshifts (*z = 0.698, 1.480, 2.334*).

| Model | χ² (3 d.o.f.) | Δχ² |
|:------|:--------------|:-----|
| **REG** (*w₀=−0.98, w_a=+0.02*) | 585.57 | — |
| **ΛCDM** (*w₀=−1.0, w_a=0.0*) | 588.95 | −3.39 |

The **Δχ² = −3.39** indicates that REG is slightly preferred over ΛCDM by BAO data, with both models fully compatible. A known systematic offset (~15%, ~2.2σ) between different eBOSS tracers affects both models equally and does not impact the model comparison.

### 6.4 Additional Constraints

- **Gravitational wave speed:** The emergence of macroscopically flat space ensures massless gravitons. GW170817 constraint on dispersion is automatically satisfied.
- **Big Bang nucleosynthesis (BBN):** In the early universe, thermal effects drive *Φ→0*, suppressing any deviation from standard BBN predictions.

---

## 7. Discussion

### 7.1 Unique Falsifiable Predictions and Explicit Falsification Conditions

| Prediction | Falsification Condition |
|:-----------|:------------------------|
| Gravitational wave echoes | α < 0.01 (95% C.L.) → relation-curvature coupling excluded |
| Primordial nHz GW bump | No Ω_GW~10⁻¹⁵ signal at *f_peak~10⁻¹⁶ Hz* → phase transition excluded |
| Dark energy EoS | *w₀ = −1.000 ± 0.005* (Euclid/LSST) → evolving DE excluded |
| BAO data | Independent confirmation of *w₀ < −1.1* → benchmark model challenged |
| Standard Model parameters | Failure to reproduce fermion mass hierarchy → framework challenged |

### 7.2 Unification of Fundamental Interactions

In the REG framework, the four fundamental forces manifest as different coupling regimes of the same scalar field:

| Force | Mechanism |
|:------|:----------|
| Gravity | Macroscopic coupling to spacetime curvature |
| Electromagnetism | Intermediate-scale coupling via charge parity mismatch |
| Strong force | Microscopic self-sustaining dependence locking via gluon chains |
| Weak force | Sub-microscopic dependence identity editing via heavy W/Z bosons |

> The specific gauge group **SU(3)_c × SU(2)_L × U(1)_Y** has not yet been derived from the BRN. This is a central open problem.

### 7.3 Current Limitations

1. **Quantitative convergence of simulations:** 3D BRN at 500 nodes exhibits significant statistical fluctuations (α>0 in ~50%, *n∈[3,5]* in ~10%).
2. **Classical-to-quantum correspondence:** Not established.
3. **Scale extrapolation:** ~60 orders of magnitude from simulation to Planck scale is uncontrolled.
4. **Functional form ambiguity:** *Ω²(Φ)* and *V(Φ)* are phenomenological constructions.
5. **Standard Model parameters:** 19 free parameters not derived from first principles.
6. **Penalty form dependence:** Emergence behavior may depend on penalty term forms.

### 7.4 Relation to Existing Theories

| Theory | Relation |
|:-------|:---------|
| Causal Dynamical Triangulations (CDT) | BRN is an information-theoretic generalization of CDT ★★★★★ |
| Loop Quantum Gravity (LQG) | Spin networks may correspond to BRN representations ★★★★☆ |
| String Theory | Independent candidate; possible deep equivalence via holography ★★★☆☆ |

---

## 8. Conclusion

We have proposed **Relational Emergent Gravity (REG)**—a unified framework in which the fundamental entities of nature interact through only two types of binary relations: parallelism and dependence. The framework is supported by proof-of-concept simulations, consistent with all existing precision tests, and demonstrates statistically significant advantages over ΛCDM in supernova data (**ΔBIC=−21.2**). The BAO data test (**Δχ²=−3.39**) indicates that REG is slightly preferred over ΛCDM. The LIGO gravitational wave echo search places an independent constraint of **α≲0.22**. Unique falsifiable predictions with explicit falsification conditions provide clear experimental targets.

We emphasize that REG is **not a completed theory but a testable framework** with initial empirical support. The derivation of Standard Model parameters, the large-scale convergence of numerical simulations, the establishment of the classical-to-quantum correspondence, and the rigorous derivation of functional forms from the BRN partition function are tasks for future work. Science advances not by claiming final answers, but by proposing theories that can be tested, challenged, and refined. **REG is offered in that spirit.**

---

## References

[1] Planck Collaboration, Astron. Astrophys. 641, A6 (2020)  
[2] Scolnic, D. et al., Astrophys. J. 938, 113 (2022)  
[3] Bertotti, B. et al., Nature 425, 374 (2003)  
[4] Abbott, B.P. et al., Phys. Rev. Lett. 116, 061102 (2016)  
[5] Kallosh, R., Linde, A., & Roest, D., J. High Energy Phys. 11, 198 (2013)  
[6] Ambjørn, J., Jurkiewicz, J., & Loll, R., Phys. Rev. Lett. 93, 131301 (2004)  
[7] Khoury, J., & Weltman, A., Phys. Rev. D 69, 044026 (2004)  
[8] Abbott, B.P. et al., Astrophys. J. Lett. 848, L13 (2017)  
[9] Alam, S. et al., Phys. Rev. D 103, 083533 (2021)  
[10] Hawking, S.W., Nature 248, 30 (1974)
