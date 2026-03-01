#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

export PYTHONPATH="$SCRIPT_DIR"
export PPT_TEMPLATE_PATH="$SCRIPT_DIR/templates"
export MCP_BASE_PATH="${MCP_BASE_PATH:-/ppt-mcp}"

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/ppt_mcp_server.py" \
    --transport http \
    --port 8083
