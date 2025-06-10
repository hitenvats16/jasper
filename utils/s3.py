import boto3
from core.config import settings
from uuid import uuid4
from urllib.parse import urlparse

def upload_file_to_s3(file_obj, filename, content_type, bucket=None):
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    print("Uploading file to S3...")
    bucket = bucket or settings.AWS_S3_BUCKET
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
