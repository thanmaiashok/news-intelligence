import json
import logging
from datetime import datetime
from typing import Dict, Optional

import aioboto3
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    def __init__(self):
        self._session = aioboto3.Session()

    def _key(self, article: Dict) -> str:
        published_at = article.get("published_at", datetime.utcnow().isoformat())
        if isinstance(published_at, str):
            dt_str = published_at[:10]  # YYYY-MM-DD
        else:
            dt_str = published_at.strftime("%Y-%m-%d")

        source = article.get("source", "unknown").replace("/", "_")
        h = article.get("content_hash", "nohash")[:16]
        return f"raw/{dt_str}/{source}/{h}.json"

    async def store_article(self, article: Dict):
        key = self._key(article)

        # Exclude embedding from raw S3 (large; stored in vector DB)
        payload = {k: v for k, v in article.items() if k != "embedding"}

        kwargs = dict(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=json.dumps(payload, default=str),
            ContentType="application/json",
        )

        extra = {}
        if settings.S3_ENDPOINT_URL:
            extra["endpoint_url"] = settings.S3_ENDPOINT_URL

        async with self._session.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            **extra,
        ) as s3:
            try:
                await s3.put_object(**kwargs)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchBucket":
                    await s3.create_bucket(Bucket=settings.S3_BUCKET)
                    await s3.put_object(**kwargs)
                else:
                    raise

    async def get_article(self, content_hash: str, date: str, source: str) -> Optional[Dict]:
        key = f"raw/{date}/{source.replace('/', '_')}/{content_hash[:16]}.json"
        extra = {}
        if settings.S3_ENDPOINT_URL:
            extra["endpoint_url"] = settings.S3_ENDPOINT_URL

        async with self._session.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            **extra,
        ) as s3:
            try:
                resp = await s3.get_object(Bucket=settings.S3_BUCKET, Key=key)
                body = await resp["Body"].read()
                return json.loads(body)
            except ClientError:
                return None
