# 量化交易系统项目结构

## 📁 根目录结构（已清理）

```
c:\dev\stock\                              # 项目根目录
├── .github/                               # GitHub配置
│   ├── copilot-instructions.md            # 项目统一上下文
│   └── workflows/                          # GitHub Actions
├── .venv/                                 # Python虚拟环境（本地）
├── archive/                               # 归档文件
├── backup/                                # 备份文件
├── data/                                  # 数据目录
│   ├── backtest/                          # 回测结果
│   ├── cache/                             # 缓存文件（.gitignore）
│   ├── clean/                             # 清洗后数据
│   ├── raw/                               # 原始数据（.gitignore） 
│   └── simulation/                        # 实时模拟数据
├── docs/                                  # 文档目录
│   ├── github_backup_setup.md             # GitHub数据备份配置指南
│   └── ...
├── examples/                              # 示例代码
├── logs/                                  # 日志文件
├── node/                                  # Node.js相关（可视化）
├── python/                                # Python核心包
│   └── stock/                             # 核心stock包
│       ├── config/                        # 配置管理
│       ├── data/                          # 数据层
│       ├── engine/                        # 引擎层
│       ├── strategies/                    # 策略层
│       └── utils/                         # 工具层
├── scripts/                               # 脚本目录
│   ├── setup_env.py                       # 环境配置脚本
│   ├── test_system.py                     # 系统测试脚本
│   ├── install.py/bat/sh                  # 安装脚本
│   ├── activate.py/bat/sh                 # 激活脚本
│   └── setup_github_token.*               # Token设置脚本
├── simulation/                            # 实时模拟系统
│   ├── core/                              # 核心组件
│   ├── engines/                           # 执行引擎
│   └── cronjobs/                          # 定时任务
├── tests/                                 # 测试文件
│   ├── check_local_stocks.py              # 本地股票检查
│   ├── test_*.py                          # 各种测试脚本
│   └── ...
├── .env.example                           # 环境变量模板
├── .gitignore                             # Git忽略规则
├── main_quantitative_system.py           # 主量化交易系统
├── realtime_risk_controller.py           # 实时风控监控
├── realtime_simulation_system.py         # 实时模拟系统
├── requirements.txt                       # Python依赖
└── README.md                              # 项目说明
```

## 🎯 目录职责

### 核心系统文件（根目录）
- `main_quantitative_system.py` - 主量化交易系统（594行，生产级）
- `realtime_simulation_system.py` - 实时模拟系统入口
- `realtime_risk_controller.py` - 实时风控监控

### python/stock/ - 核心Python包
- `config/` - 环境配置管理（.env支持）
- `data/` - 数据层（akshare + GitHub备份）
- `engine/` - 回测引擎、风控引擎
- `strategies/` - 交易策略实现
- `utils/` - 工具函数

### simulation/ - 实时模拟系统
- `core/` - 状态管理、缓存管理、调度器
- `engines/` - 策略引擎、交易引擎、风控引擎
- `cronjobs/` - 定时任务实现

### scripts/ - 工具脚本
- 安装配置脚本
- 系统测试脚本
- 环境设置脚本

### tests/ - 测试代码
- 所有测试文件统一管理
- 避免root目录混乱

## 🚀 使用指南

### 快速开始
```bash
# 1. 环境配置
python scripts/setup_env.py

# 2. 系统测试  
python scripts/test_system.py

# 3. 运行主系统
python main_quantitative_system.py
```

### 开发测试
```bash
# 运行特定测试
python tests/test_data_repo.py

# 系统安装
python scripts/install.py
```

## 📋 清理完成

✅ **已移动文件**：
- 所有 `test_*.py` → `tests/`
- 所有 `install.*` → `scripts/`  
- 所有 `activate.*` → `scripts/`
- 所有 `setup_github_token.*` → `scripts/`
- `quick_setup_token.py` → `scripts/`
- `check_local_stocks.py` → `tests/`

✅ **已清理**：
- 删除 `__pycache__/` 目录
- 更新 `.gitignore` 防止缓存文件
- 移动多余的requirements文件到archive

✅ **结果**：
- 根目录从32个项目减少到20个项目
- 文件分类清晰，职责明确
- 遵循Python项目最佳实践

---

**🎉 项目结构现在干净整洁，符合生产级项目标准！**