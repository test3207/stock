# GitHub Token 配置指南

## 🎯 配置目标
为了让数据自动上传到GitHub仓库作为备份，需要配置GitHub Token。

## 📋 完整配置步骤

### 1️⃣ 创建GitHub Personal Access Token

1. **登录GitHub** → 点击右上角头像 → **Settings**
2. **左侧菜单最底部** → **Developer settings**  
3. **左侧菜单** → **Personal access tokens** → **Tokens (classic)**
4. **点击** → **Generate new token** → **Generate new token (classic)**
5. **填写信息**：
   ```
   Token name: stock-data-repo
   Expiration: No expiration (推荐) 或 90 days
   ```
6. **勾选权限**：
   ```
   ✅ repo (完整勾选，包括所有子选项)
      ├── repo:status
      ├── repo_deployment  
      ├── public_repo
      └── repo:invite
   
   可选：
   ✅ workflow (如果需要触发GitHub Actions)
   ```
7. **点击** → **Generate token**
8. **⚠️ 重要：立即复制token并保存**（只显示一次！）

### 2️⃣ 本地环境配置

#### Windows用户：
```powershell
# 1. 编辑 setup_github_token.ps1 文件
# 2. 将 "your_token_here" 替换为实际的token
# 3. 运行脚本
.\setup_github_token.ps1
```

#### Linux/Mac用户：
```bash
# 1. 编辑 setup_github_token.sh 文件  
# 2. 将 "your_token_here" 替换为实际的token
# 3. 运行脚本
source setup_github_token.sh
```

#### 手动设置（临时）：
```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "your_actual_token_here"

# Linux/Mac/Git Bash
export GITHUB_TOKEN="your_actual_token_here"
```

### 3️⃣ 验证配置

运行测试脚本验证配置是否正确：
```bash
python test_github_token.py
```

成功输出应该包含：
```
✅ GITHUB_TOKEN 已设置
✅ DataUploader Token配置正确
✅ GitHub API连接成功
✅ 具有写入权限，可以上传数据
🎉 所有测试通过！GitHub Token配置正确
```

### 4️⃣ GitHub Actions配置

**无需额外配置！** GitHub Actions会自动使用内置的`GITHUB_TOKEN`。

如果需要自定义token：
1. 在GitHub仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. Name: `CUSTOM_GITHUB_TOKEN`，Value: 你的token
4. 修改 `.github/workflows/backtest.yml` 中的环境变量

## 🔧 使用方式

### 启用自动上传：
```python
from stock.data import IntegratedDataProvider

# 创建启用自动上传的提供者
provider = IntegratedDataProvider(auto_upload=True)

# 获取数据（自动上传到GitHub仓库）
data = provider.get_stock_daily('000001.SZ', '2024-12-20', '2024-12-31')
```

### 手动上传：
```python
# 手动上传特定股票数据
success = provider.manual_upload_data('000001.SZ', '2024-12-20', '2024-12-31')
```

## 🛡️ 安全建议

1. **不要将token提交到代码仓库**
2. **定期更换token**（建议每90天）
3. **只给必要的权限**（最小权限原则）
4. **本地开发使用临时环境变量**
5. **生产环境使用GitHub Secrets**

## 🐛 常见问题

### Q: Token设置后仍然显示未配置？
A: 重启终端/IDE，或重新设置环境变量

### Q: 403 Forbidden错误？
A: 检查token权限，确保勾选了`repo`完整权限

### Q: 404 Not Found错误？
A: 仓库`test3207/stock-data`不存在，系统会在首次上传时自动创建

### Q: Rate limit exceeded？
A: GitHub API频率限制，等待一小时或使用已认证的token

## 📊 工作流程

配置完成后的完整数据流程：
```
用户请求数据
    ↓
检查GitHub数据仓库 (如果有数据，直接返回)
    ↓
使用akshare获取数据 (如果GitHub无数据)
    ↓
自动上传到GitHub仓库 (使用配置的token)
    ↓
返回数据给用户
    ↓
下次相同请求直接从GitHub仓库获取 (更快)
```