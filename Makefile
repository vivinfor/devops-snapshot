SHELL := /bin/bash

SERVICE ?= app

BLUE  := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC    := \033[0m

.PHONY: help
help:
	@echo "$(BLUE)=== Comandos Disponíveis ===$(NC)"
	@echo "$(GREEN)make fetch$(NC)       - Extrai work items do Azure DevOps"
	@echo "$(GREEN)make report$(NC)      - Gera relatório de backlog e retrabalho"
	@echo "$(GREEN)make build$(NC)       - Reconstrói a imagem sem cache"
	@echo "$(GREEN)make shell$(NC)       - Acessa o shell do container"
	@echo "$(GREEN)make clean$(NC)       - Remove containers e volumes"

.PHONY: fetch
fetch:
	@echo "$(BLUE)Extraindo work items...$(NC)"
	docker-compose run --rm $(SERVICE) python -m app.cli fetch

.PHONY: report
report:
	@echo "$(BLUE)Gerando relatório...$(NC)"
	docker-compose run --rm $(SERVICE) python -m app.cli report

.PHONY: build
build:
	@echo "$(BLUE)Reconstruindo imagem sem cache...$(NC)"
	docker-compose build --no-cache

.PHONY: shell
shell:
	@echo "$(BLUE)Acessando shell do container $(SERVICE)...$(NC)"
	docker-compose run --rm $(SERVICE) /bin/bash

.PHONY: clean
clean:
	@echo "$(YELLOW)Removendo containers e volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)Limpeza concluída!$(NC)"
