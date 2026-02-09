"""Tests for routes/misc.py endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app
from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _close_client():
    """Ensure the shared TestClient is properly closed."""
    yield
    client.close()


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    user = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def override_get_current_user(authorization=None):
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_write_access] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_write_access, None)


class TestEnrichEndpoint:
    """Tests for POST /enrich endpoint."""

    def test_enrich_success(self, mock_auth):
        """Test successful enrichment."""
        with patch("fcp.routes.misc.enrich_entry", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"success": True, "enriched_data": {"nutrition": {}}}

            response = client.post(
                "/enrich",
                json={"log_id": "log123"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_enrich_failure(self, mock_auth):
        """Test enrichment failure."""
        with patch("fcp.routes.misc.enrich_entry", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"success": False, "error": "Log not found"}

            response = client.post(
                "/enrich",
                json={"log_id": "nonexistent"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 400


class TestSuggestEndpoint:
    """Tests for POST /suggest endpoint."""

    def test_suggest_success(self, mock_auth):
        """Test successful meal suggestions."""
        with patch("fcp.routes.misc.suggest_meal", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = [{"name": "Ramen", "reason": "Based on your preferences"}]

            response = client.post(
                "/suggest",
                json={"context": "lunch", "exclude_recent_days": 3},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert data["context"] == "lunch"


class TestImagePromptEndpoint:
    """Tests for POST /visual/image-prompt endpoint."""

    def test_image_prompt_success(self, mock_auth):
        """Test generating image prompt."""
        with patch("fcp.routes.misc.generate_image_prompt", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "A photorealistic image of ramen in a ceramic bowl..."

            response = client.post(
                "/visual/image-prompt",
                json={"subject": "ramen", "style": "photorealistic", "context": "menu"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert "prompt" in response.json()


class TestAudioLogEndpoint:
    """Tests for POST /audio/log-meal endpoint."""

    def test_audio_log_success(self, mock_auth):
        """Test logging meal from audio."""
        with patch("fcp.routes.misc.log_meal_from_audio", new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {"success": True, "log_id": "new123"}

            response = client.post(
                "/audio/log-meal",
                json={"audio_url": "https://storage.googleapis.com/audio.mp3", "notes": "Lunch"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_log.assert_called_once()


class TestVoiceCorrectionEndpoint:
    """Tests for POST /audio/voice-correction endpoint."""

    def test_voice_correction_success(self, mock_auth):
        """Test extracting voice correction intent."""
        with patch("fcp.routes.misc.extract_voice_correction", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"field": "dish_name", "new_value": "sushi"}

            response = client.post(
                "/audio/voice-correction",
                json={"voice_input": "Actually it was sushi not ramen"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200


class TestAnalyzeVoiceEndpoint:
    """Tests for POST /analyze/voice endpoint."""

    def test_analyze_voice_success(self, mock_auth):
        """Test analyzing voice transcript."""
        with patch("fcp.routes.misc.analyze_voice_transcript", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"dish_name": "pasta", "venue": "home"}

            response = client.post(
                "/analyze/voice",
                json={"transcript": "I just had some homemade pasta for lunch"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200


class TestCottageLabelEndpoint:
    """Tests for POST /cottage/label endpoint."""

    def test_cottage_label_success(self, mock_auth):
        """Test generating cottage food label."""
        with patch("fcp.routes.misc.generate_cottage_label", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"label_text": "Product Name...", "compliance_notes": []}

            response = client.post(
                "/cottage/label",
                json={
                    "product_name": "Homemade Cookies",
                    "ingredients": ["flour", "sugar", "butter"],
                    "net_weight": "12 oz",
                    "business_name": "Jane's Kitchen",
                    "business_address": "123 Main St",
                    "is_refrigerated": False,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200


class TestClinicalReportEndpoint:
    """Tests for GET /clinical/report endpoint."""

    def test_clinical_report_success(self, mock_auth):
        """Test generating clinical report."""
        with patch("fcp.routes.misc.generate_dietitian_report", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"report": "Patient shows good dietary habits..."}

            response = client.get(
                "/clinical/report?days=7",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_gen.assert_called_once_with("admin", 7, None)

    def test_clinical_report_with_focus(self, mock_auth):
        """Test generating clinical report with focus area."""
        with patch("fcp.routes.misc.generate_dietitian_report", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"report": "Sodium intake analysis..."}

            response = client.get(
                "/clinical/report?days=14&focus_area=sodium",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_gen.assert_called_once_with("admin", 14, "sodium")


class TestPlanFestivalEndpoint:
    """Tests for POST /civic/plan-festival endpoint."""

    def test_plan_festival_success(self, mock_auth):
        """Test planning food festival."""
        with patch("fcp.routes.misc.plan_food_festival", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"vendors": [], "logistics": {}}

            response = client.post(
                "/civic/plan-festival",
                json={
                    "city_name": "Seattle",
                    "theme": "Asian Street Food",
                    "target_vendor_count": 15,
                    "location_description": "Downtown waterfront",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_plan.assert_called_once_with("Seattle", "Asian Street Food", 15, "Downtown waterfront")


class TestEconomicGapsEndpoint:
    """Tests for POST /civic/economic-gaps endpoint."""

    def test_economic_gaps_success(self, mock_auth):
        """Test detecting economic gaps."""
        with patch("fcp.routes.misc.detect_economic_gaps", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = {"gaps": ["Vietnamese", "Ethiopian"], "analysis": "..."}

            response = client.post(
                "/civic/economic-gaps",
                json={
                    "neighborhood": "Capitol Hill",
                    "existing_cuisines": ["Mexican", "Italian", "Thai"],
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_detect.assert_called_once_with("Capitol Hill", ["Mexican", "Italian", "Thai"])


class TestParseMenuEndpoint:
    """Tests for POST /parser/menu endpoint."""

    def test_parse_menu_success(self, mock_auth):
        """Test parsing menu image."""
        with patch("fcp.tools.parse_menu", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {"dishes": [{"name": "Burger", "price": 12.99}]}

            response = client.post(
                "/parser/menu",
                json={"image_url": "https://firebasestorage.googleapis.com/menu.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_parse.assert_called_once()


class TestParseReceiptEndpoint:
    """Tests for POST /parser/receipt endpoint."""

    def test_parse_receipt_success(self, mock_auth):
        """Test parsing receipt image."""
        with patch("fcp.tools.parse_receipt", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {"items": [{"name": "Milk", "price": 4.99}]}

            response = client.post(
                "/parser/receipt",
                json={"image_url": "https://firebasestorage.googleapis.com/receipt.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_parse.assert_called_once()


class TestDietaryCheckEndpoint:
    """Tests for POST /taste-buddy/check endpoint."""

    def test_dietary_check_success(self, mock_auth):
        """Test dietary compatibility check."""
        with patch("fcp.routes.misc.check_dietary_compatibility", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"compatible": True, "warnings": []}

            response = client.post(
                "/taste-buddy/check",
                json={
                    "dish_name": "Pad Thai",
                    "ingredients": ["rice noodles", "shrimp", "peanuts"],
                    "user_allergies": ["shellfish"],
                    "user_diet": ["pescatarian"],
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_check.assert_called_once()


class TestFlavorPairingsEndpoint:
    """Tests for GET /flavor/pairings endpoint."""

    def test_flavor_pairings_ingredient(self, mock_auth):
        """Test getting ingredient pairings."""
        with patch("fcp.routes.misc.get_flavor_pairings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"pairings": ["garlic", "ginger", "soy sauce"]}

            response = client.get(
                "/flavor/pairings?subject=chicken&pairing_type=ingredient",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_get.assert_called_once_with("chicken", "ingredient")

    def test_flavor_pairings_beverage(self, mock_auth):
        """Test getting beverage pairings."""
        with patch("fcp.routes.misc.get_flavor_pairings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"pairings": ["red wine", "beer"]}

            response = client.get(
                "/flavor/pairings?subject=steak&pairing_type=beverage",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_get.assert_called_once_with("steak", "beverage")


class TestTrendsEndpoint:
    """Tests for GET /trends/identify endpoint."""

    def test_trends_identify_success(self, mock_auth):
        """Test identifying food trends."""
        with patch("fcp.routes.misc.identify_emerging_trends", new_callable=AsyncMock) as mock_identify:
            mock_identify.return_value = {"trends": ["fermented foods", "plant-based proteins"]}

            response = client.get(
                "/trends/identify?region=seattle&cuisine_focus=asian",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_identify.assert_called_once_with("admin", "seattle", "asian")

    def test_trends_identify_default_region(self, mock_auth):
        """Test identifying trends with default region."""
        with patch("fcp.routes.misc.identify_emerging_trends", new_callable=AsyncMock) as mock_identify:
            mock_identify.return_value = {"trends": []}

            response = client.get(
                "/trends/identify",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_identify.assert_called_once_with("admin", "local", None)
