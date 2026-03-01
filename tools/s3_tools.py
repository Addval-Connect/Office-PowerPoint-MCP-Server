"""
S3 tools for PowerPoint MCP Server.
Handles uploading presentations to S3 and generating pre-signed download URLs.

Required environment variables:
    AWS_ACCESS_KEY_ID     - IAM user access key
    AWS_SECRET_ACCESS_KEY - IAM user secret key
    AWS_REGION            - AWS region (e.g. us-east-1)
    S3_BUCKET_NAME        - Target S3 bucket name
"""
import os
from typing import Dict, Optional
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


def register_s3_tools(app: FastMCP, presentations: Dict, get_current_presentation_id, resolve_path):
    """Register S3 tools with the FastMCP app."""

    def _get_s3_client():
        """Build a boto3 S3 client from environment variables."""
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 is not installed. Run: pip install boto3")

        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("AWS_REGION", "us-east-1")

        if not access_key or not secret_key:
            raise RuntimeError(
                "AWS credentials not set. Please define AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables."
            )

        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _get_bucket() -> str:
        bucket = os.environ.get("S3_BUCKET_NAME")
        if not bucket:
            raise RuntimeError(
                "S3_BUCKET_NAME environment variable is not set."
            )
        return bucket

    @app.tool(
        annotations=ToolAnnotations(
            title="Save Presentation to S3",
        ),
    )
    def save_to_s3(
        s3_key: str,
        presentation_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict:
        """Upload a presentation to S3.

        Either uploads the in-memory presentation (by presentation_id) or an
        already-saved local file (by file_path).  The file is stored in S3
        under the given s3_key (e.g. "reports/monthly.pptx").
        """
        try:
            s3 = _get_s3_client()
            bucket = _get_bucket()
        except RuntimeError as e:
            return {"error": str(e)}

        # Determine the local file to upload
        if file_path:
            local_path = resolve_path(file_path)
        elif presentation_id or get_current_presentation_id():
            # Save the in-memory presentation to a temp file inside ./tmp first
            pres_id = presentation_id or get_current_presentation_id()
            if pres_id not in presentations:
                return {"error": f"Presentation '{pres_id}' not found."}

            filename = os.path.basename(s3_key) or f"{pres_id}.pptx"
            local_path = resolve_path(filename)
            try:
                presentations[pres_id].save(local_path)
            except Exception as e:
                return {"error": f"Failed to save presentation locally: {str(e)}"}
        else:
            return {"error": "Provide either presentation_id or file_path."}

        if not os.path.exists(local_path):
            return {"error": f"Local file not found: {local_path}"}

        try:
            s3.upload_file(local_path, bucket, s3_key)
        except Exception as e:
            return {"error": f"S3 upload failed: {str(e)}"}

        return {
            "message": f"Uploaded to s3://{bucket}/{s3_key}",
            "bucket": bucket,
            "s3_key": s3_key,
            "local_path": local_path,
        }

    @app.tool(
        annotations=ToolAnnotations(
            title="Get S3 Pre-Signed URL",
            readOnlyHint=True,
        ),
    )
    def get_signed_url(
        s3_key: str,
        expiration_minutes: int = 60,
    ) -> Dict:
        """Generate a pre-signed download URL for a file stored in S3.

        The URL expires after expiration_minutes (default 60).
        """
        try:
            s3 = _get_s3_client()
            bucket = _get_bucket()
        except RuntimeError as e:
            return {"error": str(e)}

        expiration_seconds = expiration_minutes * 60

        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiration_seconds,
            )
        except Exception as e:
            return {"error": f"Failed to generate pre-signed URL: {str(e)}"}

        return {
            "url": url,
            "bucket": bucket,
            "s3_key": s3_key,
            "expires_in_minutes": expiration_minutes,
        }
