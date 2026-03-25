"""
Unit tests for ResponseService and SarvamAIService.

These tests verify the response formatting functionality including
fallback mechanisms, caching, and external service integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from services.response import ResponseService, SarvamAIService
from models.core import SchemeModel, EligibleScheme, EligibilityModel


@pytest.fixture
def sample_schemes():
    """Create sample schemes for testing."""
    return [
        EligibleScheme(
            scheme=SchemeModel(
                id="test-scheme-001",
                name="Test Scholarship Scheme",
                description="Financial assistance for students",
                eligibility=EligibilityModel(
                    age="18-25",
                    income="< 5 lakh",
                    category="All",
                    occupation="student"
                ),
                documents=["Aadhaar", "Income Certificate"],
                state="Central",
                category="education",
                keywords="student scholarship"
            ),
            match_score=90.0,
            eligibility_reason="You meet all criteria",
            is_eligible=True
        )
    ]


@pytest.fixture
def mock_sarvam_service():
    """Create mock Sarvam AI service."""
    service = Mock(spec=SarvamAIService)
    service.llm_available = False
    service.translation_available = False
    service.api_key = None
    service.generate_response = AsyncMock(return_value="Mock LLM response")
    service.translate_text = AsyncMock(return_value="Mock translation")
    service.health_check = AsyncMock(return_value={
        "llm_service": "unavailable",
        "translation_service": "unavailable",
        "api_key_configured": False
    })
    return service


class TestResponseService:
    """Test cases for ResponseService."""
    
    def test_init(self, mock_sarvam_service):
        """Test ResponseService initialization."""
        service = ResponseService(mock_sarvam_service)
        
        assert service.sarvam_service == mock_sarvam_service
        assert isinstance(service.response_cache, dict)
        assert len(service.fallback_templates) == 2
        assert "english" in service.fallback_templates
        assert "hindi" in service.fallback_templates
    
    def test_generate_cache_key(self, sample_schemes):
        """Test cache key generation."""
        service = ResponseService()
        
        key1 = service._generate_cache_key(sample_schemes, "english")
        key2 = service._generate_cache_key(sample_schemes, "english")
        key3 = service._generate_cache_key(sample_schemes, "hindi")
        
        assert key1 == key2  # Same input should generate same key
        assert key1 != key3  # Different language should generate different key
        assert len(key1) == 32  # MD5 hash length
    
    def test_format_with_template_english(self, sample_schemes):
        """Test template-based formatting in English."""
        service = ResponseService()
        
        result = service._format_with_template(sample_schemes, "english")
        
        assert "Test Scholarship Scheme" in result
        assert "Financial assistance for students" in result
        assert "You meet all criteria" in result
        assert "Aadhaar, Income Certificate" in result
        assert "1 government schemes" in result
    
    def test_format_with_template_hindi(self, sample_schemes):
        """Test template-based formatting in Hindi."""
        service = ResponseService()
        
        result = service._format_with_template(sample_schemes, "hindi")
        
        assert "Test Scholarship Scheme" in result
        assert "Financial assistance for students" in result
        assert "You meet all criteria" in result
        assert "Aadhaar, Income Certificate" in result
        assert "1 सरकारी योजनाएं" in result
    
    def test_format_with_template_empty_schemes(self):
        """Test template formatting with empty schemes list."""
        service = ResponseService()
        
        result_en = service._format_with_template([], "english")
        result_hi = service._format_with_template([], "hindi")
        
        assert "Unfortunately, no schemes match" in result_en
        assert "दुर्भाग्य से, कोई योजना" in result_hi
    
    @pytest.mark.asyncio
    async def test_format_schemes_fallback(self, sample_schemes, mock_sarvam_service):
        """Test scheme formatting using fallback templates."""
        service = ResponseService(mock_sarvam_service)
        
        result = await service.format_schemes(sample_schemes, "english")
        
        assert "Test Scholarship Scheme" in result
        assert "Financial assistance for students" in result
        # Should not call external service since it's unavailable
        mock_sarvam_service.generate_response.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_format_schemes_with_llm(self, sample_schemes):
        """Test scheme formatting with LLM service available."""
        mock_sarvam = Mock(spec=SarvamAIService)
        mock_sarvam.llm_available = True
        mock_sarvam.generate_response = AsyncMock(return_value="LLM generated response")
        
        with patch('services.response.settings') as mock_settings:
            mock_settings.enable_llm_responses = True
            mock_settings.cache_size = 1000
            mock_settings.cache_ttl = 3600
            service = ResponseService(mock_sarvam)
            
            result = await service.format_schemes(sample_schemes, "english")
            
            assert result == "LLM generated response"
            mock_sarvam.generate_response.assert_called_once_with(sample_schemes, "english")
    
    @pytest.mark.asyncio
    async def test_format_schemes_llm_fallback(self, sample_schemes):
        """Test fallback when LLM service fails."""
        mock_sarvam = Mock(spec=SarvamAIService)
        mock_sarvam.llm_available = True
        mock_sarvam.generate_response = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('services.response.settings') as mock_settings:
            mock_settings.enable_llm_responses = True
            mock_settings.cache_size = 1000
            mock_settings.cache_ttl = 3600
            service = ResponseService(mock_sarvam)
            
            result = await service.format_schemes(sample_schemes, "english")
            
            # Should fallback to template
            assert "Test Scholarship Scheme" in result
            mock_sarvam.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, sample_schemes, mock_sarvam_service):
        """Test response caching."""
        service = ResponseService(mock_sarvam_service)
        
        # First call should generate and cache
        result1 = await service.format_schemes(sample_schemes, "english")
        
        # Second call should use cache
        result2 = await service.format_schemes(sample_schemes, "english")
        
        assert result1 == result2
        assert len(service.response_cache) == 1
    
    def test_cache_expiration(self, sample_schemes, mock_sarvam_service):
        """Test cache expiration logic."""
        service = ResponseService(mock_sarvam_service)
        
        # Manually add expired entry
        cache_key = service._generate_cache_key(sample_schemes, "english")
        expired_time = datetime.now() - timedelta(hours=2)
        service.response_cache[cache_key] = ("old response", expired_time)
        
        # Should return None for expired entry
        result = service._get_cached_response(cache_key)
        assert result is None
        assert cache_key not in service.response_cache  # Should be removed
    
    @pytest.mark.asyncio
    async def test_translate_response_english(self, mock_sarvam_service):
        """Test translation for English (should return original)."""
        service = ResponseService(mock_sarvam_service)
        
        result = await service.translate_response("Hello world", "english")
        
        assert result == "Hello world"
        mock_sarvam_service.translate_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_translate_response_hindi(self):
        """Test translation to Hindi."""
        mock_sarvam = Mock(spec=SarvamAIService)
        mock_sarvam.translation_available = True
        mock_sarvam.translate_text = AsyncMock(return_value="नमस्कार संसार")
        
        with patch('services.response.settings') as mock_settings:
            mock_settings.enable_translation = True
            mock_settings.cache_size = 1000
            mock_settings.cache_ttl = 3600
            service = ResponseService(mock_sarvam)
            
            result = await service.translate_response("Hello world", "hindi")
            
            assert result == "नमस्कार संसार"
            mock_sarvam.translate_text.assert_called_once_with("Hello world", "hi")
    
    def test_generate_scheme_explanation(self, sample_schemes):
        """Test single scheme explanation generation."""
        service = ResponseService()
        scheme = sample_schemes[0].scheme
        
        result = service.generate_scheme_explanation(scheme, "english")
        
        assert "Test Scholarship Scheme" in result
        assert "Financial assistance for students" in result
        assert "Please check eligibility criteria" in result
    
    def test_clear_cache(self, mock_sarvam_service):
        """Test cache clearing."""
        service = ResponseService(mock_sarvam_service)
        
        # Add some cache entries
        service.response_cache["key1"] = ("response1", datetime.now())
        service.response_cache["key2"] = ("response2", datetime.now())
        
        count = service.clear_cache()
        
        assert count == 2
        assert len(service.response_cache) == 0
    
    def test_get_cache_stats(self, mock_sarvam_service):
        """Test cache statistics."""
        service = ResponseService(mock_sarvam_service)
        
        # Add some cache entries
        now = datetime.now()
        service.response_cache["active"] = ("response", now)
        service.response_cache["expired"] = ("response", now - timedelta(hours=2))
        
        stats = service.get_cache_stats()
        
        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["sarvam_ai_available"] == False
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_sarvam_service):
        """Test health check functionality."""
        service = ResponseService(mock_sarvam_service)
        
        health = await service.health_check()
        
        assert health["response_service"] == "operational"
        assert "external_services" in health
        assert "cache" in health
        assert health["fallback_templates"] == 2
        assert "english" in health["supported_languages"]
        assert "hindi" in health["supported_languages"]
        mock_sarvam_service.health_check.assert_called_once()


class TestSarvamAIService:
    """Test cases for SarvamAIService."""
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        service = SarvamAIService(api_key="test-key")
        
        assert service.api_key == "test-key"
        assert service.llm_available == True
        assert service.translation_available == True
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        service = SarvamAIService(api_key=None)
        
        assert service.api_key is None
        assert service.llm_available == False
        assert service.translation_available == False
    
    @pytest.mark.asyncio
    async def test_generate_response_no_api_key(self, sample_schemes):
        """Test LLM generation without API key."""
        service = SarvamAIService(api_key=None)
        
        with pytest.raises(ValueError, match="LLM service not available"):
            await service.generate_response(sample_schemes, "english")
    
    @pytest.mark.asyncio
    async def test_translate_text_no_api_key(self):
        """Test translation without API key."""
        service = SarvamAIService(api_key=None)
        
        with pytest.raises(ValueError, match="Translation service not available"):
            await service.translate_text("Hello", "hi")
    
    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check without API key."""
        service = SarvamAIService(api_key=None)
        
        health = await service.health_check()
        
        assert health["api_key_configured"] == False
        assert health["llm_service"] == "unavailable"
        assert health["translation_service"] == "unavailable"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_generate_response_success(self, mock_client, sample_schemes):
        """Test successful LLM response generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated response"}}]
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        service = SarvamAIService(api_key="test-key")
        result = await service.generate_response(sample_schemes, "english")
        
        assert result == "Generated response"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_translate_text_success(self, mock_client):
        """Test successful translation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translated_text": "नमस्कार"}
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        service = SarvamAIService(api_key="test-key")
        result = await service.translate_text("Hello", "hi")
        
        assert result == "नमस्कार"