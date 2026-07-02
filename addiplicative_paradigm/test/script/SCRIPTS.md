# 脚本说明 / Scripts Documentation

**运行环境**: Python 3.11+ (Windows)
**依赖**: `numpy`, `scipy`, `matplotlib`, `emcee`, `corner`
**安装依赖**: `pip install numpy scipy matplotlib emcee corner`

---

## mcmc_fast_v5.py — REG 宇宙学拟合 (核心)

**功能**: 关系涌现引力论 (REG) 的宇宙学参数 MCMC 拟合
**运行**: `python mcmc_fast_v5.py` (需在 `test/` 目录运行)
**耗时**: ~150秒 (网格 ~115秒 + MCMC ~34秒)

### 核心特性
- **双线性插值加速**: 预计算 40×40 w₀-wₐ 网格，MCMC 每步直接查表
- **加速比**: ~70倍 (从 40分钟 → 34秒)
- **输出图表**: fig10, fig11, fig13

### 参数空间
| 参数 | 符号 | 先验范围 | 初始值 |
|:-----|:----:|:--------:|:------:|
| 暗能量状态方程 | w₀ | (-2.0, 0.0) | -0.89 |
| 暗能量演化参数 | wₐ | (-3.0, 3.0) | 0.00 |
| 物质密度 | Ωm | (0.20, 0.50) | 0.306 |
| 哈勃常数 | H₀ | (60, 80) | 68.3 |
| 绝对星等校准 | M₀ | (-0.30, 0.10) | -0.14 |

### 物理模型 (REG)
```python
# w(z) = w₀ + wₐ · z/(1+z)  (CPL parametrization)
# H(z) = H₀ · sqrt[Ωm(1+z)³ + (1-Ωm)·f_DE(z)]
# f_DE(z) = (1+z)^{3(1+w₀+wₐ)} · exp[-3wₐz/(1+z)]
```

### 似然函数
```python
log L = -0.5 · [χ²_SNe + χ²_Planck]
χ²_SNe   = Σ [(μ_obs - μ_th)² / σ²]
χ²_Planck = [(Ωmh²_th - 0.1430) / 0.0011]²
```

---

## brn_3d_simulate.py — BRN 三维蒙特卡洛模拟

**功能**: 关系网络 (Binary Relation Network) 的 Metropolis-Hastings 蒙特卡洛模拟
**运行**: `python brn_3d_simulate.py`
**耗时**: ~2-3分钟

### 物理模型 (BRN)
- **关系基元**: V 个节点，每个有位置 (3D欧氏空间)
- **⊕ 边 (并列)**: 欧氏距离 r < r_cut 形成空间邻接
- **⊗ 边 (依赖)**: 随机嵌套关系，有向，计数嵌套深度
- **p_curv**: 添加⊗边时同步添加⊕边的概率 → 关系-曲率耦合

### 关键测量
```python
# 关系-曲率耦合常数
α = Cov(Φ, R) / Var(Φ)
#  Φ = 半径1内平均嵌套深度
#  R  = 度偏离 (deg - d₀)

# 有效势能指数
V(Φ) ∝ Φ^n   →  n = d ln V / d ln Φ
```

---

## brn_depth_distribution.py — BRN 嵌套深度分布

**功能**: 测量 BRN 中⊗-嵌套深度的概率分布
**运行**: `python brn_depth_distribution.py`
**耗时**: ~1分钟

### 输出
- `fig3_brn_depth_distribution.png`: 深度柱状图 + 峰值检测
- `fig4_brn_depth_cdf.png`: 概率密度 + 累积分布函数

---

## brn_repeat_verify.py — BRN 可重复性验证

**功能**: 用不同随机种子重复 BRN 模拟，验证涌现机制的统计稳健性
**运行**: `python brn_repeat_verify.py`
**耗时**: ~5-8分钟

### 输出
- `fig6_brn_repeatability.png`: seed=42 vs seed=123 vs seed=777 的 α 对比
- `fig7_brn_alpha_n_space.png`: 三种子平均的 α 和 n 热力图

---

## ligo_echo_search.py — LIGO 引力波回声搜索

**功能**: 在 LIGO 公开数据中搜索 REG 理论预言的黑洞并合后回声信号
**运行**: `python ligo_echo_search.py`
**耗时**: ~1-2分钟

### REG 理论预言
```python
# 62 M☉ 双黑洞合并产生的回声:
f_echo ≈ 75 Hz
τ_decay ≈ 0.05 s
```

### 输出
- `fig8_ligo_echo_search.png`: 四面板概览图
- `fig9_ligo_snr_timeseries.png`: SNR 时间序列

---

## bao_final.py — BAO 距离比分析

**功能**: 比较 REG 模型预言 vs SDSS/eBOSS BAO 观测的 DV/rd 值
**运行**: `python bao_final.py`
**耗时**: ~10秒

### BAO 数据
7个红移点的各向同性声学尺度距离比 DV(z)/rd：
- z = 0.38, 0.51, 0.61, 0.70, 0.85, 1.48, 2.33
- 来源: SDSS DR12 / eBOSS (Alam et al. 2021)
- rd_fid = 147.09 Mpc (Planck 2018)

### 输出
- `fig5_bao_comparison.png`: 理论与观测对比图 + 残差

---

## 快速开始 / Quick Start

```bash
cd test/script
python mcmc_fast_v5.py
```

---

## 依赖安装

```bash
pip install numpy scipy matplotlib emcee corner
```

所有脚本已测试通过，Python 3.11 on Windows。
