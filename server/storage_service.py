"""
Cloud Storage Service - Cloudflare R2 Integration
Handles file uploads and downloads using S3-compatible API.
"""

import os
import io
import hashlib
import secrets
from pathlib import Path
from typing import Optional, BinaryIO, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Import path security utilities
import re
PROJECT_ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "license-builds")
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

# File size limits (in bytes)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10 MB per file
MAX_ZIP_SIZE = int(os.getenv("MAX_ZIP_SIZE", str(50 * 1024 * 1024)))  # 50 MB for ZIP uploads
MAX_TOTAL_PROJECT_SIZE = int(os.getenv("MAX_TOTAL_PROJECT_SIZE", str(100 * 1024 * 1024)))  # 100 MB total per project

# File retention (in days)
BUILD_RETENTION_DAYS = int(os.getenv("BUILD_RETENTION_DAYS", "30"))  # Keep builds for 30 days
UPLOAD_RETENTION_DAYS = int(os.getenv("UPLOAD_RETENTION_DAYS", "90"))  # Keep uploads for 90 days

# Local fallback directory (used when R2 is not configured)
LOCAL_UPLOAD_DIR = Path(__file__).parent / "uploads"
LOCAL_UPLOAD_DIR.mkdir(exist_ok=True)


# =============================================================================
# Security: Path validation helper (CodeQL-recognized pattern)
# =============================================================================

def get_safe_project_dir(project_id: str) -> Path:
    """
    Get a validated project directory path.
    
    This function validates the project_id format and ensures the resulting
    path is safely within LOCAL_UPLOAD_DIR using a CodeQL-recognized pattern.
    
    Args:
        project_id: The project ID (must be 32 hex characters)
        
    Returns:
        Validated absolute Path to the project directory
        
    Raises:
        ValueError: If project_id is invalid or path escapes base directory
    """
    # Validate project_id format
    if not PROJECT_ID_PATTERN.match(project_id):
        raise ValueError("Invalid project ID format")
    
    # Construct and resolve the path
    project_dir = (LOCAL_UPLOAD_DIR / project_id).resolve()
    base_resolved = LOCAL_UPLOAD_DIR.resolve()
    
    # Security check using str().startswith() pattern that CodeQL recognizes
    if not str(project_dir).startswith(str(base_resolved) + os.sep) and project_dir != base_resolved:
        raise ValueError("Path escapes base directory")
    
    return project_dir



@dataclass
class StoredFile:
    """Represents a stored file."""
    key: str  # S3/R2 key or local path
    bucket: str
    size: int
    hash: str
    url: Optional[str] = None
    is_local: bool = False


class StorageService:
    """
    Cloud storage service with Cloudflare R2 support.
    Falls back to local storage if R2 is not configured.
    """
    
    def __init__(self):
        self.use_r2 = bool(R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_ENDPOINT)
        self.client = None
        self.bucket = R2_BUCKET_NAME
        
        if self.use_r2:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=R2_ENDPOINT,
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                    config=Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'}
                    ),
                    region_name='auto'  # R2 uses 'auto' region
                )
                # Test connection
                self.client.head_bucket(Bucket=self.bucket)
                print(f"[Storage] Connected to Cloudflare R2: {self.bucket}")
            except Exception as e:
                print(f"[Storage] R2 connection failed: {e}")
                print("[Storage] Falling back to local storage")
                self.use_r2 = False
                self.client = None
        else:
            print("[Storage] R2 not configured, using local storage")
    
    def is_cloud_enabled(self) -> bool:
        """Check if cloud storage is enabled."""
        return self.use_r2 and self.client is not None
    
    def _generate_key(self, project_id: str, filename: str, prefix: str = "uploads") -> str:
        """Generate a unique storage key for a file."""
        ext = Path(filename).suffix
        unique_id = secrets.token_hex(8)
        return f"{prefix}/{project_id}/{unique_id}{ext}"
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute SHA256 hash of file data."""
        return hashlib.sha256(data).hexdigest()
    
    async def upload_file(
        self,
        project_id: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        prefix: str = "uploads"
    ) -> StoredFile:
        """
        Upload a file to storage.
        
        Args:
            project_id: The project ID
            filename: Original filename
            data: File content as bytes
            content_type: MIME type
            prefix: Storage prefix (e.g., 'uploads', 'builds')
        
        Returns:
            StoredFile with upload details
        """
        file_hash = self._compute_hash(data)
        file_size = len(data)
        
        if self.use_r2 and self.client:
            # Upload to R2
            key = self._generate_key(project_id, filename, prefix)
            
            try:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                    Metadata={
                        'original-filename': filename,
                        'project-id': project_id,
                        'sha256': file_hash
                    }
                )
                
                # Generate URL (if public bucket) or signed URL
                url = self._get_public_url(key)
                
                return StoredFile(
                    key=key,
                    bucket=self.bucket,
                    size=file_size,
                    hash=file_hash,
                    url=url,
                    is_local=False
                )
            except ClientError as e:
                print(f"[Storage] R2 upload failed: {e}")
                # Fall through to local storage
        
        # Local storage fallback
        # Security: Use helper function with CodeQL-recognized validation
        project_dir = get_safe_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        ext = Path(filename).suffix
        unique_filename = f"{secrets.token_hex(8)}{ext}"
        file_path = project_dir / unique_filename
        
        with open(file_path, 'wb') as f:
            f.write(data)
        
        return StoredFile(
            key=str(file_path),
            bucket="local",
            size=file_size,
            hash=file_hash,
            url=None,
            is_local=True
        )
    
    async def download_file(self, key: str, is_local: bool = False) -> Optional[bytes]:
        """
        Download a file from storage.
        
        Args:
            key: Storage key or local path
            is_local: Whether the file is stored locally
        
        Returns:
            File content as bytes, or None if not found
        """
        if is_local or not self.use_r2:
            # Local file
            file_path = Path(key)
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            return None
        
        # R2 download
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
    
    async def delete_file(self, key: str, is_local: bool = False) -> bool:
        """
        Delete a file from storage.
        
        Args:
            key: Storage key or local path
            is_local: Whether the file is stored locally
        
        Returns:
            True if deleted, False if not found
        """
        if is_local or not self.use_r2:
            # Local file
            file_path = Path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        
        # R2 delete
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
    
    async def delete_project_files(self, project_id: str) -> int:
        """
        Delete all files for a project.
        
        Args:
            project_id: The project ID
        
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        if self.use_r2 and self.client:
            # List and delete from R2
            try:
                prefix = f"uploads/{project_id}/"
                response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        self.client.delete_object(Bucket=self.bucket, Key=obj['Key'])
                        deleted_count += 1
                
                # Also delete builds
                prefix = f"builds/{project_id}/"
                response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        self.client.delete_object(Bucket=self.bucket, Key=obj['Key'])
                        deleted_count += 1
                        
            except ClientError as e:
                print(f"[Storage] Error deleting project files from R2: {e}")
        
        # Also clean local storage
        # Security: Use helper function with CodeQL-recognized validation
        try:
            local_project_dir = get_safe_project_dir(project_id)
        except ValueError:
            return deleted_count  # Skip invalid project IDs
        
        if local_project_dir.exists():
            import shutil
            shutil.rmtree(local_project_dir)
            deleted_count += 1
        
        return deleted_count
    
    def _get_public_url(self, key: str) -> Optional[str]:
        """Get public URL for a file (if bucket is public)."""
        if R2_PUBLIC_URL:
            return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
        return None
    
    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        for_upload: bool = False
    ) -> Optional[str]:
        """
        Generate a presigned URL for file access or upload.
        
        Args:
            key: Storage key
            expires_in: URL expiration time in seconds (default 1 hour)
            for_upload: If True, generate upload URL; otherwise download URL
        
        Returns:
            Presigned URL or None if R2 not available
        """
        if not self.use_r2 or not self.client:
            return None
        
        try:
            method = 'put_object' if for_upload else 'get_object'
            url = self.client.generate_presigned_url(
                ClientMethod=method,
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"[Storage] Error generating presigned URL: {e}")
            return None
    
    def generate_download_url(self, key: str, filename: str, expires_in: int = 1800) -> Optional[str]:
        """
        Generate a presigned download URL with content-disposition.
        
        Args:
            key: Storage key
            filename: Suggested download filename
            expires_in: URL expiration time in seconds (default 30 min)
        
        Returns:
            Presigned URL or None if R2 not available
        """
        if not self.use_r2 or not self.client:
            return None
        
        try:
            url = self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"[Storage] Error generating download URL: {e}")
            return None
    
    async def file_exists(self, key: str, is_local: bool = False) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            key: Storage key or local path
            is_local: Whether to check local storage
        
        Returns:
            True if file exists
        """
        if is_local or not self.use_r2:
            return Path(key).exists()
        
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
    
    async def get_file_info(self, key: str, is_local: bool = False) -> Optional[dict]:
        """
        Get file metadata.
        
        Args:
            key: Storage key or local path
            is_local: Whether to check local storage
        
        Returns:
            Dict with file info or None if not found
        """
        if is_local or not self.use_r2:
            file_path = Path(key)
            if file_path.exists():
                stat = file_path.stat()
                return {
                    'key': key,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'is_local': True
                }
            return None
        
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return {
                'key': key,
                'size': response['ContentLength'],
                'modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'is_local': False
            }
        except ClientError:
            return None


# Global storage service instance
storage_service = StorageService()


# =============================================================================
# Helper Functions
# =============================================================================

async def upload_project_file(
    project_id: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream"
) -> StoredFile:
    """Upload a project source file."""
    return await storage_service.upload_file(
        project_id=project_id,
        filename=filename,
        data=content,
        content_type=content_type,
        prefix="uploads"
    )


async def upload_build_artifact(
    project_id: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream"
) -> StoredFile:
    """Upload a compiled build artifact."""
    return await storage_service.upload_file(
        project_id=project_id,
        filename=filename,
        data=content,
        content_type=content_type,
        prefix="builds"
    )


async def cleanup_old_files() -> dict:
    """
    Clean up old files that exceed retention period.
    Runs through local storage and removes files older than configured retention.
    
    Returns:
        Dict with cleanup stats
    """
    import time
    
    stats = {
        "uploads_deleted": 0,
        "builds_deleted": 0,
        "bytes_freed": 0,
        "errors": []
    }
    
    now = time.time()
    upload_cutoff = now - (UPLOAD_RETENTION_DAYS * 24 * 60 * 60)
    build_cutoff = now - (BUILD_RETENTION_DAYS * 24 * 60 * 60)
    
    # Clean local uploads
    for project_dir in LOCAL_UPLOAD_DIR.iterdir():
        if not project_dir.is_dir():
            continue
            
        # Clean source/upload files
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                try:
                    file_mtime = file_path.stat().st_mtime
                    is_build = "output" in str(file_path) or file_path.suffix == ".exe"
                    cutoff = build_cutoff if is_build else upload_cutoff
                    
                    if file_mtime < cutoff:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        stats["bytes_freed"] += file_size
                        if is_build:
                            stats["builds_deleted"] += 1
                        else:
                            stats["uploads_deleted"] += 1
                except Exception as e:
                    stats["errors"].append(f"{file_path}: {str(e)}")
        
        # Remove empty project directories
        try:
            if project_dir.exists() and not any(project_dir.iterdir()):
                project_dir.rmdir()
        except OSError:
            pass
    
    print(f"[Storage Cleanup] Deleted {stats['uploads_deleted']} uploads, "
          f"{stats['builds_deleted']} builds, freed {stats['bytes_freed'] / 1024 / 1024:.2f} MB")
    
    return stats


def validate_file_size(file_size: int, is_zip: bool = False) -> tuple[bool, str]:
    """
    Validate file size against limits.
    
    Args:
        file_size: Size of file in bytes
        is_zip: Whether this is a ZIP file upload
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    limit = MAX_ZIP_SIZE if is_zip else MAX_FILE_SIZE
    limit_mb = limit / (1024 * 1024)
    
    if file_size > limit:
        file_mb = file_size / (1024 * 1024)
        return (False, f"File size ({file_mb:.1f} MB) exceeds limit ({limit_mb:.0f} MB)")
    
    return (True, "")


async def get_download_url(key: str, filename: str, is_local: bool = False) -> Tuple[Optional[str], Optional[bytes]]:

    """
    Get download URL or file content.
    
    Returns:
        Tuple of (url, content) - one will be None depending on storage type
    """
    if is_local or not storage_service.is_cloud_enabled():
        # Return file content for local files
        content = await storage_service.download_file(key, is_local=True)
        return (None, content)
    
    # Return presigned URL for R2 files
    url = storage_service.generate_download_url(key, filename)
    return (url, None)


# Testing
if __name__ == '__main__':
    import asyncio
    
    async def test_storage():
        print(f"Cloud storage enabled: {storage_service.is_cloud_enabled()}")
        
        # Test upload
        test_data = b"Hello, this is a test file!"
        result = await storage_service.upload_file(
            project_id="test-project",
            filename="test.txt",
            data=test_data,
            content_type="text/plain"
        )
        print(f"Uploaded: {result}")
        
        # Test download
        downloaded = await storage_service.download_file(result.key, result.is_local)
        print(f"Downloaded: {downloaded}")
        
        # Test delete
        deleted = await storage_service.delete_file(result.key, result.is_local)
        print(f"Deleted: {deleted}")
    
    asyncio.run(test_storage())
