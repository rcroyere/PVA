"""
CLI Handler for orchestrating test execution
Layer 1 - Entry point for command-line test execution
"""
import asyncio
import click
import yaml
import os
import sys
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import uuid

from models import TestExecutionReport, ServiceTestSuite
from handlers.report_handler import ReportHandler

# CFK use cases
from usecases.cfk.archive_service_usecase import ArchiveServiceUseCase
from usecases.cfk.connector_builder_usecase import ConnectorBuilderUseCase
from usecases.cfk.observability_api_usecase import ObservabilityApiUseCase
from usecases.cfk.open_api_service_usecase import OpenApiServiceUseCase
from usecases.cfk.pso_data_stack_usecase import PSODataStackUseCase
from usecases.cfk.pso_in_provider_usecase import PSOInProviderUseCase
from usecases.cfk.pso_in_service_usecase import PSOInServiceUseCase
from usecases.cfk.pso_io_kms_usecase import PSOIoKmsUseCase
from usecases.cfk.pso_io_transformer_usecase import PSOIoTransformerUseCase
from usecases.cfk.pso_out_file_delivery_usecase import PSOOutFileDeliveryUseCase
from usecases.cfk.pso_out_mapping_usecase import PSOOutMappingUseCase
from usecases.cfk.pso_out_provider_usecase import PSOOutProviderUseCase
from usecases.cfk.pso_out_scheduler_usecase import PSOOutSchedulerUseCase
from usecases.cfk.pso_out_smart_connector_usecase import PSOOutSmartConnectorUseCase
from usecases.cfk.temporal_translator_usecase import TemporalTranslatorUseCase

# Core API use cases
from usecases.core.core_api_usecase import CoreAPIUseCase
from usecases.core.queue_worker_usecase import QueueWorkerUseCase
from usecases.core.scheduler_usecase import SchedulerUseCase
from usecases.core.rabbit_consumer_usecase import RabbitConsumerUseCase
from usecases.core.auth_api_usecase import AuthAPIUseCase
from usecases.core.docgen_usecase import DocgenUseCase
from usecases.core.search_engine_api_usecase import SearchEngineApiUseCase
from usecases.core.search_engine_consumer_usecase import SearchEngineConsumerUseCase
from usecases.core.backoffice_usecase import BackofficeUseCase
from usecases.core.pso_io_webhook_usecase import PSOIoWebhookUseCase
from usecases.core.ecosystem_api_usecase import EcosystemApiUseCase
from usecases.core.kms_api_usecase import KmsApiUseCase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# All registered use cases grouped by domain
_CFK_USECASES = [
    ArchiveServiceUseCase,
    ConnectorBuilderUseCase,
    ObservabilityApiUseCase,
    OpenApiServiceUseCase,
    PSODataStackUseCase,
    PSOInProviderUseCase,
    PSOInServiceUseCase,
    PSOIoKmsUseCase,
    PSOIoTransformerUseCase,
    PSOOutFileDeliveryUseCase,
    PSOOutMappingUseCase,
    PSOOutProviderUseCase,
    PSOOutSchedulerUseCase,
    PSOOutSmartConnectorUseCase,
    TemporalTranslatorUseCase,
]

_CORE_USECASES = [
    CoreAPIUseCase,
    QueueWorkerUseCase,
    SchedulerUseCase,
    RabbitConsumerUseCase,
    AuthAPIUseCase,
    DocgenUseCase,
    SearchEngineApiUseCase,
    SearchEngineConsumerUseCase,
    BackofficeUseCase,
    PSOIoWebhookUseCase,
    EcosystemApiUseCase,
    KmsApiUseCase,
]

_ALL_USECASES = _CFK_USECASES + _CORE_USECASES

_USECASE_MAP = {
    # CFK services
    'archive-service': ArchiveServiceUseCase,
    'connector-builder': ConnectorBuilderUseCase,
    'observability-api': ObservabilityApiUseCase,
    'open-api-service': OpenApiServiceUseCase,
    'pso-data-flow': PSODataStackUseCase,
    'pso-data-stack': PSODataStackUseCase,
    'pso-in-provider': PSOInProviderUseCase,
    'pso-in-service': PSOInServiceUseCase,
    'pso-io-kms': PSOIoKmsUseCase,
    'pso-io-transformer': PSOIoTransformerUseCase,
    'pso-out-file-delivery': PSOOutFileDeliveryUseCase,
    'pso-out-mapping': PSOOutMappingUseCase,
    'pso-out-provider': PSOOutProviderUseCase,
    'pso-out-scheduler': PSOOutSchedulerUseCase,
    'pso-out-smart-connector': PSOOutSmartConnectorUseCase,
    'temporal-translator': TemporalTranslatorUseCase,
    # Core API services
    'core-api': CoreAPIUseCase,
    'api-rest-coreapi': CoreAPIUseCase,
    'queue-worker': QueueWorkerUseCase,
    'scheduler': SchedulerUseCase,
    'rabbit-consumer': RabbitConsumerUseCase,
    'auth-api': AuthAPIUseCase,
    'docgen': DocgenUseCase,
    'search-engine-api': SearchEngineApiUseCase,
    'search-engine-consumer': SearchEngineConsumerUseCase,
    'backoffice': BackofficeUseCase,
    'pso-io-webhook': PSOIoWebhookUseCase,
    'ecosystem-api': EcosystemApiUseCase,
    'kms-api': KmsApiUseCase,
}


class CLIHandler:
    """CLI handler for test orchestration"""

    def __init__(self, config_path: str = 'config/environments.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.report_handler = ReportHandler()

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            sys.exit(1)

    def _load_env_variables(self):
        """Load environment variables for sensitive data"""
        from dotenv import load_dotenv
        load_dotenv()

    def _get_env_config(self, environment: str) -> dict:
        """Get configuration for specific environment"""
        if environment not in self.config.get('environments', {}):
            logger.error(f"Environment '{environment}' not found in config")
            sys.exit(1)

        env_config = self.config['environments'][environment].copy()
        env_config['environment'] = environment
        env_config['mode'] = getattr(self, '_mode', 'direct')

        # Replace environment variables
        self._replace_env_vars(env_config)

        return env_config

    def _replace_env_vars(self, config: dict):
        """Recursively replace ${VAR} with environment variables"""
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, value)
            elif isinstance(value, dict):
                self._replace_env_vars(value)

    def _get_available_usecases(self, env_config: dict) -> List:
        """Get list of all registered use case classes"""
        return _ALL_USECASES

    def _get_cfk_usecases(self) -> List:
        return _CFK_USECASES

    def _get_core_usecases(self) -> List:
        return _CORE_USECASES

    def _get_usecase_by_service(self, service_name: str, env_config: dict):
        """Get specific use case by service name"""
        usecase_class = _USECASE_MAP.get(service_name.lower())
        if usecase_class:
            return usecase_class(env_config)
        return None

    async def run_all_tests(self, environment: str) -> TestExecutionReport:
        """Run all tests for all services"""
        logger.info(f"Starting test execution for environment: {environment}")

        env_config = self._get_env_config(environment)
        execution_id = str(uuid.uuid4())

        report = TestExecutionReport(
            environment=environment,
            execution_id=execution_id,
            started_at=datetime.utcnow()
        )

        usecase_classes = self._get_available_usecases(env_config)

        for usecase_class in usecase_classes:
            try:
                usecase = usecase_class(env_config)
                suite = await usecase.run_all_tests()
                report.suites.append(suite)
            except Exception as e:
                logger.error(f"Failed to run tests for {usecase_class.__name__}: {e}")

        report.completed_at = datetime.utcnow()

        logger.info(
            f"Test execution completed: "
            f"{report.total_passed}/{report.total_tests} passed "
            f"({report.overall_success_rate:.2f}%)"
        )

        return report

    async def run_service_tests(self, environment: str, service_name: str) -> TestExecutionReport:
        """Run tests for a specific service"""
        logger.info(f"Starting tests for service '{service_name}' in environment: {environment}")

        env_config = self._get_env_config(environment)
        execution_id = str(uuid.uuid4())

        report = TestExecutionReport(
            environment=environment,
            execution_id=execution_id,
            started_at=datetime.utcnow()
        )

        usecase = self._get_usecase_by_service(service_name, env_config)

        if not usecase:
            logger.error(f"No use case found for service: {service_name}")
            logger.info(f"Available services: {', '.join(sorted(_USECASE_MAP.keys()))}")
            sys.exit(1)

        try:
            suite = await usecase.run_all_tests()
            report.suites.append(suite)
        except Exception as e:
            logger.error(f"Failed to run tests for {service_name}: {e}")

        report.completed_at = datetime.utcnow()

        logger.info(
            f"Tests completed for {service_name}: "
            f"{report.total_passed}/{report.total_tests} passed "
            f"({report.overall_success_rate:.2f}%)"
        )

        return report

    async def run_category_tests(self, environment: str, category: str) -> TestExecutionReport:
        """Run tests filtered by category (kafka, rabbitmq, database, cfk, core, etc.)"""
        logger.info(f"Starting '{category}' tests in environment: {environment}")

        env_config = self._get_env_config(environment)
        execution_id = str(uuid.uuid4())

        report = TestExecutionReport(
            environment=environment,
            execution_id=execution_id,
            started_at=datetime.utcnow()
        )

        category_lower = category.lower()
        if category_lower == 'cfk':
            usecase_classes = _CFK_USECASES
        elif category_lower == 'core':
            usecase_classes = _CORE_USECASES
        else:
            usecase_classes = _ALL_USECASES

        for usecase_class in usecase_classes:
            try:
                usecase = usecase_class(env_config)
                suite = await usecase.run_all_tests()
                report.suites.append(suite)
            except Exception as e:
                logger.error(f"Failed to run tests for {usecase_class.__name__}: {e}")

        report.completed_at = datetime.utcnow()

        logger.info(f"Category '{category}' tests completed: "
                    f"{report.total_passed}/{report.total_tests} passed")

        return report


@click.group()
def cli():
    """Pod Connectivity Test Suite - CLI"""
    pass


@cli.command()
@click.option('--env', required=True, type=click.Choice(['dev', 'qa', 'pp', 'prod']),
              help='Environment to test')
@click.option('--all', 'run_all', is_flag=True, help='Run all tests')
@click.option('--service', help='Specific service to test')
@click.option('--category', help='Test category: kafka, rabbitmq, database, http, cfk, core')
@click.option('--report-format', type=click.Choice(['html', 'json', 'junit']),
              default='html', help='Report format')
@click.option('--output-dir', default='reports', help='Output directory for reports')
@click.option('--mode', type=click.Choice(['direct', 'kubectl']), default='direct',
              help='Connection mode: direct (from workstation) or kubectl (exec inside pods)')
def run(env, run_all, service, category, report_format, output_dir, mode):
    """Run connectivity tests"""

    handler = CLIHandler()
    handler._load_env_variables()
    handler._mode = mode

    if run_all:
        report = asyncio.run(handler.run_all_tests(env))
    elif service:
        report = asyncio.run(handler.run_service_tests(env, service))
    elif category:
        report = asyncio.run(handler.run_category_tests(env, category))
    else:
        click.echo("Please specify --all, --service, or --category")
        sys.exit(1)

    output_path = handler.report_handler.generate_report(
        report=report,
        format_type=report_format,
        output_dir=output_dir
    )

    click.echo(f"\n{'='*80}")
    click.echo(f"Test Execution Summary")
    click.echo(f"{'='*80}")
    click.echo(f"Environment: {env}")
    click.echo(f"Total Tests: {report.total_tests}")
    click.echo(f"Passed: {report.total_passed}")
    click.echo(f"Failed: {report.total_failed}")
    click.echo(f"Errors: {report.total_errors}")
    click.echo(f"Success Rate: {report.overall_success_rate:.2f}%")
    click.echo(f"Duration: {report.total_duration_seconds:.2f}s")
    click.echo(f"\nReport saved to: {output_path}")
    click.echo(f"{'='*80}\n")

    if report.total_failed > 0 or report.total_errors > 0:
        sys.exit(1)


@cli.command()
@click.option('--env', required=True, type=click.Choice(['dev', 'qa', 'pp', 'prod']))
def list_services(env):
    """List available services for testing"""
    handler = CLIHandler()
    env_config = handler._get_env_config(env)

    click.echo(f"\nAvailable services in '{env}' environment:")
    click.echo("-" * 50)

    click.echo("\n[CFK - Connecteur Framework]")
    for usecase_class in _CFK_USECASES:
        usecase = usecase_class(env_config)
        click.echo(f"  - {usecase.service_name} ({usecase.namespace})")

    click.echo("\n[Core API]")
    for usecase_class in _CORE_USECASES:
        usecase = usecase_class(env_config)
        click.echo(f"  - {usecase.service_name} ({usecase.namespace})")

    click.echo()


if __name__ == '__main__':
    cli()
