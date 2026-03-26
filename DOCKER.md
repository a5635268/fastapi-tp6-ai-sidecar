# Docker 运行指南

## 快速启动

```bash
# 构建并启动（后台运行）
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 访问地址

- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 常用命令

```bash
# 重新构建镜像
docker-compose build --no-cache

# 查看容器状态
docker-compose ps

# 进入容器
docker-compose exec fastapi-app /bin/bash

# 查看实时日志
docker-compose logs -f fastapi-app
```