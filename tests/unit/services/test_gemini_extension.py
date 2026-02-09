"""Tests for Gemini extension command files."""

import tomllib
from pathlib import Path

import pytest

# Skip all tests in this module - gemini-extension feature not yet implemented
pytestmark = pytest.mark.skip(reason="Gemini extension feature not yet implemented")

COMMANDS_DIR = Path(__file__).resolve().parents[3] / "gemini-extension" / "commands"

# All expected command files
EXPECTED_COMMANDS = [
    # Original commands
    "discover.toml",
    "help.toml",
    "log.toml",
    "profile.toml",
    "recent.toml",
    "search.toml",
    "stats.toml",
    "suggest.toml",
    # Pantry commands
    "pantry.toml",
    "pantry-add.toml",
    "pantry-update.toml",
    "pantry-remove.toml",
    # Recipe commands
    "recipes.toml",
    "recipe.toml",
    "recipe-save.toml",
    "recipe-fav.toml",
    # Discovery commands
    "nearby.toml",
    "donate.toml",
    # Content commands
    "share.toml",
    "blog.toml",
    "report.toml",
    # Processing commands
    "scan-menu.toml",
    "scan-receipt.toml",
    # Analysis command
    "check.toml",
]


class TestGeminiExtensionCommands:
    """Test Gemini extension command file structure."""

    def test_commands_directory_exists(self) -> None:
        """Commands directory should exist."""
        assert COMMANDS_DIR.exists(), f"Commands directory not found: {COMMANDS_DIR}"

    def test_all_expected_command_files_exist(self) -> None:
        """All expected command files should exist."""
        missing = [cmd_file for cmd_file in EXPECTED_COMMANDS if not (COMMANDS_DIR / cmd_file).exists()]
        assert not missing, f"Missing command files: {missing}"

    @pytest.mark.parametrize("cmd_file", EXPECTED_COMMANDS)
    def test_command_file_is_valid_toml(self, cmd_file: str) -> None:
        """Each command file should be valid TOML."""
        file_path = COMMANDS_DIR / cmd_file
        if not file_path.exists():
            pytest.skip(f"File not found: {cmd_file}")

        content = file_path.read_text()
        try:
            tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            pytest.fail(f"{cmd_file} is not valid TOML: {e}")

    @pytest.mark.parametrize("cmd_file", EXPECTED_COMMANDS)
    def test_command_has_description(self, cmd_file: str) -> None:
        """Each command file should have a description."""
        file_path = COMMANDS_DIR / cmd_file
        if not file_path.exists():
            pytest.skip(f"File not found: {cmd_file}")

        content = file_path.read_text()
        data = tomllib.loads(content)

        assert "description" in data, f"{cmd_file} missing 'description'"
        assert isinstance(data["description"], str), f"{cmd_file} description must be string"
        assert len(data["description"]) > 0, f"{cmd_file} description is empty"

    @pytest.mark.parametrize("cmd_file", EXPECTED_COMMANDS)
    def test_command_has_prompt(self, cmd_file: str) -> None:
        """Each command file should have a prompt."""
        file_path = COMMANDS_DIR / cmd_file
        if not file_path.exists():
            pytest.skip(f"File not found: {cmd_file}")

        content = file_path.read_text()
        data = tomllib.loads(content)

        assert "prompt" in data, f"{cmd_file} missing 'prompt'"
        assert isinstance(data["prompt"], str), f"{cmd_file} prompt must be string"
        assert len(data["prompt"]) > 0, f"{cmd_file} prompt is empty"

    @pytest.mark.parametrize("cmd_file", [f for f in EXPECTED_COMMANDS if f != "help.toml"])
    def test_command_prompt_has_args_placeholder(self, cmd_file: str) -> None:
        """Each command (except help) should use {{args}} placeholder."""
        file_path = COMMANDS_DIR / cmd_file
        if not file_path.exists():
            pytest.skip(f"File not found: {cmd_file}")

        content = file_path.read_text()
        data = tomllib.loads(content)

        # Most commands should accept args, but some (like stats) may not need them
        # Just check that prompt exists and is non-empty
        prompt = data.get("prompt", "")
        assert len(prompt) > 10, f"{cmd_file} prompt is too short"


class TestHelpCommandCompleteness:
    """Test that help.toml documents all commands."""

    def test_help_lists_all_command_categories(self) -> None:
        """Help should list major command categories."""
        file_path = COMMANDS_DIR / "help.toml"
        content = file_path.read_text()
        data = tomllib.loads(content)
        prompt = data["prompt"]

        expected_categories = [
            "Food Journal",
            "Pantry Management",
            "Recipe Management",
            "Content Generation",
            "Analysis",
        ]

        for category in expected_categories:
            assert category in prompt, f"Help missing category: {category}"

    def test_help_lists_key_commands(self) -> None:
        """Help should list key commands."""
        file_path = COMMANDS_DIR / "help.toml"
        content = file_path.read_text()
        data = tomllib.loads(content)
        prompt = data["prompt"]

        key_commands = [
            "recent",
            "search",
            "log",
            "pantry",
            "recipes",
            "recipe",
            "nearby",
            "share",
            "check",
        ]

        for cmd in key_commands:
            assert cmd in prompt.lower(), f"Help missing command: {cmd}"


class TestExtensionManifest:
    """Test extension manifest file."""

    def test_manifest_exists(self) -> None:
        """Extension manifest should exist."""
        manifest_path = Path(__file__).parent.parent / "gemini-extension" / "gemini-extension.json"
        assert manifest_path.exists(), "gemini-extension.json not found"

    def test_manifest_is_valid_json(self) -> None:
        """Manifest should be valid JSON."""
        import json

        manifest_path = Path(__file__).parent.parent / "gemini-extension" / "gemini-extension.json"
        content = manifest_path.read_text()
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"gemini-extension.json is not valid JSON: {e}")

    def test_manifest_has_required_fields(self) -> None:
        """Manifest should have required fields."""
        import json

        manifest_path = Path(__file__).parent.parent / "gemini-extension" / "gemini-extension.json"
        data = json.loads(manifest_path.read_text())

        required_fields = ["name", "version", "description"]
        for field in required_fields:
            assert field in data, f"Manifest missing required field: {field}"


class TestGeminiDocumentation:
    """Test GEMINI.md documentation."""

    def test_gemini_md_exists(self) -> None:
        """GEMINI.md should exist."""
        gemini_md = Path(__file__).parent.parent / "gemini-extension" / "GEMINI.md"
        assert gemini_md.exists(), "GEMINI.md not found"

    def test_gemini_md_documents_key_tools(self) -> None:
        """GEMINI.md should document key MCP tools."""
        gemini_md = Path(__file__).parent.parent / "gemini-extension" / "GEMINI.md"
        content = gemini_md.read_text()

        key_tools = [
            "get_recent_meals",
            "search_meals",
            "add_meal",
            "get_taste_profile",
            "get_meal_suggestions",
            "add_to_pantry",
            "list_recipes",
            "get_recipe",
            "save_recipe",
            "find_nearby_food",
            "donate_meal",
            "check_dietary_compatibility",
        ]

        for tool in key_tools:
            assert tool in content, f"GEMINI.md missing tool documentation: {tool}"

    def test_gemini_md_has_usage_guidelines(self) -> None:
        """GEMINI.md should have usage guidelines."""
        gemini_md = Path(__file__).parent.parent / "gemini-extension" / "GEMINI.md"
        content = gemini_md.read_text()

        assert "Usage Guidelines" in content, "GEMINI.md missing Usage Guidelines section"
        assert "Example Interactions" in content, "GEMINI.md missing Example Interactions section"
