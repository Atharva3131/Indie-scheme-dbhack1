"""
Core data models for the Government Scheme Copilot.

This module contains the fundamental Pydantic models for user profiles,
scheme data, and eligibility criteria.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class CategoryEnum(str, Enum):
    """Enumeration for user categories."""
    GENERAL = "General"
    OBC = "OBC"
    SC = "SC"
    ST = "ST"
    MINORITY = "Minority"


class StateEnum(str, Enum):
    """Enumeration for Indian states."""
    KARNATAKA = "Karnataka"
    CENTRAL = "Central"
    ANDHRA_PRADESH = "Andhra Pradesh"
    TAMIL_NADU = "Tamil Nadu"
    TELANGANA = "Telangana"
    KERALA = "Kerala"
    MAHARASHTRA = "Maharashtra"
    GUJARAT = "Gujarat"
    RAJASTHAN = "Rajasthan"
    UTTAR_PRADESH = "Uttar Pradesh"
    WEST_BENGAL = "West Bengal"
    BIHAR = "Bihar"
    ODISHA = "Odisha"
    MADHYA_PRADESH = "Madhya Pradesh"
    PUNJAB = "Punjab"
    HARYANA = "Haryana"
    JHARKHAND = "Jharkhand"
    CHHATTISGARH = "Chhattisgarh"
    ASSAM = "Assam"
    HIMACHAL_PRADESH = "Himachal Pradesh"
    UTTARAKHAND = "Uttarakhand"
    GOA = "Goa"
    MANIPUR = "Manipur"
    MEGHALAYA = "Meghalaya"
    TRIPURA = "Tripura"
    NAGALAND = "Nagaland"
    MIZORAM = "Mizoram"
    ARUNACHAL_PRADESH = "Arunachal Pradesh"
    SIKKIM = "Sikkim"


class SchemeCategoryEnum(str, Enum):
    """Enumeration for scheme categories."""
    EDUCATION = "education"
    HEALTH = "health"
    AGRICULTURE = "agriculture"
    HOUSING = "housing"
    EMPLOYMENT = "employment"
    SOCIAL_WELFARE = "social_welfare"
    WOMEN_EMPOWERMENT = "women_empowerment"
    SKILL_DEVELOPMENT = "skill_development"
    FINANCIAL_INCLUSION = "financial_inclusion"
    RURAL_DEVELOPMENT = "rural_development"


class UserProfile(BaseModel):
    """
    User profile model containing demographic and preference information.
    
    This model represents a user's profile for scheme eligibility checking.
    All fields are validated for proper ranges and formats.
    """
    age: int = Field(..., ge=0, le=120, description="User's age in years")
    income: float = Field(..., ge=0, description="Annual income in INR")
    category: CategoryEnum = Field(..., description="Social category")
    occupation: str = Field(..., min_length=1, max_length=100, description="User's occupation")
    state: StateEnum = Field(default=StateEnum.KARNATAKA, description="State of residence")
    
    @validator('occupation')
    def validate_occupation(cls, v):
        """Validate occupation field."""
        if not v or v.isspace():
            raise ValueError('Occupation cannot be empty or whitespace')
        return v.strip().lower()
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "age": 22,
                "income": 400000,
                "category": "General",
                "occupation": "student",
                "state": "Karnataka"
            }
        }


class EligibilityModel(BaseModel):
    """
    Eligibility criteria model for government schemes.
    
    This model defines the eligibility requirements for a scheme,
    including age ranges, income limits, and other criteria.
    """
    age: str = Field(..., description="Age criteria (e.g., '18-25', '60+', 'All')")
    income: str = Field(..., description="Income criteria (e.g., '< 5 lakh', 'BPL families', 'All')")
    category: str = Field(..., description="Category criteria (e.g., 'SC/ST', 'All', 'Women')")
    occupation: str = Field(..., description="Occupation criteria (e.g., 'farmer', 'student', 'All')")
    
    @validator('age', 'income', 'category', 'occupation')
    def validate_non_empty(cls, v):
        """Validate that criteria fields are not empty."""
        if not v or v.isspace():
            raise ValueError('Eligibility criteria cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "age": "18-25",
                "income": "< 6 lakh",
                "category": "All",
                "occupation": "student"
            }
        }


class SchemeModel(BaseModel):
    """
    Government scheme model containing all scheme information.
    
    This model represents a complete government scheme with all
    metadata, eligibility criteria, and search embeddings.
    """
    id: str = Field(..., min_length=1, description="Unique scheme identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Scheme name")
    description: str = Field(..., min_length=1, description="Detailed scheme description")
    eligibility: EligibilityModel = Field(..., description="Eligibility criteria")
    documents: List[str] = Field(..., min_items=1, description="Required documents list")
    state: StateEnum = Field(..., description="Applicable state or Central")
    category: SchemeCategoryEnum = Field(..., description="Scheme category")
    keywords: str = Field(..., description="Search keywords for the scheme")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    
    @validator('documents')
    def validate_documents(cls, v):
        """Validate documents list."""
        if not v:
            raise ValueError('At least one document must be required')
        # Remove empty strings and duplicates
        cleaned = list(dict.fromkeys([doc.strip() for doc in v if doc and not doc.isspace()]))
        if not cleaned:
            raise ValueError('Documents list cannot contain only empty values')
        return cleaned
    
    @validator('embedding')
    def validate_embedding(cls, v):
        """Validate embedding dimensions."""
        if v is not None:
            if len(v) != 384:  # Expected embedding dimension
                raise ValueError('Embedding must have exactly 384 dimensions')
            if not all(isinstance(x, (int, float)) for x in v):
                raise ValueError('Embedding values must be numeric')
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "pm-scholarship-001",
                "name": "PM Scholarship Scheme",
                "description": "Financial assistance for students pursuing higher education",
                "eligibility": {
                    "age": "18-25",
                    "income": "< 6 lakh",
                    "category": "All",
                    "occupation": "student"
                },
                "documents": ["Aadhaar", "Income Certificate", "Marksheet"],
                "state": "Central",
                "category": "education",
                "keywords": "student scholarship education higher"
            }
        }


class EligibleScheme(BaseModel):
    """
    Model representing a scheme with eligibility assessment results.
    
    This model combines scheme information with eligibility matching
    results and explanations.
    """
    scheme: SchemeModel = Field(..., description="The government scheme")
    match_score: float = Field(..., ge=0, le=100, description="Eligibility match score (0-100)")
    eligibility_reason: str = Field(..., description="Human-readable eligibility explanation")
    is_eligible: bool = Field(..., description="Whether user is eligible for this scheme")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "scheme": {
                    "id": "pm-scholarship-001",
                    "name": "PM Scholarship Scheme",
                    "description": "Financial assistance for students",
                    "eligibility": {
                        "age": "18-25",
                        "income": "< 6 lakh",
                        "category": "All",
                        "occupation": "student"
                    },
                    "documents": ["Aadhaar", "Income Certificate"],
                    "state": "Central",
                    "category": "education",
                    "keywords": "student scholarship"
                },
                "match_score": 95.0,
                "eligibility_reason": "You meet all eligibility criteria: age 22 is within 18-25 range, income ₹4,00,000 is below ₹6 lakh limit, and you are a student.",
                "is_eligible": True
            }
        }


class SearchResult(BaseModel):
    """
    Model representing a search result with similarity scoring.
    
    This model combines scheme information with semantic search
    similarity scores and optional combined scoring.
    """
    scheme: SchemeModel = Field(..., description="The government scheme")
    similarity_score: float = Field(..., ge=0, le=1, description="Semantic similarity score (0-1)")
    combined_score: Optional[float] = Field(None, ge=0, le=100, description="Combined similarity and eligibility score")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "scheme": {
                    "id": "pm-scholarship-001",
                    "name": "PM Scholarship Scheme",
                    "description": "Financial assistance for students",
                    "eligibility": {
                        "age": "18-25",
                        "income": "< 6 lakh",
                        "category": "All",
                        "occupation": "student"
                    },
                    "documents": ["Aadhaar", "Income Certificate"],
                    "state": "Central",
                    "category": "education",
                    "keywords": "student scholarship"
                },
                "similarity_score": 0.85,
                "combined_score": 92.5
            }
        }