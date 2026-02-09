"""Tests for deep research tool and routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.tools.research import generate_research_report


class TestGenerateResearchReport:
    """Tests for generate_research_report function."""

    @pytest.mark.asyncio
    async def test_generates_report_with_topic_only(self):
        """Test research with just a topic."""
        mock_result = {
            "report": "Research findings about Mediterranean diet.",
            "interaction_id": "int_123",
            "status": "completed",
        }

        with patch("fcp.tools.research.gemini") as mock_gemini:
            mock_gemini.generate_deep_research = AsyncMock(return_value=mock_result)

            result = await generate_research_report(topic="Mediterranean diet health benefits")

            assert result["status"] == "completed"
            assert result["report"] == "Research findings about Mediterranean diet."
            assert result["topic"] == "Mediterranean diet health benefits"
            assert result["interaction_id"] == "int_123"

            # Verify query was built correctly
            mock_gemini.generate_deep_research.assert_called_once()
            call_args = mock_gemini.generate_deep_research.call_args
            assert "Mediterranean diet health benefits" in call_args.kwargs["query"]

    @pytest.mark.asyncio
    async def test_generates_report_with_context(self):
        """Test research with topic and user context."""
        mock_result = {
            "report": "Personalized research findings.",
            "interaction_id": "int_456",
            "status": "completed",
        }

        with patch("fcp.tools.research.gemini") as mock_gemini:
            mock_gemini.generate_deep_research = AsyncMock(return_value=mock_result)

            result = await generate_research_report(
                topic="Best foods for runners",
                context="I am training for a marathon",
            )

            assert result["status"] == "completed"
            assert result["topic"] == "Best foods for runners"

            # Verify context was included in query
            call_args = mock_gemini.generate_deep_research.call_args
            query = call_args.kwargs["query"]
            assert "Best foods for runners" in query
            assert "I am training for a marathon" in query

    @pytest.mark.asyncio
    async def test_passes_custom_timeout(self):
        """Test that custom timeout is passed through."""
        mock_result = {"status": "completed", "report": "Report"}

        with patch("fcp.tools.research.gemini") as mock_gemini:
            mock_gemini.generate_deep_research = AsyncMock(return_value=mock_result)

            await generate_research_report(
                topic="Test topic",
                timeout_seconds=600,
            )

            call_args = mock_gemini.generate_deep_research.call_args
            assert call_args.kwargs["timeout_seconds"] == 600

    @pytest.mark.asyncio
    async def test_handles_timeout_status(self):
        """Test handling of timeout status."""
        mock_result = {
            "interaction_id": "int_789",
            "status": "timeout",
            "message": "Research still in progress",
        }

        with patch("fcp.tools.research.gemini") as mock_gemini:
            mock_gemini.generate_deep_research = AsyncMock(return_value=mock_result)

            result = await generate_research_report(topic="Complex topic")

            assert result["status"] == "timeout"
            assert result["message"] == "Research still in progress"
            assert result["topic"] == "Complex topic"

    @pytest.mark.asyncio
    async def test_handles_failed_status(self):
        """Test handling of failed status."""
        mock_result = {
            "interaction_id": "int_failed",
            "status": "failed",
            "message": "API error occurred",
        }

        with patch("fcp.tools.research.gemini") as mock_gemini:
            mock_gemini.generate_deep_research = AsyncMock(return_value=mock_result)

            result = await generate_research_report(topic="Failing topic")

            assert result["status"] == "failed"
            assert result["message"] == "API error occurred"
            assert result["topic"] == "Failing topic"


class TestDeepResearchGeminiMethod:
    """Tests for the Gemini client generate_deep_research method."""

    @pytest.mark.asyncio
    async def test_generate_deep_research_completed(self):
        """Test successful deep research completion."""
        from fcp.services.gemini import GeminiClient

        # Create mock interaction
        mock_interaction = MagicMock()
        mock_interaction.id = "test-interaction-id"
        mock_interaction.status = "completed"
        mock_output = MagicMock()
        mock_output.text = "Research report content"
        mock_interaction.outputs = [mock_output]

        # Create mock client
        mock_client = MagicMock()
        mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_deep_research(
            query="Test research query",
            timeout_seconds=30,
        )

        assert result["status"] == "completed"
        assert result["report"] == "Research report content"
        assert result["interaction_id"] == "test-interaction-id"

    @pytest.mark.asyncio
    async def test_generate_deep_research_failed(self):
        """Test deep research failure handling."""
        from fcp.services.gemini import GeminiClient

        # Create mock interaction that fails
        mock_interaction_initial = MagicMock()
        mock_interaction_initial.id = "test-interaction-id"
        mock_interaction_initial.status = "pending"

        mock_interaction_failed = MagicMock()
        mock_interaction_failed.id = "test-interaction-id"
        mock_interaction_failed.status = "failed"
        mock_interaction_failed.error = "Agent error occurred"

        mock_client = MagicMock()
        mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction_initial)
        mock_client.aio.interactions.get = AsyncMock(return_value=mock_interaction_failed)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_deep_research(
            query="Test query",
            timeout_seconds=30,
        )

        assert result["status"] == "failed"
        assert "Agent error" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_deep_research_no_client(self):
        """Test error when Gemini client not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_deep_research(query="Test query")

    @pytest.mark.asyncio
    async def test_generate_deep_research_empty_outputs(self):
        """Test deep research with empty outputs."""
        from fcp.services.gemini import GeminiClient

        # Create mock interaction with no outputs
        mock_interaction = MagicMock()
        mock_interaction.id = "test-interaction-id"
        mock_interaction.status = "completed"
        mock_interaction.outputs = []

        mock_client = MagicMock()
        mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)
        mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_deep_research(
            query="Test query",
            timeout_seconds=30,
        )

        assert result["status"] == "completed"
        assert result["report"] == ""
        assert result["interaction_id"] == "test-interaction-id"

    @pytest.mark.asyncio
    async def test_generate_deep_research_timeout_with_polling(self):
        """Test deep research timeout with actual polling simulation."""
        from fcp.services.gemini import GeminiClient

        # Create mock interaction that stays pending
        mock_interaction = MagicMock()
        mock_interaction.id = "test-interaction-id"
        mock_interaction.status = "pending"

        mock_client = MagicMock()
        mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client = GeminiClient()
        client.client = mock_client

        # Patch time module to control the loop
        # Sequence: start=0, first_check=5 (enters loop, sleeps), second_check=15 (exits)
        time_values = [0, 5, 15]
        time_index = [0]

        def mock_time():
            """Simulate time passing to allow one iteration then timeout."""
            idx = time_index[0]
            time_index[0] += 1
            return time_values[idx] if idx < len(time_values) else 1000

        with patch("fcp.services.gemini.time.monotonic", side_effect=mock_time):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await client.generate_deep_research(
                    query="Test query",
                    timeout_seconds=10,
                )

                # Verify sleep was called (polling interval)
                mock_sleep.assert_awaited_with(10)

        assert result["status"] == "timeout"
        assert result["interaction_id"] == "test-interaction-id"
        assert "still in progress" in result["message"]
        assert "10s" in result["message"]


class TestResearchRouteValidation:
    """Tests for research route request validation."""

    def test_research_request_model_valid(self):
        """Test valid research request model."""
        from fcp.routes.research import ResearchRequest

        request = ResearchRequest(topic="Mediterranean diet benefits")
        assert request.topic == "Mediterranean diet benefits"
        assert request.context is None
        assert request.timeout_seconds == 300

    def test_research_request_model_with_all_fields(self):
        """Test research request model with all fields."""
        from fcp.routes.research import ResearchRequest

        request = ResearchRequest(
            topic="Low-carb diet",
            context="I have diabetes",
            timeout_seconds=120,
        )
        assert request.topic == "Low-carb diet"
        assert request.context == "I have diabetes"
        assert request.timeout_seconds == 120

    def test_research_request_model_topic_too_short(self):
        """Test research request model rejects short topics."""
        from pydantic import ValidationError

        from fcp.routes.research import ResearchRequest

        with pytest.raises(ValidationError):
            ResearchRequest(topic="ab")  # Less than 3 characters

    def test_research_request_model_timeout_bounds(self):
        """Test research request model validates timeout bounds."""
        from pydantic import ValidationError

        from fcp.routes.research import ResearchRequest

        # Too low
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic", timeout_seconds=30)

        # Too high
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic", timeout_seconds=1000)

    def test_research_request_model_timeout_valid_range(self):
        """Test valid timeout values."""
        from fcp.routes.research import ResearchRequest

        # Minimum valid
        request = ResearchRequest(topic="Valid topic", timeout_seconds=60)
        assert request.timeout_seconds == 60

        # Maximum valid
        request = ResearchRequest(topic="Valid topic", timeout_seconds=600)
        assert request.timeout_seconds == 600


class TestResearchRouterConfig:
    """Tests for research router configuration."""

    def test_research_router_exists(self):
        """Test research router is properly configured."""
        from fcp.routes.research import router

        assert router is not None

    def test_research_route_registered(self):
        """Test research route is registered in the router."""
        from fcp.routes.research import router

        routes = [r.path for r in router.routes]
        assert "/research" in routes
