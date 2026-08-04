import os
import boto3
import logging
from botocore.exceptions import ClientError
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class GarageStorageClient:
    """Garage (S3-compatible) storage client for FlowSense."""
    def __init__(self):
        self.endpoint = os.getenv("GARAGE_ENDPOINT", "http://localhost:3900")
        self.access_key = os.getenv("GARAGE_ACCESS_KEY", "")
        self.secret_key = os.getenv("GARAGE_SECRET_KEY", "")
        self.bucket_name = os.getenv("GARAGE_BUCKET", "flowsense")
        self.region = os.getenv("GARAGE_REGION", "garage")
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def ensure_bucket(self) -> bool:
        """Create bucket if not exists."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket {self.bucket_name}")
                    return True
                except ClientError as create_err:
                    logger.error(f"Failed to create bucket: {create_err}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False

    def upload_file(self, local_path: str, remote_key: str) -> bool:
        """Upload file to bucket."""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, remote_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file {local_path} to {remote_key}: {e}")
            return False

    def download_file(self, remote_key: str, local_path: str) -> bool:
        """Download from bucket."""
        try:
            self.s3_client.download_file(self.bucket_name, remote_key, local_path)
            return True
        except ClientError as e:
            logger.error(f"Failed to download {remote_key} to {local_path}: {e}")
            return False

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream") -> bool:
        """Upload raw bytes."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=remote_key,
                Body=data,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to upload bytes to {remote_key}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> List[str]:
        """List objects with prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            return []
        except ClientError as e:
            logger.error(f"Failed to list objects with prefix {prefix}: {e}")
            return []

    def delete_object(self, remote_key: str) -> bool:
        """Delete object."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {remote_key}: {e}")
            return False

    def get_presigned_url(self, remote_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": remote_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {remote_key}: {e}")
            return None

    def sync_directory(self, local_dir: str, remote_prefix: str) -> bool:
        """Sync entire directory to bucket."""
        success = True
        local_path = Path(local_dir)
        if not local_path.exists() or not local_path.is_dir():
            logger.error(f"Directory {local_dir} does not exist.")
            return False
            
        for filepath in local_path.rglob("*"):
            if filepath.is_file():
                rel_path = filepath.relative_to(local_path)
                key = f"{remote_prefix.rstrip('/')}/{rel_path.as_posix()}"
                if not self.upload_file(str(filepath), key):
                    success = False
        return success
