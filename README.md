# A股量化交易系统

本项目为A股市场量化交易的完整生产级系统，支持历史回测、实时模拟与实盘部署，适合个人及机构投资者使用。

## 主要功能

- 历史回测：基于5年真实数据，验证策略有效性
- 实时模拟：cronjob驱动，支持断点恢复、多实例与完整状态迁移
- 实盘交易：预留券商API对接接口
- 完整风控：多层ST过滤、止损止盈、资金管理
- 自动化脚本：支持Windows与Linux定时任务

## 快速开始

### 🚀 一键安装（推荐）

**Windows用户：**

```cmd
# 双击运行，或在命令行执行：
install.bat
```

**Linux/Mac用户：**

```bash
# 设置执行权限并运行
chmod +x install.sh
./install.sh
```

**手动运行：**

```bash
python install.py
```

> 💡 **智能安装特性**：
>
> - 自动检测网络环境，选择最优镜像源（清华、阿里云、豆瓣等）
> - 国外网络使用官方源，国内网络自动切换加速镜像  
> - 支持断点续传和错误重试
> - 自动创建虚拟环境和激活脚本

### 1. 手动安装依赖（备用方案）

```powershell
# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖（多种方式）
pip install -r requirements.txt

# 或者只安装核心依赖
pip install pandas numpy akshare requests

# 如果网络较慢，可使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

> 💡 **依赖说明**: 项目使用 akshare 作为数据源，pandas/numpy 进行数据处理。如遇安装问题可考虑使用 conda 环境。

### 2. 运行历史回测（唯一推荐入口）

```powershell
python main_quantitative_system.py
```

> ⚠️ `main_quantitative_system.py` 是生产级回测主力，`complete_backtest_system.py` 仅为初版弱策略，不建议常用。

### 3. 启动实时模拟系统

交互模式：

```powershell
python simulation/main.py --mode interactive
```

生产环境（推荐cronjob/守护进程）：

```powershell
python simulation/main.py --mode cronjob --instance default
python simulation/main.py --mode daemon --instance default
```

更多命令与实例管理、断点恢复、状态迁移等高级用法请详见：

- `docs/实时模拟系统使用手册.md`
- `docs/realtime_simulation_architecture.md`

## 目录结构

- `main_quantitative_system.py`  主量化系统（唯一推荐回测入口）
- `complete_backtest_system.py`  初版弱策略（仅供参考）
- `realtime_simulation_system.py` 实时模拟系统主控
- `python/stock/`                核心算法包
- `simulation/`                  实时模拟核心与调度
- `scripts/`                     自动化与运维脚本
- `docs/`                        系统文档与使用手册

## 适用对象

- 量化投资爱好者
- 机构策略研究员
- 需要高可用、可恢复量化管道的用户

---
如需详细策略说明、风控参数、实时模拟系统命令与维护建议，请参见 `docs/` 目录下相关文档。
