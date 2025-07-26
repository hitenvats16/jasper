import boto3
from core.config import settings
from uuid import uuid4
from urllib.parse import urlparse
import logging
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Cache for presigned URLs with TTL tracking
presigned_url_cache: Dict[str, Tuple[str, datetime]] = {}

def get_s3_client():
    """Get a configured S3 client"""
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def get_presigned_url(s3_key: str, bucket: Optional[str] = None, expiry: Optional[int] = None) -> str:
    """
    Generate a presigned URL for an S3 object with caching.
    
    Args:
        s3_key: The S3 key of the object
        bucket: Optional bucket name, defaults to settings.AWS_S3_BUCKET
        expiry: URL expiration time in seconds, defaults to settings.S3_PRESIGNED_URL_EXPIRY
        
    Returns:
        str: Presigned URL for the object
    """
    if not s3_key:
        return None
        
    bucket = bucket or settings.AWS_S3_BUCKET
    expiry = expiry or settings.S3_PRESIGNED_URL_EXPIRY
    cache_key = f"{bucket}:{s3_key}"
    
    # Check cache
    now = datetime.utcnow()
    if cache_key in presigned_url_cache:
        url, expiry_time = presigned_url_cache[cache_key]
        # Return cached URL if it's still valid for at least cache TTL seconds
        if expiry_time > now + timedelta(seconds=settings.S3_PRESIGNED_URL_CACHE_TTL):
            return url
    
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': s3_key
            },
            ExpiresIn=expiry
        )
        
        # Cache the URL with its expiry time
        presigned_url_cache[cache_key] = (url, now + timedelta(seconds=expiry))
        
        # Clean old cache entries
        _clean_presigned_url_cache()
        
        return url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
        return None

def _clean_presigned_url_cache():
    """Remove expired entries from the presigned URL cache"""
    now = datetime.utcnow()
    expired_keys = [
        k for k, (_, exp_time) in presigned_url_cache.items()
        if exp_time <= now
    ]
    for k in expired_keys:
        presigned_url_cache.pop(k, None)

def upload_file_to_s3(file_obj, filename, bucket=None, custom_key=None):
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    print("Uploading file to S3...")
    bucket = bucket or settings.AWS_S3_BUCKET
    
    if custom_key:
        key = custom_key
    else:
        key = f"voice_samples/{uuid4()}_{filename}"
    
    s3.upload_fileobj(
        file_obj,
        bucket,
        key
    )

    return key

def delete_file_from_s3(s3_url: str, bucket=None):
    """Delete a file from S3 using its URL"""
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    bucket = bucket or settings.AWS_S3_BUCKET
    
    # Parse the S3 URL to get the key
    parsed_url = urlparse(s3_url)
    key = parsed_url.path.lstrip('/')
    
    # Delete the object
    s3.delete_object(Bucket=bucket, Key=key) 


def load_file_from_s3(s3_key: str, buffer = None, bucket=None):
    """Load a file from S3 using its key into a buffer"""
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    bucket = bucket or settings.AWS_S3_BUCKET
    print(f"Loading file from S3: {s3_key}")
    return s3.download_fileobj(bucket, s3_key, buffer)

async def delete_s3_objects_with_prefix(prefix: str, bucket=None) -> None:
    """
    Delete all objects in S3 with a given prefix.
    
    Args:
        prefix: The S3 key prefix to match
        bucket: Optional bucket name, defaults to settings.AWS_S3_BUCKET
        
    Raises:
        Exception: If deletion fails
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    bucket = bucket or settings.AWS_S3_BUCKET
    
    try:
        # List all objects with the prefix
        objects = []
        paginator = s3.get_paginator('list_objects_v2')
        async_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        async for page in async_iterator:
            if 'Contents' in page:
                objects.extend([{'Key': obj['Key']} for obj in page['Contents']])
        
        if objects:
            # Delete objects in batches of 1000 (S3 limit)
            for i in range(0, len(objects), 1000):
                batch = objects[i:i + 1000]
                s3.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': batch}
                )
            
            logger.info(f"Successfully deleted {len(objects)} objects with prefix {prefix}")
        else:
            logger.info(f"No objects found with prefix {prefix}")
            
    except Exception as e:
        logger.error(f"Failed to delete objects with prefix {prefix}: {str(e)}")
        raise
