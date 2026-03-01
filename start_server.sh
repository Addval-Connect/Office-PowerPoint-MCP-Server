#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PYTHONPATH="$SCRIPT_DIR"
export PPT_TEMPLATE_PATH="$SCRIPT_DIR/templates"

# AWS credentials for S3 tools (save_to_s3 / get_signed_url)
# Set these variables before running the server, e.g.:
#   export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
#   export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
#   export AWS_REGION="us-east-1"
#   export S3_BUCKET_NAME="my-presentations-bucket"

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/ppt_mcp_server.py" \
    --transport http \
    --port 8083
