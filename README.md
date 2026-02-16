# Pod Connectivity Tests

Framework de tests de connectivité pour les pods Kubernetes basé sur la matrice des flux PeopleSpheres.

## Architecture

Le projet est structuré en 3 couches selon les principes de Clean Architecture:

```
pod-connectivity-tests/
├── handlers/          # Layer 1 - Points d'entrée et orchestration
├── usecases/          # Layer 2 - Logique métier des tests par service
├── infrastructure/    # Layer 3 - Adapters pour Kafka, RabbitMQ, HTTP, DB, etc.
├── config/            # Configuration des environnements
├── reports/           # Rapports de tests générés
└── tests/             # Tests unitaires
```

## Principes

1. **Handlers** : Orchestrent l'exécution des tests (CLI, API, Scheduled)
2. **Use Cases** : Définissent les scénarios de test pour chaque service
3. **Infrastructure** : Implémentent les clients de communication (Kafka, RabbitMQ, PostgreSQL, HTTP, SFTP)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Modifier `config/environments.yaml` pour adapter aux environnements DEV/QA/PP/PROD.

## Utilisation

### Exécuter tous les tests
```bash
python main.py --env dev --all
```

### Exécuter les tests d'un service spécifique
```bash
python main.py --env dev --service pso-out-mapping
```

### Exécuter les tests d'une catégorie
```bash
python main.py --env dev --category kafka
python main.py --env dev --category rabbitmq
python main.py --env dev --category database
```

### Générer un rapport détaillé
```bash
python main.py --env dev --all --report-format html
```

## Services testés

### Core Services
- AutoComplete (EmailGenerator, EmailPrefixGenerator, NumberGenerator, RegistrationNumberGenerator)
- HARBINGER WEB-APP
- AuthAPI Middleware
- API REST CoreAPI
- BackOffice
- Queue Worker
- Scheduler
- DOCGEN
- Search Engine Consumer
- KMS API

### CFK Services
- pso-out-mapping
- pso-out-scheduler
- pso-out-provider
- pso-out-smart-connector
- pso-out-file-delivery
- pso-io-transformer
- pso-io-kms
- pso-in-provider
- pso-in-service
- tracking-flow-service
- Archive-service
- Connector-builder

### Message Brokers
- RabbitMQ (AMQP 5672)
- Kafka (SASL/TLS 9092)

### Databases
- PostgreSQL (CoreDB, Gateway, Keycloak, Search Engine)
- ElasticSearch

### Third Party
- Keycloak
- KONG Gateway
- Memcached
- SFTP Servers

## Types de tests

1. **Connectivity Tests** : Vérification de la connectivité réseau (TCP/TLS)
2. **Authentication Tests** : Validation des credentials et tokens
3. **Functional Tests** : Tests de bout-en-bout des flux métier
4. **Performance Tests** : Mesure de latence et throughput

## Rapports

Les rapports sont générés dans `reports/` avec:
- Résultats détaillés par service
- Métriques de performance
- Logs d'erreurs
- Recommandations
