@echo off
chcp 65001 >nul
echo ===================================
echo  ESE 一键运行脚本
echo  全部验证 + 生成论文
echo ===================================

set PYTHON=C:\Users\languangheng\AppData\Local\Python\pythoncore-3.14-64\python.exe
set WORKDIR=C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\github

cd /d "%WORKDIR%"

echo.
echo [1/7] 运行基础模拟（ese_minimal_simulation.py）...
"%PYTHON%" ese_minimal_simulation.py
if errorlevel 1 echo ⚠️  基础模拟失败 & pause

echo.
echo [2/7] 素数幂律分析（ese_prime_analysis_v2.py）...
"%PYTHON%" ese_prime_analysis_v2.py
if errorlevel 1 echo ⚠️  素数分析失败 & pause

echo.
echo [3/7] 标度律研究（ese_scaling_law.py）...
"%PYTHON%" ese_scaling_law.py
if errorlevel 1 echo ⚠️  标度律失败 & pause

echo.
echo [4/7] 精细结构常数验证（verify_fine_structure_50runs.py）...
"%PYTHON%" verify_fine_structure_50runs.py
if errorlevel 1 echo ⚠️  精细结构验证失败 & pause

echo.
echo [5/7] 弱耦合常数验证（verify_weak_coupling.py）...
"%PYTHON%" verify_weak_coupling.py
if errorlevel 1 echo ⚠️  弱耦合验证失败 & pause

echo.
echo [6/7] 三代费米子镜像验证（verify_fermion_mirror.py）...
"%PYTHON%" verify_fermion_mirror.py
if errorlevel 1 echo ⚠️  镜像验证失败 & pause

echo.
echo [7/7] 生成中文论文（带图片）...
"%PYTHON%" generate_paper_chinese_img.py
if errorlevel 1 echo ⚠️  中文论文生成失败 & pause

echo.
echo [可选] 生成英文论文（带图片）...
"%PYTHON%" generate_paper_english.py
if errorlevel 1 echo ⚠️  英文论文生成失败 & pause

echo.
echo ===================================
echo  全部完成！
echo ===================================
echo.
echo 生成的文件：
echo  - ESE论文_完整版_带图片.docx（中文，带图片）
echo  - ESE_paper_English_v1.docx（英文，带图片）
echo  - 各验证脚本生成的 .png 图片
echo.
pause
