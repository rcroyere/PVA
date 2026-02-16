"""
Report Handler for generating test execution reports
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

from models import TestExecutionReport

logger = logging.getLogger(__name__)


class ReportHandler:
    """Handler for generating test reports in multiple formats"""
    
    def generate_report(
        self, 
        report: TestExecutionReport, 
        format_type: str = 'html',
        output_dir: str = 'reports'
    ) -> str:
        """Generate report in specified format"""
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_report_{report.environment}_{timestamp}.{format_type}"
        file_path = output_path / filename
        
        # Generate report based on format
        if format_type == 'html':
            self._generate_html_report(report, file_path)
        elif format_type == 'json':
            self._generate_json_report(report, file_path)
        elif format_type == 'junit':
            self._generate_junit_report(report, file_path)
        else:
            raise ValueError(f"Unsupported report format: {format_type}")
        
        logger.info(f"Report generated: {file_path}")
        return str(file_path)
    
    def _generate_json_report(self, report: TestExecutionReport, file_path: Path):
        """Generate JSON report"""
        with open(file_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
    
    def _generate_html_report(self, report: TestExecutionReport, file_path: Path):
        """Generate HTML report"""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Pod Connectivity Test Report - {environment}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card.success {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .summary-card.failed {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .summary-card.error {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
            margin: 0;
        }}
        .service-suite {{
            margin: 30px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .suite-header {{
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .suite-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }}
        .suite-stats {{
            display: flex;
            gap: 15px;
            font-size: 14px;
        }}
        .stat-badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 500;
        }}
        .stat-badge.passed {{ background-color: #d4edda; color: #155724; }}
        .stat-badge.failed {{ background-color: #f8d7da; color: #721c24; }}
        .stat-badge.error {{ background-color: #f8d7da; color: #721c24; }}
        .test-results {{
            padding: 0;
        }}
        .test-result {{
            padding: 12px 20px;
            border-bottom: 1px solid #f0f0f0;
            display: grid;
            grid-template-columns: 30px 1fr 150px 100px 100px;
            gap: 15px;
            align-items: center;
        }}
        .test-result:last-child {{
            border-bottom: none;
        }}
        .test-result:hover {{
            background-color: #f8f9fa;
        }}
        .status-icon {{
            font-size: 20px;
        }}
        .status-icon.passed {{ color: #28a745; }}
        .status-icon.failed {{ color: #dc3545; }}
        .status-icon.error {{ color: #dc3545; }}
        .test-name {{
            font-weight: 500;
            color: #333;
        }}
        .test-category {{
            color: #666;
            font-size: 13px;
        }}
        .test-duration {{
            color: #666;
            font-size: 13px;
            text-align: right;
        }}
        .error-message {{
            grid-column: 2 / -1;
            background-color: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            color: #856404;
            font-size: 13px;
            margin-top: 5px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pod Connectivity Test Report</h1>
        <p><strong>Environment:</strong> {environment} | <strong>Execution ID:</strong> {execution_id}</p>
        <p><strong>Started:</strong> {started_at} | <strong>Completed:</strong> {completed_at} | <strong>Duration:</strong> {duration}s</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <p class="value">{total_tests}</p>
            </div>
            <div class="summary-card success">
                <h3>Passed</h3>
                <p class="value">{total_passed}</p>
            </div>
            <div class="summary-card failed">
                <h3>Failed</h3>
                <p class="value">{total_failed}</p>
            </div>
            <div class="summary-card error">
                <h3>Errors</h3>
                <p class="value">{total_errors}</p>
            </div>
            <div class="summary-card">
                <h3>Success Rate</h3>
                <p class="value">{success_rate}%</p>
            </div>
        </div>
        
        <h2>Test Results by Service</h2>
        {service_suites}
        
        <div class="footer">
            <p>Generated by Pod Connectivity Test Suite | PeopleSpheres DevOps</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Generate service suites HTML
        suites_html = []
        for suite in report.suites:
            results_html = []
            for result in suite.results:
                status_icon = '✓' if result.status.value == 'passed' else '✗'
                
                error_html = ''
                if result.error:
                    error_html = f'<div class="error-message">{result.error}</div>'
                
                result_html = f"""
                <div class="test-result">
                    <span class="status-icon {result.status.value}">{status_icon}</span>
                    <div>
                        <div class="test-name">{result.test_name}</div>
                        <div class="test-category">{result.category.value} - {result.protocol.value}</div>
                    </div>
                    <div class="test-category">{result.timestamp.strftime('%H:%M:%S')}</div>
                    <div class="test-duration">{result.duration_ms:.2f}ms</div>
                    <div class="test-category">{result.status.value}</div>
                    {error_html}
                </div>
                """
                results_html.append(result_html)
            
            suite_html = f"""
            <div class="service-suite">
                <div class="suite-header">
                    <div class="suite-title">{suite.service_name} ({suite.namespace})</div>
                    <div class="suite-stats">
                        <span class="stat-badge passed">{suite.passed_count} passed</span>
                        <span class="stat-badge failed">{suite.failed_count} failed</span>
                        <span class="stat-badge error">{suite.error_count} errors</span>
                    </div>
                </div>
                <div class="test-results">
                    {''.join(results_html)}
                </div>
            </div>
            """
            suites_html.append(suite_html)
        
        # Format report
        html_content = html_template.format(
            environment=report.environment.upper(),
            execution_id=report.execution_id,
            started_at=report.started_at.strftime('%Y-%m-%d %H:%M:%S') if report.started_at else 'N/A',
            completed_at=report.completed_at.strftime('%Y-%m-%d %H:%M:%S') if report.completed_at else 'N/A',
            duration=f"{report.total_duration_seconds:.2f}",
            total_tests=report.total_tests,
            total_passed=report.total_passed,
            total_failed=report.total_failed,
            total_errors=report.total_errors,
            success_rate=f"{report.overall_success_rate:.2f}",
            service_suites=''.join(suites_html)
        )
        
        with open(file_path, 'w') as f:
            f.write(html_content)
    
    def _generate_junit_report(self, report: TestExecutionReport, file_path: Path):
        """Generate JUnit XML report"""
        
        junit_template = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Pod Connectivity Tests" tests="{total_tests}" failures="{total_failed}" errors="{total_errors}" time="{duration}">
{test_suites}
</testsuites>
"""
        
        suites_xml = []
        for suite in report.suites:
            tests_xml = []
            for result in suite.results:
                test_xml = f'    <testcase name="{result.test_name}" classname="{suite.service_name}" time="{result.duration_ms / 1000:.3f}">'
                
                if result.status.value == 'failed':
                    test_xml += f'\n      <failure message="{result.error or "Test failed"}"/>'
                elif result.status.value == 'error':
                    test_xml += f'\n      <error message="{result.error or "Test error"}"/>'
                
                test_xml += '\n    </testcase>'
                tests_xml.append(test_xml)
            
            suite_xml = f'  <testsuite name="{suite.service_name}" tests="{suite.total_count}" failures="{suite.failed_count}" errors="{suite.error_count}" time="{suite.duration_seconds:.3f}">\n'
            suite_xml += '\n'.join(tests_xml)
            suite_xml += '\n  </testsuite>'
            
            suites_xml.append(suite_xml)
        
        junit_content = junit_template.format(
            total_tests=report.total_tests,
            total_failed=report.total_failed,
            total_errors=report.total_errors,
            duration=f"{report.total_duration_seconds:.3f}",
            test_suites='\n'.join(suites_xml)
        )
        
        with open(file_path, 'w') as f:
            f.write(junit_content)
