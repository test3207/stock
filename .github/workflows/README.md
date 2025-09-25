# Workflows 使用说明

## 回测工作流 (backtest.yml)

### 功能

- **触发方式**: 手动运行 或 代码推送到 main 分支
- **执行内容**: 运行 main_quantitative_system.py 生成完整回测分析
- **输出结果**:
  - 在 Actions 控制台显示关键指标（年化收益、最大回撤、夏普比率等）
  - 通过 Artifacts 下载完整 JSON 报告

### 使用方法

#### 手动运行

1. 进入 GitHub 仓库的 Actions 页面
2. 点击 "Quantitative Trading Backtest" 工作流  
3. 点击 "Run workflow" 按钮
4. 选择输出格式（json 或 detailed）
5. 点击绿色的 "Run workflow" 按钮开始执行

#### 自动触发

当推送以下文件的修改到 main 分支时自动运行：

- `main_quantitative_system.py`
- `python/stock/**` 目录下的任何文件

### 查看结果

#### 快速查看关键指标

在 Actions 执行日志中直接查看：

- 📈 年化收益率
- 💰 总收益率  
- 📉 最大回撤
- ⚖️ 夏普比率

#### 下载完整报告

1. 在 Actions 执行完成后，滚动到页面底部
2. 在 "Artifacts" 区域点击 `backtest-results-xxxxx`
3. 下载压缩包获取完整 JSON 分析报告

### 无需配置

该工作流开箱即用，无需配置任何 Secrets 或环境变量。

---
预计执行时间：5-15 分钟，取决于数据获取速度
