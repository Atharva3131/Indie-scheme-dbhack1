# Requirements Document

## Introduction

Convert the existing Databricks-based Indic Government Scheme Copilot project into a standalone, runnable FastAPI application. The system should maintain all existing functionality while being deployable outside of the Databricks environment using mock data and simplified dependencies.

## Glossary

- **FastAPI_Server**: The main web server application built with FastAPI framework
- **Knowledge_Base**: In-memory data structure containing government scheme information
- **Eligibility_Engine**: Component that matches user profiles against scheme eligibility criteria
- **Response_Formatter**: Component that generates user-friendly responses in multiple languages
- **Mock_Data**: Simplified dataset replacing Databricks Delta Lake storage
- **Vector_Search**: Semantic similarity search functionality for scheme matching
- **User_Profile**: Data structure containing user demographic and preference information

## Requirements

### Requirement 1: FastAPI Server Setup

**User Story:** As a developer, I want to set up a FastAPI server, so that I can serve the government scheme copilot functionality via REST APIs.

#### Acceptance Criteria

1. THE FastAPI_Server SHALL initialize with all required dependencies
2. THE FastAPI_Server SHALL serve on configurable host and port
3. THE FastAPI_Server SHALL include CORS middleware for frontend integration
4. THE FastAPI_Server SHALL provide health check endpoint
5. THE FastAPI_Server SHALL handle graceful startup and shutdown

### Requirement 2: Knowledge Base Integration

**User Story:** As a system administrator, I want to load government scheme data, so that the application can provide scheme information without external dependencies.

#### Acceptance Criteria

1. THE Knowledge_Base SHALL load 30+ curated government schemes from Mock_Data
2. THE Knowledge_Base SHALL support semantic search using vector embeddings
3. THE Knowledge_Base SHALL maintain scheme metadata including eligibility criteria and documents
4. THE Knowledge_Base SHALL provide fast in-memory access to scheme information
5. THE Knowledge_Base SHALL support filtering by category, state, and eligibility criteria

### Requirement 3: Eligibility Matching API

**User Story:** As a user, I want to check my eligibility for government schemes, so that I can find relevant programs based on my profile.

#### Acceptance Criteria

1. WHEN a user profile is provided, THE Eligibility_Engine SHALL parse age, income, category, occupation, and state
2. THE Eligibility_Engine SHALL calculate match scores based on eligibility criteria
3. THE Eligibility_Engine SHALL return eligible schemes with eligibility reasons
4. THE Eligibility_Engine SHALL support complex eligibility rules including age ranges and income limits
5. THE Eligibility_Engine SHALL provide recommendation scores for partially matching schemes

### Requirement 4: Semantic Search API

**User Story:** As a user, I want to search for schemes using natural language, so that I can find relevant programs without knowing exact scheme names.

#### Acceptance Criteria

1. WHEN a search query is provided, THE Vector_Search SHALL generate query embeddings
2. THE Vector_Search SHALL calculate cosine similarity with scheme embeddings
3. THE Vector_Search SHALL return top-K most relevant schemes above similarity threshold
4. THE Vector_Search SHALL combine semantic similarity with eligibility matching when user profile is provided
5. THE Vector_Search SHALL support configurable similarity thresholds and result limits

### Requirement 5: Response Formatting and Translation

**User Story:** As a user, I want to receive scheme information in my preferred language, so that I can understand the benefits and requirements clearly.

#### Acceptance Criteria

1. THE Response_Formatter SHALL generate user-friendly explanations of scheme benefits
2. THE Response_Formatter SHALL support English and Hindi language output
3. THE Response_Formatter SHALL format eligibility criteria in simple, understandable terms
4. THE Response_Formatter SHALL list required documents clearly
5. THE Response_Formatter SHALL provide fallback responses when external translation services fail

### Requirement 6: Frontend Integration Support

**User Story:** As a frontend developer, I want REST API endpoints, so that I can integrate the scheme copilot with web and mobile applications.

#### Acceptance Criteria

1. THE FastAPI_Server SHALL provide POST /api/eligibility endpoint for eligibility checking
2. THE FastAPI_Server SHALL provide POST /api/search endpoint for semantic search
3. THE FastAPI_Server SHALL provide GET /api/schemes endpoint for browsing all schemes
4. THE FastAPI_Server SHALL return JSON responses with consistent schema
5. THE FastAPI_Server SHALL include proper HTTP status codes and error handling

### Requirement 7: Mock Data Implementation

**User Story:** As a developer, I want to use mock data, so that the application runs without external database dependencies.

#### Acceptance Criteria

1. THE Mock_Data SHALL include Central and Karnataka government schemes
2. THE Mock_Data SHALL maintain the same schema as the original Databricks implementation
3. THE Mock_Data SHALL include pre-computed embeddings for semantic search
4. THE Mock_Data SHALL support all existing scheme categories (education, health, agriculture, etc.)
5. THE Mock_Data SHALL be easily replaceable with real database connections in production

### Requirement 8: Error Handling and Resilience

**User Story:** As a user, I want the system to handle errors gracefully, so that I receive helpful feedback when something goes wrong.

#### Acceptance Criteria

1. WHEN invalid input is provided, THE FastAPI_Server SHALL return descriptive error messages
2. WHEN external services fail, THE FastAPI_Server SHALL provide fallback responses
3. THE FastAPI_Server SHALL log errors for debugging while protecting user privacy
4. THE FastAPI_Server SHALL validate input parameters and return 400 status for invalid requests
5. THE FastAPI_Server SHALL handle timeout scenarios gracefully

### Requirement 9: Configuration Management

**User Story:** As a system administrator, I want configurable settings, so that I can customize the application behavior for different environments.

#### Acceptance Criteria

1. THE FastAPI_Server SHALL support environment-based configuration
2. THE FastAPI_Server SHALL allow configuration of similarity thresholds and result limits
3. THE FastAPI_Server SHALL support configurable language settings
4. THE FastAPI_Server SHALL allow enabling/disabling of external service integrations
5. THE FastAPI_Server SHALL provide configuration validation on startup

### Requirement 10: Performance Optimization

**User Story:** As a user, I want fast response times, so that I can quickly find relevant government schemes.

#### Acceptance Criteria

1. THE Vector_Search SHALL complete similarity calculations within 200ms for typical queries
2. THE Eligibility_Engine SHALL process user profiles within 100ms
3. THE FastAPI_Server SHALL support concurrent requests efficiently
4. THE Knowledge_Base SHALL use optimized data structures for fast lookups
5. THE Response_Formatter SHALL cache common responses to reduce processing time