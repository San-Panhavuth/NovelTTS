from typing import Protocol


class StorageProvider(Protocol):
    async def put(self, key: str, payload: bytes) -> str: ...

    async def get(self, key: str) -> bytes: ...
