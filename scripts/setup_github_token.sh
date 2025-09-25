#!/bin/bash
# Linux/Mac 环境变量设置
# 将你的GitHub Token替换下面的 "your_token_here"

export GITHUB_TOKEN="your_token_here"

echo "GitHub Token 已设置: ${GITHUB_TOKEN:0:4}..."

# 可选：添加到 ~/.bashrc 或 ~/.zshrc 永久保存
# echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.bashrc
# echo "已添加到 ~/.bashrc"