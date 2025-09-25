# Windows PowerShell 环境变量设置
# 将你的GitHub Token替换下面的 "your_token_here"

$env:GITHUB_TOKEN = "your_token_here"

# 验证设置是否成功
Write-Host "GitHub Token 已设置: $($env:GITHUB_TOKEN.Substring(0,4))..." -ForegroundColor Green

# 可选：将token永久保存到系统环境变量
# [Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "your_token_here", [EnvironmentVariableTarget]::User)
# Write-Host "已永久保存到系统环境变量" -ForegroundColor Yellow