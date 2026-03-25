"""
Response Service for Government Scheme Copilot.

This service formats scheme information into user-friendly responses with translation
support. It integrates with Sarvam AI for LLM-based response generation and translation,
with fallback mechanisms for when external services fail.
"""

import asyncio
import hashlib
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from collections import OrderedDict
import threading
import time

import httpx
from models.core import SchemeModel, EligibleScheme
from models.api import LanguageEnum
from models.exceptions import (
    ExternalServiceException, TranslationServiceException, 
    ExternalServiceTimeoutException, ProcessingException
)
from utils.timeout_handler import timeout_manager, with_external_service_timeout
from config import settings

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe LRU cache with TTL support and performance monitoring.
    
    This cache provides:
    - Least Recently Used eviction policy
    - Time-to-live (TTL) expiration
    - Thread-safe operations
    - Performance metrics
    - Memory usage tracking
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live for entries in seconds
        """
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self._lock = threading.RLock()
        
        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            value, timestamp = self._cache[key]
            
            # Check if expired
            if datetime.now() - timestamp >= self.ttl:
                del self._cache[key]
                self._expirations += 1
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value
    
    def put(self, key: str, value: Any) -> None:
        """
        Put value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = datetime.now()
            
            if key in self._cache:
                # Update existing entry
                self._cache[key] = (value, current_time)
                self._cache.move_to_end(key)
            else:
                # Add new entry
                if len(self._cache) >= self.max_size:
                    # Evict least recently used
                    self._cache.popitem(last=False)
                    self._evictions += 1
                
                self._cache[key] = (value, current_time)
    
    def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = datetime.now()
            expired_keys = []
            
            for key, (_, timestamp) in self._cache.items():
                if current_time - timestamp >= self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._expirations += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions,
                'expirations': self._expirations,
                'ttl_seconds': self.ttl.total_seconds()
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Estimate memory usage of cache.
        
        Returns:
            Dictionary with memory usage estimates
        """
        with self._lock:
            # Rough estimation of memory usage
            total_keys_size = sum(len(key.encode('utf-8')) for key in self._cache.keys())
            
            # Estimate value sizes (rough approximation)
            total_values_size = 0
            for value, _ in self._cache.values():
                if isinstance(value, str):
                    total_values_size += len(value.encode('utf-8'))
                elif isinstance(value, (dict, list)):
                    total_values_size += len(str(value).encode('utf-8'))
                else:
                    total_values_size += 100  # Rough estimate for other types
            
            return {
                'entries': len(self._cache),
                'keys_size_bytes': total_keys_size,
                'values_size_bytes': total_values_size,
                'total_size_bytes': total_keys_size + total_values_size,
                'avg_entry_size_bytes': (total_keys_size + total_values_size) / len(self._cache) if self._cache else 0
            }


class SarvamAIService:
    """
    Service for integrating with Sarvam AI APIs for LLM and translation.
    
    This service handles communication with Sarvam AI's chat completions API
    for generating user-friendly responses and translation API for multilingual support.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.sarvam.ai"):
        """
        Initialize Sarvam AI service.
        
        Args:
            api_key: Sarvam AI API key (defaults to settings)
            base_url: Base URL for Sarvam AI APIs
        """
        self.api_key = api_key or settings.sarvam_api_key
        self.base_url = base_url.rstrip('/')
        self.llm_url = f"{self.base_url}/v1/chat/completions"
        self.translate_url = f"{self.base_url}/translate"
        self.timeout = settings.external_service_timeout
        
        # Service availability flags
        self.llm_available = bool(self.api_key)
        self.translation_available = bool(self.api_key)
        
        if not self.api_key:
            logger.warning("No Sarvam AI API key provided - external services will be disabled")
    
    async def generate_response(
        self, 
        schemes: List[EligibleScheme], 
        language: str = "english"
    ) -> str:
        """
        Generate user-friendly response using Sarvam AI LLM.
        
        Args:
            schemes: List of eligible schemes with eligibility information
            language: Target language for response generation
            
        Returns:
            Generated response text in the target language
            
        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If response format is invalid
        """
        if not self.llm_available:
            raise ExternalServiceException(
                service_name="Sarvam AI LLM",
                message="LLM service not available - no API key configured",
                fallback_available=True
            )
        
        # Prepare scheme information for the LLM
        scheme_text = ""
        for i, eligible_scheme in enumerate(schemes, 1):
            scheme = eligible_scheme.scheme
            scheme_text += f"\n{i}. {scheme.name}\n"
            scheme_text += f"   Description: {scheme.description}\n"
            scheme_text += f"   Eligibility: {eligible_scheme.eligibility_reason}\n"
            scheme_text += f"   Documents: {', '.join(scheme.documents)}\n"
        
        # Adjust prompt based on target language
        if language.lower() == "hindi":
            language_instruction = "Respond in Hindi (Devanagari script). "
        else:
            language_instruction = ""
        
        # Create prompt for Sarvam AI (based on original Databricks implementation)
        prompt = f"""{language_instruction}Explain the following government schemes clearly for a common Indian citizen. Include benefits, eligibility reasons, and required documents. Keep it simple and structured.

Schemes:
{scheme_text}

Format the response with:
- Numbered list for each scheme
- Clear benefit description
- Eligibility reason
- Required documents as bullet points
- Simple, non-technical language
- Keep it concise (under 1500 characters total)
"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sarvam-m",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant explaining Indian government schemes in simple language."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            return await timeout_manager.external_service_call(
                self._make_llm_request(payload, headers),
                service_name="Sarvam AI LLM",
                timeout_seconds=self.timeout
            )
                
        except Exception as e:
            if isinstance(e, ExternalServiceTimeoutException):
                raise e
            else:
                raise ExternalServiceException(
                    service_name="Sarvam AI LLM",
                    message=f"LLM request failed: {str(e)}",
                    fallback_available=True,
                    original_exception=e
                )
    
    async def _make_llm_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """Make the actual LLM request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(self.llm_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if 'choices' not in result or not result['choices']:
                raise ValueError("Invalid response format from Sarvam AI")
            
            generated_text = result['choices'][0]['message']['content']
            logger.info(f"LLM generation successful")
            return generated_text.strip()
            raise ValueError(f"Invalid response format: {e}")
    
    async def translate_text(self, text: str, target_language: str = "hi") -> str:
        """
        Translate text using Sarvam AI Translation API.
        
        Args:
            text: English text to translate
            target_language: Target language code (default: 'hi' for Hindi)
            
        Returns:
            Translated text
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        if not self.translation_available:
            raise TranslationServiceException(
                target_language=target_language,
                message="Translation service not available - no API key configured"
            )
        
        try:
            # Translation API uses different auth header format
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": text,
                "source_language_code": "en-IN",
                "target_language_code": f"{target_language}-IN",
                "speaker_gender": "Male",  # Must be capitalized
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True
            }
            
            return await timeout_manager.external_service_call(
                self._make_translation_request(payload, headers),
                service_name="Sarvam AI Translation",
                timeout_seconds=self.timeout
            )
                
        except Exception as e:
            if isinstance(e, ExternalServiceTimeoutException):
                raise TranslationServiceException(
                    target_language=target_language,
                    message=f"Translation timed out after {self.timeout} seconds",
                    original_exception=e
                )
            else:
                raise TranslationServiceException(
                    target_language=target_language,
                    message=f"Translation failed: {str(e)}",
                    original_exception=e
                )
    
    async def _make_translation_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """Make the actual translation request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(self.translate_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            translated_text = result.get('translated_text', payload['input'])
            
            logger.info(f"Translation successful")
            return translated_text
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Sarvam AI services.
        
        Returns:
            Dictionary with service health status
        """
        health_status = {
            "llm_service": "unavailable",
            "translation_service": "unavailable",
            "api_key_configured": bool(self.api_key)
        }
        
        if not self.api_key:
            return health_status
        
        # Test LLM service with minimal request
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sarvam-m",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self.llm_url, headers=headers, json=payload)
                if response.status_code == 200:
                    health_status["llm_service"] = "operational"
                else:
                    health_status["llm_service"] = f"error_{response.status_code}"
                    
        except Exception as e:
            health_status["llm_service"] = f"error: {str(e)[:50]}"
        
        # Test translation service
        try:
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": "Hello",
                "source_language_code": "en-IN",
                "target_language_code": "hi-IN",
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True
            }
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self.translate_url, headers=headers, json=payload)
                if response.status_code == 200:
                    health_status["translation_service"] = "operational"
                else:
                    health_status["translation_service"] = f"error_{response.status_code}"
                    
        except Exception as e:
            health_status["translation_service"] = f"error: {str(e)[:50]}"
        
        return health_status


class ResponseService:
    """
    Service for formatting scheme information into user-friendly responses.
    
    This service generates natural language explanations of schemes with multilingual
    support, caching for performance, and fallback mechanisms for reliability.
    """
    
    def __init__(self, sarvam_service: Optional[SarvamAIService] = None):
        """
        Initialize response service with enhanced caching.
        
        Args:
            sarvam_service: Optional Sarvam AI service instance
        """
        self.sarvam_service = sarvam_service or SarvamAIService()
        
        # Enhanced LRU cache with TTL
        self.response_cache = LRUCache(
            max_size=settings.cache_size,
            ttl_seconds=settings.cache_ttl
        )
        
        # Separate cache for translations
        self.translation_cache = LRUCache(
            max_size=settings.cache_size // 2,  # Smaller cache for translations
            ttl_seconds=settings.cache_ttl * 2  # Longer TTL for translations
        )
        
        # Load fallback templates
        self.fallback_templates = self._load_fallback_templates()
        
        # Background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("ResponseService initialized with enhanced LRU caching and TTL support")
    
    def _start_cleanup_task(self):
        """Start background task for cache cleanup."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Cleanup every 5 minutes
                    expired_responses = self.response_cache.cleanup_expired()
                    expired_translations = self.translation_cache.cleanup_expired()
                    
                    if expired_responses > 0 or expired_translations > 0:
                        logger.debug(f"Cache cleanup: {expired_responses} responses, {expired_translations} translations expired")
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        # Start cleanup task if we're in an async context
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            pass
    def _load_fallback_templates(self) -> Dict[str, Dict[str, str]]:
        """Load fallback response templates for when external services fail."""
        return {
            "english": {
                "response_format": "Based on your profile, here are {count} government schemes you may be eligible for:\n\n{schemes}",
                "scheme_format": "{number}. **{name}**\n   Benefits: {description}\n   Eligibility: {reason}\n   Documents: {documents}",
                "no_schemes": "Unfortunately, no schemes match your current profile. Consider checking eligibility criteria or contacting local authorities for assistance."
            },
            "hindi": {
                "response_format": "आपकी प्रोफाइल के आधार पर, यहाँ {count} सरकारी योजनाएं हैं जिनके लिए आप पात्र हो सकते हैं:\n\n{schemes}",
                "scheme_format": "{number}. **{name}**\n   लाभ: {description}\n   पात्रता: {reason}\n   दस्तावेज़: {documents}",
                "no_schemes": "दुर्भाग्य से, कोई योजना आपकी वर्तमान प्रोफाइल से मेल नहीं खाती। पात्रता मानदंड की जांच करने या सहायता के लिए स्थानीय अधिकारियों से संपर्क करने पर विचार करें।"
            }
        }
    
    def _generate_cache_key(self, schemes: List[EligibleScheme], language: str) -> str:
        """
        Generate cache key from schemes and language.
        
        Args:
            schemes: List of eligible schemes
            language: Target language
            
        Returns:
            MD5 hash as cache key
        """
        # Create deterministic key from scheme IDs, match scores, and language
        key_data = []
        for scheme in schemes:
            key_data.append(f"{scheme.scheme.id}:{scheme.match_score:.1f}")
        
        key_string = f"{'-'.join(sorted(key_data))}-{language}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """
        Get cached response using LRU cache.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached response or None if not found/expired
        """
        return self.response_cache.get(cache_key)
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """
        Cache response using LRU cache.
        
        Args:
            cache_key: Cache key
            response: Response to cache
        """
        self.response_cache.put(cache_key, response)
    
    def _get_cached_translation(self, text: str, target_language: str) -> Optional[str]:
        """
        Get cached translation.
        
        Args:
            text: Original text
            target_language: Target language
            
        Returns:
            Cached translation or None if not found
        """
        cache_key = hashlib.md5(f"{text}-{target_language}".encode()).hexdigest()
        return self.translation_cache.get(cache_key)
    
    def _cache_translation(self, text: str, target_language: str, translation: str) -> None:
        """
        Cache translation.
        
        Args:
            text: Original text
            target_language: Target language
            translation: Translated text
        """
        cache_key = hashlib.md5(f"{text}-{target_language}".encode()).hexdigest()
        self.translation_cache.put(cache_key, translation)
    
    def _format_with_template(self, schemes: List[EligibleScheme], language: str) -> str:
        """
        Format schemes using fallback templates.
        
        Args:
            schemes: List of eligible schemes
            language: Target language
            
        Returns:
            Formatted response using templates
        """
        if not schemes:
            template = self.fallback_templates.get(language, self.fallback_templates['english'])
            return template['no_schemes']
        
        template = self.fallback_templates.get(language, self.fallback_templates['english'])
        
        formatted_schemes = []
        for i, eligible_scheme in enumerate(schemes, 1):
            scheme = eligible_scheme.scheme
            scheme_text = template['scheme_format'].format(
                number=i,
                name=scheme.name,
                description=scheme.description,
                reason=eligible_scheme.eligibility_reason,
                documents=', '.join(scheme.documents)
            )
            formatted_schemes.append(scheme_text)
        
        return template['response_format'].format(
            count=len(schemes),
            schemes='\n\n'.join(formatted_schemes)
        )
    
    async def format_schemes(
        self, 
        schemes: List[EligibleScheme], 
        language: str = "english"
    ) -> str:
        """
        Format schemes into user-friendly response with caching and fallback.
        
        Args:
            schemes: List of eligible schemes to format
            language: Target language for response
            
        Returns:
            Formatted response string
        """
        if not schemes:
            return self._format_with_template([], language)
        
        # Check cache first
        cache_key = self._generate_cache_key(schemes, language)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Try Sarvam AI first if available
        if self.sarvam_service.llm_available and settings.enable_llm_responses:
            try:
                response = await self.sarvam_service.generate_response(schemes, language)
                
                # Cache successful response
                self._cache_response(cache_key, response)
                
                logger.info(f"Generated LLM response for {len(schemes)} schemes in {language}")
                return response
                
            except Exception as e:
                logger.warning(f"Sarvam AI LLM failed, using fallback: {e}")
        
        # Fallback to template-based formatting
        fallback_response = self._format_with_template(schemes, language)
        
        # Cache fallback response too (shorter TTL could be implemented)
        self._cache_response(cache_key, fallback_response)
        
        logger.info(f"Generated fallback response for {len(schemes)} schemes in {language}")
        return fallback_response
    
    async def translate_response(self, text: str, target_language: str) -> str:
        """
        Translate response text to target language with caching.
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Translated text (or original if translation fails)
        """
        if target_language.lower() == "english" or target_language == "en":
            return text
        
        # Check translation cache first
        cached_translation = self._get_cached_translation(text, target_language)
        if cached_translation:
            logger.debug(f"Translation cache hit for {target_language}")
            return cached_translation
        
        # Map language names to codes
        language_codes = {
            "hindi": "hi",
            "tamil": "ta",
            "telugu": "te",
            "bengali": "bn"
        }
        
        target_code = language_codes.get(target_language.lower(), target_language)
        
        if self.sarvam_service.translation_available and settings.enable_translation:
            try:
                translated = await self.sarvam_service.translate_text(text, target_code)
                
                # Cache successful translation
                self._cache_translation(text, target_language, translated)
                
                logger.info(f"Translation successful: {target_language}")
                return translated
                
            except Exception as e:
                logger.warning(f"Translation failed, returning original text: {e}")
        
        return text
    
    def generate_scheme_explanation(self, scheme: SchemeModel, language: str = "english") -> str:
        """
        Generate explanation for a single scheme.
        
        Args:
            scheme: Scheme to explain
            language: Target language
            
        Returns:
            Scheme explanation text
        """
        template = self.fallback_templates.get(language, self.fallback_templates['english'])
        
        return template['scheme_format'].format(
            number=1,
            name=scheme.name,
            description=scheme.description,
            reason="Please check eligibility criteria",
            documents=', '.join(scheme.documents)
        )
    
    def clear_cache(self) -> Dict[str, int]:
        """
        Clear all caches.
        
        Returns:
            Dictionary with number of entries cleared from each cache
        """
        response_count = self.response_cache.clear()
        translation_count = self.translation_cache.clear()
        
        logger.info(f"Cleared {response_count} response cache entries and {translation_count} translation cache entries")
        
        return {
            'response_cache': response_count,
            'translation_cache': translation_count,
            'total': response_count + translation_count
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics and performance metrics
        """
        response_stats = self.response_cache.get_stats()
        translation_stats = self.translation_cache.get_stats()
        response_memory = self.response_cache.get_memory_usage()
        translation_memory = self.translation_cache.get_memory_usage()
        
        return {
            'response_cache': {
                'performance': response_stats,
                'memory': response_memory
            },
            'translation_cache': {
                'performance': translation_stats,
                'memory': translation_memory
            },
            'total_memory_bytes': response_memory['total_size_bytes'] + translation_memory['total_size_bytes'],
            'sarvam_ai_available': self.sarvam_service.llm_available,
            'cache_efficiency': {
                'overall_hit_rate': (response_stats['hits'] + translation_stats['hits']) / 
                                  max(1, response_stats['hits'] + response_stats['misses'] + 
                                      translation_stats['hits'] + translation_stats['misses']),
                'total_requests': response_stats['hits'] + response_stats['misses'] + 
                                translation_stats['hits'] + translation_stats['misses']
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of response service and dependencies.
        
        Returns:
            Dictionary with health status
        """
        sarvam_health = await self.sarvam_service.health_check()
        cache_stats = self.get_cache_stats()
        
        return {
            "response_service": "operational",
            "external_services": sarvam_health,
            "cache": cache_stats,
            "fallback_templates": len(self.fallback_templates),
            "supported_languages": list(self.fallback_templates.keys())
        }