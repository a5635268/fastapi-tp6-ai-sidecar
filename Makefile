# 尝试加载 .env 文件（可选，仅用于自定义配置）
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# 颜色输出
GREEN = \033[0;32m
RED = \033[0;31m
NC = \033[0m # No Color

# 服务器配置：dev92 或 xiaoxi149
DEPLOY_TARGET ?= xiaoxi149

# 根据目标服务器设置配置
ifeq ($(DEPLOY_TARGET),dev92)
    SERVER = root@dev92
    REMOTE_PATH = /www/wwwroot/fastapi-tp6/fastapi-tp6
    CONTAINER = fastapi-tp6-app
else ifeq ($(DEPLOY_TARGET),xiaoxi149)
    SERVER = root@xiaoxi149
    REMOTE_PATH = /www/wwwroot/fastapi-tp6-docker
    CONTAINER = fastapi-tp6-app
else
    # 自定义配置
    SERVER = $(DEPLOY_USER)@$(DEPLOY_HOST)
    REMOTE_PATH = $(DEPLOY_PATH)
    CONTAINER = $(DEPLOY_CONTAINER)
endif

.PHONY: help deploy restart logs

help:
	@echo "可用命令列表:"
	@echo "  make deploy                     - \033[0;32m同步代码到默认服务器 (xiaoxi149) 并重启容器\033[0m"
	@echo "  make deploy DEPLOY_TARGET=dev92 - \033[0;32m同步代码到 dev92 服务器\033[0m"
	@echo "  make deploy DEPLOY_TARGET=xiaoxi149 - \033[0;32m同步代码到 xiaoxi149 服务器\033[0m"
	@echo "  make restart                    - 重启默认服务器容器"
	@echo "  make logs                       - 追踪服务器端容器日志"

deploy:
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

restart:
	@echo "$(GREEN)🔄 重启容器 $(CONTAINER)...$(NC)"
	ssh $(SERVER) "cd $(REMOTE_PATH) && docker-compose restart $(CONTAINER)"
	@echo "$(GREEN)✅ 重启完成！$(NC)"

logs:
	@echo "$(GREEN)📋 查看 $(CONTAINER) 日志 (按 Ctrl+C 退出)...$(NC)"
	ssh $(SERVER) "cd $(REMOTE_PATH) && docker-compose logs -f $(CONTAINER)"
