# -*- coding: utf-8 -*-
"""
快速测试：验证同花顺深度跳转链接是否有效
直接运行此脚本，会打印出跳转链接，微信/QQ 中点击测试
"""

from ths_deep_link import StockCode, make_qq_message, make_clickable_link

if __name__ == "__main__":
    test_stocks = [
        ("600519", "贵州茅台"),
        ("000001", "平安银行"),
        ("300750", "宁德时代"),
    ]

    print("=" * 60)
    print("同花顺深度跳转链接测试")
    print("=" * 60)

    for code, name in test_stocks:
        s = StockCode(code)
        print(f"\n📌 {name} ({code})")
        print(f"   网页地址 : {s.fallback_url()}")
        print(f"   安卓 Deep Link :")
        print(f"   {s.android_deep_link()}")
        print(f"   HTML 链接 : {make_clickable_link(code, name)}")
        print(f"   QQ 消息示例:")
        msg = make_qq_message(code, name, "MA金叉买入", 1688.0, 2.35)
        print("   " + "\n   ".join(msg.split("\n")))

    print("\n" + "=" * 60)
    print("✅ 将以上链接发送到手机 QQ/微信，点击即可跳转")
    print("   （需确保手机已安装同花顺 App）")
    print("=" * 60)
