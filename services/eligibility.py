"""
Eligibility Engine Service for Government Scheme Copilot.

This module implements the core eligibility matching logic, porting the original
Databricks eligibility engine to work with the FastAPI application.
"""

import re
from typing import List, Optional, Tuple
from models.core import UserProfile, SchemeModel, EligibleScheme, EligibilityModel


class EligibilityService:
    """
    Service for matching user profiles against scheme eligibility criteria.
    
    This service implements complex eligibility rules including age range parsing,
    income limit parsing, category matching, and occupation matching. It provides
    match scoring and human-readable explanations for eligibility decisions.
    """
    
    def __init__(self):
        """Initialize the eligibility service."""
        self.age_patterns = {
            'range': re.compile(r'(\d+)-(\d+)'),  # e.g., "18-25"
            'above': re.compile(r'(\d+)\+'),      # e.g., "60+"
            'below': re.compile(r'<\s*(\d+)'),    # e.g., "< 18"
            'exact': re.compile(r'^(\d+)$')       # e.g., "18"
        }
        
        self.income_patterns = {
            'below_lakh': re.compile(r'<\s*(\d+(?:\.\d+)?)\s*lakh', re.IGNORECASE),  # e.g., "< 5 lakh"
            'below_amount': re.compile(r'<\s*₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', re.IGNORECASE),  # e.g., "< ₹5,00,000"
            'bpl': re.compile(r'bpl|below\s+poverty\s+line', re.IGNORECASE),
            'apl': re.compile(r'apl|above\s+poverty\s+line', re.IGNORECASE)
        }
    
    def parse_age_criteria(self, age_criteria: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse age criteria string into min and max age values.
        
        Args:
            age_criteria: Age criteria string (e.g., "18-25", "60+", "All")
            
        Returns:
            Tuple of (min_age, max_age). None values indicate no limit.
        """
        age_criteria = age_criteria.strip()
        
        if age_criteria.lower() in ['all', 'any', 'no limit']:
            return None, None
        
        # Check for range pattern (18-25)
        range_match = self.age_patterns['range'].search(age_criteria)
        if range_match:
            min_age = int(range_match.group(1))
            max_age = int(range_match.group(2))
            return min_age, max_age
        
        # Check for above pattern (60+)
        above_match = self.age_patterns['above'].search(age_criteria)
        if above_match:
            min_age = int(above_match.group(1))
            return min_age, None
        
        # Check for below pattern (< 18)
        below_match = self.age_patterns['below'].search(age_criteria)
        if below_match:
            max_age = int(below_match.group(1)) - 1  # Exclusive upper bound
            return None, max_age
        
        # Check for exact age
        exact_match = self.age_patterns['exact'].search(age_criteria)
        if exact_match:
            age = int(exact_match.group(1))
            return age, age
        
        # Default to no restrictions if pattern not recognized
        return None, None
    
    def parse_income_criteria(self, income_criteria: str) -> Optional[float]:
        """
        Parse income criteria string into maximum income value in INR.
        
        Args:
            income_criteria: Income criteria string (e.g., "< 5 lakh", "BPL families")
            
        Returns:
            Maximum income in INR, or None if no limit
        """
        income_criteria = income_criteria.strip()
        
        if income_criteria.lower() in ['all', 'any', 'no limit']:
            return None
        
        # Check for BPL (Below Poverty Line) - typically around ₹1.5 lakh rural, ₹2 lakh urban
        if self.income_patterns['bpl'].search(income_criteria):
            return 150000  # Conservative BPL threshold
        
        # Check for APL (Above Poverty Line) - no upper limit
        if self.income_patterns['apl'].search(income_criteria):
            return None
        
        # Check for lakh format (< 5 lakh)
        lakh_match = self.income_patterns['below_lakh'].search(income_criteria)
        if lakh_match:
            lakhs = float(lakh_match.group(1))
            return lakhs * 100000  # Convert lakhs to INR
        
        # Check for direct amount format (< ₹5,00,000)
        amount_match = self.income_patterns['below_amount'].search(income_criteria)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            return float(amount_str)
        
        # Default to no limit if pattern not recognized
        return None
    
    def check_age_eligibility(self, user_age: int, age_criteria: str) -> Tuple[bool, str]:
        """
        Check if user age meets the scheme's age criteria.
        
        Args:
            user_age: User's age in years
            age_criteria: Scheme's age criteria string
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        min_age, max_age = self.parse_age_criteria(age_criteria)
        
        if min_age is None and max_age is None:
            return True, f"age {user_age} meets criteria (no age restrictions)"
        
        if min_age is not None and user_age < min_age:
            return False, f"age {user_age} is below minimum age {min_age}"
        
        if max_age is not None and user_age > max_age:
            return False, f"age {user_age} is above maximum age {max_age}"
        
        # Construct positive reason
        if min_age is not None and max_age is not None:
            return True, f"age {user_age} is within {min_age}-{max_age} range"
        elif min_age is not None:
            return True, f"age {user_age} is above minimum age {min_age}"
        else:
            return True, f"age {user_age} is below maximum age {max_age}"
    
    def check_income_eligibility(self, user_income: float, income_criteria: str) -> Tuple[bool, str]:
        """
        Check if user income meets the scheme's income criteria.
        
        Args:
            user_income: User's annual income in INR
            income_criteria: Scheme's income criteria string
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        max_income = self.parse_income_criteria(income_criteria)
        
        if max_income is None:
            return True, f"income ₹{user_income:,.0f} meets criteria (no income restrictions)"
        
        if user_income <= max_income:
            return True, f"income ₹{user_income:,.0f} is below ₹{max_income:,.0f} limit"
        else:
            return False, f"income ₹{user_income:,.0f} exceeds ₹{max_income:,.0f} limit"
    
    def check_category_eligibility(self, user_category: str, category_criteria: str) -> Tuple[bool, str]:
        """
        Check if user category meets the scheme's category criteria.
        
        Args:
            user_category: User's social category
            category_criteria: Scheme's category criteria string
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        category_criteria = category_criteria.strip().lower()
        user_category = user_category.strip().lower()
        
        if category_criteria in ['all', 'any', 'general']:
            return True, f"category {user_category} meets criteria (open to all categories)"
        
        # Check for specific category matches
        criteria_categories = [cat.strip().lower() for cat in category_criteria.replace('/', ',').split(',')]
        
        if user_category in criteria_categories:
            return True, f"category {user_category} matches required categories"
        
        # Check for special patterns
        if 'sc/st' in category_criteria and user_category in ['sc', 'st']:
            return True, f"category {user_category} matches SC/ST criteria"
        
        if 'minority' in category_criteria and user_category == 'minority':
            return True, f"category {user_category} matches minority criteria"
        
        return False, f"category {user_category} does not match required categories: {category_criteria}"
    
    def check_occupation_eligibility(self, user_occupation: str, occupation_criteria: str) -> Tuple[bool, str]:
        """
        Check if user occupation meets the scheme's occupation criteria.
        
        Args:
            user_occupation: User's occupation
            occupation_criteria: Scheme's occupation criteria string
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        occupation_criteria = occupation_criteria.strip().lower()
        user_occupation = user_occupation.strip().lower()
        
        if occupation_criteria in ['all', 'any', 'no restriction']:
            return True, f"occupation {user_occupation} meets criteria (open to all occupations)"
        
        # Check for direct match
        if user_occupation == occupation_criteria:
            return True, f"occupation {user_occupation} matches required occupation"
        
        # Check for partial matches and synonyms
        occupation_synonyms = {
            'student': ['student', 'pupil', 'learner'],
            'farmer': ['farmer', 'agriculturist', 'cultivator'],
            'unemployed': ['unemployed', 'jobless', 'seeking employment'],
            'self-employed': ['self-employed', 'entrepreneur', 'business owner'],
            'employed': ['employed', 'working', 'job holder']
        }
        
        for key, synonyms in occupation_synonyms.items():
            if occupation_criteria == key and user_occupation in synonyms:
                return True, f"occupation {user_occupation} matches {key} criteria"
            if user_occupation == key and occupation_criteria in synonyms:
                return True, f"occupation {user_occupation} matches {occupation_criteria} criteria"
        
        return False, f"occupation {user_occupation} does not match required occupation: {occupation_criteria}"
    
    def calculate_match_score(self, user_profile: UserProfile, scheme: SchemeModel) -> float:
        """
        Calculate a match score (0-100) for how well a user matches a scheme.
        
        Args:
            user_profile: User's profile information
            scheme: Government scheme to evaluate
            
        Returns:
            Match score from 0 (no match) to 100 (perfect match)
        """
        total_score = 0.0
        criteria_weights = {
            'age': 25.0,
            'income': 25.0,
            'category': 25.0,
            'occupation': 25.0
        }
        
        # Age eligibility scoring
        age_eligible, _ = self.check_age_eligibility(user_profile.age, scheme.eligibility.age)
        if age_eligible:
            total_score += criteria_weights['age']
        else:
            # Partial scoring for near misses
            min_age, max_age = self.parse_age_criteria(scheme.eligibility.age)
            if min_age is not None and user_profile.age < min_age:
                # Score based on how close to minimum age
                age_diff = min_age - user_profile.age
                if age_diff <= 5:  # Within 5 years
                    total_score += criteria_weights['age'] * (1 - age_diff / 10)
            elif max_age is not None and user_profile.age > max_age:
                # Score based on how close to maximum age
                age_diff = user_profile.age - max_age
                if age_diff <= 5:  # Within 5 years
                    total_score += criteria_weights['age'] * (1 - age_diff / 10)
        
        # Income eligibility scoring
        income_eligible, _ = self.check_income_eligibility(user_profile.income, scheme.eligibility.income)
        if income_eligible:
            total_score += criteria_weights['income']
        else:
            # Partial scoring for income slightly above limit
            max_income = self.parse_income_criteria(scheme.eligibility.income)
            if max_income is not None and user_profile.income > max_income:
                income_ratio = max_income / user_profile.income
                if income_ratio >= 0.8:  # Within 20% of limit
                    total_score += criteria_weights['income'] * income_ratio
        
        # Category eligibility scoring
        category_eligible, _ = self.check_category_eligibility(user_profile.category, scheme.eligibility.category)
        if category_eligible:
            total_score += criteria_weights['category']
        
        # Occupation eligibility scoring
        occupation_eligible, _ = self.check_occupation_eligibility(user_profile.occupation, scheme.eligibility.occupation)
        if occupation_eligible:
            total_score += criteria_weights['occupation']
        
        return round(total_score, 1)
    
    def generate_eligibility_reason(self, user_profile: UserProfile, scheme: SchemeModel) -> str:
        """
        Generate a human-readable explanation of eligibility status.
        
        Args:
            user_profile: User's profile information
            scheme: Government scheme to evaluate
            
        Returns:
            Human-readable eligibility explanation
        """
        reasons = []
        
        # Check each criteria and collect reasons
        age_eligible, age_reason = self.check_age_eligibility(user_profile.age, scheme.eligibility.age)
        income_eligible, income_reason = self.check_income_eligibility(user_profile.income, scheme.eligibility.income)
        category_eligible, category_reason = self.check_category_eligibility(user_profile.category, scheme.eligibility.category)
        occupation_eligible, occupation_reason = self.check_occupation_eligibility(user_profile.occupation, scheme.eligibility.occupation)
        
        # Collect positive reasons
        if age_eligible:
            reasons.append(age_reason)
        if income_eligible:
            reasons.append(income_reason)
        if category_eligible:
            reasons.append(category_reason)
        if occupation_eligible:
            reasons.append(occupation_reason)
        
        # Collect negative reasons
        negative_reasons = []
        if not age_eligible:
            negative_reasons.append(age_reason)
        if not income_eligible:
            negative_reasons.append(income_reason)
        if not category_eligible:
            negative_reasons.append(category_reason)
        if not occupation_eligible:
            negative_reasons.append(occupation_reason)
        
        # Format the explanation
        if not negative_reasons:
            return f"You meet all eligibility criteria: {', '.join(reasons)}."
        elif len(negative_reasons) == 1:
            positive_part = f"You meet most criteria ({', '.join(reasons)})" if reasons else "However"
            return f"{positive_part}, but {negative_reasons[0]}."
        else:
            return f"You do not meet the following criteria: {'; '.join(negative_reasons)}."
    
    def check_eligibility(self, user_profile: UserProfile, schemes: List[SchemeModel]) -> List[EligibleScheme]:
        """
        Check user eligibility against a list of schemes.
        
        Args:
            user_profile: User's profile information
            schemes: List of government schemes to evaluate
            
        Returns:
            List of EligibleScheme objects with eligibility results
        """
        eligible_schemes = []
        
        for scheme in schemes:
            match_score = self.calculate_match_score(user_profile, scheme)
            eligibility_reason = self.generate_eligibility_reason(user_profile, scheme)
            is_eligible = match_score >= 75.0  # Consider eligible if 75%+ match
            
            eligible_scheme = EligibleScheme(
                scheme=scheme,
                match_score=match_score,
                eligibility_reason=eligibility_reason,
                is_eligible=is_eligible
            )
            eligible_schemes.append(eligible_scheme)
        
        # Sort by match score (highest first)
        eligible_schemes.sort(key=lambda x: x.match_score, reverse=True)
        
        return eligible_schemes
    
    def get_recommendations(self, user_profile: UserProfile, schemes: List[SchemeModel], max_results: int = 5) -> List[EligibleScheme]:
        """
        Get scheme recommendations for a user, including partially matching schemes.
        
        Args:
            user_profile: User's profile information
            schemes: List of government schemes to evaluate
            max_results: Maximum number of recommendations to return
            
        Returns:
            List of recommended EligibleScheme objects
        """
        # Get all eligibility results
        all_results = self.check_eligibility(user_profile, schemes)
        
        # Filter for schemes with reasonable match scores (>= 25%)
        recommendations = [result for result in all_results if result.match_score >= 25.0]
        
        # Return top recommendations
        return recommendations[:max_results]