# Using FCP with Claude Desktop

This guide explains how to connect the Food Context Protocol (FCP) to Claude Desktop as an MCP (Model Context Protocol) server.

---

## 🚀 Setup with uv

We recommend using `uv` for managing the FCP environment.

1.  **Install uv** (if not already installed):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone and Sync**:
    ```bash
    git clone https://github.com/Food-Context-Protocol/fcp-gemini-server.git
    cd fcp-gemini-server
    uv sync
    ```

3.  **Configure Environment**:
    Create a `.env` file in the project root:
    ```bash
    GEMINI_API_KEY=your_key_here
    ```

---

## 🖥️ Connecting to Claude Desktop

To use FCP tools inside Claude, you need to add the server configuration to your Claude Desktop config file.

### 1. Open Claude Config
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add FCP Server
Add the following entry to the `mcpServers` section. Replace `/path/to/fcp-gemini-server` with the absolute path to your cloned repository.

```json
{
  "mcpServers": {
    "fcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/fcp-gemini-server",
        "run",
        "python",
        "-m",
        "fcp.server"
      ],
      "env": {
        "GEMINI_API_KEY": "your_api_key_here",
        "FCP_TOKEN": "optional_write_token"
      }
    }
  }
}
```

### 3. Restart Claude
Restart Claude Desktop. You should see a 🔌 (plug) icon indicating that the FCP tools are available.

---

## 🛠️ Available Tools

Once connected, Claude can use all **43 FCP tools**, including:
- `add_meal`: Log food directly from chat.
- `get_taste_profile`: Analyze your eating patterns.
- `check_food_recalls`: Real-time safety checks using Google Search.
- `extract_recipe_from_media`: Turn images or URLs into structured recipes.

---

## ☁️ Remote Access (SSE)

If you prefer to connect to our hosted demo instead of running locally, you can use the SSE transport:

```json
{
  "mcpServers": {
    "fcp-remote": {
      "url": "https://mcp.fcp.dev"
    }
  }
}
```

---

Built for the **Google Gemini 3 API Developer Competition (February 2026)**.
