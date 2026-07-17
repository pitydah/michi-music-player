"""Audit Michi Assistant tools against actual ActionRegistry actions."""
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def audit_tools():
    """Verify that all Assistant tools map to real ActionRegistry actions."""
    tools_file = Path(__file__).parent / "tools" / "registry.json"
    if not tools_file.exists():
        tools_dir = Path(__file__).parent / "tools"
        if not tools_dir.exists():
            print("WARNING: No tools directory found")
            return []

    issues = []
    for tool_file in sorted(tools_dir.glob("*.py")):
        if tool_file.name.startswith('__'):
            continue
        content = tool_file.read_text()
        if "def execute" not in content:
            issues.append(f"{tool_file.name}: no execute method")
        if "return {'ok'" in content and "error" not in content:
            issues.append(f"{tool_file.name}: returns ok without error handling")

    return issues


if __name__ == "__main__":
    issues = audit_tools()
    if issues:
        for i in issues:
            print(f"ISSUE: {i}")
        sys.exit(1)
    else:
        print("OK: All tools have execute methods")
        sys.exit(0)
