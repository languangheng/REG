# Relational Emergent Gravity (REG)
## 关系涌现引力论

[![Open Access](https://img.shields.io/badge/Open_Access-Green-brightgreen?style=flat-square)](https://www.tsa.cn/)
[![Copyright Protected](https://img.shields.io/badge/Copyright-Protected-red?style=flat-square)](https://www.tsa.cn/)
[![Language](https://img.shields.io/badge/Language-English-blue?style=flat-square)](#)
[![Language](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-orange?style=flat-square)](paper/zh/README_zh.html)

> ### &#9888; 简体中文 | [English](#)
> 本仓库包含 **关系涌现引力论（REG）** 的完整论文、模拟代码和数据分析结果。
> **本论文受中华人民共和国著作权法保护。未经作者明确书面授权，任何单位和个人不得以任何方式使用本论文的全部或部分内容。违者将依法追究法律责任。**
> 本论文已通过 [tsa.cn](https://www.tsa.cn/) 时间戳认证。

---

## &#127757; Project Overview | 项目概览

**Relational Emergent Gravity (REG)** proposes that the fundamental entities of nature — *relational primitives* — interact through **only two binary relations**:

| Symbol | Name | Physical Meaning |
|:------:|:-----|:-----------------|
| **⊕** | Parallelism | Entities side by side → spatial degrees of freedom |
| **⊗** | Dependence | One inside another → temporal evolution & matter |

From these two relations alone, we derive:
- **3+1D spacetime** (from Hurwitz theorem via quaternion associativity)
- **Einstein field equations** with scalar-tensor corrections
- **ξ-attractor inflation** → *n_s=0.967, r=0.0044*
- **Dark energy** with *w₀≈−0.98*
- **Unified description** of all four fundamental interactions

## &#128202; Key Results | 关键结果

| Test | Result | Significance |
|:-----|:-------|:-------------|
| SNe + CMB MCMC (Pantheon+, 1580 SNe) | **ΔBIC = −21.2** vs ΛCDM | "Very strong" |
| Pantheon+ joint fit | **w₀ = −0.89 [−1.00, −0.78]** | Theory ✓ in 68% C.L. |
| ξ-attractor inflation | **n_s = 0.967** | 0.5σ from Planck 2018 |
| LIGO O4c echo search | **α ≲ 0.22** (90% C.L.) | Independent constraint |
| eBOSS DR16 BAO | **Δχ² = −3.39** | REG slightly preferred |
| 3D BRN depth peaks | **3 stable peaks** | Matches SM fermion generations |

## &#128196; Repository Structure | 仓库结构

```
REG-Paper/
├── index.html              # Language selection page (auto-detect)
├── paper/
│   ├── zh/
│   │   ├── README_zh.html  # Chinese paper (full HTML)
│   │   └── README.html     # English paper (full HTML)
│   ├── en/
│   │   └── REG_Paper_EN.docx
│   └── assets/             # All figures (12 PNG files)
├── scripts/
│   ├── brn_simulation.py   # Binary Relation Network Monte Carlo
│   ├── mcmc_analysis.py   # Pantheon+ + Planck joint MCMC
│   ├── ligo_echo_search.py # LIGO O4c echo analysis
│   ├── bao_analysis.py    # eBOSS DR16 BAO comparison
│   └── inflation_calc.py   # ξ-attractor inflation predictions
└── results/
    ├── corner_plot.png     # MCMC posterior corner plot
    ├── bao_comparison.png  # BAO model comparison
    └── ligo_results.png    # LIGO echo search results
```

## &#128279; DOI / Zenodo | 数字对象标识符

| Theory | Zenodo Record | DOI |
|:------:|:--------------:|:---:|
| **ESE** (Emergent Structural Emerulation) | [zenodo.org/records/21111987](https://zenodo.org/records/21111987) | [10.5281/zenodo.21111987](https://doi.org/10.5281/zenodo.21111987) |
| **REG** (Relational Emergent Gravity) | [zenodo.org/records/21071504](https://zenodo.org/records/21071504) | [10.5281/zenodo.21071504](https://doi.org/10.5281/zenodo.21071504) |

---

## &#128218; Papers | 论文

| Version | Format | File |
|:--------|:-------|:-----|
| English | PDF | [`paper/REG_Paper_EN.pdf`](paper/REG_Paper_EN.pdf) |
### 🎬 Theory Origin Story | 理论起源故事

**如何从哥德巴赫猜想推导出万物理论？**

这是一个完整的故事，讲述了一个数学猜想（哥德巴赫猜想）如何启发了一个新的宇宙理论：

- 📖 **[从1+1到宇宙：一个数学猜想如何让我推导出万物理论](video/理论起源完整版.md)** (Markdown, 中文)

**内容大纲：**
1. 一个困扰了数学家280年的问题（哥德巴赫猜想）
2. 乘法和加法，两套完全不兼容的规则
3. 这个鸿沟不只是数学问题（E=mc²的启示）
4. 加法和乘法长出了空间和时间（为什么是3+1维）
5. 如果宇宙底层就是加法和乘法呢？（关系基元）
6. 代码跑出来的结果让我震惊（三代费米子涌现）
7. 从微观网络到宇宙学（导出引力场方程）
8. 用真实数据检验（MCMC拟合超新星）
9. 最冒险的预言——引力波回声（LIGO搜索）
10. 这个理论能解释什么？不能解释什么？

---

## &#128274; Copyright Notice | 版权声明

```
⚠ 本论文受中华人民共和国著作权法保护。
⚠ This paper is protected under PRC Copyright Law.

未经作者蓝光恒 (Lan Guangheng) 明确书面授权：
Without explicit written permission from the author Lan Guangheng:

  ✗ 复制 (Reproduce)
  ✗ 转载 (Republish)  
  ✗ 摘编 (Excerpt)
  ✗ 镜像 (Mirror)
  ✗ 传播 (Transmit)
  ✗ 出版 (Publish)
  ✗ 商业使用 (Commercial use)

本论文已通过 tsa.cn（国家授时中心时间戳认证平台）完成时间戳认证，
可作为创作时间及内容完整性的法律证据。

This paper has been timestamp-certified through tsa.cn, providing
legal evidence of creation time and content integrity.
```

## &#9881; Getting Started | 快速开始

### 1. View the Paper | 查看论文

Open in browser: **[paper/zh/README.html](paper/zh/README.html)** (English)
or **[paper/zh/README_zh.html](paper/zh/README_zh.html)** (Chinese)

### 2. Run the BRN Simulation | 运行BRN模拟

```bash
# Requires: numpy, matplotlib, tqdm
pip install numpy matplotlib tqdm

python scripts/brn_simulation.py
```

### 3. Run MCMC Analysis | 运行MCMC分析

```bash
# Requires: numpy, scipy, emcee, corner
pip install scipy emcee corner

python scripts/mcmc_analysis.py
```

### 4. Reproduce BAO Analysis | 重现BAO分析

```bash
python scripts/bao_analysis.py
```

## &#128161; Falsifiable Predictions | 可证伪预测

| Prediction | How to Test | Falsification Condition |
|:-----------|:------------|:-----------------------|
| GW echoes | Future GW detectors (ET, CE) | α < 0.01 (95% C.L.) |
| nHz GW bump | Space-based detectors (LISA) | No signal at ~10⁻¹⁶ Hz |
| Evolving dark energy | Euclid / LSST | w₀ = −1.000 ± 0.005 |
| BAO data | DESI / Euclid BAO | Independent w₀ < −1.1 |

## &#128187; Tech Stack

- **Simulation:** Python 3, NumPy, Matplotlib, tqdm
- **MCMC:** emcee, scipy, corner
- **Paper:** python-docx (Word), Markdown + HTML (web)
- **Authentication:** tsa.cn timestamp certification

## &#128221; Author | 作者

**Lan Guangheng** (蓝光恒)  
Theoretical Physics / Cosmology  
July 2026

- **tsa.cn certified:** [https://www.tsa.cn/](https://www.tsa.cn/)
- **GitHub:** This repository

## &#128220; License | 许可证

**Copyright © 2026 Lan Guangheng. All Rights Reserved.**  
**版权所有 © 2026 蓝光恒。保留所有权利。**

This repository is for **open review and scientific discussion**.  
Commercial use, reproduction, or redistribution of the paper content **without explicit written permission** is strictly prohibited.

---

*Science advances not by claiming final answers, but by proposing theories that can be tested, challenged, and refined.*
