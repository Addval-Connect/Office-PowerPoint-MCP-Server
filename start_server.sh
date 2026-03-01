#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PYTHONPATH="$SCRIPT_DIR"
export PPT_TEMPLATE_PATH="$SCRIPT_DIR/templates"

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/ppt_mcp_server.py" \
    --transport http \
    --port 8083
