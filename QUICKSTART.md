# Guide de Démarrage Rapide

## Installation

### 1. Cloner le repository

```bash
git clone <repository-url>
cd pod-connectivity-tests
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
.\venv\Scripts\activate  # Sur Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

ou avec Make:

```bash
make install
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos credentials
```

## Utilisation Basique

### Lister les services disponibles

```bash
python main.py list-services --env dev
```

### Exécuter tous les tests en DEV

```bash
python main.py --env dev --all --report-format html
```

ou avec Make:

```bash
make run-dev
```

### Exécuter les tests pour un service spécifique

```bash
python main.py --env dev --service pso-out-mapping --report-format html
```

ou avec Make:

```bash
make run-service ENV=dev SERVICE=pso-out-mapping
```

### Exécuter les tests par catégorie

```bash
# Tests Kafka uniquement
python main.py --env dev --category kafka

# Tests RabbitMQ uniquement
python main.py --env dev --category rabbitmq

# Tests Database uniquement
python main.py --env dev --category database
```

### Générer différents formats de rapports

```bash
# Rapport HTML (par défaut)
python main.py --env dev --all --report-format html

# Rapport JSON
python main.py --env dev --all --report-format json

# Rapport JUnit (pour CI/CD)
python main.py --env dev --all --report-format junit
```

## Utilisation avec Docker

### Build de l'image

```bash
docker build -t pod-connectivity-tests:latest .
```

ou avec Make:

```bash
make docker-build
```

### Exécution avec Docker

```bash
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  --env-file .env \
  pod-connectivity-tests:latest \
  --env dev --all --report-format html
```

### Utilisation de Docker Compose

```bash
# Exécuter les tests
docker-compose up

# Modifier les arguments dans docker-compose.yml au besoin
```

## Structure des Rapports

Les rapports sont générés dans le répertoire `reports/` avec le format:

```
reports/
├── test_report_dev_20240216_143022.html
├── test_report_dev_20240216_143022.json
└── test_report_dev_20240216_143022.xml
```

### Rapport HTML

Ouvrez le fichier HTML dans votre navigateur pour une vue interactive avec:
- Résumé global (total tests, passed, failed, success rate)
- Détails par service
- Durée d'exécution
- Messages d'erreur détaillés

### Rapport JSON

Format structuré pour intégration avec d'autres outils:

```json
{
  "environment": "dev",
  "execution_id": "uuid",
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

## Exemples d'Utilisation

### Tester la connectivité avant un déploiement

```bash
# Vérifier que tous les services sont accessibles
python main.py --env qa --all

# Si tous les tests passent (exit code 0), le déploiement peut continuer
if [ $? -eq 0 ]; then
  echo "✅ Tous les services sont accessibles"
  # Continuer le déploiement
else
  echo "❌ Certains services ne sont pas accessibles"
  exit 1
fi
```

### Monitoring régulier

Configurer un cron job pour exécuter les tests régulièrement:

```bash
# Crontab: Tous les jours à 6h du matin
0 6 * * * cd /path/to/pod-connectivity-tests && ./venv/bin/python main.py --env prod --all --report-format html
```

### Tests de non-régression

Après une mise à jour d'infrastructure:

```bash
# Tester tous les environnements
for env in dev qa pp; do
  echo "Testing $env..."
  python main.py --env $env --all --report-format html
done
```

## Commandes Make Disponibles

```bash
make help              # Affiche toutes les commandes disponibles
make install           # Installe les dépendances
make test             # Exécute les tests unitaires
make clean            # Nettoie les fichiers temporaires
make run-dev          # Exécute tous les tests en DEV
make run-qa           # Exécute tous les tests en QA
make run-service      # Exécute les tests pour un service (ENV=dev SERVICE=xxx)
make run-kafka        # Tests Kafka uniquement
make run-rabbitmq     # Tests RabbitMQ uniquement
make run-database     # Tests Database uniquement
make list-services    # Liste les services disponibles
make setup-env        # Crée .env depuis .env.example
make lint             # Vérifie le code
make format           # Formate le code
make docker-build     # Build l'image Docker
make docker-run-dev   # Exécute dans Docker
```

## Résolution de Problèmes

### Erreur de connexion Kafka

```
Error: NoBrokersAvailable
```

**Solution:**
- Vérifier que le bootstrap server est correct dans `config/environments.yaml`
- Vérifier les credentials dans `.env`
- Vérifier la connectivité réseau: `telnet kafka-host 9092`

### Erreur d'authentification PostgreSQL

```
Error: authentication failed
```

**Solution:**
- Vérifier les credentials dans `.env`
- Vérifier que l'utilisateur a les permissions nécessaires
- Vérifier le SSL mode (require, prefer, disable)

### Timeout sur les tests

```
Error: Connection timeout after 30s
```

**Solution:**
- Augmenter le timeout dans `config/environments.yaml`:
  ```yaml
  test_settings:
    timeout: 60  # Augmenter à 60 secondes
  ```

### Import errors

```
ModuleNotFoundError: No module named 'kafka'
```

**Solution:**
```bash
pip install -r requirements.txt
```

## Prochaines Étapes

1. **Ajouter vos services** - Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour ajouter de nouveaux services
2. **Configurer CI/CD** - Intégrer dans votre pipeline GitLab
3. **Monitoring** - Mettre en place des alertes sur échec
4. **Dashboard** - Créer un dashboard Grafana pour visualiser les tendances

## Support

Pour toute question ou problème:
1. Consulter [ARCHITECTURE.md](ARCHITECTURE.md) pour les détails techniques
2. Consulter les logs dans `logs/`
3. Ouvrir une issue sur GitLab
