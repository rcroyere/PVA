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
        start_time = time.time()
        
        try:
            conn_string = self._get_connection_string()
            
            # Establish connection
            self.connection = psycopg2.connect(conn_string)
            
            # Test with a simple query
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
        start_time = time.time()
        
        try:
            conn_string = self._get_connection_string()
            
            # Try to connect with credentials
            connection = psycopg2.connect(conn_string)
            
            # Verify we can execute queries
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
        start_time = time.time()
        
        try:
            if not self.connection or self.connection.closed:
                await self.test_connectivity()
            
            cursor = self.connection.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table_name,))
            
            exists = cursor.fetchone()[0]
            
            if exists:
                # Try to select from table
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                
                cursor.close()
                
                duration_ms = (time.time() - start_time) * 1000
                
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Table '{table_name}' is accessible",
                    metadata={
                        'table': table_name,
                        'row_count': count,
                        'exists': True
                    }
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
        start_time = time.time()
        
        try:
            if not self.connection or self.connection.closed:
                await self.test_connectivity()
            
            cursor = self.connection.cursor()
            
            # Execute query with EXPLAIN ANALYZE
            explain_query = f"EXPLAIN ANALYZE {query}"
            cursor.execute(explain_query)
            explain_result = cursor.fetchall()
            
            cursor.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract execution time from EXPLAIN ANALYZE
            execution_time = None
            for row in explain_result:
                if 'Execution Time' in str(row):
                    # Parse execution time
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
