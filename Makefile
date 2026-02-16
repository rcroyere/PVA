.PHONY: help install test clean run-dev run-qa run-all list-services

help: ## Affiche l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances
	pip install -r requirements.txt

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
