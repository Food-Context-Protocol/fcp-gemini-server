#!/usr/bin/env python3
"""Add @pytest.mark.asyncio decorators to async test functions."""

import re
from pathlib import Path

# Files that need fixing
TEST_FILES = [
    "tests/unit/services/test_fda.py",
    "tests/unit/services/test_firestore_wrapper.py",
    "tests/unit/services/test_gemini_extension.py",
    "tests/unit/services/test_services.py",
    "tests/unit/tools/test_recipe_crud.py",
    "tests/unit/tools/test_tools.py",
]

def add_async_decorators(file_path: str) -> None:
    """Add @pytest.mark.asyncio to async test functions."""
    path = Path(file_path)
    content = path.read_text()

    # Check if pytest import exists
    has_pytest_import = "import pytest" in content

    # Pattern to match async test functions without the decorator
    # Look for lines like "    async def test_" or "        async def test_"
    pattern = r'(\n( +))async def (test_[a-zA-Z0-9_]+)'

    def replacer(match):
        indent = match.group(2)
        func_name = match.group(3)
        # Check if decorator already exists on previous line
        # Get content before this match
        start_pos = match.start()
        lines_before = content[:start_pos].split('\n')
        if lines_before and '@pytest.mark.asyncio' in lines_before[-1]:
            # Decorator already exists
            return match.group(0)
        # Add decorator
        return f'\n{indent}@pytest.mark.asyncio\n{indent}async def {func_name}'

    new_content = re.sub(pattern, replacer, content)

    # Add pytest import if not present and we made changes
    if new_content != content and not has_pytest_import:
        # Add import after existing imports
        lines = new_content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        lines.insert(import_index, 'import pytest')
        new_content = '\n'.join(lines)

    # Only write if changes were made
    if new_content != content:
        path.write_text(new_content)
        print(f"✓ Fixed {file_path}")
    else:
        print(f"  No changes needed for {file_path}")

if __name__ == "__main__":
    for file_path in TEST_FILES:
        add_async_decorators(file_path)
    print("\nDone! All async test functions now have @pytest.mark.asyncio decorators.")
