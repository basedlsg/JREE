"""Tests for JRE Quote Search API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from backend.main import app
from backend.models import SearchRequest, QuoteResult, SearchResponse


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_pinecone_index():
    """Mock Pinecone index for testing."""
    mock_index = Mock()
    mock_index.describe_index_stats.return_value = MagicMock(
        total_vector_count=10000,
        dimension=1024,
        namespaces={},
    )
    return mock_index


@pytest.fixture
def mock_cohere_client():
    """Mock Cohere client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.embeddings = [[0.1] * 1024]  # Fake embedding
    mock_client.embed.return_value = mock_response
    return mock_client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_success(self, client, mock_pinecone_index, mock_cohere_client):
        """Test health check returns healthy when services are connected."""
        with patch("backend.main.get_pinecone_index", return_value=mock_pinecone_index):
            with patch("backend.main.get_cohere_client", return_value=mock_cohere_client):
                response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["pinecone_connected"] is True
        assert data["cohere_connected"] is True

    def test_health_check_pinecone_down(self, client, mock_cohere_client):
        """Test health check returns degraded when Pinecone is down."""
        mock_bad_index = Mock()
        mock_bad_index.describe_index_stats.side_effect = Exception("Connection failed")

        with patch("backend.main.get_pinecone_index", return_value=mock_bad_index):
            with patch("backend.main.get_cohere_client", return_value=mock_cohere_client):
                response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["pinecone_connected"] is False
        assert data["cohere_connected"] is True

    def test_health_check_cohere_down(self, client, mock_pinecone_index):
        """Test health check returns degraded when Cohere is down."""
        mock_bad_cohere = Mock()
        mock_bad_cohere.embed.side_effect = Exception("API error")

        with patch("backend.main.get_pinecone_index", return_value=mock_pinecone_index):
            with patch("backend.main.get_cohere_client", return_value=mock_bad_cohere):
                response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["pinecone_connected"] is True
        assert data["cohere_connected"] is False


class TestSearchEndpoint:
    """Tests for /api/search endpoint."""

    def test_search_success(self, client, mock_pinecone_index, mock_cohere_client):
        """Test successful search returns results."""
        # Setup mock Pinecone response
        mock_match = Mock()
        mock_match.id = "jre-2100-chunk-0001"
        mock_match.score = 0.95
        mock_match.metadata = {
            "text": "This is a test quote about consciousness.",
            "episode_number": 2100,
            "episode_title": "Guest Name - Episode Title",
            "guest": "Guest Name",
            "timestamp": None,
        }

        mock_query_response = Mock()
        mock_query_response.matches = [mock_match]
        mock_pinecone_index.query.return_value = mock_query_response

        with patch("backend.search.get_pinecone_index", return_value=mock_pinecone_index):
            with patch("backend.search.get_cohere_client", return_value=mock_cohere_client):
                response = client.post(
                    "/api/search",
                    json={"query": "consciousness", "top_k": 5},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "consciousness"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["text"] == "This is a test quote about consciousness."
        assert data["results"][0]["episode_number"] == 2100
        assert data["results"][0]["score"] == 0.95
        assert "search_time_ms" in data

    def test_search_empty_query(self, client):
        """Test search with empty query returns 422."""
        response = client.post("/api/search", json={"query": "", "top_k": 5})
        assert response.status_code == 422

    def test_search_invalid_top_k(self, client):
        """Test search with invalid top_k returns 422."""
        response = client.post("/api/search", json={"query": "test", "top_k": 100})
        assert response.status_code == 422

    def test_search_with_episode_filter(self, client, mock_pinecone_index, mock_cohere_client):
        """Test search with episode filter passes filter to Pinecone."""
        mock_query_response = Mock()
        mock_query_response.matches = []
        mock_pinecone_index.query.return_value = mock_query_response

        with patch("backend.search.get_pinecone_index", return_value=mock_pinecone_index):
            with patch("backend.search.get_cohere_client", return_value=mock_cohere_client):
                response = client.post(
                    "/api/search",
                    json={
                        "query": "aliens",
                        "top_k": 10,
                        "episode_filter": [2000, 2001, 2002],
                    },
                )

        assert response.status_code == 200
        # Verify filter was passed to Pinecone
        call_kwargs = mock_pinecone_index.query.call_args.kwargs
        assert call_kwargs["filter"] == {"episode_number": {"$in": [2000, 2001, 2002]}}

    def test_search_no_results(self, client, mock_pinecone_index, mock_cohere_client):
        """Test search returns empty results gracefully."""
        mock_query_response = Mock()
        mock_query_response.matches = []
        mock_pinecone_index.query.return_value = mock_query_response

        with patch("backend.search.get_pinecone_index", return_value=mock_pinecone_index):
            with patch("backend.search.get_cohere_client", return_value=mock_cohere_client):
                response = client.post(
                    "/api/search",
                    json={"query": "xyznonexistentquery123"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert data["results"] == []


class TestStatsEndpoint:
    """Tests for /api/stats endpoint."""

    def test_stats_success(self, client, mock_pinecone_index):
        """Test stats endpoint returns index statistics."""
        with patch("backend.search.get_pinecone_index", return_value=mock_pinecone_index):
            response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_vectors"] == 10000
        assert data["index_dimension"] == 1024
        assert "index_name" in data

    def test_stats_pinecone_error(self, client):
        """Test stats returns 500 when Pinecone fails."""
        mock_bad_index = Mock()
        mock_bad_index.describe_index_stats.side_effect = Exception("Connection failed")

        with patch("backend.search.get_pinecone_index", return_value=mock_bad_index):
            response = client.get("/api/stats")

        assert response.status_code == 500


class TestGoldenQueries:
    """Golden query tests for search quality validation.

    These tests verify that known queries return expected results.
    They require a populated Pinecone index to run.
    """

    # Mark as integration tests - skip in unit test runs
    @pytest.mark.integration
    def test_golden_query_consciousness(self, client):
        """Test that 'consciousness' query returns relevant results."""
        response = client.post(
            "/api/search",
            json={"query": "what is consciousness", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return some results
        assert data["total_results"] > 0

        # Top result should be relevant (score > 0.7)
        if data["results"]:
            assert data["results"][0]["score"] > 0.7

    @pytest.mark.integration
    def test_golden_query_ufo(self, client):
        """Test that 'UFO' query returns relevant results."""
        response = client.post(
            "/api/search",
            json={"query": "UFO sightings aliens", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] > 0

    @pytest.mark.integration
    def test_golden_query_diet(self, client):
        """Test that diet/nutrition query returns relevant results."""
        response = client.post(
            "/api/search",
            json={"query": "carnivore diet benefits", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] > 0

    @pytest.mark.integration
    def test_golden_query_comedy(self, client):
        """Test that comedy query returns relevant results."""
        response = client.post(
            "/api/search",
            json={"query": "stand up comedy clubs", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] > 0


class TestModels:
    """Tests for Pydantic models."""

    def test_search_request_defaults(self):
        """Test SearchRequest default values."""
        request = SearchRequest(query="test")
        assert request.query == "test"
        assert request.top_k == 10
        assert request.episode_filter is None
        assert request.guest_filter is None

    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Valid request
        request = SearchRequest(query="test", top_k=5)
        assert request.top_k == 5

        # Invalid top_k
        with pytest.raises(ValueError):
            SearchRequest(query="test", top_k=0)

        with pytest.raises(ValueError):
            SearchRequest(query="test", top_k=51)

    def test_quote_result_model(self):
        """Test QuoteResult model."""
        result = QuoteResult(
            text="Test quote",
            episode_number=2100,
            episode_title="Test Episode",
            guest="Test Guest",
            score=0.95,
            chunk_id="jre-2100-chunk-0001",
        )
        assert result.text == "Test quote"
        assert result.timestamp is None  # Optional field

    def test_search_response_model(self):
        """Test SearchResponse model."""
        response = SearchResponse(
            query="test",
            results=[],
            total_results=0,
            search_time_ms=10.5,
        )
        assert response.query == "test"
        assert response.results == []
