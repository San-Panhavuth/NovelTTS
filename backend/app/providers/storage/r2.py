from __future__ import annotations

import io

import boto3

from app.config import settings


class R2StorageProvider:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        self._bucket = settings.r2_bucket

    async def put(self, key: str, payload: bytes) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=io.BytesIO(payload),
            ContentType="audio/mpeg",
        )
        public_base = settings.r2_public_url.rstrip("/")
        if public_base:
            return f"{public_base}/{key}"
        # Fallback for private buckets without a public origin.
        return f"r2://{key}"

    async def get(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()


_instance: R2StorageProvider | None = None


def get_storage_provider() -> R2StorageProvider:
    global _instance
    if _instance is None:
        _instance = R2StorageProvider()
    return _instance
