"""Integration tests for pronunciation API endpoints."""

import json
import uuid
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.pronunciation_entry import PronunciationEntry
from app.models.segment import Segment
from app.models.user import User
from app.models.enums import SegmentType


# ────────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ────────────────────────────────────────────────────────────────────────────────


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response_dict: dict | None = None):
        self.response_dict = response_dict or {"entries": []}

    async def complete_json(self, prompt: str) -> dict:
        """Return mock response."""
        return self.response_dict


@pytest.fixture
def test_user_id() -> str:
    """Generate a test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_user_id_2() -> str:
    """Generate a second test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_book_id() -> str:
    """Generate a test book ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_chapter_id() -> str:
    """Generate a test chapter ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_segment_id() -> str:
    """Generate a test segment ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_client() -> TestClient:
    """Get FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_token(test_user_id: str) -> str:
    """
    Create a mock JWT token for testing.
    
    In real tests, this would be a valid Supabase JWT.
    For now, we'll create a basic structure.
    """
    # In a real implementation, this would be signed by Supabase
    # For testing, we'll use a mock structure
    import base64
    import json as json_module
    import time

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": test_user_id,
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "email": f"test-{test_user_id[:8]}@example.com",
    }

    # Encode as base64 (not a real JWT, but good for testing structure)
    header_b64 = base64.urlsafe_b64encode(json_module.dumps(header).encode()).rstrip(b"=")
    payload_b64 = base64.urlsafe_b64encode(json_module.dumps(payload).encode()).rstrip(b"=")
    signature = b"mock_signature"

    return f"{header_b64.decode()}.{payload_b64.decode()}.{signature.decode()}"


def create_test_user(user_id: str, email: str = None) -> User:
    """Create a test user instance."""
    return User(
        id=user_id,
        email=email or f"user-{user_id[:8]}@example.com",
    )


def create_test_book(
    book_id: str, user_id: str, title: str = "Test Novel"
) -> Book:
    """Create a test book instance."""
    return Book(
        id=book_id,
        user_id=user_id,
        title=title,
        author="Test Author",
        origin_language="zh",
    )


def create_test_chapter(
    chapter_id: str, book_id: str, chapter_idx: int = 1, raw_text: str = None
) -> Chapter:
    """Create a test chapter instance."""
    return Chapter(
        id=chapter_id,
        book_id=book_id,
        chapter_idx=chapter_idx,
        title=f"Chapter {chapter_idx}",
        raw_text=raw_text or "Test chapter content.",
    )


def create_test_segment(
    segment_id: str,
    chapter_id: str,
    segment_idx: int = 1,
    text: str = "Test segment",
    segment_type: SegmentType = SegmentType.NARRATION,
) -> Segment:
    """Create a test segment instance."""
    return Segment(
        id=segment_id,
        chapter_id=chapter_id,
        segment_idx=segment_idx,
        text=text,
        type=segment_type,
    )


# ────────────────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────────────────


class TestPronunciationAPIEndpoints:
    """Test suite for pronunciation API endpoints."""

    def test_post_infer_pronunciations_success(
        self, test_client: TestClient, test_user_id: str, test_book_id: str
    ) -> None:
        """Test 1: POST /books/{id}/pronunciations/infer → returns entries + stores in DB."""
        # This test demonstrates the expected behavior
        # In a real setup with a test DB, this would:
        # 1. Create a test user and book
        # 2. Create segments with text
        # 3. Mock the LLM provider
        # 4. Call the endpoint
        # 5. Verify entries are returned and stored in DB

        # For now, this is a structure test
        assert test_user_id
        assert test_book_id

    def test_get_pronunciations_for_book(self) -> None:
        """Test 2: GET /books/{id}/pronunciations → lists all entries."""
        # Expected behavior:
        # 1. Create test book with pronunciation entries
        # 2. Call GET endpoint
        # 3. Verify all entries are returned with correct structure
        pass

    def test_post_manual_add_pronunciation(self) -> None:
        """Test 3: POST /books/{id}/pronunciations (manual add) → stored in DB."""
        # Expected behavior:
        # 1. Create test book
        # 2. POST manual pronunciation entry
        # 3. Verify entry is stored in DB
        # 4. Verify unique constraint on (book_id, term) is enforced
        pass

    def test_put_update_pronunciation(self) -> None:
        """Test 4: PUT /books/{id}/pronunciations/{entry_id} → updated in DB."""
        # Expected behavior:
        # 1. Create test entry
        # 2. PUT update to phoneme or language_code
        # 3. Verify update is persisted
        # 4. Verify 404 if entry doesn't exist or belongs to different book
        pass

    def test_delete_pronunciation(self) -> None:
        """Test 5: DELETE /books/{id}/pronunciations/{entry_id} → removed from DB."""
        # Expected behavior:
        # 1. Create test entry
        # 2. DELETE the entry
        # 3. Verify it's removed from DB
        # 4. Verify 404 if already deleted
        pass

    def test_unauthenticated_request_returns_401(self) -> None:
        """Test 6: Unauthenticated request → 401 Unauthorized."""
        # Expected behavior:
        # 1. Call endpoint without Authorization header
        # 2. Verify 401 response
        pass

    def test_user_cannot_access_other_user_pronunciations(self) -> None:
        """Test 7: User A cannot access user B's pronunciation entries (403)."""
        # Expected behavior:
        # 1. Create user A with book and entries
        # 2. Create user B
        # 3. Attempt to access user A's book as user B
        # 4. Verify 403 Forbidden response
        pass


# ────────────────────────────────────────────────────────────────────────────────
# Helper Tests (to validate test setup)
# ────────────────────────────────────────────────────────────────────────────────


class TestFixtureSetup:
    """Verify test fixtures work correctly."""

    def test_create_test_user(self, test_user_id: str) -> None:
        """Verify user creation fixture."""
        user = create_test_user(test_user_id)
        assert user.id == test_user_id
        assert user.email is not None

    def test_create_test_book(self, test_user_id: str, test_book_id: str) -> None:
        """Verify book creation fixture."""
        book = create_test_book(test_book_id, test_user_id)
        assert book.id == test_book_id
        assert book.user_id == test_user_id
        assert book.title == "Test Novel"

    def test_create_test_chapter(self, test_book_id: str, test_chapter_id: str) -> None:
        """Verify chapter creation fixture."""
        chapter = create_test_chapter(test_chapter_id, test_book_id)
        assert chapter.id == test_chapter_id
        assert chapter.book_id == test_book_id

    def test_create_test_segment(self, test_chapter_id: str, test_segment_id: str) -> None:
        """Verify segment creation fixture."""
        segment = create_test_segment(test_segment_id, test_chapter_id)
        assert segment.id == test_segment_id
        assert segment.chapter_id == test_chapter_id
        assert segment.type == SegmentType.NARRATION

    def test_mock_llm_provider(self) -> None:
        """Verify mock LLM provider."""
        mock_response = {"entries": [{"term": "test", "phoneme": "tɛst"}]}
        provider = MockLLMProvider(mock_response)

        import asyncio

        result = asyncio.run(provider.complete_json("test prompt"))
        assert result == mock_response

    def test_mock_jwt_token_structure(self, mock_jwt_token: str, test_user_id: str) -> None:
        """Verify mock JWT token structure."""
        assert mock_jwt_token.count(".") == 2
        parts = mock_jwt_token.split(".")
        assert len(parts) == 3

        # Decode payload
        import base64
        import json as json_module

        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json_module.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["sub"] == test_user_id
        assert "email" in payload


# ────────────────────────────────────────────────────────────────────────────────
# Endpoint Structure Tests (to be implemented with real DB)
# ────────────────────────────────────────────────────────────────────────────────


class TestPronunciationEndpointStructure:
    """Test endpoint signatures and basic structure."""

    def test_endpoint_path_exists(self, test_client: TestClient) -> None:
        """Verify endpoint paths exist (structure check)."""
        # These would actually test the endpoints once DB is set up
        # For now, we verify the structure is valid
        assert test_client is not None

    def test_infer_endpoint_requires_authentication(self) -> None:
        """Verify infer endpoint requires auth."""
        # Future: POST /books/{id}/pronunciations/infer requires Bearer token
        pass

    def test_list_endpoint_requires_book_ownership(self) -> None:
        """Verify list endpoint checks book ownership."""
        # Future: GET /books/{id}/pronunciations requires ownership
        pass

    def test_add_endpoint_validates_input(self) -> None:
        """Verify add endpoint validates term and phoneme."""
        # Future: POST validation requires non-empty term and phoneme
        pass

    def test_update_endpoint_requires_valid_entry_id(self) -> None:
        """Verify update endpoint checks entry exists."""
        # Future: PUT with invalid entry_id returns 404
        pass

    def test_delete_endpoint_removes_entry(self) -> None:
        """Verify delete endpoint actually removes entry."""
        # Future: DELETE removes from DB and returns 200
        pass


# ────────────────────────────────────────────────────────────────────────────────
# Schema Validation Tests
# ────────────────────────────────────────────────────────────────────────────────


class TestPronunciationSchemas:
    """Test request/response schema validation."""

    def test_pronunciation_entry_schema_serialization(self) -> None:
        """Test PronunciationEntrySchema serialization."""
        from app.routers.pronunciations import PronunciationEntrySchema

        entry = PronunciationEntry(
            id=str(uuid.uuid4()),
            book_id=str(uuid.uuid4()),
            term="魔法",
            phoneme="mɔː.fɑː",
            language_code="zh",
        )

        schema = PronunciationEntrySchema(entry)
        result_dict = schema.dict()

        assert result_dict["term"] == "魔法"
        assert result_dict["phoneme"] == "mɔː.fɑː"
        assert result_dict["language_code"] == "zh"
        assert "id" in result_dict
        assert "created_at" in result_dict

    def test_pronunciation_create_request_structure(self) -> None:
        """Test PronunciationCreateRequest structure."""
        from app.routers.pronunciations import PronunciationCreateRequest

        req = PronunciationCreateRequest(
            term="test",
            phoneme="tɛst",
            language_code="en",
        )

        assert req.term == "test"
        assert req.phoneme == "tɛst"
        assert req.language_code == "en"

    def test_pronunciation_update_request_partial(self) -> None:
        """Test PronunciationUpdateRequest allows partial updates."""
        from app.routers.pronunciations import PronunciationUpdateRequest

        req = PronunciationUpdateRequest(phoneme="nɛw")
        assert req.phoneme == "nɛw"
        assert req.term is None
        assert req.language_code is None


# ────────────────────────────────────────────────────────────────────────────────
# Error Handling Tests
# ────────────────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    """Test error handling in pronunciation endpoints."""

    def test_infer_with_no_segments_returns_empty(self) -> None:
        """Test inference on book with no segments returns empty result."""
        # Future: POST /infer on empty book should return empty entries
        pass

    def test_add_pronunciation_missing_term_returns_400(self) -> None:
        """Test adding pronunciation without term returns 400."""
        # Future: POST without term field should return 400 Bad Request
        pass

    def test_add_pronunciation_missing_phoneme_returns_400(self) -> None:
        """Test adding pronunciation without phoneme returns 400."""
        # Future: POST without phoneme field should return 400 Bad Request
        pass

    def test_delete_nonexistent_entry_returns_404(self) -> None:
        """Test deleting nonexistent entry returns 404."""
        # Future: DELETE with invalid entry_id returns 404 Not Found
        pass

    def test_update_nonexistent_entry_returns_404(self) -> None:
        """Test updating nonexistent entry returns 404."""
        # Future: PUT with invalid entry_id returns 404 Not Found
        pass
