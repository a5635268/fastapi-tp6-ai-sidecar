# 尝试加载 .env 文件中的环境变量
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# 服务器和远程路径配置，如果没有在 .env 中设置，将赋予空值
SERVER ?= $(DEPLOY_USER)@$(DEPLOY_HOST)
REMOTE_PATH ?= $(DEPLOY_PATH)
CONTAINER ?= $(DEPLOY_CONTAINER)

# 颜色输出
GREEN = \033[0;32m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help check-env deploy restart logs

help:
	@echo "可用命令列表:"
	@echo "  make deploy  - \033[0;32m同步代码到远程服务器并重启容器 (推荐)\033[0m"
	@echo "  make restart - 仅在服务器上端重启容器"
	@echo "  make logs    - 追踪服务器端 $(CONTAINER) 容器的日志"

check-env:
	@if [ -z "$(DEPLOY_USER)" ] || [ -z "$(DEPLOY_HOST)" ] || [ -z "$(DEPLOY_PATH)" ] || [ -z "$(DEPLOY_CONTAINER)" ]; then \
		echo "$(RED)错误: .env 文件配置缺失！$(NC)"; \
		echo "请务必在项目根目录的 .env 文件中添加如下配置："; \
		echo "DEPLOY_USER=your-username"; \
		echo "DEPLOY_HOST=your-server-ip"; \
		echo "DEPLOY_PATH=/path/to/your/app"; \
		echo "DEPLOY_CONTAINER=fastapi-tp6-app"; \
		exit 1; \
	fi

deploy: check-env
	@echo "$(GREEN)🚀 正在同步代码到 $(SERVER):$(REMOTE_PATH) ...$(NC)"
	rsync -avz --delete \
		--exclude '__pycache__' \
		--exclude '*.pyc' \
		--exclude '.git' \
		--exclude '.vscode' \
		--exclude '.env' \
		--exclude 'venv' \
		--exclude 'logs' \
		--exclude 'doc' \
		--exclude '.spec-workflow' \
		--exclude '.venv' \
		--exclude '.idea' \
		./ $(SERVER):$(REMOTE_PATH)/
	@echo "$(GREEN)🔄 正在重建并拉起容器以应用新代码...$(NC)"
	ssh $(SERVER) "cd $(REMOTE_PATH) && docker-compose up -d --build $(CONTAINER)"
	@echo "$(GREEN)✅ 部署完成！$(NC)"

restart: check-env
	@echo "$(GREEN)🔄 重启容器 $(CONTAINER)...$(NC)"
	ssh $(SERVER) "cd $(REMOTE_PATH) && docker-compose restart $(CONTAINER)"
	@echo "$(GREEN)✅ 重启完成！$(NC)"

logs: check-env
	@echo "$(GREEN)📋 查看 $(CONTAINER) 日志 (按 Ctrl+C 退出)...$(NC)"
	ssh $(SERVER) "cd $(REMOTE_PATH) && docker-compose logs -f $(CONTAINER)"
