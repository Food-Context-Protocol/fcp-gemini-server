# FCP Gemini Extension Debug Report
**Date**: 2026-02-09

## Problem Summary
The fcp-gemini-extension (located at `../fcp-gemini-extension`) cannot connect to the fcp-gemini-server because of several configuration mismatches and missing CLI functionality.

## Issues Found

### 1. Missing CLI Argument Parser
**File**: `src/fcp/server.py`
**Issue**: The server has no CLI argument parser to handle `--mcp` or `--http` flags.

**Current state**:
```python
async def main():
    """Run the FCP MCP server."""
    logger.info("MCP server starting on stdio...")
    # ... MCP server code

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Expected by Makefile**:
- `python -m fcp.server --mcp` → Run MCP server
- `python -m fcp.server --http` → Run HTTP server
- `python -m fcp.server` → Run both (?)

### 2. Wrong pyproject.toml Entry Point
**File**: `pyproject.toml:78`
**Issue**: Entry point references an async function that can't be called directly.

```toml
[project.scripts]
fcp-server = "fcp.server:main"
```

**Problem**: `main` is an async function, so running `fcp-server` fails with:
```
coroutine 'main' was never awaited
```

### 3. Extension Configuration Mismatch
**File**: `../fcp-gemini-extension/gemini-extension.json:8-15`
**Issue**: Extension tries to run `uv run fcp-server --mcp` which doesn't work.

```json
"mcpServers": {
  "fcp-server": {
    "command": "uv",
    "args": ["run", "fcp-server", "--mcp"],
    "cwd": "${FCP_SERVER_PATH}",
    "env": {
      "FCP_TOKEN": "${FCP_TOKEN}"
    }
  }
}
```

**What happens**:
1. `uv run fcp-server` attempts to call the entry point
2. Entry point tries to call async `main()` directly → fails
3. Even if fixed, `--mcp` flag is not parsed

### 4. Default Server Path in Extension
**File**: `../fcp-gemini-extension/gemini-extension.json:30`
**Issue**: Hardcoded default path that likely doesn't exist for most users.

```json
"default": "/Users/jwegis/Google/FCP/fcp-gemini-server"
```

## Root Cause Analysis

The server was likely refactored without updating:
1. The CLI entry point to be synchronous
2. Adding argument parsing for `--mcp`/`--http` modes
3. Updating the extension configuration
4. Updating documentation

## Recommended Fixes

### Fix 1: Create Proper CLI Entry Point
Create a new synchronous `main()` function that:
- Parses command-line arguments (`--mcp`, `--http`)
- Calls the appropriate server (MCP or HTTP)
- Is compatible with pyproject.toml entry points

### Fix 2: Update Extension Configuration
The extension should use:
```json
"args": ["--directory", "${FCP_SERVER_PATH}", "run", "python", "-m", "fcp.server"]
```

This matches the CLAUDE.md example and doesn't rely on the broken entry point.

### Fix 3: Remove User-Specific Default Path
Either remove the default or use a relative path that works universally.

## Impact

**Current state**: Extension completely non-functional
- Cannot start MCP server
- Cannot connect to FCP tools
- User experience: Gemini CLI shows no tools available

**After fixes**: Extension should work as designed
- MCP server starts via stdio
- Tools are discovered and available
- Gemini CLI can use all 43 FCP tools

## Testing Plan

1. **Test entry point**: `uv run fcp-server --help`
2. **Test MCP mode**: `uv run fcp-server --mcp` (should start and wait for MCP connections)
3. **Test HTTP mode**: `uv run fcp-server --http` (should start HTTP API on port 8080)
4. **Test extension**: Install extension in Gemini CLI and verify tools load
5. **Test CLAUDE.md approach**: Verify the documented uv command works

## Files to Modify

1. `src/fcp/server.py` - Add CLI argument parsing ✅
2. `pyproject.toml` - Fix entry point (or remove if not needed) ✅ (kept, now works)
3. `../fcp-gemini-extension/gemini-extension.json` - Fix command args ✅
4. `docs/` - Update any relevant documentation ✅

## Priority

**P0 - Critical**: Extension is completely broken without these fixes.

---

## Resolution (2026-02-09)

### Changes Made

#### 1. Fixed `src/fcp/server.py` (fcp-gemini-server)
- **Renamed**: `async def main()` → `async def run_mcp_server()`
- **Added**: New synchronous `main()` function with CLI argument parsing using `argparse`
- **Supports**:
  - `--mcp`: Run MCP server on stdio (default if no flag)
  - `--http`: Run HTTP API server
  - `--port PORT`: Custom port for HTTP server (default: 8080)
  - Validates that both modes can't run simultaneously
- **Entry point**: `fcp-server` command now works correctly with `pyproject.toml`

#### 2. Fixed `../fcp-gemini-extension/gemini-extension.json`
- **Changed**: Command args from `["run", "fcp-server", "--mcp"]`
- **To**: `["--directory", "${FCP_SERVER_PATH}", "run", "python", "-m", "fcp.server", "--mcp"]`
- **Removed**: `cwd` parameter (now using `--directory` flag instead)
- **Removed**: Hardcoded user-specific default path

#### 3. Updated `../fcp-gemini-extension/README.md`
- Added step-by-step installation instructions
- Documented extension settings configuration
- Clarified setup requirements

#### 4. Added Tests
- Added 4 new tests in `tests/unit/api/test_server_mcp.py::TestServerMain`
- Tests verify CLI argument parsing for `--mcp`, `--http`, `--port`, and default behavior
- All tests pass ✅

### Verification

```bash
# Test CLI help
$ uv run fcp-server --help
usage: fcp-server [-h] [--mcp] [--http] [--port PORT]

# Test MCP mode
$ uv run fcp-server --mcp
# (Starts MCP server on stdio)

# Test HTTP mode
$ uv run fcp-server --http --port 9000
# (Starts HTTP API on port 9000)

# Test tests
$ uv run pytest tests/unit/api/test_server_mcp.py::TestServerMain -v
# 4 passed ✅
```

### Extension Setup (New)

Users can now install the extension with:

```bash
# 1. Clone and setup server
git clone https://github.com/Food-Context-Protocol/fcp-gemini-server.git
cd fcp-gemini-server
uv sync
echo "GEMINI_API_KEY=your_key_here" > .env

# 2. Install extension in Gemini CLI
gemini extension install /path/to/fcp-gemini-extension

# 3. Configure settings
gemini extension settings fcp-gemini-extension
# Set FCP_SERVER_PATH to absolute path of fcp-gemini-server directory
```

### Status

✅ **RESOLVED**: Extension should now work correctly with Gemini CLI.
