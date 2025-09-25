# CI 脚本说明

本目录包含用于 GitHub Actions 和其他 CI/CD 流程的辅助脚本。

## 文件说明

### `generate_workflow_summary.py`

生成 GitHub Actions 工作流执行摘要

**用法**:

```bash
python generate_workflow_summary.py <output_dir> <run_id> <commit_sha> <trigger> <output_format>
```

**功能**:

- 生成包含工作流信息的 JSON 摘要文件
- 统计生成的结果文件数量
- 记录执行时间、触发方式等元信息

### `display_key_metrics.py`

解析回测结果并在控制台显示关键指标

**用法**:

```bash
python display_key_metrics.py <output_dir>
```

**功能**:

- 自动查找回测结果 JSON 文件
- 提取并格式化显示核心性能指标
- 支持多个结果文件的批量处理

## 本地测试

这些脚本也可以在本地环境中测试使用：

```bash
# 测试指标显示（假设有 data/backtest 目录中有结果文件）
python scripts/ci/display_key_metrics.py data/backtest

# 测试摘要生成
python scripts/ci/generate_workflow_summary.py ./test_output test_run abc123 manual json
```
