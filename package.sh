#!/bin/bash

# 打包项目脚本
# 排除 .gitignore 中的内容，但包含 .env 文件

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="$(basename "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d%H%M%S)
OUTPUT_FILE="${PARENT_DIR}/${PROJECT_NAME}-${TIMESTAMP}.tar.gz"

echo "正在打包项目: ${PROJECT_NAME}"
echo "输出文件: ${OUTPUT_FILE}"

# 打包，排除 gitignore 内容但包含 .env
cd "${PARENT_DIR}"

tar --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '*.pyd' \
    --exclude 'venv' \
    --exclude '.venv' \
    --exclude 'test.db*' \
    --exclude '.DS_Store' \
    --exclude '.env.*' \
    --exclude '.spec-workflow' \
    --exclude '.vscode' \
    --exclude '._*' \
    --exclude '.git' \
    -czvf "${OUTPUT_FILE}" "${PROJECT_NAME}"

# 显示结果
echo ""
echo "✅ 打包完成!"
echo "文件: ${OUTPUT_FILE}"
echo "大小: $(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')"