@echo off
:: 设置控制台代码页为UTF-8
chcp 65001 >nul
echo ===================================
echo  豆包 API 双图对比分析工具启动脚本
echo ===================================
echo.

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境未找到
    echo 请先运行以下命令创建虚拟环境:
    echo.
    echo     python -m venv venv
    echo     .\venv\Scripts\activate
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: 激活环境并启动
echo [信息] 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 正在启动应用...
echo [信息] 应用启动后，请在浏览器中访问显示的URL地址
echo [信息] 通常是 http://127.0.0.1:7860
echo [信息] 使用组合键 Ctrl 加 C 可停止应用
echo.

:: 启动应用
python -u app.py

echo.
echo [信息] 应用已关闭
pause 