# 数据文件说明 / Data Files

---

## pantheon_data.txt

**来源**: Pantheon+ with SH0ES (Scolnic et al. 2022, ApJ 938, 113)
**文件**: `pantheon_data.txt`
**行数**: 1702 行 (1 header + 1701 SN events)
**使用行数**: 1580 个有效超新星（过滤掉缺失/无效数据后）

### 文件格式 (空格分隔)

| 列索引 | 列名 | 说明 | 单位 |
|:------:|:-----|:-----|:-----|
| 0 | CID | 超新星名称 | — |
| 1 | IDSURVEY | 巡天编号 | — |
| 2 | zHD | 红移 (CMB frame) | — |
| 3 | zHDERR | 红移误差 | — |
| 4 | zCMB | CMB红移 (备选) | — |
| 5 | zCMBERR | CMB红移误差 | — |
| 6 | zHEL | 局域红移 (备选) | — |
| 7 | zHELERR | 局域红移误差 | — |
| 8 | m_b_corr | 修正后的峰值B波段视星等 | mag |
| 9 | m_b_corr_err_DIAG | 视星等误差（对角协方差） | mag |
| **10** | **MU_SH0ES** | **距离模数（最终值）** | mag |
| **11** | **MU_SH0ES_ERR_DIAG** | **距离模数误差** | mag |
| 12 | CEPH_DIST | 造父变星距离 | Mpc |
| 13 | IS_CALIBRATOR | 是否为造父定标源 (0/1) | — |
| 14 | USED_IN_SH0ES_HF | 是否用于SH0ES哈勃残差拟合 | — |
| ... | (更多列) | 详见 Pantheon+ 数据说明 | |

### 使用的关键列

```python
z = float(parts[2])    # zHD (CMB frame redshift)
mu = float(parts[10])  # MU_SH0ES (distance modulus, mag)
mu_err = float(parts[11])  # MU_SH0ES_ERR_DIAG (uncertainty, mag)
```

### 数据过滤条件

```python
if z > 0 and mu > 0 and mu_err > 0:
    # 保留该数据点
```

### 红移覆盖范围

| 统计量 | 值 |
|:-------|:---|
| 数据点数 | 1580 |
| 最小红移 | z = 0.0102 |
| 最大红移 | z = 2.2614 |
| 距离模数范围 | ~33 - ~46 mag |

### 物理公式

**光度距离**:
```
d_L(z) = (1+z) · c · ∫₀ᶻ dx / H(x)
H(x) = H₀ · √[Ωm(1+x)³ + ΩΛ·f_DE(x)]
f_DE(x) = (1+x)^{3(w₀+wₐ)} · exp[-3wₐx/(1+x)]
```

**距离模数**:
```
μ(z) = 5·log₁₀[d_L(z)/Mpc] + 25
```

**χ² 拟合**:
```
χ² = Σ [(μ_obs - μ_theory)² / σ²]
```

### 注意事项

1. 文件名在代码中引用为相对路径 `pantheon_data.txt`
2. 放在与 Python 脚本同一目录下，或修改脚本中的 `BASE` 路径
3. Pantheon+ 是目前最大的 Ia 型超新星统一样本 (1701颗)
4. SH0ES 校准将距离模数精度提升到 ~0.03 mag

### 数据文件引用

> Scolnic, D. et al. 2022, "The Pantheon+ Type Ia Supernova Sample: The Most Precise Cosmological Constraints to Date", *ApJ* 938, 113
> arXiv: 2112.03863
