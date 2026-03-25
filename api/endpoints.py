"""
REST API endpoints for Government Scheme Copilot.

This module implements all the REST API endpoints including eligibility checking,
semantic search, scheme browsing, and response formatting with proper error handling
and HTTP status codes.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from models.api import (
    EligibilityRequest, EligibilityResponse,
    SearchRequest, SearchResponse,
    SchemeFilterRequest, SchemeResponse,
    FormatRequest, FormatResponse,
    LanguageEnum
)
from models.core import EligibleScheme, SearchResult, SchemeCategoryEnum, StateEnum
from models.errors import ErrorResponse, ErrorCode
from services.knowledge_base import KnowledgeBaseService
from services.eligibility import EligibilityService
from services.search import SearchService
from services.response import ResponseService
from config import settings

logger = logging.getLogger(__name__)

# Initialize services
knowledge_base = KnowledgeBaseService()
eligibility_service = EligibilityService()
search_service = SearchService(knowledge_base, eligibility_service)
response_service = ResponseService()

# Create API router
router = APIRouter(prefix=settings.api_prefix, tags=["Government Schemes"])


@router.post("/eligibility", response_model=EligibilityResponse)
async def check_eligibility(request: EligibilityRequest) -> EligibilityResponse:
    """
    Check user eligibility for government schemes.
    
    This endpoint evaluates a user profile against all available schemes,
    returning eligible schemes and recommendations with match scores and
    human-readable eligibility explanations.
    
    Args:
        request: User profile and language preferences
        
    Returns:
        EligibilityResponse with eligible and recommended schemes
        
    Raises:
        HTTPException: 400 for validation errors, 500 for internal errors
    """
    try:
        logger.info(f"Processing eligibility check for user: age={request.user_profile.age}, "
                   f"income={request.user_profile.income}, category={request.user_profile.category}")
        
        # Get all schemes from knowledge base
        all_schemes = knowledge_base.get_all_schemes()
        if not all_schemes:
            raise HTTPException(
                status_code=503,
                detail="Knowledge base is empty - no schemes available"
            )
        
        # Check eligibility for all schemes
        eligibility_results = eligibility_service.check_eligibility(
            request.user_profile, all_schemes
        )
        
        # Separate eligible and recommended schemes
        eligible_schemes = [result for result in eligibility_results if result.is_eligible]
        recommended_schemes = [
            result for result in eligibility_results 
            if not result.is_eligible and result.match_score >= 25.0
        ]
        
        # Limit results to prevent overwhelming responses
        max_eligible = settings.max_search_results
        max_recommended = max(5, settings.max_search_results // 2)
        
        eligible_schemes = eligible_schemes[:max_eligible]
        recommended_schemes = recommended_schemes[:max_recommended]
        
        logger.info(f"Eligibility check completed: {len(eligible_schemes)} eligible, "
                   f"{len(recommended_schemes)} recommended")
        
        return EligibilityResponse(
            eligible_schemes=eligible_schemes,
            recommended_schemes=recommended_schemes,
            user_profile=request.user_profile,
            total_eligible=len(eligible_schemes),
            total_recommended=len(recommended_schemes),
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Eligibility check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during eligibility check: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_schemes(request: SearchRequest) -> SearchResponse:
    """
    Perform semantic search for government schemes.
    
    This endpoint provides semantic search using TF-IDF embeddings and cosine
    similarity. When a user profile is provided, it combines semantic similarity
    with eligibility matching for better results.
    
    Args:
        request: Search query, optional user profile, and preferences
        
    Returns:
        SearchResponse with ranked search results
        
    Raises:
        HTTPException: 400 for validation errors, 500 for internal errors
    """
    try:
        logger.info(f"Processing search query: '{request.query}' with user_profile={bool(request.user_profile)}")
        
        # Perform semantic search
        search_results = search_service.semantic_search(
            query=request.query,
            user_profile=request.user_profile,
            top_k=request.top_k,
            similarity_threshold=settings.similarity_threshold
        )
        
        logger.info(f"Search completed: {len(search_results)} results found")
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total_results=len(search_results),
            similarity_threshold=settings.similarity_threshold,
            language=request.language
        )
        
    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during search: {str(e)}"
        )


@router.get("/schemes", response_model=SchemeResponse)
async def get_schemes(
    category: Optional[SchemeCategoryEnum] = Query(None, description="Filter by scheme category"),
    state: Optional[StateEnum] = Query(None, description="Filter by state"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of schemes to return"),
    offset: int = Query(0, ge=0, description="Number of schemes to skip for pagination")
) -> SchemeResponse:
    """
    Browse all available government schemes with filtering and pagination.
    
    This endpoint provides access to all schemes in the knowledge base with
    optional filtering by category and state, plus pagination support.
    
    Args:
        category: Optional scheme category filter
        state: Optional state filter  
        limit: Maximum number of schemes to return (1-50)
        offset: Number of schemes to skip for pagination
        
    Returns:
        SchemeResponse with filtered schemes and pagination info
        
    Raises:
        HTTPException: 400 for validation errors, 500 for internal errors
    """
    try:
        logger.info(f"Browsing schemes: category={category}, state={state}, limit={limit}, offset={offset}")
        
        # Apply filters
        filtered_schemes = knowledge_base.filter_schemes(
            category=category if category else None,
            state=state if state else None
        )
        
        # Apply pagination
        total_filtered = len(filtered_schemes)
        paginated_schemes = filtered_schemes[offset:offset + limit]
        
        # Convert to EligibleScheme format (without eligibility assessment)
        scheme_results = []
        for scheme in paginated_schemes:
            eligible_scheme = EligibleScheme(
                scheme=scheme,
                match_score=100.0,  # No scoring for browsing
                eligibility_reason="Eligibility assessment not performed for browsing",
                is_eligible=False  # Not assessed
            )
            scheme_results.append(eligible_scheme)
        
        # Prepare filter metadata
        filters_applied = {}
        if category:
            filters_applied["category"] = category
        if state:
            filters_applied["state"] = state
        
        # Pagination metadata
        pagination = {
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_filtered,
            "total_available": total_filtered
        }
        
        logger.info(f"Schemes browsing completed: {len(scheme_results)} schemes returned, "
                   f"{total_filtered} total available")
        
        return SchemeResponse(
            schemes=scheme_results,
            total_count=len(scheme_results),
            filters_applied=filters_applied,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Scheme browsing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during scheme browsing: {str(e)}"
        )


@router.post("/format", response_model=FormatResponse)
async def format_response(request: FormatRequest) -> FormatResponse:
    """
    Format schemes into user-friendly response with translation support.
    
    This endpoint takes a list of schemes and formats them into a natural
    language response in the requested language, using Sarvam AI for LLM
    generation and translation with fallback templates.
    
    Args:
        request: List of schemes to format and target language
        
    Returns:
        FormatResponse with formatted text in requested language
        
    Raises:
        HTTPException: 400 for validation errors, 500 for internal errors
    """
    try:
        logger.info(f"Formatting {len(request.schemes)} schemes in {request.language}")
        
        # Format schemes using response service
        formatted_text = await response_service.format_schemes(
            schemes=request.schemes,
            language=request.language
        )
        
        logger.info(f"Response formatting completed for {len(request.schemes)} schemes")
        
        return FormatResponse(
            formatted_response=formatted_text,
            language=request.language,
            scheme_count=len(request.schemes)
        )
        
    except Exception as e:
        logger.error(f"Response formatting failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during response formatting: {str(e)}"
        )


@router.get("/schemes/{scheme_id}")
async def get_scheme_details(scheme_id: str):
    """
    Get detailed information for a specific scheme.
    
    Args:
        scheme_id: Unique identifier of the scheme
        
    Returns:
        Detailed scheme information
        
    Raises:
        HTTPException: 404 if scheme not found, 500 for internal errors
    """
    try:
        scheme = knowledge_base.get_scheme_by_id(scheme_id)
        if not scheme:
            raise HTTPException(
                status_code=404,
                detail=f"Scheme with ID '{scheme_id}' not found"
            )
        
        return {
            "status": "success",
            "scheme": scheme,
            "similar_schemes": search_service.get_similar_schemes(scheme_id, top_k=3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scheme details for {scheme_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/categories")
async def get_categories():
    """
    Get all available scheme categories.
    
    Returns:
        List of available categories with counts
    """
    try:
        stats = knowledge_base.get_statistics()
        categories = [
            {
                "category": category,
                "count": count,
                "display_name": category.replace('_', ' ').title()
            }
            for category, count in stats['category_distribution'].items()
        ]
        
        return {
            "status": "success",
            "categories": categories,
            "total_categories": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/states")
async def get_states():
    """
    Get all available states.
    
    Returns:
        List of available states with scheme counts
    """
    try:
        stats = knowledge_base.get_statistics()
        states = [
            {
                "state": state,
                "count": count
            }
            for state, count in stats['state_distribution'].items()
        ]
        
        return {
            "status": "success",
            "states": states,
            "total_states": len(states)
        }
        
    except Exception as e:
        logger.error(f"Failed to get states: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/statistics")
async def get_statistics():
    """
    Get knowledge base and service statistics.
    
    Returns:
        Comprehensive statistics about the system
    """
    try:
        kb_stats = knowledge_base.get_statistics()
        search_stats = search_service.get_search_statistics()
        cache_stats = response_service.get_cache_stats()
        
        return {
            "status": "success",
            "knowledge_base": kb_stats,
            "search_service": search_stats,
            "response_cache": cache_stats,
            "configuration": {
                "similarity_threshold": settings.similarity_threshold,
                "max_results": settings.max_search_results,
                "supported_languages": [lang.value for lang in settings.supported_languages]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Error handlers for the router
# Note: Exception handlers should be added to the main FastAPI app, not the router