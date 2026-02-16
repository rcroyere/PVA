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
from usecases.pso_out_mapping_usecase import PSOOutMappingUseCase
from usecases.core_api_usecase import CoreAPIUseCase
from handlers.report_handler import ReportHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        """Get list of available use case classes"""
        return [
            PSOOutMappingUseCase,
            CoreAPIUseCase,
            # Add more use cases here as they are implemented
        ]
    
    def _get_usecase_by_service(self, service_name: str, env_config: dict):
        """Get specific use case by service name"""
        usecase_map = {
            'pso-out-mapping': PSOOutMappingUseCase,
            'core-api': CoreAPIUseCase,
            'api-rest-coreapi': CoreAPIUseCase,
        }
        
        usecase_class = usecase_map.get(service_name.lower())
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
        
        # Get all use cases
        usecase_classes = self._get_available_usecases(env_config)
        
        # Execute tests for each service
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
        
        # Get specific use case
        usecase = self._get_usecase_by_service(service_name, env_config)
        
        if not usecase:
            logger.error(f"No use case found for service: {service_name}")
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
        """Run tests filtered by category (kafka, rabbitmq, database, etc.)"""
        logger.info(f"Starting {category} tests in environment: {environment}")
        
        # For now, run all tests and filter in reporting
        # In production, you'd filter at execution level
        report = await self.run_all_tests(environment)
        
        # Filter results by protocol/category
        # This is a simplified version - you'd implement proper filtering
        logger.info(f"Category filtering for '{category}' would be applied here")
        
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
@click.option('--category', help='Test category (kafka, rabbitmq, database, http)')
@click.option('--report-format', type=click.Choice(['html', 'json', 'junit']),
              default='html', help='Report format')
@click.option('--output-dir', default='reports', help='Output directory for reports')
def run(env, run_all, service, category, report_format, output_dir):
    """Run connectivity tests"""
    
    handler = CLIHandler()
    handler._load_env_variables()
    
    # Execute tests based on options
    if run_all:
        report = asyncio.run(handler.run_all_tests(env))
    elif service:
        report = asyncio.run(handler.run_service_tests(env, service))
    elif category:
        report = asyncio.run(handler.run_category_tests(env, category))
    else:
        click.echo("Please specify --all, --service, or --category")
        sys.exit(1)
    
    # Generate report
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
    
    # Exit with error code if tests failed
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
    
    usecases = handler._get_available_usecases(env_config)
    for usecase_class in usecases:
        usecase = usecase_class(env_config)
        click.echo(f"  - {usecase.service_name} ({usecase.namespace})")
    
    click.echo()


if __name__ == '__main__':
    cli()
