# 生成理论起源网页 - 避免中文乱码
# 使用方法：在PowerShell中运行这个脚本

$outputFile = "theory_origin_fixed.html"

# 创建HTML内容
$html = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>从1+1到宇宙：一个数学猜想如何让我推导出万物理论</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 50px rgba(0,0,0,0.3);
        }
        .hero {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 20px;
            text-align: center;
        }
        .hero h1 {
            font-size: 3em;
            margin-bottom: 20px;
        }
        .hero .subtitle {
            font-size: 1.5em;
            margin-bottom: 30px;
        }
        .section {
            padding: 80px 40px;
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.8s ease-out;
        }
        .section.visible {
            opacity: 1;
            transform: translateY(0);
        }
        .section h2 {
            font-size: 2.5em;
            margin-bottom: 30px;
            color: #667eea;
            border-left: 5px solid #764ba2;
            padding-left: 20px;
        }
        .section p {
            font-size: 1.1em;
            margin-bottom: 20px;
            text-align: justify;
        }
        .highlight {
            background: linear-gradient(120deg, #ffd700 0%, #ffed4e 100%);
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
        }
        .figure {
            margin: 40px 0;
            text-align: center;
        }
        .figure img {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }
        .conclusion {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 80px 40px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>从1+1到宇宙</h1>
            <p class="subtitle">一个数学猜想如何让我推导出万物理论</p>
            <p>—— 蓝光恒</p>
        </div>

        <div class="section" id="section1">
            <h2>第一部分：一个困扰了数学家280年的问题</h2>
            <p>1742年，一个叫哥德巴赫的人给大数学家欧拉写了一封信。信里说：<span class="highlight">我发现，任何一个大于2的偶数，好像都可以写成两个素数之和。</span></p>
            <p>欧拉回信说：这个猜想应该是对的，但我证明不了。</p>
            <p>从那天起，<span class="highlight">280年过去了</span>，无数最聪明的数学家尝试过这个问题。</p>
            <h3>为什么这么难？</h3>
            <p>因为这里面藏着一个<span class="highlight">宇宙级别的秘密</span>：<strong>乘法和加法，是不通的。</strong></p>
        </div>

        <div class="section" id="section2">
            <h2>第二部分：乘法和加法，两套完全不兼容的规则</h2>
            <p><strong>素数是什么？</strong>素数是用乘法定义的——只能被1和自己整除的数。</p>
            <p><strong>哥德巴赫猜想在问什么？</strong>用加法，能不能拼出乘法定义的东西？</p>
            <p>这就像在问：<span class="highlight">用中文的语法，能不能说出一个英文单词的意思？</span></p>
        </div>

        <div class="conclusion">
            <h2>结尾：我们是谁？我们是宇宙理解自己的方式</h2>
            <p>整个理论，从哥德巴赫猜想开始，一路走到了这里。</p>
            <p>我是蓝光恒。下个视频见。</p>
        </div>
    </div>
</body>
</html>
"@

# 保存为UTF-8 with BOM
$utf8BOM = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($outputFile, $html, $utf8BOM)

Write-Output "网页已生成：$outputFile"
Write-Output "请用浏览器打开查看效果"
