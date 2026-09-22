"""
AWS S3 integration for archiving generated Ganesh Visarjan operational PDF reports.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def upload_report_to_s3(pdf_bytes: bytes, filename: str, content_type: str = 'application/pdf') -> str | None:
    """
    Uploads report binary bytes to AWS S3 if AWS_STORAGE_BUCKET_NAME is configured.
    Returns the S3 URI (e.g. s3://bucket/reports/...) or None if S3 is unconfigured.
    """
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    if not bucket_name:
        return None

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        client_kwargs = {
            'region_name': getattr(settings, 'AWS_S3_REGION_NAME', 'ap-south-1'),
        }
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        if access_key and secret_key:
            client_kwargs['aws_access_key_id'] = access_key
            client_kwargs['aws_secret_access_key'] = secret_key

        s3 = boto3.client('s3', **client_kwargs)
        s3_key = f"reports/{filename}"

        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType=content_type,
            Metadata={
                'source': 'hyderabad-police-visarjan-tracking'
            }
        )
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        logger.info(f"Report archived to S3: {s3_uri}")
        return s3_uri

    except Exception as e:
        logger.warning(f"Failed to upload report to S3 ({e}); continuing with direct stream.")
        return None
