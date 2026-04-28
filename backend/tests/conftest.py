"""Test configuration and fixtures for NovelTTS backend tests."""

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.config import settings


# ────────────────────────────────────────────────────────────────────────────────
# Test Database Setup
# ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Get test database URL."""
    # Use a test database; in CI, this would be set via environment
    return settings.database_url or "postgresql+asyncpg://test:test@localhost/test_novelTts"


@pytest.fixture(scope="session")
async def test_engine(test_db_url: str):
    """Create test database engine."""
    engine = create_async_engine(test_db_url, echo=False)
    # Note: In a real test environment, you'd create tables here
    # For now, we assume tables exist from migrations
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get async test database session."""
    async_session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


# ────────────────────────────────────────────────────────────────────────────────
# Mock Providers
# ────────────────────────────────────────────────────────────────────────────────


class MockLLMProvider:
    """Mock LLMProvider that returns controllable responses."""

    def __init__(self, response: dict[str, Any] | None = None):
        self.response = response or {"entries": []}
        self.call_count = 0
        self.last_prompt = None

    async def complete_json(self, prompt: str) -> dict[str, Any]:
        """Return mock JSON response."""
        self.call_count += 1
        self.last_prompt = prompt
        return self.response


class MockTTSProvider:
    """Mock TTSProvider that returns dummy audio bytes."""

    def __init__(self, audio_bytes: bytes | None = None):
        self.audio_bytes = audio_bytes or b"MOCK_AUDIO"
        self.call_count = 0
        self.last_call_args = None

    async def generate(self, text: str, voice_id: str, **kwargs) -> bytes:
        """Return mock audio bytes."""
        self.call_count += 1
        self.last_call_args = {"text": text, "voice_id": voice_id, **kwargs}
        return self.audio_bytes


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    """Provide a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def mock_llm_provider_with_response() -> MockLLMProvider:
    """Provide a mock LLM provider with sample response."""
    return MockLLMProvider(
        {
            "entries": [
                {
                    "term": "魔法",
                    "phoneme": "mɔː.fɑː",
                    "language_code": "zh",
                    "confidence": 0.95,
                },
                {
                    "term": "修仙",
                    "phoneme": "ʃoʊ̯.ɕjæn",
                    "language_code": "zh",
                    "confidence": 0.90,
                },
            ]
        }
    )


@pytest.fixture
def mock_tts_provider() -> MockTTSProvider:
    """Provide a mock TTS provider."""
    return MockTTSProvider()


# ────────────────────────────────────────────────────────────────────────────────
# FastAPI Test Client
# ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Get FastAPI test client."""
    with TestClient(app) as client:
        yield client


# ────────────────────────────────────────────────────────────────────────────────
# Markers for Test Organization
# ────────────────────────────────────────────────────────────────────────────────


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (requires pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (uses test DB)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
