<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

---

## Ollama MCP Integration (oll-mcp)

This project has the **`mcp_client_for_ollama`** package (oll-mcp) installed for connecting Ollama models to MCP servers.

### What is oll-mcp?

`oll-mcp` is a bridge that enables Ollama models to use MCP (Model Context Protocol) tools seamlessly. It pre-loads MCP servers at startup and integrates their tools into Ollama chat requests.

### Usage

Run Ollama with MCP server integration:

```bash
# Using a local MCP server script
ollmcp --mcp-server /path/to/weather.py --model llama3.2:3b

# Using multiple MCP servers
ollmcp --mcp-server /path/to/weather.py --mcp-server /path/to/filesystem.js

# Using MCP server URLs (SSE or Streamable HTTP)
ollmcp --mcp-server-url http://localhost:8000/sse --model qwen2.5:latest

# Using a configuration file
ollmcp --servers-json ~/.config/ollmcp/mcp-servers/config.json
```

### Configuration File Format

Create `~/.config/ollmcp/mcp-servers/config.json`:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "type": "stdio"
    },
    "duckduckgo": {
      "command": "uvx",
      "args": ["duckduckgo-mcp-server"],
      "type": "stdio"
    }
  }
}
```

### Recommended Models for MCP Tool Use

Models configured in `.continue/config.yaml` with `tool_use` capability:

- **qwen2.5-coder:7b** — Fast, reliable tool calling (primary recommendation)
- **qwen3.5:35b** — Higher quality tool execution
- **qwen3-coder:30b** — Code-focused with tool support
- **hhao/qwen2.5-coder-tools:latest** — Optimized for tool usage

---

## MCP Servers Available

### VS Code / Continue Extension (`.mcp.json`)

The `.mcp.json` file configures MCP servers for the Continue extension:

```json
{
  "mcpServers": {
    "code-review-graph": {
      "command": "uvx",
      "args": ["code-review-graph", "serve"],
      "type": "stdio"
    },
    "kite": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.kite.trade/mcp"]
    },
    "groww": {
      "command": "npx",
      "args": ["mcp-remote@0.1.18", "https://mcp.groww.in/mcp", "52155"]
    },
    "zerodha": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.zerodha.com/mcp"]
    }
  }
}
```

### Application-Level Servers (`src/mcp/mcp_config.py`)

Servers used by CustodianAIArmy agents:

| Server | Command | Tools |
|--------|---------|-------|
| **fetch** | `uvx mcp-server-fetch` | `fetch` — Fetch web content from any URL |
| **duckduckgo** | `uvx duckduckgo-mcp-server` | `duckduckgo_web_search`, `duckduckgo_news_search` |
| **filesystem** | `npx -y @modelcontextprotocol/server-filesystem` | `read_file`, `write_file`, `list_directory`, `search_files`, `create_directory` |
| **memory** | `npx -y @modelcontextprotocol/server-memory` | Knowledge graph operations |
| **sequential_thinking** | `npx -y @modelcontextprotocol/server-sequential-thinking` | `sequentialthinking` |

---

## Agent-to-Tools Mapping

Different agent specializations have access to different MCP tools:

| Agent Type | Available Tools |
|------------|-----------------|
| **coordinator** | fetch, web search, memory, sequential thinking |
| **researcher** | fetch, web search, memory, sequential thinking |
| **fact_checker** | fetch, web search |
| **technical / coder / architect** | fetch, filesystem, sequential thinking |
| **analyst** | fetch, web search, sequential thinking |
| **creative / writer** | fetch, web search |

---

## Continue Extension Configuration

To use MCP tools in Continue:

1. Ensure your `.continue/config.yaml` has models with `capabilities: [tool_use]`
2. Place `.mcp.json` in your workspace root or home directory
3. Restart Continue to load MCP servers
4. Select a tool-use capable model (e.g., qwen2.5-coder-7b) for Agent/Plan mode

### Continue Model Configuration Example

```yaml
models:
  - name: qwen2.5-coder-7b
    provider: ollama
    model: qwen2.5-coder:7b
    capabilities:
      - tool_use
    roles:
      - chat
      - edit
      - apply
```

---

## Best Practices

1. **Use tool-use capable models** for Agent/Plan mode in Continue
2. **Pre-configure MCP servers** in `.mcp.json` for consistent access
3. **Use `oll-mcp`** when running Ollama outside of Continue for standalone tool usage
4. **Prefer `duckduckgo`** for web search (free, no API key required)
5. **Enable memory server** for persistent context across sessions
