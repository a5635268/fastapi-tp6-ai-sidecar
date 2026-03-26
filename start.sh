#!/bin/bash

# ==========================================================
# FastAPI 项目一键 Docker 部署脚本
# ==========================================================

# 配置变量
IMAGE_NAME="fastapi-tp6-image"
CONTAINER_NAME="fastapi-tp6-app"
PORT="8000"

echo "====================================="
echo "🚀 开始构建与部署项目..."
echo "====================================="

# 1. 检测是否需要先停止旧容器
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "📦 发现旧容器 [${CONTAINER_NAME}]，正在停止并移除..."
    docker stop ${CONTAINER_NAME} > /dev/null
    docker rm ${CONTAINER_NAME} > /dev/null
    echo "✅ 旧容器已清理完毕。"
fi

# 2. 检查是否有 test.db 文件，如果没有则创建一个空文件，防止挂载报错
if [ ! -f "test.db" ]; then
    echo "🗄️ 未找到 test.db，正在创建空数据库文件以便 Docker 挂载..."
    touch test.db
fi

# 3. 检查环境变量文件是否存
ENV_FILE=""
if [ -f ".env" ]; then
    echo "⚙️ 发现 .env 配置文件，将被挂载到容器中..."
    ENV_FILE="--env-file .env"
fi

# 4. 构建 Docker 镜像
echo "🔨 正在使用当前目录构建 Docker 镜像: ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} .

# 检测构建是否成功
if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功！正在启动新容器..."
    echo "====================================="
    
    # 5. 运行容器
    # 挂载 test.db，防止重新发布时数据库丢失
    docker run -d \
        --name ${CONTAINER_NAME} \
        -p ${PORT}:8000 \
        ${ENV_FILE} \
        -v $(pwd)/test.db:/app/test.db \
        --restart unless-stopped \
        ${IMAGE_NAME}
        
    echo "====================================="
    echo "🎉 恭喜！服务已成功启动！"
    echo "🌐 API 访问: http://localhost:${PORT}"
    echo "📜 文档访问: http://localhost:${PORT}/docs"
    echo "🔍 查看日志: docker logs -f ${CONTAINER_NAME}"
    echo "⏹ 停止服务: docker stop ${CONTAINER_NAME}"
    echo "====================================="
else
    echo "====================================="
    echo "❌ 错误：Docker 镜像构建失败，请检查 Dockerfile 及报错信息。"
    echo "====================================="
    exit 1
fi
