.PHONY: help install test clean run-dev run-qa run-all list-services

help: ## Affiche l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances
	pip install -r requirements.txt

dependencies: ## Vérifie et affiche l'état de toutes les dépendances de l'application
	@echo ""
	@echo "=== Dépendances système ==="
	@echo ""
	@printf "  %-20s" "python3"; python3 --version 2>/dev/null && echo "  [OK]" || echo "  [MANQUANT]"
	@printf "  %-20s" "pip"; pip --version 2>/dev/null | awk '{print $$1, $$2}' && echo "  [OK]" || echo "  [MANQUANT]"
	@printf "  %-20s" "kubectl"; kubectl version --client --short 2>/dev/null | head -1 && echo "  [OK]" || echo "  [MANQUANT] (requis pour --mode kubectl)"
	@echo ""
	@echo "=== Dépendances Python ==="
	@echo ""
	@printf "  %-30s %s\n" "pyyaml"               "Configuration YAML (environments.yaml)"
	@python3 -c "import yaml; print('  [OK]  yaml', yaml.__version__)" 2>/dev/null || echo "  [KO]  pip install pyyaml>=6.0.1"
	@printf "  %-30s %s\n" "pydantic"              "Validation des modèles de données"
	@python3 -c "import pydantic; print('  [OK]  pydantic', pydantic.__version__)" 2>/dev/null || echo "  [KO]  pip install pydantic>=2.5.0"
	@printf "  %-30s %s\n" "python-dotenv"         "Chargement des credentials (.env)"
	@python3 -c "import dotenv; print('  [OK]  python-dotenv', dotenv.__version__)" 2>/dev/null || echo "  [KO]  pip install python-dotenv>=1.0.0"
	@printf "  %-30s %s\n" "click"                 "Interface CLI (main.py)"
	@python3 -c "import click; print('  [OK]  click', click.__version__)" 2>/dev/null || echo "  [KO]  pip install click>=8.1.7"
	@printf "  %-30s %s\n" "rich"                  "Affichage terminal enrichi"
	@python3 -c "import rich; print('  [OK]  rich', rich.__version__)" 2>/dev/null || echo "  [KO]  pip install rich>=13.7.0"
	@printf "  %-30s %s\n" "kafka-python"          "Protocole Kafka (SASL/TLS)"
	@python3 -c "import kafka; print('  [OK]  kafka-python', kafka.__version__)" 2>/dev/null || echo "  [KO]  pip install kafka-python>=2.0.2"
	@printf "  %-30s %s\n" "pika"                  "Protocole RabbitMQ (AMQP)"
	@python3 -c "import pika; print('  [OK]  pika', pika.__version__)" 2>/dev/null || echo "  [KO]  pip install pika>=1.3.2"
	@printf "  %-30s %s\n" "psycopg2-binary"       "Protocole PostgreSQL"
	@python3 -c "import psycopg2; print('  [OK]  psycopg2', psycopg2.__version__)" 2>/dev/null || echo "  [KO]  pip install psycopg2-binary>=2.9.9"
	@printf "  %-30s %s\n" "paramiko"              "Protocole SFTP/SSH"
	@python3 -c "import paramiko; print('  [OK]  paramiko', paramiko.__version__)" 2>/dev/null || echo "  [KO]  pip install paramiko>=3.4.0"
	@printf "  %-30s %s\n" "aiohttp"               "Client HTTP/HTTPS async"
	@python3 -c "import aiohttp; print('  [OK]  aiohttp', aiohttp.__version__)" 2>/dev/null || echo "  [KO]  pip install aiohttp>=3.9.1"
	@printf "  %-30s %s\n" "httpx"                 "Client HTTP/HTTPS alternatif"
	@python3 -c "import httpx; print('  [OK]  httpx', httpx.__version__)" 2>/dev/null || echo "  [KO]  pip install httpx>=0.25.2"
	@printf "  %-30s %s\n" "jinja2"                "Génération rapports HTML"
	@python3 -c "import jinja2; print('  [OK]  jinja2', jinja2.__version__)" 2>/dev/null || echo "  [KO]  pip install jinja2>=3.1.2"
	@printf "  %-30s %s\n" "cryptography"          "TLS/mTLS, chiffrement"
	@python3 -c "import cryptography; print('  [OK]  cryptography', cryptography.__version__)" 2>/dev/null || echo "  [KO]  pip install cryptography>=41.0.7"
	@printf "  %-30s %s\n" "tenacity"              "Retry automatique sur les tests"
	@python3 -c "import tenacity; print('  [OK]  tenacity', tenacity.__version__)" 2>/dev/null || echo "  [KO]  pip install tenacity>=8.2.3"
	@printf "  %-30s %s\n" "structlog"             "Logging structuré"
	@python3 -c "import structlog; print('  [OK]  structlog', structlog.__version__)" 2>/dev/null || echo "  [KO]  pip install structlog>=23.2.0"
	@echo ""
	@echo "=== Pour installer toutes les dépendances manquantes ==="
	@echo ""
	@echo "  make install"
	@echo ""

test: ## Exécute les tests unitaires
	pytest tests/ -v --cov=. --cov-report=html

clean: ## Nettoie les fichiers temporaires
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf reports/*.html reports/*.json reports/*.xml

run-dev: ## Exécute tous les tests en DEV
	python main.py --env dev --all --report-format html

run-qa: ## Exécute tous les tests en QA
	python main.py --env qa --all --report-format html

run-pp: ## Exécute tous les tests en PP
	python main.py --env pp --all --report-format html

run-prod: ## Exécute tous les tests en PROD (avec prudence!)
	@echo "⚠️  WARNING: Vous allez exécuter des tests en PRODUCTION!"
	@read -p "Êtes-vous sûr? (tapez 'yes' pour continuer): " confirm && [ "$$confirm" = "yes" ]
	python main.py --env prod --all --report-format html

run-service: ## Exécute les tests pour un service spécifique (usage: make run-service ENV=dev SERVICE=pso-out-mapping)
	python main.py --env $(ENV) --service $(SERVICE) --report-format html

run-kafka: ## Exécute uniquement les tests Kafka en DEV
	python main.py --env dev --category kafka --report-format html

run-rabbitmq: ## Exécute uniquement les tests RabbitMQ en DEV
	python main.py --env dev --category rabbitmq --report-format html

run-database: ## Exécute uniquement les tests Database en DEV
	python main.py --env dev --category database --report-format html

list-services: ## Liste les services disponibles pour les tests
	python main.py list-services --env dev

setup-env: ## Crée le fichier .env à partir de .env.example
	cp .env.example .env
	@echo "✅ Fichier .env créé. Veuillez éditer ce fichier avec vos credentials."

lint: ## Vérifie le code avec flake8
	flake8 --max-line-length=120 --exclude=venv,__pycache__,.pytest_cache

format: ## Formate le code avec black
	black --line-length=120 .

docker-build: ## Construit l'image Docker
	docker build -t pod-connectivity-tests:latest .

docker-run-dev: ## Exécute les tests dans Docker (DEV)
	docker run --rm -v $(PWD)/reports:/app/reports --env-file .env pod-connectivity-tests:latest --env dev --all

ci-test: ## Exécute les tests en mode CI/CD
	python main.py --env dev --all --report-format junit

# Commandes de développement
dev-install: ## Installe les dépendances de développement
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio black flake8

dev-watch: ## Mode développement avec auto-reload
	watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- python main.py --env dev --all
