"""
REG湍流模拟批量运行脚本
自动执行所有5个模拟并保存结果
"""
import subprocess
import time
import os

# 切换到目标目录
os.chdir(r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\github\scripts\task1")

scripts = [
    ("turbulence_scan.py", "参数扫描"),
    ("turbulence_fluids.py", "多流体对比"),
]

print("=" * 70)
print("REG湍流模拟批量执行")
print("=" * 70)
print("\n提示：前3个脚本(1D/2D/3D)会弹出动画窗口，请观察后手动关闭窗口继续。")
print("后2个脚本会自动保存图片并退出。\n")

# 先运行不依赖动画的脚本
for script, desc in scripts:
    print(f"\n{'='*70}")
    print(f"正在运行: {desc} ({script})")
    print(f"{'='*70}")
    try:
        result = subprocess.run(
            ["python", script],
            capture_output=False,
            text=True,
            timeout=300  # 5分钟超时
        )
        if result.returncode == 0:
            print(f"✓ {desc} 完成")
        else:
            print(f"✗ {desc} 执行失败，返回码: {result.returncode}")
    except subprocess.TimeoutExpired:
        print(f"✗ {desc} 执行超时")
    except Exception as e:
        print(f"✗ {desc} 执行出错: {e}")

print("\n" + "=" * 70)
print("批量执行完成！")
print("=" * 70)
print("\n生成的文件:")
for f in ["turbulence_scan.png", "fluid_comparison.png"]:
    if os.path.exists(f):
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} (未生成)")
