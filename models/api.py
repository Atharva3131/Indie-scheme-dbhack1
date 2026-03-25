"""
API request and response models for the Government Scheme Copilot.

This module contains Pydantic models for API endpoints including
request validation and response formatting.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

from .core import UserProfile, EligibleScheme, SearchResult, SchemeCategoryEnum, StateEnum


class LanguageEnum(str, Enum):
    """Enumeration for supported languages."""
    ENGLISH = "english"
    HINDI = "hindi"


class EligibilityRequest(BaseModel):
    """
    Request model for eligibility checking endpoint.
    
    This model validates user profile data and language preferences
    for scheme eligibility assessment.
    """
    user_profile: UserProfile = Field(..., description="User demographic and preference data")
    language: LanguageEnum = Field(default=LanguageEnum.ENGLISH, description="Response language preference")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "user_profile": {
                    "age": 22,
                    "income": 400000,
                    "category": "General",
                    "occupation": "student",
                    "state": "Karnataka"
                },
                "language": "english"
            }
        }


class SearchRequest(BaseModel):
    """
    Request model for semantic search endpoint.
    
    This model validates search queries with optional user profile
    for combined semantic and eligibility matching.
    """
    query: str = Field(..., min_length=1, max_length=500, description="Search query text")
    user_profile: Optional[UserProfile] = Field(None, description="Optional user profile for eligibility filtering")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")
    language: LanguageEnum = Field(default=LanguageEnum.ENGLISH, description="Response language preference")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        if not v or v.isspace():
            raise ValueError('Search query cannot be empty or whitespace')
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "query": "student scholarship for engineering",
                "user_profile": {
                    "age": 22,
                    "income": 400000,
                    "category": "General",
                    "occupation": "student",
                    "state": "Karnataka"
                },
                "top_k": 5,
                "language": "english"
            }
        }


class SchemeFilterRequest(BaseModel):
    """
    Request model for scheme browsing with filters.
    
    This model validates filtering criteria for browsing
    all available schemes.
    """
    category: Optional[SchemeCategoryEnum] = Field(None, description="Filter by scheme category")
    state: Optional[StateEnum] = Field(None, description="Filter by state")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of schemes to return")
    offset: int = Field(default=0, ge=0, description="Number of schemes to skip for pagination")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "category": "education",
                "state": "Karnataka",
                "limit": 10,
                "offset": 0
            }
        }


class FormatRequest(BaseModel):
    """
    Request model for response formatting endpoint.
    
    This model validates scheme lists for formatting
    into user-friendly responses.
    """
    schemes: List[EligibleScheme] = Field(..., min_items=1, description="List of schemes to format")
    language: LanguageEnum = Field(default=LanguageEnum.ENGLISH, description="Target language for formatting")
    
    @validator('schemes')
    def validate_schemes(cls, v):
        """Validate schemes list."""
        if not v:
            raise ValueError('At least one scheme must be provided for formatting')
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class EligibilityResponse(BaseModel):
    """
    Response model for eligibility checking endpoint.
    
    This model provides structured results from eligibility
    assessment including eligible and recommended schemes.
    """
    status: str = Field(default="success", description="Response status")
    eligible_schemes: List[EligibleScheme] = Field(..., description="Schemes user is eligible for")
    recommended_schemes: List[EligibleScheme] = Field(..., description="Partially matching schemes")
    user_profile: UserProfile = Field(..., description="Processed user profile")
    total_eligible: int = Field(..., ge=0, description="Total number of eligible schemes")
    total_recommended: int = Field(..., ge=0, description="Total number of recommended schemes")
    language: str = Field(..., description="Response language")
    
    @validator('total_eligible')
    def validate_total_eligible(cls, v, values):
        """Validate total eligible count matches list length."""
        if 'eligible_schemes' in values and len(values['eligible_schemes']) != v:
            raise ValueError('Total eligible count must match eligible schemes list length')
        return v
    
    @validator('total_recommended')
    def validate_total_recommended(cls, v, values):
        """Validate total recommended count matches list length."""
        if 'recommended_schemes' in values and len(values['recommended_schemes']) != v:
            raise ValueError('Total recommended count must match recommended schemes list length')
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "eligible_schemes": [],
                "recommended_schemes": [],
                "user_profile": {
                    "age": 22,
                    "income": 400000,
                    "category": "General",
                    "occupation": "student",
                    "state": "Karnataka"
                },
                "total_eligible": 0,
                "total_recommended": 0,
                "language": "english"
            }
        }


class SearchResponse(BaseModel):
    """
    Response model for semantic search endpoint.
    
    This model provides structured search results with
    similarity scores and metadata.
    """
    status: str = Field(default="success", description="Response status")
    results: List[SearchResult] = Field(..., description="Search results with similarity scores")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., ge=0, description="Total number of results returned")
    similarity_threshold: float = Field(..., ge=0, le=1, description="Minimum similarity threshold used")
    language: str = Field(..., description="Response language")
    
    @validator('total_results')
    def validate_total_results(cls, v, values):
        """Validate total results count matches list length."""
        if 'results' in values and len(values['results']) != v:
            raise ValueError('Total results count must match results list length')
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "results": [],
                "query": "student scholarship",
                "total_results": 0,
                "similarity_threshold": 0.3,
                "language": "english"
            }
        }


class SchemeResponse(BaseModel):
    """
    Response model for scheme browsing endpoint.
    
    This model provides structured scheme listings with
    filtering and pagination metadata.
    """
    status: str = Field(default="success", description="Response status")
    schemes: List[EligibleScheme] = Field(..., description="List of schemes")
    total_count: int = Field(..., ge=0, description="Total number of schemes returned")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filter criteria")
    pagination: Dict[str, int] = Field(..., description="Pagination information")
    
    @validator('total_count')
    def validate_total_count(cls, v, values):
        """Validate total count matches schemes list length."""
        if 'schemes' in values and len(values['schemes']) != v:
            raise ValueError('Total count must match schemes list length')
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "schemes": [],
                "total_count": 0,
                "filters_applied": {
                    "category": "education",
                    "state": "Karnataka"
                },
                "pagination": {
                    "limit": 10,
                    "offset": 0,
                    "has_more": False
                }
            }
        }


class FormatResponse(BaseModel):
    """
    Response model for response formatting endpoint.
    
    This model provides formatted, user-friendly scheme
    descriptions in the requested language.
    """
    status: str = Field(default="success", description="Response status")
    formatted_response: str = Field(..., description="User-friendly formatted response")
    language: str = Field(..., description="Response language")
    scheme_count: int = Field(..., ge=0, description="Number of schemes formatted")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "formatted_response": "Based on your profile, here are the government schemes you're eligible for...",
                "language": "english",
                "scheme_count": 3
            }
        }


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    This model provides system health status and metadata.
    """
    status: str = Field(default="healthy", description="System health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field(default="1.0.0", description="Application version")
    services: Dict[str, str] = Field(default_factory=dict, description="Service status information")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "services": {
                    "knowledge_base": "operational",
                    "eligibility_engine": "operational",
                    "search_service": "operational"
                }
            }
        }