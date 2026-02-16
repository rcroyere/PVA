# Pod Connectivity Tests

Framework de tests de connectivité pour les pods Kubernetes basé sur le DAL (Dossier d'Architecture Logicielle) PeopleSpheres.

## Architecture

Le projet est structuré en 3 couches selon les principes de Clean Architecture:

```
pod-connectivity-tests/
├── handlers/          # Layer 1 - Points d'entrée et orchestration
├── usecases/
│   ├── base_usecase.py
│   ├── cfk/           # Un use case par service Connecteur Framework (15 services)
│   └── core/          # Un use case par service Core API (12 services)
├── infrastructure/    # Layer 3 - Adapters Kafka, RabbitMQ, HTTP, DB, SFTP
├── config/            # Configuration des environnements
├── reports/           # Rapports de tests générés
└── tests/             # Tests unitaires des adapters
```

## Principes

1. **Handlers** : Orchestrent l'exécution des tests (CLI, rapport)
2. **Use Cases** : Définissent les scénarios de test pour chaque service, calqués sur les connexions du DAL
3. **Infrastructure** : Implémentent les clients de communication (Kafka, RabbitMQ, PostgreSQL, HTTP, SFTP)

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Remplir .env avec les credentials
```

## Modes de test

### Mode `direct` (par défaut)

Tests exécutés **depuis le poste de travail** via les clients Python (kafka-python, psycopg2, paramiko…). Nécessite un accès réseau direct aux services.

### Mode `kubectl`

Tests exécutés **depuis l'intérieur des pods** via `kubectl exec`. Reflète la vraie connectivité intra-cluster (NetworkPolicies, DNS interne, mTLS). Nécessite `kubectl` configuré avec accès au cluster.

```bash
# Mode kubectl : tests depuis le pod pso-out-mapping
python main.py run --env dev --service pso-out-mapping --mode kubectl

# Mode kubectl sur tous les services
python main.py run --env dev --all --mode kubectl
```

**Comportement en mode kubectl :**
- TCP (Kafka, PostgreSQL, RabbitMQ, SFTP) → `bash -c "echo >/dev/tcp/host/port"` (sans outils)
- HTTP/HTTPS → `curl -sf --max-time 10`
- Auth / fonctionnel → fallback TCP avec note (SASL, psql, AMQP non disponibles dans les pods applicatifs)

## Utilisation

### Exécuter tous les tests

```bash
python main.py run --env dev --all
```

### Exécuter les tests d'un service spécifique

```bash
python main.py run --env dev --service pso-out-mapping
python main.py run --env dev --service core-api
```

### Exécuter les tests par domaine ou catégorie

```bash
python main.py run --env dev --category cfk       # Tous les services CFK
python main.py run --env dev --category core      # Tous les services Core API
python main.py run --env dev --category kafka     # Filtrer par protocole
python main.py run --env dev --category rabbitmq
python main.py run --env dev --category database
```

### Lister les services disponibles

```bash
python main.py list-services --env dev
```

### Générer un rapport détaillé

```bash
python main.py run --env dev --all --report-format html
python main.py run --env dev --all --report-format json
python main.py run --env dev --all --report-format junit
```

## Services testés

### CFK - Connecteur Framework (15 services)

| Service | Connexions testées |
|---|---|
| archive-service | PostgreSQL CFK (archive), Kafka, SFTP, GCP Secret Manager |
| connector-builder | Temporal.io |
| observability-api | Kafka (service désactivé → SKIPPED) |
| open-api-service | PostgreSQL CFK (openapi), Kafka |
| pso-data-stack | PostgreSQL CoreDB, PostgreSQL CFK (openapi), Kafka |
| pso-in-provider | PostgreSQL CFK (mapping), Kafka |
| pso-in-service | Kafka |
| pso-io-kms | PostgreSQL CFK (kms), Kafka |
| pso-io-transformer | Kafka |
| pso-out-file-delivery | PostgreSQL CFK (file_out_delivery), Kafka, GCP Secret Manager |
| pso-out-mapping | PostgreSQL CFK (mapping), Kafka |
| pso-out-provider | PostgreSQL CFK (provider), Kafka |
| pso-out-scheduler | PostgreSQL CFK (scheduler), Kafka |
| pso-out-smart-connector | Kafka |
| temporal-translator | Kafka, Temporal.io |

### Core API (12 services)

| Service | Connexions testées |
|---|---|
| core-api | RabbitMQ, PostgreSQL CoreDB, PostgreSQL Gateway, Search Engine API, KMS API, Keycloak, SFTP |
| queue-worker | RabbitMQ, PostgreSQL CoreDB, PostgreSQL Gateway, Search Engine API, KMS API, Keycloak, SFTP |
| scheduler | RabbitMQ, PostgreSQL CoreDB, PostgreSQL Gateway, Keycloak, SFTP, Mandrill |
| rabbit-consumer | RabbitMQ |
| auth-api | CoreAPI HTTP, Keycloak, SFTP |
| docgen | RabbitMQ, SFTP, API-TO-PDF |
| search-engine-api | PostgreSQL Search Engine, CoreAPI HTTP |
| search-engine-consumer | RabbitMQ, PostgreSQL Search Engine |
| backoffice | AuthAPI HTTP, PostgreSQL Gateway, PostgreSQL Search Engine, Kafka |
| pso-io-webhook | RabbitMQ, PostgreSQL CoreDB, Keycloak |
| ecosystem-api | PostgreSQL EcosystemDB, Keycloak |
| kms-api | GCP KMS, PostgreSQL KMS |

### Infrastructures communes

- **Message Brokers** : RabbitMQ (AMQP/TLS 5672), Kafka (SASL/TLS 9092)
- **Bases de données** : PostgreSQL (CoreDB, Gateway, Keycloak, CFK×7, Search Engine, Ecosystem, KMS)
- **Services tiers** : Keycloak, Temporal.io, GCP Secret Manager, GCP KMS, SFTP

## Types de tests

1. **Connectivity** : Vérification de la connectivité réseau (TCP/TLS)
2. **Authentication** : Validation des credentials
3. **Functional** : Tests de bout-en-bout (topics Kafka, queues RabbitMQ, tables PostgreSQL)
4. **Skipped** : Service désactivé (ex: observability-api)

## Rapports

Les rapports sont générés dans `reports/` :
- `html` — rapport interactif avec détails par service
- `json` — format structuré pour intégrations
- `junit` — XML compatible GitLab CI/CD, Jenkins
