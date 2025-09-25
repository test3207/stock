# GitHub数据备份系统配置指南

## 🎯 系统概述

完整的数据仓库备份系统，将akshare数据自动备份到GitHub，实现数据的云端存储和版本管理。

## 🚀 快速开始

### 1. 自动配置（推荐）

```bash
# 运行交互式配置工具
python scripts/interactive_token_setup.py
```

### 2. 手动配置

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env 文件，添加你的 GITHUB_TOKEN
```

### 3. 系统测试

```bash
# 测试所有组件
python scripts/test_system.py
```

### 4. 开始使用

```python
from stock.data import IntegratedDataProvider

# 自动备份模式（推荐）
provider = IntegratedDataProvider(auto_upload=True)

# 获取数据（优先从GitHub，失败时用akshare并自动备份）
data = provider.get_stock_basic()
```

## 📁 系统架构

### 核心组件

```
python/stock/
├── data/
│   ├── github_repo.py          # GitHub仓库访问
│   ├── data_uploader.py        # 数据上传工具  
│   ├── integrated_provider.py  # 智能数据提供者
│   └── akshare_provider.py     # 原akshare提供者
├── config/
│   ├── env.py                  # 环境配置管理
│   └── __init__.py
└── ...
```

### 数据流程

1. **GitHub优先**: 首先尝试从GitHub仓库获取数据
2. **智能后备**: GitHub失败时自动切换到akshare
3. **自动备份**: 使用akshare数据时自动上传到GitHub
4. **格式统一**: 自动处理不同数据源的格式差异

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件（已有 `.env.example` 模板）:

```env
# GitHub配置
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=stock-data

# 可选配置
GITHUB_API_TIMEOUT=30
GITHUB_MAX_RETRIES=3
```

### GitHub Token权限

需要的权限:

- `repo` (访问私有仓库)
- `public_repo` (访问公开仓库)

## 🔧 高级用法

```
python/stock/
├── data/
│   ├── github_repo.py          # GitHub仓库访问
│   ├── data_uploader.py        # 数据上传工具  
│   ├── integrated_provider.py  # 智能数据提供者
│   └── akshare_provider.py     # 原akshare提供者
├── config/
│   ├── env.py                  # 环境配置管理
│   └── __init__.py
└── ...
```

### 数据流程

1. **GitHub优先**: 首先尝试从GitHub仓库获取数据
2. **智能后备**: GitHub失败时自动切换到akshare
3. **自动备份**: 使用akshare数据时自动上传到GitHub
4. **格式统一**: 自动处理不同数据源的格式差异

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件:

```env
# GitHub配置
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=stock-data

# 可选配置
GITHUB_API_TIMEOUT=30
GITHUB_MAX_RETRIES=3
```

### GitHub Token权限

需要的权限:
- `repo` (访问私有仓库)
- `public_repo` (访问公开仓库)

## 🔧 高级用法

### 手动上传数据

```python
from stock.data import DataUploader

uploader = DataUploader()
# 上传股票基础信息
uploader.upload_stock_basic()
# 上传日线数据
uploader.upload_daily_data('2024-01-01', '2024-12-31')
```

### 仅使用GitHub数据

```python
from stock.data.github_repo import GitHubStockRepo

repo = GitHubStockRepo()
data = repo.get_stock_basic()  # 纯GitHub数据，不使用akshare
```

### 配置验证

```python
from stock.config import validate_github_token, get_github_token

token = get_github_token()
if validate_github_token(token):
    print("GitHub配置正确！")
```

## 🛠️ 故障排除

### 常见问题

1. **Token无效**
   - 检查Token权限设置
   - 确认Token未过期
   - 验证仓库访问权限

2. **网络问题**
   - 检查GitHub API连通性
   - 调整超时设置
   - 使用代理（如需要）

3. **数据格式**
   - 系统自动处理格式差异
   - 检查数据完整性
   - 验证日期范围

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 现在会输出详细调试信息
from stock.data import IntegratedDataProvider
provider = IntegratedDataProvider(auto_upload=True)
```

## 📊 监控和维护

### 数据同步状态

- 检查GitHub仓库的最新提交
- 查看本地缓存目录: `data/cache/`
- 监控日志输出

### 定期维护

- 定期更新GitHub Token
- 清理过期缓存文件
- 验证数据完整性

## 🔒 安全注意事项

- **永远不要**将 `.env` 文件提交到版本控制
- 定期轮换GitHub Token
- 使用最小权限原则
- 监控API使用情况

## 📈 性能优化

- 使用本地缓存减少API调用
- 批量上传减少请求次数
- 合理设置重试和超时参数
- 监控GitHub API限制

---

**🎉 配置完成后，你的量化交易系统将拥有可靠的云端数据备份！**