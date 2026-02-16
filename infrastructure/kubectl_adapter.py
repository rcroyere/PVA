"""
Kubectl Adapter - executes commands inside Kubernetes pods via kubectl exec
Layer 3 - Infrastructure

Used when --mode kubectl is specified to test connectivity from within pods,
reflecting the real cluster network paths (NetworkPolicies, DNS, mTLS).
"""
import asyncio
import subprocess
import time
import logging
from typing import Optional

from models import ConnectionResult

logger = logging.getLogger(__name__)


class KubectlAdapter:
    """
    Runs shell commands inside pods via kubectl exec.
    Tests TCP connectivity using bash /dev/tcp (no extra tools required).
    Tests HTTP via curl (when available in the pod).
    """

    def find_pod(self, namespace: str, app_label: str) -> str:
        """
        Find the name of a running pod by app label.

        Args:
            namespace: Kubernetes namespace
            app_label: Value of the 'app' label (e.g. 'pso-out-mapping')

        Returns:
            Pod name (e.g. 'pso-out-mapping-7d4f9b-xkj2p')

        Raises:
            RuntimeError: If no running pod is found
        """
        cmd = [
            'kubectl', 'get', 'pods',
            '-n', namespace,
            '-l', f'app={app_label}',
            '--field-selector=status.phase=Running',
            '-o', 'name',
            '--no-headers',
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            pods = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
            if not pods:
                raise RuntimeError(
                    f"No running pod found for app={app_label} in namespace {namespace}"
                )
            pod_name = pods[0].replace('pod/', '')
            logger.info(f"Found pod '{pod_name}' for app={app_label} in {namespace}")
            return pod_name
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"kubectl timed out looking for app={app_label} in {namespace}")
        except FileNotFoundError:
            raise RuntimeError("kubectl is not installed or not in PATH")

    def exec_command(self, namespace: str, pod: str, command: list) -> tuple:
        """
        Execute a command inside a pod.

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = ['kubectl', 'exec', '-n', namespace, pod, '--'] + command
        logger.debug(f"kubectl exec: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, '', 'Command timed out after 30s'
        except FileNotFoundError:
            return 1, '', 'kubectl not found'

    async def test_tcp(
        self, namespace: str, pod: str, host: str, port: int
    ) -> ConnectionResult:
        """
        Test TCP connectivity from within the pod using bash /dev/tcp.
        Works on any pod that has bash, without needing nc/telnet/nmap.

        Command: bash -c "timeout 5 bash -c 'echo >/dev/tcp/<host>/<port>' && echo ok || echo fail"
        """
        start = time.time()
        try:
            rc, stdout, stderr = await asyncio.to_thread(
                self.exec_command,
                namespace, pod,
                [
                    'bash', '-c',
                    f'timeout 5 bash -c "echo >/dev/tcp/{host}/{port}" '
                    f'&& echo "ok" || echo "fail"'
                ]
            )
            duration_ms = (time.time() - start) * 1000
            success = rc == 0 and 'ok' in stdout

            return ConnectionResult(
                success=success,
                duration_ms=duration_ms,
                message=(
                    f"TCP {host}:{port} reachable from pod {pod}"
                    if success
                    else f"TCP {host}:{port} unreachable from pod {pod}"
                ),
                error=stderr.strip() if not success else None,
                metadata={
                    'host': host,
                    'port': port,
                    'pod': pod,
                    'namespace': namespace,
                    'mode': 'kubectl',
                }
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
                metadata={'host': host, 'port': port, 'mode': 'kubectl'}
            )

    async def test_http(
        self, namespace: str, pod: str, url: str
    ) -> ConnectionResult:
        """
        Test an HTTP/HTTPS endpoint from within the pod using curl.
        Falls back to TCP port check if curl is not available.

        Command: curl -sf --max-time 10 -o /dev/null -w '%{http_code}' <url>
        """
        start = time.time()
        try:
            rc, stdout, stderr = await asyncio.to_thread(
                self.exec_command,
                namespace, pod,
                [
                    'curl', '-sf', '--max-time', '10',
                    '-o', '/dev/null',
                    '-w', '%{http_code}',
                    url
                ]
            )
            duration_ms = (time.time() - start) * 1000

            # curl exit code 127 = command not found
            if rc == 127:
                return await self._test_http_fallback_tcp(namespace, pod, url, duration_ms)

            status_code = stdout.strip()
            success = rc == 0 and status_code.startswith('2')

            return ConnectionResult(
                success=success,
                duration_ms=duration_ms,
                message=f"HTTP {url} → {status_code} from pod {pod}",
                error=stderr.strip() if not success else None,
                metadata={
                    'url': url,
                    'status_code': status_code,
                    'pod': pod,
                    'namespace': namespace,
                    'mode': 'kubectl',
                }
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
                metadata={'url': url, 'mode': 'kubectl'}
            )

    async def _test_http_fallback_tcp(
        self, namespace: str, pod: str, url: str, elapsed_ms: float
    ) -> ConnectionResult:
        """Fallback to TCP check when curl is not available in the pod."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname or ''
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            result = await self.test_tcp(namespace, pod, host, port)
            result.metadata['fallback'] = 'tcp (curl not available)'
            result.metadata['url'] = url
            if result.message:
                result.message = f"HTTP fallback to TCP: {result.message}"
            return result
        except Exception as e:
            return ConnectionResult(
                success=False,
                duration_ms=elapsed_ms,
                error=f"curl not available and TCP fallback failed: {e}",
                metadata={'url': url, 'mode': 'kubectl'}
            )
