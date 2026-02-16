"""
PostgreSQL adapter for database connectivity testing
"""
import time
import asyncio
import psycopg2
from typing import Dict, Any, Optional, List
import logging

from .base_adapter import BaseAdapter, ConnectionResult

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(BaseAdapter):
    """PostgreSQL database connectivity adapter"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection: Optional[psycopg2.extensions.connection] = None

        # kubectl mode: test from within the pod via kubectl exec
        self._kubectl = config.get('_kubectl')
        if self._kubectl:
            self._kube_host = self.config.get('host', 'localhost')
            self._kube_port = int(self.config.get('port', 5432))

    def _get_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        return (
            f"host={self.config.get('host')} "
            f"port={self.config.get('port', 5432)} "
            f"dbname={self.config.get('database')} "
            f"user={self.config.get('username')} "
            f"password={self.config.get('password')} "
            f"sslmode={self.config.get('ssl_mode', 'require')} "
            f"connect_timeout={self.connection_config.timeout}"
        )

    async def test_connectivity(self) -> ConnectionResult:
        """Test PostgreSQL database connectivity"""
        if self._kubectl:
            return await self._kubectl['executor'].test_tcp(
                self._kubectl['namespace'], self._kubectl['pod'],
                self._kube_host, self._kube_port
            )

        start_time = time.time()

        try:
            conn_string = self._get_connection_string()
            self.connection = psycopg2.connect(conn_string)

            cursor = self.connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()

            duration_ms = (time.time() - start_time) * 1000

            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Successfully connected to PostgreSQL database '{self.config.get('database')}'",
                metadata={
                    'host': self.config.get('host'),
                    'database': self.config.get('database'),
                    'version': version
                }
            )

        except psycopg2.OperationalError as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"PostgreSQL connection failed: {str(e)}"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"PostgreSQL connectivity test failed: {str(e)}"
            )

    async def test_authentication(self) -> ConnectionResult:
        """Test PostgreSQL authentication"""
        if self._kubectl:
            # Cannot test psql auth without client tools in pod — fall back to TCP
            result = await self.test_connectivity()
            result.metadata['note'] = 'authentication not testable in kubectl mode (no psql client in pod)'
            return result

        start_time = time.time()

        try:
            conn_string = self._get_connection_string()
            connection = psycopg2.connect(conn_string)

            cursor = connection.cursor()
            cursor.execute("SELECT current_user, current_database();")
            user, database = cursor.fetchone()
            cursor.close()
            connection.close()

            duration_ms = (time.time() - start_time) * 1000

            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message="PostgreSQL authentication successful",
                metadata={
                    'current_user': user,
                    'current_database': database
                }
            )

        except psycopg2.OperationalError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            if "authentication failed" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"PostgreSQL authentication failed: Invalid credentials"
                )
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"PostgreSQL authentication failed: {str(e)}"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"PostgreSQL authentication test failed: {str(e)}"
            )

    async def test_table_access(self, table_name: str) -> ConnectionResult:
        """Test access to a specific table"""
        if self._kubectl:
            return ConnectionResult(
                success=True,
                duration_ms=0,
                message=f"Table access test skipped in kubectl mode (no psql client in pod)",
                metadata={'mode': 'kubectl', 'table': table_name}
            )

        start_time = time.time()

        try:
            if not self.connection or self.connection.closed:
                await self.test_connectivity()

            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                );
            """, (table_name,))

            exists = cursor.fetchone()[0]

            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                cursor.close()
                duration_ms = (time.time() - start_time) * 1000
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Table '{table_name}' is accessible",
                    metadata={'table': table_name, 'row_count': count, 'exists': True}
                )
            else:
                cursor.close()
                duration_ms = (time.time() - start_time) * 1000
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Table '{table_name}' does not exist"
                )

        except psycopg2.Error as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Table access test failed for '{table_name}': {str(e)}"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Table access test failed: {str(e)}"
            )

    async def test_query_performance(self, query: str) -> ConnectionResult:
        """Test query execution performance"""
        if self._kubectl:
            return ConnectionResult(
                success=True,
                duration_ms=0,
                message=f"Query performance test skipped in kubectl mode (no psql client in pod)",
                metadata={'mode': 'kubectl', 'query': query}
            )

        start_time = time.time()

        try:
            if not self.connection or self.connection.closed:
                await self.test_connectivity()

            cursor = self.connection.cursor()
            explain_query = f"EXPLAIN ANALYZE {query}"
            cursor.execute(explain_query)
            explain_result = cursor.fetchall()
            cursor.close()

            duration_ms = (time.time() - start_time) * 1000

            execution_time = None
            for row in explain_result:
                if 'Execution Time' in str(row):
                    parts = str(row).split('Execution Time:')
                    if len(parts) > 1:
                        execution_time = float(parts[1].strip().split()[0])

            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Query executed successfully",
                metadata={
                    'query': query,
                    'execution_time_ms': execution_time,
                    'explain_plan': str(explain_result)
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Query performance test failed: {str(e)}"
            )

    async def close(self):
        """Close PostgreSQL connection"""
        try:
            if self.connection and not self.connection.closed:
                self.connection.close()
        except Exception as e:
            logger.warning(f"Error closing PostgreSQL connection: {e}")
