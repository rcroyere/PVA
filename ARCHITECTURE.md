# Architecture du Framework de Tests - Pod Connectivity

## Vue d'ensemble

Ce framework de tests suit les principes de **Clean Architecture** avec une séparation stricte en 3 couches:

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1 - HANDLERS                        │
│  (Points d'entrée: CLI, API, Scheduled)                     │
│  • cli_handler.py - Orchestration CLI                       │
│  • report_handler.py - Génération de rapports               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 2 - USE CASES                       │
│  (Logique métier des tests par service)                     │
│  • pso_out_mapping_usecase.py                               │
│  • pso_out_scheduler_usecase.py                             │
│  • core_api_usecase.py                                      │
│  • ... (un use case par service)                            │
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
└─────────────────────────────────────────────────────────────┘
```

## Responsabilités des Couches

### Layer 1 - Handlers (Orchestration)

**Responsabilités:**
- Points d'entrée de l'application (CLI, API, Scheduled tasks)
- Orchestration de l'exécution des tests
- Gestion de la configuration des environnements
- Génération et export des rapports

**Fichiers:**
- `handlers/cli_handler.py` - Handler CLI principal
- `handlers/report_handler.py` - Génération de rapports (HTML, JSON, JUnit)

**Exemple d'utilisation:**
```python
# Exécution via CLI
python main.py --env dev --all --report-format html

# Exécution programmatique
handler = CLIHandler()
report = await handler.run_all_tests('dev')
```

### Layer 2 - Use Cases (Logique Métier)

**Responsabilités:**
- Définir les scénarios de tests spécifiques à chaque service
- Implémenter les tests de connectivité
- Implémenter les tests fonctionnels (end-to-end)
- Utiliser les adapters de la couche infrastructure

**Structure d'un Use Case:**
```python
class ServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        # Initialisation des adapters nécessaires
        self.kafka_adapter = KafkaAdapter(...)
        self.pg_adapter = PostgreSQLAdapter(...)
    
    async def run_connectivity_tests(self):
        # Tests de connectivité basique
        # - Peut-on joindre le service?
        # - L'authentification fonctionne-t-elle?
        pass
    
    async def run_functional_tests(self):
        # Tests fonctionnels end-to-end
        # - Les topics Kafka sont-ils accessibles?
        # - Peut-on écrire/lire des messages?
        pass
```

**Fichiers:**
- `usecases/base_usecase.py` - Classe de base abstraite
- `usecases/pso_out_mapping_usecase.py` - Tests pour pso-out-mapping
- `usecases/core_api_usecase.py` - Tests pour Core API
- etc.

### Layer 3 - Infrastructure (Adapters)

**Responsabilités:**
- Implémenter les clients de communication pour chaque protocole
- Gérer les connexions, authentification, retries
- Fournir des méthodes de test standardisées
- Abstraction des détails techniques de communication

**Interface Adapter:**
```python
class BaseAdapter(ABC):
    async def test_connectivity(self) -> ConnectionResult
    async def test_authentication(self) -> ConnectionResult
    async def close(self)
```

**Adapters disponibles:**
- `KafkaAdapter` - Kafka (SASL/TLS, topics, produce/consume)
- `RabbitMQAdapter` - RabbitMQ (AMQP/TLS, queues, publish/subscribe)
- `PostgreSQLAdapter` - PostgreSQL (mTLS, queries, tables)
- `HTTPAdapter` - HTTP/HTTPS (REST APIs, health checks)
- `SFTPAdapter` - SFTP/SSH (file operations)

## Flux de Données

```
1. CLI/Handler
   └─> Charge la configuration de l'environnement (dev/qa/pp/prod)
   └─> Sélectionne les Use Cases à exécuter
   
2. Use Case
   └─> Initialise les Adapters nécessaires
   └─> Exécute les tests de connectivité
   └─> Exécute les tests fonctionnels
   └─> Retourne un ServiceTestSuite
   
3. Adapter
   └─> Établit la connexion au service
   └─> Authentifie si nécessaire
   └─> Exécute l'opération de test
   └─> Retourne un ConnectionResult
   
4. Report Handler
   └─> Agrège tous les ServiceTestSuite
   └─> Génère le rapport dans le format demandé
   └─> Sauvegarde le rapport
```

## Modèles de Données

### TestResult
Résultat d'un test individuel
- `test_name`: Nom du test
- `service_name`: Service testé
- `category`: Type de test (connectivity, authentication, functional, performance)
- `protocol`: Protocole utilisé (kafka, rabbitmq, postgresql, http, etc.)
- `status`: Résultat (passed, failed, error, skipped)
- `duration_ms`: Durée d'exécution
- `message`: Message de succès
- `error`: Message d'erreur si échec
- `metadata`: Données additionnelles

### ServiceTestSuite
Collection de tests pour un service
- `service_name`: Nom du service
- `namespace`: Namespace Kubernetes
- `results`: Liste de TestResult
- `started_at`: Date de début
- `completed_at`: Date de fin
- Métriques: passed_count, failed_count, success_rate

### TestExecutionReport
Rapport global d'exécution
- `environment`: Environnement testé
- `execution_id`: ID unique d'exécution
- `suites`: Liste de ServiceTestSuite
- Métriques globales: total_tests, total_passed, overall_success_rate

## Ajout d'un Nouveau Service

Pour ajouter un nouveau service à tester:

### 1. Créer un nouveau Use Case

```python
# usecases/mon_service_usecase.py
from usecases.base_usecase import BaseServiceUseCase
from infrastructure import KafkaAdapter, PostgreSQLAdapter

class MonServiceUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__(
            service_name="mon-service",
            namespace="mon-namespace",
            env_config=env_config
        )
        # Initialiser les adapters selon la matrice de flux
        self.kafka_adapter = KafkaAdapter(env_config.get('kafka'))
    
    async def run_connectivity_tests(self):
        results = []
        # Implémenter les tests de connectivité
        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result(...))
        return results
    
    async def run_functional_tests(self):
        results = []
        # Implémenter les tests fonctionnels
        return results
```

### 2. Enregistrer le Use Case dans le Handler

```python
# handlers/cli_handler.py
def _get_available_usecases(self, env_config):
    return [
        PSOOutMappingUseCase,
        CoreAPIUseCase,
        MonServiceUseCase,  # <-- Ajouter ici
    ]

def _get_usecase_by_service(self, service_name, env_config):
    usecase_map = {
        'pso-out-mapping': PSOOutMappingUseCase,
        'core-api': CoreAPIUseCase,
        'mon-service': MonServiceUseCase,  # <-- Ajouter ici
    }
```

### 3. Ajouter la configuration du service

```yaml
# config/environments.yaml
environments:
  dev:
    services:
      mon-service:
        namespace: "mon-namespace"
        service_name: "mon-service"
        port: 8080
```

C'est tout! Le nouveau service sera automatiquement inclus dans les tests.

## Bonnes Pratiques

### Tests de Connectivité
- Toujours tester la connexion basique en premier
- Vérifier l'authentification séparément
- Utiliser des timeouts appropriés
- Gérer les retries pour la résilience

### Tests Fonctionnels
- Tester les scénarios réels d'utilisation
- Utiliser des données de test dédiées
- Nettoyer après les tests (delete test queues, etc.)
- Mesurer les performances (latence, throughput)

### Gestion des Erreurs
- Toujours wrapper dans try/catch
- Logger les erreurs avec contexte
- Retourner des messages d'erreur clairs
- Ne pas faire échouer toute la suite si un test échoue

### Configuration
- Utiliser des variables d'environnement pour les secrets
- Ne jamais commiter de credentials
- Documenter toutes les configurations requises
- Fournir des valeurs par défaut sensées

## Intégration CI/CD

Le framework peut être intégré dans GitLab CI:

```yaml
# .gitlab-ci.yml
test:connectivity:dev:
  stage: test
  script:
    - pip install -r requirements.txt
    - python main.py --env dev --all --report-format junit
  artifacts:
    reports:
      junit: reports/*.xml
```

## Extension Future

Le framework peut être étendu pour:
- Tests de performance (load testing)
- Tests de sécurité (penetration testing)
- Tests de conformité (security policies)
- Monitoring continu (scheduled tests)
- Alerting automatique (Slack, Email)
- Dashboard temps réel (Grafana)
