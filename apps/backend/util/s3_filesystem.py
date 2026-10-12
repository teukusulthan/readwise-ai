from config.base import settings
import s3fs
import boto3
from botocore.config import Config


class S3FileSystem:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            client = {
                "key": settings.S3FS_KEY,
                "secret": settings.S3FS_SECRET,
                "endpoint_url": settings.S3FS_END_POINT,
                "anon": False
            }
            cls.instance = s3fs.S3FileSystem(**client)
        return cls.instance


class BaseBoto3:

    instance = None

    def __new__(cls, aws_access_key_id, aws_secret_access_key, endpoint_url, *args, **kwargs):
        if cls.instance is None:
            cls.instance = boto3.client("s3",
                                        aws_access_key_id=aws_access_key_id,
                                        aws_secret_access_key=aws_secret_access_key,
                                        endpoint_url=endpoint_url)
        return cls.instance


class NewBaseBoto3:
    def __init__(self, aws_access_key_id, aws_secret_access_key, endpoint_url):
        self.client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
            config=Config(s3={"addressing_style": "path"}),
        )


class Boto3:

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = boto3.client("s3",
                                        aws_access_key_id=settings.S3FS_KEY,
                                        aws_secret_access_key=settings.S3FS_SECRET,
                                        endpoint_url=settings.S3FS_END_POINT)
        return cls.instance