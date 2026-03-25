# Implementation Plan: Databricks to FastAPI Refactor

## Overview

Convert the existing Databricks-based Indic Government Scheme Copilot into a standalone FastAPI application. This implementation maintains all existing functionality while being deployable outside Databricks using mock data and simplified dependencies.

## Tasks

- [x] 1. Set up FastAPI project structure and core dependencies
  - Create project directory structure with proper Python package organization
  - Create and activate Python virtual environment using `python -m venv venv`
  - Activate virtual environment (`source venv/bin/activate` on Unix or `venv\Scripts\activate` on Windows)
  - Install FastAPI, Pydantic, uvicorn, and other core dependencies using pip
  - Create requirements.txt file with all project dependencies
  - Create main.py with basic FastAPI application initialization
  - Add CORS middleware configuration for frontend integration
  - Implement health check endpoint at /health
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 1.1 Write property test for FastAPI server initialization
  - **Property 1: Server Initialization Completeness**
  - **Validates: Requirements 1.1, 1.5**

- [x] 2. Implement configuration management system
  - Create config.py with Pydantic Settings for environment-based configuration
  - Define configuration for server settings (host, port, debug mode)
  - Add configuration for external services (Sarvam AI API key, similarity thresholds)
  - Implement configuration validation on startup
  - Add support for .env file loading
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 2.1 Write property test for configuration consistency
  - **Property 2: Configuration Consistency**
  - **Validates: Requirements 1.2, 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 3. Create data models and schemas
  - Define Pydantic models for UserProfile, SchemeModel, EligibilityModel
  - Create API request/response models (EligibilityRequest, SearchRequest, SchemeResponse)
  - Implement EligibleScheme and SearchResult models with validation
  - Add ErrorResponse model with proper error codes
  - Define enum classes for categories and error types
  - _Requirements: 6.4, 8.1_

- [x] 4. Implement mock data layer and knowledge base service
  - Create data/schemes.json with 30+ government schemes from original Databricks data
  - Convert original scheme data structure to match new schema
  - Implement KnowledgeBaseService class for in-memory data management
  - Add methods for loading schemes, filtering by category/state, and scheme lookup
  - Include pre-computed mock embeddings for semantic search
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]* 4.1 Write property test for knowledge base filtering accuracy
  - **Property 5: Knowledge Base Filtering Accuracy**
  - **Validates: Requirements 2.2, 2.5**

- [ ]* 4.2 Write property test for scheme metadata completeness
  - **Property 6: Scheme Metadata Completeness**
  - **Validates: Requirements 2.3, 7.2, 7.3**

- [x] 5. Implement eligibility engine service
  - Create EligibilityService class based on original Databricks eligibility logic
  - Port age range parsing (18-25, 60+, All) and income limit parsing functions
  - Implement check_eligibility method with complex eligibility rules
  - Add calculate_match_score method for scheme ranking (0-100 scale)
  - Create generate_eligibility_reason method for human-readable explanations
  - Add get_recommendations method for partially matching schemes
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 5.1 Write property test for eligibility processing completeness
  - **Property 7: Eligibility Processing Completeness**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 6. Checkpoint - Ensure core services are working
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement mock vector search service
  - Create MockEmbeddingService using TF-IDF vectorization for query embeddings
  - Implement SearchService class with semantic_search method
  - Add cosine similarity calculation using scikit-learn
  - Create generate_query_embedding method for new search queries
  - Implement combined scoring that merges semantic similarity with eligibility matching
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 7.1 Write property test for semantic search consistency
  - **Property 4: Semantic Search Consistency**
  - **Validates: Requirements 4.1, 4.2, 4.3, 4.5**

- [ ]* 7.2 Write property test for combined search scoring
  - **Property 8: Combined Search Scoring**
  - **Validates: Requirements 4.4**

- [x] 8. Implement response formatting and translation service
  - Create ResponseService class based on original Databricks response formatter
  - Port format_output function with scheme explanation generation
  - Implement SarvamAIService integration for LLM-based response generation
  - Add translate_text method using Sarvam AI Translation API
  - Create fallback response templates for when external services fail
  - Add response caching mechanism for performance optimization
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 10.5_

- [ ]* 8.1 Write property test for response language consistency
  - **Property 9: Response Language Consistency**
  - **Validates: Requirements 5.2, 5.4**

- [ ]* 8.2 Write property test for fallback response reliability
  - **Property 10: Fallback Response Reliability**
  - **Validates: Requirements 5.5, 8.2**

- [ ]* 8.3 Write property test for response caching consistency
  - **Property 13: Response Caching Consistency**
  - **Validates: Requirements 10.5**

- [x] 9. Create REST API endpoints
  - Implement POST /api/eligibility endpoint for eligibility checking
  - Create POST /api/search endpoint for semantic search functionality
  - Add GET /api/schemes endpoint for browsing all schemes with filtering
  - Implement POST /api/format endpoint for response formatting and translation
  - Add proper HTTP status codes and error handling for all endpoints
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 9.1 Write property test for API response schema consistency
  - **Property 11: API Response Schema Consistency**
  - **Validates: Requirements 6.4, 6.5**

- [ ]* 9.2 Write property test for CORS header presence
  - **Property 3: CORS Header Presence**
  - **Validates: Requirements 1.3**

- [x] 10. Implement comprehensive error handling
  - Create custom exception classes for different error scenarios
  - Add global exception handlers for validation errors and HTTP exceptions
  - Implement graceful degradation for external service failures
  - Add proper logging for errors while protecting user privacy
  - Create timeout handling for external API calls
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 10.1 Write property test for input validation and error handling
  - **Property 12: Input Validation and Error Handling**
  - **Validates: Requirements 8.1, 8.4, 8.5**

- [x] 11. Optimize performance and add caching
  - Implement in-memory data structures for fast scheme lookups
  - Add vectorized similarity calculations using NumPy arrays
  - Create response caching with LRU eviction policy
  - Optimize concurrent request handling with async/await patterns
  - Add performance monitoring and metrics collection
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 12. Integration and wiring
  - Wire all services together in main FastAPI application
  - Connect API endpoints to service layer methods
  - Integrate external services (Sarvam AI) with proper error handling
  - Add startup event handlers for service initialization
  - Implement graceful shutdown procedures
  - _Requirements: 1.5, 6.1, 6.2, 6.3_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- **Virtual Environment**: Always use `python -m venv venv` to create virtual environments and activate before installing dependencies
- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of core functionality
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation maintains full compatibility with the original Databricks functionality
- All external dependencies are properly mocked for standalone operation
- Performance optimizations ensure sub-200ms response times for typical queries