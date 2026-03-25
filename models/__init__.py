"""
Data models package for Government Scheme Copilot.

This package contains Pydantic models for:
- User profiles and scheme data
- API request/response models
- Error handling models
- Configuration models
"""

# Core data models
from .core import (
    CategoryEnum,
    StateEnum,
    SchemeCategoryEnum,
    UserProfile,
    EligibilityModel,
    SchemeModel,
    EligibleScheme,
    SearchResult,
)

# API request/response models
from .api import (
    LanguageEnum,
    EligibilityRequest,
    SearchRequest,
    SchemeFilterRequest,
    FormatRequest,
    EligibilityResponse,
    SearchResponse,
    SchemeResponse,
    FormatResponse,
    HealthResponse,
)

# Error handling models
from .errors import (
    ErrorCode,
    ErrorSeverity,
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    ExternalServiceErrorResponse,
    RateLimitErrorResponse,
    ERROR_CODE_STATUS_MAP,
    get_http_status_code,
)

__all__ = [
    # Core models
    "CategoryEnum",
    "StateEnum", 
    "SchemeCategoryEnum",
    "UserProfile",
    "EligibilityModel",
    "SchemeModel",
    "EligibleScheme",
    "SearchResult",
    
    # API models
    "LanguageEnum",
    "EligibilityRequest",
    "SearchRequest",
    "SchemeFilterRequest",
    "FormatRequest",
    "EligibilityResponse",
    "SearchResponse",
    "SchemeResponse",
    "FormatResponse",
    "HealthResponse",
    
    # Error models
    "ErrorCode",
    "ErrorSeverity",
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "ExternalServiceErrorResponse",
    "RateLimitErrorResponse",
    "ERROR_CODE_STATUS_MAP",
    "get_http_status_code",
]