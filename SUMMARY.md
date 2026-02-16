# Framework de Tests de Connectivité - Pods Kubernetes

## Vue d'ensemble

Framework complet de tests de connectivité pour l'infrastructure Kubernetes de PeopleSpheres, basé sur le DAL (Dossier d'Architecture Logicielle). Architecture en 3 couches (Clean Architecture) avec support multi-environnements (DEV/QA/PP/PROD).

## Architecture

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
│           (Un use case par service, calqué sur le DAL)       │
│  usecases/cfk/  → 15 services Connecteur Framework         │
│  usecases/core/ → 12 services Core API                     │
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

## Contenu du Framework

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
├── base_usecase.py
├── cfk/                             # Connecteur Framework (15 services)
│   ├── archive_service_usecase.py
│   ├── connector_builder_usecase.py
│   ├── observability_api_usecase.py
│   ├── open_api_service_usecase.py
│   ├── pso_data_stack_usecase.py
│   ├── pso_in_provider_usecase.py
│   ├── pso_in_service_usecase.py
│   ├── pso_io_kms_usecase.py
│   ├── pso_io_transformer_usecase.py
│   ├── pso_out_file_delivery_usecase.py
│   ├── pso_out_mapping_usecase.py
│   ├── pso_out_provider_usecase.py
│   ├── pso_out_scheduler_usecase.py
│   ├── pso_out_smart_connector_usecase.py
│   └── temporal_translator_usecase.py
└── core/                            # Core API (12 services)
    ├── core_api_usecase.py
    ├── queue_worker_usecase.py
    ├── scheduler_usecase.py
    ├── rabbit_consumer_usecase.py
    ├── auth_api_usecase.py
    ├── docgen_usecase.py
    ├── search_engine_api_usecase.py
    ├── search_engine_consumer_usecase.py
    ├── backoffice_usecase.py
    ├── pso_io_webhook_usecase.py
    ├── ecosystem_api_usecase.py
    └── kms_api_usecase.py
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
FLUX_MAPPING.md    # Mapping DAL → tests
```

## Démarrage Rapide

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
python main.py list-services --env dev

# Exécuter tous les tests en DEV
python main.py run --env dev --all

# Tester un service spécifique
python main.py run --env dev --service pso-out-mapping

# Tests par domaine
python main.py run --env dev --category cfk    # Tous les services CFK
python main.py run --env dev --category core   # Tous les services Core API

# Tests par protocole
python main.py run --env dev --category kafka
python main.py run --env dev --category rabbitmq
```

### Rapports Générés
```bash
reports/
├── test_report_dev_20240216_143022.html  # Rapport interactif
├── test_report_dev_20240216_143022.json  # Format structuré
└── test_report_dev_20240216_143022.xml   # JUnit XML (CI/CD)
```

## Types de Tests Implémentés

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

## Services Couverts

### Services CFK (Connecteur Framework) — 15 services
| Service | Connexions testées |
|---|---|
| ✅ archive-service | PostgreSQL CFK (archive), Kafka, SFTP, GCP Secret Manager |
| ✅ connector-builder | Temporal.io |
| ✅ observability-api | Kafka (service désactivé → SKIPPED) |
| ✅ open-api-service | PostgreSQL CFK (openapi), Kafka |
| ✅ pso-data-stack | PostgreSQL CoreDB, PostgreSQL CFK (openapi), Kafka |
| ✅ pso-in-provider | PostgreSQL CFK (mapping), Kafka |
| ✅ pso-in-service | Kafka |
| ✅ pso-io-kms | PostgreSQL CFK (kms), Kafka |
| ✅ pso-io-transformer | Kafka |
| ✅ pso-out-file-delivery | PostgreSQL CFK (file_out_delivery), Kafka, GCP Secret Manager |
| ✅ pso-out-mapping | PostgreSQL CFK (mapping), Kafka |
| ✅ pso-out-provider | PostgreSQL CFK (provider), Kafka |
| ✅ pso-out-scheduler | PostgreSQL CFK (scheduler), Kafka |
| ✅ pso-out-smart-connector | Kafka |
| ✅ temporal-translator | Kafka, Temporal.io |

### Services Core API — 12 services
| Service | Connexions testées |
|---|---|
| ✅ core-api | RabbitMQ, PostgreSQL CoreDB+Gateway, KMS API, Search Engine, Keycloak, SFTP |
| ✅ queue-worker | RabbitMQ, PostgreSQL CoreDB+Gateway, KMS API, Search Engine, Keycloak, SFTP |
| ✅ scheduler | RabbitMQ, PostgreSQL CoreDB+Gateway, Keycloak, SFTP, Mandrill |
| ✅ rabbit-consumer | RabbitMQ |
| ✅ auth-api | CoreAPI HTTP, Keycloak, SFTP |
| ✅ docgen | RabbitMQ, SFTP, API-TO-PDF |
| ✅ search-engine-api | PostgreSQL Search Engine, CoreAPI HTTP |
| ✅ search-engine-consumer | RabbitMQ, PostgreSQL Search Engine |
| ✅ backoffice | AuthAPI HTTP, PostgreSQL Gateway+SearchEngine, Kafka |
| ✅ pso-io-webhook | RabbitMQ, PostgreSQL CoreDB, Keycloak |
| ✅ ecosystem-api | PostgreSQL EcosystemDB, Keycloak |
| ✅ kms-api | GCP KMS, PostgreSQL KMS |

### Message Brokers
- ✅ Kafka (SASL/TLS, port 9092)
- ✅ RabbitMQ (AMQP/TLS, port 5672)

### Bases de Données PostgreSQL
- ✅ CoreDB, Gateway, Keycloak
- ✅ CFK (archive, mapping, openapi, kms, file_delivery, provider, scheduler)
- ✅ Search Engine, Ecosystem, KMS

### Services Tiers
- ✅ Keycloak (authentification)
- ✅ Temporal.io
- ✅ GCP Secret Manager / GCP KMS
- ✅ SFTP Servers

## Extensibilité

### Ajouter un Nouveau Service

**Étape 1:** Créer le use case dans le domaine approprié
```python
# usecases/cfk/mon_service_usecase.py  (ou usecases/core/)
class MonServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__("mon-service", "namespace", env_config)
        # Initialiser adapters selon les connexions du DAL

    async def run_connectivity_tests(self):
        # Implémenter tests de connectivité

    async def run_functional_tests(self):
        # Implémenter tests fonctionnels
```

**Étape 2:** Enregistrer dans le handler
```python
# handlers/cli_handler.py
_CFK_USECASES = [
    ...,
    MonServiceUseCase,  # Ajouter à la liste du domaine
]

_USECASE_MAP = {
    ...,
    'mon-service': MonServiceUseCase,
}
```

**C'est tout !** Le nouveau service est automatiquement inclus.

## Docker

### Build et Run
```bash
# Build l'image
make docker-build

# Exécuter avec Docker
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  --env-file .env \
  pod-connectivity-tests:latest \
  run --env dev --all

# Ou avec Docker Compose
docker-compose up
```

## CI/CD

### GitLab CI/CD Pipeline
```yaml
# Automatique sur push main/develop
connectivity_tests_dev:
  script:
    - python main.py run --env dev --all --report-format junit

# Manuel pour QA/PP
connectivity_tests_qa:
  when: manual
  script:
    - python main.py run --env qa --all --report-format junit

# Scheduled (cron)
scheduled_connectivity_tests:
  only:
    - schedules
  script:
    - python main.py run --env dev --all
```

## Commandes Make Disponibles

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

## Securité

- Credentials stockés dans `.env` (non versionné)
- Support mTLS pour PostgreSQL
- Support SASL/TLS pour Kafka
- Support AMQP/TLS pour RabbitMQ
- Variables d'environnement pour tous les secrets

## Basé sur le DAL

Ce framework est directement basé sur le DAL (Dossier d'Architecture Logicielle) PeopleSpheres:
- Connexions CFK → Use cases `usecases/cfk/`
- Connexions Core → Use cases `usecases/core/`
- Chaque use case ne teste que les connexions déclarées dans le DAL pour son service

Voir **FLUX_MAPPING.md** pour détails du mapping.

## Auteur

Framework développé pour PeopleSpheres - DevOps/Platform Engineering

## Licence

Propriétaire PeopleSpheres
