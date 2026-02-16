# Mapping Matrice de Flux → Tests

Ce document explique comment la matrice des flux Excel a été traduite en tests automatisés.

## Principe de Mapping

Pour chaque ligne de la matrice de flux, nous créons des tests correspondants dans le use case du service source.

### Structure de la Matrice

```
Source → Destination | Sens | Port | Sécurité | Justification
```

### Types de Tests Générés

1. **Test de Connectivité** - Peut-on joindre la destination?
2. **Test d'Authentification** - Les credentials fonctionnent-ils?
3. **Test Fonctionnel** - Peut-on effectuer l'opération métier?
4. **Test de Performance** - Quelle est la latence?

## Exemples de Mapping

### Exemple 1: pso-out-mapping → Kafka

**Matrice de flux:**
```
Source: pso-out-mapping
Destination: Kafka
Sens: Sortant
Port: 9092
Sécurité: SASL/TLS
```

**Tests générés:**

```python
class PSOOutMappingUseCase(BaseServiceUseCase):
    
    async def run_connectivity_tests(self):
        # Test 1: Connexion au broker Kafka
        kafka_result = await self.kafka_adapter.test_connectivity()
        
        # Test 2: Authentification SASL
        kafka_auth = await self.kafka_adapter.test_authentication()
    
    async def run_functional_tests(self):
        # Test 3: Accès en lecture aux topics
        topic_read = await self.kafka_adapter.test_topic_access(
            'dev.backoffice.in.request.data.json', 'READ'
        )
        
        # Test 4: Accès en écriture aux topics
        topic_write = await self.kafka_adapter.test_topic_access(
            'dev.out.processing.exceptions', 'WRITE'
        )
        
        # Test 5: Test end-to-end publish/consume
        e2e = await self.kafka_adapter.test_produce_consume(...)
```

### Exemple 2: Core API → RabbitMQ

**Matrice de flux:**
```
Source: API REST (CoreAPI)
Destination: RabbitMQ Message Broker
Sens: Sortant
Port: 5672
Sécurité: AMQP/TLS
```

**Tests générés:**

```python
class CoreAPIUseCase(BaseServiceUseCase):
    
    async def run_connectivity_tests(self):
        # Test 1: Connexion au broker RabbitMQ
        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        
        # Test 2: Authentification AMQP
        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
    
    async def run_functional_tests(self):
        # Test 3: Accès à la queue core.jobs
        queue_access = await self.rabbitmq_adapter.test_queue_access('core.jobs')
        
        # Test 4: Test publish/consume
        e2e = await self.rabbitmq_adapter.test_publish_consume('core.jobs', {})
```

### Exemple 3: Core API → PostgreSQL

**Matrice de flux:**
```
Source: API REST (CoreAPI)
Destination: PostgreSQL CoreDB
Sens: Bidirectionnel
Port: 5432
Sécurité: mTLS
Database: <NOM DU CLIENT>
User: core_db
```

**Tests générés:**

```python
class CoreAPIUseCase(BaseServiceUseCase):
    
    async def run_connectivity_tests(self):
        # Test 1: Connexion à PostgreSQL
        pg_result = await self.pg_adapter.test_connectivity()
        
        # Test 2: Authentification avec user core_db
        pg_auth = await self.pg_adapter.test_authentication()
    
    async def run_functional_tests(self):
        # Test 3: Accès aux tables métier
        for table in ['users', 'organizations', 'roles']:
            table_access = await self.pg_adapter.test_table_access(table)
        
        # Test 4: Performance d'une query type
        query_perf = await self.pg_adapter.test_query_performance(
            "SELECT COUNT(*) FROM users WHERE active = true"
        )
```

## Mapping par Type de Protocole

### Kafka (SASL/TLS, port 9092)

**Flux dans la matrice:**
- Sens: Bidirectionnel / Sortant / Entrant
- ACLs définies dans l'onglet "Kafka_ACL"

**Tests générés:**
```python
# Connectivité
- test_kafka_connectivity()
- test_kafka_authentication()

# Fonctionnel (basé sur ACLs)
- test_kafka_topic_read_{topic_name}()   # Pour chaque topic en READ
- test_kafka_topic_write_{topic_name}()  # Pour chaque topic en WRITE
- test_kafka_produce_consume_e2e()       # Test end-to-end
```

**Exemple avec ACLs:**
```
Service: pso-out-mapping
Consumer Group: *
Topic: dev.backoffice.in.request.data.json
Right: READ
```
→ Génère: `test_kafka_topic_read_dev_backoffice_in_request_data_json()`

### RabbitMQ (AMQP/TLS, port 5672)

**Flux dans la matrice:**
- VHost: / (par défaut)
- Queues définies dans l'onglet "RabbitMQ"

**Tests générés:**
```python
# Connectivité
- test_rabbitmq_connectivity()
- test_rabbitmq_authentication()

# Fonctionnel (basé sur queues)
- test_rabbitmq_queue_{queue_name}()     # Pour chaque queue
- test_rabbitmq_publish_consume_e2e()    # Test end-to-end
```

**Exemple avec Queues:**
```
VHost: /
Queue: core.jobs
Environment: DEV
```
→ Génère: `test_rabbitmq_queue_core_jobs()`

### PostgreSQL (mTLS, port 5432)

**Flux dans la matrice:**
- Onglet "External_DB"
- Database, User spécifiés

**Tests générés:**
```python
# Connectivité
- test_postgresql_{db_name}_connectivity()
- test_postgresql_{db_name}_authentication()

# Fonctionnel
- test_postgresql_table_{table_name}()   # Pour tables importantes
- test_postgresql_query_performance()     # Performance test
```

### HTTP/HTTPS (mTLS, ports 8080/8443)

**Flux dans la matrice:**
- Services REST API
- Health checks

**Tests générés:**
```python
# Connectivité
- test_http_connectivity()
- test_http_authentication()

# Fonctionnel
- test_health_check()
- test_endpoint_{endpoint_name}()
```

### SFTP (SSH, ports 22/2324)

**Flux dans la matrice:**
- File delivery services

**Tests générés:**
```python
# Connectivité
- test_sftp_connectivity()
- test_sftp_authentication()

# Fonctionnel
- test_sftp_directory_access()
- test_sftp_upload_download()
```

## Processus de Création d'un Nouveau Use Case

### Étape 1: Identifier les Flux du Service

Aller dans la matrice Excel et filtrer par "Source" = nom du service

Exemple pour `pso-out-file-delivery`:
```
pso-out-file-delivery → PostgreSQL CFK (5432, TLS)
pso-out-file-delivery → SFTP server (2324, SSH/SFTP)
pso-out-file-delivery → Kafka (9092, SASL/TLS)
```

### Étape 2: Créer le Use Case

```python
class PSOOutFileDeliveryUseCase(BaseServiceUseCase):
    def __init__(self, env_config):
        super().__init__(
            service_name="pso-out-file-delivery",
            namespace="cfk-out",
            env_config=env_config
        )
        
        # Initialiser les adapters selon les flux
        self.pg_adapter = PostgreSQLAdapter(...)
        self.sftp_adapter = SFTPAdapter(...)
        self.kafka_adapter = KafkaAdapter(...)
```

### Étape 3: Implémenter les Tests de Connectivité

Pour chaque destination unique, créer un test de connectivité:

```python
async def run_connectivity_tests(self):
    results = []
    
    # PostgreSQL
    pg_result = await self.pg_adapter.test_connectivity()
    results.append(self._create_test_result(...))
    
    # SFTP
    sftp_result = await self.sftp_adapter.test_connectivity()
    results.append(self._create_test_result(...))
    
    # Kafka
    kafka_result = await self.kafka_adapter.test_connectivity()
    results.append(self._create_test_result(...))
    
    return results
```

### Étape 4: Implémenter les Tests Fonctionnels

Basé sur la justification métier dans la matrice:

```python
async def run_functional_tests(self):
    results = []
    
    # Test SFTP upload (basé sur justification: "File delivery")
    sftp_test = await self.sftp_adapter.test_file_upload_download('/delivery')
    results.append(self._create_test_result(...))
    
    # Test Kafka topics (basé sur ACLs)
    topic_test = await self.kafka_adapter.test_topic_access(...)
    results.append(self._create_test_result(...))
    
    return results
```

### Étape 5: Enregistrer le Use Case

Dans `handlers/cli_handler.py`:

```python
def _get_available_usecases(self, env_config):
    return [
        PSOOutMappingUseCase,
        PSOOutFileDeliveryUseCase,  # <-- Ajouter ici
        # ...
    ]
```

## Checklist de Validation

Avant de considérer un use case complet, vérifier:

- [ ] Tous les flux de la matrice sont couverts
- [ ] Tests de connectivité pour chaque destination
- [ ] Tests d'authentification pour chaque protocole sécurisé
- [ ] Tests fonctionnels pour les opérations critiques
- [ ] ACLs Kafka respectées (READ/WRITE)
- [ ] Queues RabbitMQ testées
- [ ] Tables PostgreSQL importantes testées
- [ ] Cleanup après tests (delete test data)
- [ ] Gestion d'erreurs appropriée
- [ ] Logging informatif

## Correspondance Onglets Excel → Tests

| Onglet Excel | Tests Générés |
|--------------|---------------|
| Core_Services | Use cases pour services core (CoreAPI, AuthAPI, etc.) |
| CFK | Use cases pour services CFK (pso-out-*, pso-in-*, etc.) |
| Broker_Services | Tests Kafka et RabbitMQ dans chaque use case |
| RabbitMQ | Validation des queues dans tests RabbitMQ |
| Kafka_ACL | Validation des topics et droits READ/WRITE |
| External_DB | Tests PostgreSQL avec databases spécifiques |
| Third_Party_Services | Tests Keycloak, KONG, Memcached, etc. |
| File_Services | Tests SFTP et filesystem |

## Maintenance

Lorsque la matrice de flux est mise à jour:

1. **Nouveau flux ajouté**
   - Ajouter le test correspondant dans le use case
   - Vérifier que l'adapter existe (sinon le créer)

2. **Flux modifié**
   - Mettre à jour le test (port, sécurité, etc.)
   - Vérifier que le test passe toujours

3. **Flux supprimé**
   - Marquer le test comme `@skip` avec raison
   - Ne pas supprimer immédiatement (garder historique)

4. **Nouveau service**
   - Créer un nouveau use case
   - Implémenter tous les flux du service
   - Ajouter au handler

## Exemple Complet: Workflow de Création

```bash
# 1. Analyser la matrice
grep "mon-service" MatriceFlux.xlsx

# 2. Créer le use case
cp usecases/pso_out_mapping_usecase.py usecases/mon_service_usecase.py

# 3. Adapter le code
# - Remplacer nom du service
# - Ajouter/retirer adapters selon flux
# - Implémenter tests de connectivité
# - Implémenter tests fonctionnels

# 4. Tester
python main.py --env dev --service mon-service

# 5. Valider
# - Tous les tests passent
# - Rapports corrects
# - Cleanup OK

# 6. Commit
git add usecases/mon_service_usecase.py
git commit -m "Add tests for mon-service"
```
