# Architecture du Framework de Tests - Pod Connectivity

## Vue d'ensemble

Ce framework de tests suit les principes de **Clean Architecture** avec une séparation stricte en 3 couches:

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1 - HANDLERS                        │
│  (Points d'entrée: CLI)                                     │
│  • cli_handler.py - Orchestration CLI                       │
│  • report_handler.py - Génération de rapports               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 2 - USE CASES                       │
│  (Un use case par service, connexions issues du DAL)        │
│  usecases/cfk/  → 15 services Connecteur Framework         │
│  usecases/core/ → 12 services Core API                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 3 - INFRASTRUCTURE                     │
│  (Adapters pour les protocoles de communication)            │
│  • kafka_adapter.py - Client Kafka SASL/TLS                 │
│  • rabbitmq_adapter.py - Client RabbitMQ AMQP               │
│  • postgresql_adapter.py - Client PostgreSQL                │
│  • http_adapter.py - Client HTTP/HTTPS REST                 │
│  • sftp_adapter.py - Client SFTP/SSH                        │
│  • kubectl_adapter.py - Exécution via kubectl exec (pods)   │
└─────────────────────────────────────────────────────────────┘
```

## Responsabilités des Couches

### Layer 1 - Handlers (Orchestration)

**Fichiers:**
- `handlers/cli_handler.py` — Handler CLI ; contient les listes `_CFK_USECASES`, `_CORE_USECASES`, `_USECASE_MAP`
- `handlers/report_handler.py` — Génération de rapports (HTML, JSON, JUnit)

**Exemple d'utilisation:**
```python
handler = CLIHandler()
report = await handler.run_all_tests('dev')
report = await handler.run_service_tests('dev', 'pso-out-mapping')
```

### Layer 2 - Use Cases (Logique Métier)

**Responsabilités:**
- Définir les scénarios de tests pour chaque service, calqués sur ses connexions dans le DAL
- Implémenter les tests de connectivité et fonctionnels
- Utiliser les adapters de la couche infrastructure

**Organisation:**
```
usecases/
├── base_usecase.py                  # Classe abstraite commune
├── cfk/                             # Connecteur Framework
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
└── core/                            # Core API
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

**Structure d'un Use Case:**
```python
class ServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__("service-name", "namespace", env_config)
        # self._k() injecte le contexte kubectl si --mode kubectl, sinon no-op
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('cfk_mapping', {})))

    async def run_connectivity_tests(self) -> List[TestResult]:
        # Tests de connectivité : joindre + authentifier chaque destination
        pass

    async def run_functional_tests(self) -> List[TestResult]:
        # Tests fonctionnels : topics Kafka, queues RabbitMQ, tables PostgreSQL
        pass
```

### Layer 3 - Infrastructure (Adapters)

**Interface Adapter:**
```python
class BaseAdapter(ABC):
    async def test_connectivity(self) -> ConnectionResult
    async def test_authentication(self) -> ConnectionResult
    async def close(self)
```

**Adapters disponibles:**
- `KafkaAdapter` — Kafka (SASL/TLS, topics READ/WRITE, produce/consume)
- `RabbitMQAdapter` — RabbitMQ (AMQP/TLS, queues, publish/subscribe)
- `PostgreSQLAdapter` — PostgreSQL (mTLS, queries, tables)
- `HTTPAdapter` — HTTP/HTTPS (REST APIs, health checks)
- `SFTPAdapter` — SFTP/SSH (file operations)
- `KubectlAdapter` — Exécution de commandes dans les pods via `kubectl exec`

## Modes d'Exécution

### Mode `direct` (par défaut)

Les adapters utilisent leurs clients Python natifs (kafka-python, psycopg2, aio-pika, paramiko) depuis le poste de travail. Requiert un accès réseau direct aux services.

### Mode `kubectl`

Les adapters délèguent tous les tests à `KubectlAdapter`, qui exécute des commandes shell **dans le pod** via `kubectl exec` :

| Protocole | Commande exécutée dans le pod |
|---|---|
| TCP (Kafka, PostgreSQL, RabbitMQ, SFTP) | `bash -c "echo >/dev/tcp/host/port"` |
| HTTP/HTTPS | `curl -sf --max-time 10 -o /dev/null -w '%{http_code}'` |
| Auth / Fonctionnel | Fallback TCP (SASL, psql, AMQP non dispo dans les pods applicatifs) |

**Activation :** `python main.py run --env dev --service pso-out-mapping --mode kubectl`

**Mécanisme :**
1. `BaseServiceUseCase.__init__` détecte `env_config['mode'] == 'kubectl'`
2. `KubectlAdapter.find_pod(namespace, app_label)` localise le pod via `kubectl get pods -n ns -l app=label -o name`
3. `self._k(config)` injecte le contexte kubectl dans chaque config d'adapter
4. Chaque adapter détecte `config['_kubectl']` et redirige vers `KubectlAdapter.test_tcp()` ou `test_http()`

## Flux de Données

```
1. CLI/Handler
   └─> Charge la configuration de l'environnement (dev/qa/pp/prod)
   └─> Injecte le mode ('direct' ou 'kubectl') dans env_config
   └─> Sélectionne les Use Cases (_CFK_USECASES / _CORE_USECASES / _ALL_USECASES)

2. Use Case
   └─> Initialise les Adapters selon les connexions du DAL (self._k() injecte le ctx kubectl)
   └─> [mode kubectl] KubectlAdapter.find_pod() localise le pod dans le namespace
   └─> Exécute run_connectivity_tests()
   └─> Exécute run_functional_tests()
   └─> Retourne un ServiceTestSuite

3. Adapter (mode direct)          │  3. KubectlAdapter (mode kubectl)
   └─> Établit la connexion        │     └─> kubectl exec pod -- bash -c "echo >/dev/tcp/host/port"
   └─> Authentifie si nécessaire   │     └─> kubectl exec pod -- curl -sf url
   └─> Exécute l'opération         │     └─> Retourne un ConnectionResult
   └─> Retourne un ConnectionResult│

4. Report Handler
   └─> Agrège tous les ServiceTestSuite
   └─> Génère le rapport dans le format demandé (html/json/junit)
```

## Modèles de Données

### TestResult
Résultat d'un test individuel
- `test_name`, `service_name`, `category`, `protocol`, `status`
- `duration_ms`, `message`, `error`, `metadata`

### ServiceTestSuite
Collection de tests pour un service
- `service_name`, `namespace`, `results[]`
- Métriques: `passed_count`, `failed_count`, `success_rate`

### TestExecutionReport
Rapport global d'exécution
- `environment`, `execution_id`, `suites[]`
- Métriques globales: `total_tests`, `total_passed`, `overall_success_rate`

## Ajout d'un Nouveau Service

### 1. Créer le Use Case

```python
# usecases/cfk/mon_service_usecase.py  (ou usecases/core/)
from usecases.base_usecase import BaseServiceUseCase
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter

class MonServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__(
            service_name="mon-service",
            namespace="cfk-out",
            env_config=env_config
        )
        # Adapters selon les connexions définies dans le DAL
        # self._k() est un no-op en mode direct, injecte le ctx kubectl en mode kubectl
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('cfk_mapping', {})))

    async def run_connectivity_tests(self):
        results = []
        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity",
            TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))
        return results

    async def run_functional_tests(self):
        results = []
        env = self.env_config.get('environment', 'dev')
        topic_result = await self.kafka_adapter.test_topic_access(f"{env}.mon.topic", 'READ')
        results.append(self._create_test_result(f"kafka_topic_read",
            TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result))
        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
```

### 2. Enregistrer dans le Handler

```python
# handlers/cli_handler.py
from usecases.cfk.mon_service_usecase import MonServiceUseCase

_CFK_USECASES = [
    ...,
    MonServiceUseCase,  # <-- Ajouter à la liste du domaine
]

_USECASE_MAP = {
    ...,
    'mon-service': MonServiceUseCase,  # <-- Pour --service mon-service
}
```

### 3. Ajouter la configuration

```yaml
# config/environments.yaml
environments:
  dev:
    services:
      mon-service:
        namespace: "cfk-out"
        service_name: "mon-service"
        port: 8080
```

## Intégration CI/CD

```yaml
# .gitlab-ci.yml
test:connectivity:dev:
  stage: test
  script:
    - pip install -r requirements.txt
    - python main.py run --env dev --all --report-format junit
  artifacts:
    reports:
      junit: reports/*.xml
```
