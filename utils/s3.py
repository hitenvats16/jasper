import boto3
from core.config import settings
from uuid import uuid4
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

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

def list_s3_contents(prefix: str = "", bucket=None):
    """List contents of S3 bucket with optional prefix"""
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    bucket = bucket or settings.AWS_S3_BUCKET
    
    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix
    )
    
    if 'Contents' in response:
        return [item['Key'] for item in response['Contents']]
    return []

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
