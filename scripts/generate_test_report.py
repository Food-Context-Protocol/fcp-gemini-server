#!/usr/bin/env python3
"""Generate markdown report from integration test logs.

Usage:
    pytest tests/integration/test_fcp_workflows.py -v -s --log-cli-level=DEBUG 2>&1 | tee /tmp/test.log
    python scripts/generate_test_report.py /tmp/test.log > test_report.md
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestResult:
    name: str
    passed: bool
    method: str = ""
    requests: list = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


@dataclass
class Request:
    method: str  # GET, POST
    url: str
    request_body: dict = field(default_factory=dict)
    response_status: str = ""
    response_body: dict = field(default_factory=dict)
    content_type: str = ""
    content_length: int = 0


def parse_log(log_path: str) -> list[TestResult]:
    """Parse pytest log output and extract test results."""
    with open(log_path) as f:
        content = f.read()

    results = []
    current_test = None

    # Split by test boundaries
    test_pattern = r'tests/integration/test_fcp_workflows\.py::(\w+)::(\w+)'

    for line in content.split('\n'):
        # New test starting
        match = re.search(test_pattern, line)
        if match:
            if current_test:
                results.append(current_test)
            test_name = f"{match.group(1)}.{match.group(2)}"
            current_test = TestResult(name=match.group(2), passed=False)

        if not current_test:
            continue

        # Check pass/fail
        if 'PASSED' in line:
            current_test.passed = True
        elif 'FAILED' in line:
            current_test.passed = False

        # Extract Gemini method
        method_match = re.search(r'\[(\w+)\] START', line)
        if method_match:
            current_test.method = method_match.group(1)

        # Extract token usage
        usage_match = re.search(
            r'Gemini API usage \[([^\]]+)\]: input=(\d+), output=(\d+), total=(\d+), cost=\$([0-9.]+)',
            line
        )
        if usage_match:
            current_test.input_tokens = int(usage_match.group(2))
            current_test.output_tokens = int(usage_match.group(3))
            current_test.cost = float(usage_match.group(5))

        # Extract HTTP requests
        http_match = re.search(r'HTTP Request: (GET|POST) ([^\s]+) "HTTP/[\d.]+ (\d+ \w+)"', line)
        if http_match:
            req = Request(
                method=http_match.group(1),
                url=http_match.group(2),
                response_status=http_match.group(3)
            )
            current_test.requests.append(req)

    if current_test:
        results.append(current_test)

    return results


def generate_markdown(results: list[TestResult]) -> str:
    """Generate markdown report from test results."""
    lines = [
        "## Integration Test Summary",
        "",
        "### Task",
        "Add debug logging to Gemini client to capture input/output during tests",
        "",
        "### Final Result",
    ]

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    lines.append(f"**{passed}/{total} tests passed**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Test Results")
    lines.append("")

    for i, result in enumerate(results, 1):
        status = "✅" if result.passed else "❌"
        lines.append(f"#### {i}. {result.name} {status}")
        lines.append("")

        if result.requests:
            for req in result.requests:
                lines.append("```")
                lines.append(f"{req.method} {req.url}")
                lines.append("")
                lines.append(f"Response: {req.response_status}")
                lines.append("```")
                lines.append("")

        if result.input_tokens:
            lines.append(f"Tokens: {result.input_tokens} in / {result.output_tokens} out")
            lines.append(f"Cost: ${result.cost:.6f}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Cost summary table
    lines.append("### API Costs")
    lines.append("")
    lines.append("| Method | Input | Output | Total | Cost |")
    lines.append("|--------|-------|--------|-------|------|")

    total_input = 0
    total_output = 0
    total_cost = 0.0

    for result in results:
        if result.input_tokens:
            total = result.input_tokens + result.output_tokens
            lines.append(
                f"| {result.method} | {result.input_tokens} | {result.output_tokens} | "
                f"{total} | ${result.cost:.6f} |"
            )
            total_input += result.input_tokens
            total_output += result.output_tokens
            total_cost += result.cost

    lines.append(
        f"| **Total** | **{total_input}** | **{total_output}** | "
        f"**{total_input + total_output}** | **${total_cost:.6f}** |"
    )

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    log_path = sys.argv[1]
    if not Path(log_path).exists():
        print(f"Error: {log_path} not found")
        sys.exit(1)

    results = parse_log(log_path)
    print(generate_markdown(results))


if __name__ == "__main__":
    main()
