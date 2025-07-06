# 设置输出编码为UTF-8，解决中文显示问题
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================" -ForegroundColor Cyan
Write-Host " 豆包 API 双图对比分析工具启动脚本" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境是否存在
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "[错误] 虚拟环境未找到" -ForegroundColor Red
    Write-Host "请先运行以下命令创建虚拟环境:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    python -m venv venv" -ForegroundColor Yellow
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# 激活虚拟环境并启动应用
Write-Host "[信息] 正在激活虚拟环境..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

Write-Host "[信息] 正在启动应用..." -ForegroundColor Green
Write-Host "[信息] 应用启动后，请在浏览器中访问显示的URL地址" -ForegroundColor Cyan
Write-Host "[信息] 通常是 http://127.0.0.1:7860" -ForegroundColor Cyan
Write-Host "[信息] 使用组合键 Ctrl 加 C 可停止应用" -ForegroundColor Yellow
Write-Host ""

try {
    # 使用-u参数确保Python输出不会被缓冲，并使用UTF-8编码
    python -u app.py
}
catch {
    Write-Host "[错误] 应用运行出错: $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "[信息] 应用已关闭" -ForegroundColor Green
    Read-Host "按回车键退出"
} 