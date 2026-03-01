"""
S3 tools for PowerPoint MCP Server.
Handles uploading presentations to S3 and generating pre-signed download URLs.

Required environment variables (set in .env):
    S3_STORAGE_BUCKET_NAME        - Target S3 bucket name
    S3_STORAGE_ACCESS_KEY_ID      - IAM user access key
    S3_STORAGE_SECRET_ACCESS_KEY  - IAM user secret key
    S3_STORAGE_REGION             - AWS region (e.g. us-east-1)
    S3_PUBLIC_FOLDER              - S3 URI prefix for uploads (e.g. s3://bucket/public/)
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

        access_key = os.environ.get("S3_STORAGE_ACCESS_KEY_ID")
        secret_key = os.environ.get("S3_STORAGE_SECRET_ACCESS_KEY")
        region = os.environ.get("S3_STORAGE_REGION", "us-east-1")

        if not access_key or not secret_key:
            raise RuntimeError(
                "AWS credentials not set. Please define S3_STORAGE_ACCESS_KEY_ID and "
                "S3_STORAGE_SECRET_ACCESS_KEY in the .env file."
            )

        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _get_bucket() -> str:
        bucket = os.environ.get("S3_STORAGE_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("S3_STORAGE_BUCKET_NAME is not set in the .env file.")
        return bucket

    def _get_folder_prefix() -> str:
        """Extract the key prefix from S3_PUBLIC_FOLDER.

        S3_PUBLIC_FOLDER=s3://bucket-name/public/  →  prefix = "public/"
        """
        folder = os.environ.get("S3_PUBLIC_FOLDER", "")
        if not folder:
            return ""
        # Strip the s3://bucket-name/ part, keep only the path
        if folder.startswith("s3://"):
            parts = folder[5:].split("/", 1)   # ["bucket-name", "public/"]
            prefix = parts[1] if len(parts) > 1 else ""
        else:
            prefix = folder
        # Ensure trailing slash
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        return prefix

    @app.tool(
        annotations=ToolAnnotations(
            title="Save Presentation to S3",
        ),
    )
    def save_to_s3(
        filename: str,
        presentation_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict:
        """Upload a presentation to the configured S3 public folder.

        The file is stored at <S3_PUBLIC_FOLDER>/<filename> in the bucket.
        Provide either presentation_id (uploads from memory) or file_path
        (uploads an existing file from ./tmp).
        """
        try:
            s3 = _get_s3_client()
            bucket = _get_bucket()
            prefix = _get_folder_prefix()
        except RuntimeError as e:
            return {"error": str(e)}

        s3_key = f"{prefix}{filename}"

        # Determine the local file to upload
        if file_path:
            local_path = resolve_path(file_path)
        elif presentation_id or get_current_presentation_id():
            pres_id = presentation_id or get_current_presentation_id()
            if pres_id not in presentations:
                return {"error": f"Presentation '{pres_id}' not found."}
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
        filename: str,
        expiration_minutes: int = 60,
    ) -> Dict:
        """Generate a pre-signed download URL for a file in the S3 public folder.

        Looks up <S3_PUBLIC_FOLDER>/<filename> and returns a URL that expires
        after expiration_minutes (default 60).
        """
        try:
            s3 = _get_s3_client()
            bucket = _get_bucket()
            prefix = _get_folder_prefix()
        except RuntimeError as e:
            return {"error": str(e)}

        s3_key = f"{prefix}{filename}"

        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiration_minutes * 60,
            )
        except Exception as e:
            return {"error": f"Failed to generate pre-signed URL: {str(e)}"}

        return {
            "url": url,
            "bucket": bucket,
            "s3_key": s3_key,
            "expires_in_minutes": expiration_minutes,
        }
