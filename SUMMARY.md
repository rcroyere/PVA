# 🎯 Framework de Tests de Connectivité - Pods Kubernetes

## 📋 Vue d'ensemble

Framework complet de tests de connectivité pour l'infrastructure Kubernetes de PeopleSpheres, basé sur la matrice des flux réseau. Architecture en 3 couches (Clean Architecture) avec support multi-environnements (DEV/QA/PP/PROD).

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1 - HANDLERS                        │
│             (Points d'entrée et orchestration)               │
│  • CLI Handler: Exécution ligne de commande                 │
│  • Report Handler: Génération rapports HTML/JSON/JUnit      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 2 - USE CASES                       │
│           (Logique métier des tests par service)             │
│  • pso-out-mapping: Tests mapping + Kafka + PostgreSQL      │
│  • pso-out-scheduler: Tests scheduler + Kafka               │
│  • core-api: Tests API + RabbitMQ + PostgreSQL + Keycloak   │
│  • ... (extensible facilement)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 3 - INFRASTRUCTURE                     │
│          (Adapters pour protocoles de communication)         │
│  • Kafka: Client SASL/TLS, topics, produce/consume          │
│  • RabbitMQ: Client AMQP/TLS, queues, publish/subscribe     │
│  • PostgreSQL: Client mTLS, queries, tables                 │
│  • HTTP/HTTPS: REST APIs, health checks                     │
│  • SFTP: SSH, file operations                               │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Contenu du Framework

### Fichiers Principaux
- **main.py** - Point d'entrée de l'application
- **models.py** - Modèles de données (TestResult, ServiceTestSuite, TestExecutionReport)
- **requirements.txt** - Dépendances Python
- **Makefile** - Commandes utilitaires
- **Dockerfile** - Image Docker pour déploiement
- **.gitlab-ci.yml** - Pipeline CI/CD

### Layer 1 - Handlers (Orchestration)
```
handlers/
├── cli_handler.py      # Orchestration CLI, gestion config
└── report_handler.py   # Génération HTML/JSON/JUnit
```

### Layer 2 - Use Cases (Logique Métier)
```
usecases/
├── base_usecase.py               # Classe abstraite de base
├── pso_out_mapping_usecase.py    # Tests pso-out-mapping
├── pso_out_scheduler_usecase.py  # Tests pso-out-scheduler
└── core_api_usecase.py           # Tests Core API
```

### Layer 3 - Infrastructure (Adapters)
```
infrastructure/
├── base_adapter.py        # Interface adapter
├── kafka_adapter.py       # Client Kafka SASL/TLS
├── rabbitmq_adapter.py    # Client RabbitMQ AMQP/TLS
├── postgresql_adapter.py  # Client PostgreSQL mTLS
├── http_adapter.py        # Client HTTP/HTTPS REST
└── sftp_adapter.py        # Client SFTP/SSH
```

### Configuration
```
config/
└── environments.yaml  # Configuration DEV/QA/PP/PROD
```

### Tests
```
tests/
└── test_adapters.py  # Tests unitaires des adapters
```

### Documentation
```
README.md          # Documentation principale
QUICKSTART.md      # Guide démarrage rapide
ARCHITECTURE.md    # Architecture détaillée 3 layers
FLUX_MAPPING.md    # Mapping matrice Excel → tests
STRUCTURE.txt      # Synthèse de la structure
```

## 🚀 Démarrage Rapide

### Installation
```bash
# Cloner et installer
git clone <repository-url>
cd pod-connectivity-tests
make install

# Configurer les credentials
cp .env.example .env
# Éditer .env avec vos credentials
```

### Utilisation Basique
```bash
# Lister les services disponibles
make list-services

# Exécuter tous les tests en DEV
make run-dev

# Tester un service spécifique
make run-service ENV=dev SERVICE=pso-out-mapping

# Tests par catégorie
make run-kafka      # Tests Kafka uniquement
make run-rabbitmq   # Tests RabbitMQ uniquement
make run-database   # Tests Database uniquement
```

### Rapports Générés
```bash
reports/
├── test_report_dev_20240216_143022.html  # Rapport interactif
├── test_report_dev_20240216_143022.json  # Format structuré
└── test_report_dev_20240216_143022.xml   # JUnit XML (CI/CD)
```

## 🧪 Types de Tests Implémentés

### 1. Tests de Connectivité
- Vérification de la disponibilité des services
- Test des timeouts et retries
- Validation des ports et protocoles

### 2. Tests d'Authentification
- Validation SASL pour Kafka
- Validation AMQP pour RabbitMQ
- Validation mTLS pour PostgreSQL
- Validation tokens pour APIs REST

### 3. Tests Fonctionnels
- **Kafka**: Accès topics (READ/WRITE), produce/consume end-to-end
- **RabbitMQ**: Accès queues, publish/subscribe end-to-end
- **PostgreSQL**: Accès tables, performance queries
- **HTTP**: Health checks, endpoints REST
- **SFTP**: Upload/download fichiers

### 4. Tests de Performance
- Mesure de latence (en ms)
- Mesure de throughput
- Profiling des queries SQL

## 📊 Services Couverts

### Services CFK (Connector Framework)
- ✅ pso-out-mapping
- ✅ pso-out-scheduler
- ⏳ pso-out-provider
- ⏳ pso-out-smart-connector
- ⏳ pso-out-file-delivery
- ⏳ pso-io-transformer
- ⏳ pso-in-provider
- ⏳ tracking-flow-service

### Services Core
- ✅ API REST CoreAPI
- ⏳ AuthAPI Middleware
- ⏳ Queue Worker
- ⏳ Scheduler
- ⏳ Search Engine
- ⏳ KMS API

### Message Brokers
- ✅ Kafka (SASL/TLS, port 9092)
- ✅ RabbitMQ (AMQP/TLS, port 5672)

### Bases de Données
- ✅ PostgreSQL CoreDB
- ✅ PostgreSQL Gateway
- ✅ PostgreSQL Keycloak
- ⏳ Elasticsearch

### Services Tiers
- ✅ Keycloak (authentification)
- ⏳ KONG Gateway
- ⏳ Memcached
- ⏳ SFTP Servers

**Légende:** ✅ Implémenté | ⏳ À implémenter (template disponible)

## 🔧 Extensibilité

### Ajouter un Nouveau Service

**Étape 1:** Créer le use case
```python
# usecases/mon_service_usecase.py
class MonServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__("mon-service", "namespace", env_config)
        # Initialiser adapters selon matrice de flux
        
    async def run_connectivity_tests(self):
        # Implémenter tests de connectivité
        
    async def run_functional_tests(self):
        # Implémenter tests fonctionnels
```

**Étape 2:** Enregistrer dans le handler
```python
# handlers/cli_handler.py
def _get_available_usecases(self, env_config):
    return [
        ...,
        MonServiceUseCase  # <-- Ajouter ici
    ]
```

**C'est tout !** Le nouveau service est automatiquement inclus.

## 🐳 Docker

### Build et Run
```bash
# Build l'image
make docker-build

# Exécuter avec Docker
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  --env-file .env \
  pod-connectivity-tests:latest \
  --env dev --all

# Ou avec Docker Compose
docker-compose up
```

## 🔄 CI/CD

### GitLab CI/CD Pipeline
```yaml
# Automatique sur push main/develop
connectivity_tests_dev:
  script:
    - python main.py --env dev --all --report-format junit
    
# Manuel pour QA/PP
connectivity_tests_qa:
  when: manual
  script:
    - python main.py --env qa --all --report-format junit

# Scheduled (cron)
scheduled_connectivity_tests:
  only:
    - schedules
  script:
    - python main.py --env dev --all
```

## 📈 Métriques et Rapports

### Rapport HTML Interactif
- Résumé global avec graphiques
- Détails par service et namespace
- Messages d'erreur détaillés
- Durée d'exécution
- Taux de succès

### Rapport JSON
```json
{
  "environment": "dev",
  "summary": {
    "total_tests": 45,
    "passed": 42,
    "failed": 3,
    "success_rate": 93.33
  },
  "suites": [...]
}
```

### Rapport JUnit XML
Compatible avec GitLab CI/CD, Jenkins, etc.

## 📚 Documentation

- **README.md** - Ce fichier
- **QUICKSTART.md** - Guide de démarrage rapide
- **ARCHITECTURE.md** - Documentation architecture détaillée
- **FLUX_MAPPING.md** - Guide de mapping matrice Excel → tests
- **STRUCTURE.txt** - Vue d'ensemble de la structure

## 🛠️ Commandes Make Disponibles

```bash
make help              # Affiche toutes les commandes
make install           # Installe dépendances
make test             # Tests unitaires
make clean            # Nettoie fichiers temporaires
make run-dev          # Tests DEV
make run-qa           # Tests QA
make run-service      # Tests service spécifique
make list-services    # Liste services
make docker-build     # Build Docker
make lint             # Vérifie code
make format           # Formate code
```

## 🔐 Sécurité

- Credentials stockés dans `.env` (non versionné)
- Support mTLS pour PostgreSQL
- Support SASL/TLS pour Kafka
- Support AMQP/TLS pour RabbitMQ
- Variables d'environnement pour tous les secrets

## 📝 Basé sur la Matrice de Flux

Ce framework est directement basé sur la matrice des flux PeopleSpheres:
- Onglet "Core_Services" → Tests services core
- Onglet "CFK" → Tests services CFK
- Onglet "Broker_Services" → Tests Kafka/RabbitMQ
- Onglet "Kafka_ACL" → Validation topics et droits
- Onglet "RabbitMQ" → Validation queues
- Onglet "External_DB" → Tests PostgreSQL

Voir **FLUX_MAPPING.md** pour détails du mapping.

## 🎯 Use Cases Principaux

1. **Tests pré-déploiement** - Vérifier infrastructure avant deploy
2. **Tests post-déploiement** - Valider que tout fonctionne
3. **Monitoring continu** - Scheduled tests quotidiens
4. **Non-régression** - Après changement infrastructure
5. **Documentation** - Preuve de connectivité

## 🚦 Status du Projet

✅ **Livré:**
- Architecture 3 layers complète
- 5 adapters (Kafka, RabbitMQ, PostgreSQL, HTTP, SFTP)
- 3 use cases exemples (pso-out-mapping, pso-out-scheduler, core-api)
- CLI handler avec multi-environnements
- Génération rapports HTML/JSON/JUnit
- Tests unitaires
- Documentation complète
- Docker + GitLab CI/CD

⏳ **À venir:**
- Use cases additionnels pour tous les services
- Dashboard Grafana
- Alerting Slack/Email
- Tests de performance avancés
- Intégration Prometheus

## 👥 Auteur

Framework développé pour PeopleSpheres - DevOps/Platform Engineering

## 📄 Licence

Propriétaire PeopleSpheres
