#!/usr/bin/env python
"""
ARQ Worker 启动脚本

独立进程运行，与 FastAPI 应用解耦。

启动方式：
    # 开发环境（前台运行）
    python workers/run_worker.py

    # 后台运行
    nohup python workers/run_worker.py > logs/worker.log 2>&1 &

    # 生产环境（使用 systemd 管理）
    sudo systemctl start arq-worker
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arq import run_worker
from app.tasks.worker import WorkerSettings


if __name__ == "__main__":
    """
    启动 ARQ Worker

    Worker 会：
    - 连接到 Redis
    - 轮询任务队列
    - 执行任务函数
    - 运行 Cron 定时任务
    """
    # 运行 Worker
    run_worker(WorkerSettings)