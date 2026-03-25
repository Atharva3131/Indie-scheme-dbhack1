"""
Test core services functionality for checkpoint verification.

This test suite verifies that the core services implemented in tasks 1-5
are working correctly before proceeding to the remaining implementation tasks.
"""

import pytest
from typing import List
from models.core import UserProfile, SchemeModel, EligibleScheme
from services.knowledge_base import KnowledgeBaseService
from services.eligibility import EligibilityService


class TestKnowledgeBaseService:
    """Test Knowledge Base Service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.kb_service = KnowledgeBaseService()
    
    def test_knowledge_base_loads_schemes(self):
        """Test that knowledge base loads schemes from data file."""
        schemes = self.kb_service.get_all_schemes()
        
        # Verify schemes are loaded
        assert len(schemes) > 0, "No schemes loaded from data file"
        assert len(schemes) >= 30, f"Expected at least 30 schemes, got {len(schemes)}"
        
        # Verify scheme structure
        first_scheme = schemes[0]
        assert hasattr(first_scheme, 'id'), "Scheme missing id field"
        assert hasattr(first_scheme, 'name'), "Scheme missing name field"
        assert hasattr(first_scheme, 'description'), "Scheme missing description field"
        assert hasattr(first_scheme, 'eligibility'), "Scheme missing eligibility field"
        assert hasattr(first_scheme, 'documents'), "Scheme missing documents field"
        assert hasattr(first_scheme, 'state'), "Scheme missing state field"
        assert hasattr(first_scheme, 'category'), "Scheme missing category field"
        
        print(f"✅ Knowledge base loaded {len(schemes)} schemes successfully")
    
    def test_scheme_lookup_by_id(self):
        """Test scheme lookup by ID functionality."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Test with existing scheme
        first_scheme = schemes[0]
        found_scheme = self.kb_service.get_scheme_by_id(first_scheme.id)
        
        assert found_scheme is not None, f"Failed to find scheme with ID {first_scheme.id}"
        assert found_scheme.id == first_scheme.id, "Retrieved scheme has different ID"
        assert found_scheme.name == first_scheme.name, "Retrieved scheme has different name"
        
        # Test with non-existent scheme
        non_existent = self.kb_service.get_scheme_by_id("non-existent-id")
        assert non_existent is None, "Should return None for non-existent scheme ID"
        
        print("✅ Scheme lookup by ID working correctly")
    
    def test_filter_by_category(self):
        """Test filtering schemes by category."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Get available categories
        categories = self.kb_service.get_categories()
        assert len(categories) > 0, "No categories found"
        
        # Test filtering by first available category
        test_category = categories[0]
        filtered_schemes = self.kb_service.filter_by_category(test_category)
        
        assert len(filtered_schemes) > 0, f"No schemes found for category {test_category}"
        
        # Verify all returned schemes have the correct category
        for scheme in filtered_schemes:
            assert scheme.category == test_category, f"Scheme {scheme.id} has wrong category"
        
        print(f"✅ Category filtering working correctly ({len(filtered_schemes)} schemes in {test_category})")
    
    def test_filter_by_state(self):
        """Test filtering schemes by state."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Get available states
        states = self.kb_service.get_states()
        assert len(states) > 0, "No states found"
        
        # Test filtering by first available state
        test_state = states[0]
        filtered_schemes = self.kb_service.filter_by_state(test_state)
        
        assert len(filtered_schemes) > 0, f"No schemes found for state {test_state}"
        
        # Verify all returned schemes have the correct state
        for scheme in filtered_schemes:
            assert scheme.state == test_state, f"Scheme {scheme.id} has wrong state"
        
        print(f"✅ State filtering working correctly ({len(filtered_schemes)} schemes in {test_state})")
    
    def test_semantic_search_functionality(self):
        """Test semantic search functionality."""
        # Test with a simple query
        results = self.kb_service.search_semantic("student scholarship", top_k=5)
        
        # Should return results (even if mock embeddings)
        assert isinstance(results, list), "Search should return a list"
        
        # If results are returned, verify structure
        if results:
            first_result = results[0]
            assert 'scheme' in first_result, "Search result missing scheme"
            assert 'similarity_score' in first_result, "Search result missing similarity_score"
            assert isinstance(first_result['similarity_score'], (int, float)), "Similarity score should be numeric"
            assert 0 <= first_result['similarity_score'] <= 1, "Similarity score should be between 0 and 1"
        
        print(f"✅ Semantic search working correctly ({len(results)} results)")
    
    def test_knowledge_base_statistics(self):
        """Test knowledge base statistics functionality."""
        stats = self.kb_service.get_statistics()
        
        # Verify statistics structure
        required_fields = ['total_schemes', 'categories', 'states', 'schemes_with_embeddings']
        for field in required_fields:
            assert field in stats, f"Statistics missing {field} field"
        
        # Verify statistics values
        assert stats['total_schemes'] > 0, "Total schemes should be greater than 0"
        assert stats['categories'] > 0, "Should have at least one category"
        assert stats['states'] > 0, "Should have at least one state"
        
        print(f"✅ Knowledge base statistics: {stats['total_schemes']} schemes, {stats['categories']} categories, {stats['states']} states")


class TestEligibilityService:
    """Test Eligibility Service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.eligibility_service = EligibilityService()
        self.kb_service = KnowledgeBaseService()
        
        # Create test user profiles
        self.student_profile = UserProfile(
            age=20,
            income=300000,  # 3 lakh
            category="General",
            occupation="student",
            state="Karnataka"
        )
        
        self.farmer_profile = UserProfile(
            age=45,
            income=150000,  # 1.5 lakh
            category="OBC",
            occupation="farmer",
            state="Karnataka"
        )
    
    def test_age_criteria_parsing(self):
        """Test age criteria parsing functionality."""
        # Test range parsing
        min_age, max_age = self.eligibility_service.parse_age_criteria("18-25")
        assert min_age == 18, "Failed to parse minimum age from range"
        assert max_age == 25, "Failed to parse maximum age from range"
        
        # Test above pattern
        min_age, max_age = self.eligibility_service.parse_age_criteria("60+")
        assert min_age == 60, "Failed to parse minimum age from above pattern"
        assert max_age is None, "Maximum age should be None for above pattern"
        
        # Test all pattern
        min_age, max_age = self.eligibility_service.parse_age_criteria("All")
        assert min_age is None, "Minimum age should be None for 'All'"
        assert max_age is None, "Maximum age should be None for 'All'"
        
        print("✅ Age criteria parsing working correctly")
    
    def test_income_criteria_parsing(self):
        """Test income criteria parsing functionality."""
        # Test lakh format
        max_income = self.eligibility_service.parse_income_criteria("< 5 lakh")
        assert max_income == 500000, "Failed to parse lakh format income"
        
        # Test BPL format
        max_income = self.eligibility_service.parse_income_criteria("BPL families")
        assert max_income == 150000, "Failed to parse BPL income criteria"
        
        # Test all format
        max_income = self.eligibility_service.parse_income_criteria("All")
        assert max_income is None, "Income should be None for 'All'"
        
        print("✅ Income criteria parsing working correctly")
    
    def test_eligibility_checking(self):
        """Test eligibility checking against schemes."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Test with student profile
        eligible_schemes = self.eligibility_service.check_eligibility(
            self.student_profile, 
            schemes[:10]  # Test with first 10 schemes
        )
        
        assert isinstance(eligible_schemes, list), "Should return a list of eligible schemes"
        assert len(eligible_schemes) == 10, "Should return results for all input schemes"
        
        # Verify structure of results
        for eligible_scheme in eligible_schemes:
            assert hasattr(eligible_scheme, 'scheme'), "Missing scheme field"
            assert hasattr(eligible_scheme, 'match_score'), "Missing match_score field"
            assert hasattr(eligible_scheme, 'eligibility_reason'), "Missing eligibility_reason field"
            assert hasattr(eligible_scheme, 'is_eligible'), "Missing is_eligible field"
            
            # Verify data types
            assert isinstance(eligible_scheme.match_score, (int, float)), "Match score should be numeric"
            assert 0 <= eligible_scheme.match_score <= 100, "Match score should be between 0 and 100"
            assert isinstance(eligible_scheme.eligibility_reason, str), "Eligibility reason should be string"
            assert isinstance(eligible_scheme.is_eligible, bool), "Is_eligible should be boolean"
        
        print(f"✅ Eligibility checking working correctly ({len(eligible_schemes)} results)")
    
    def test_match_score_calculation(self):
        """Test match score calculation."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Test with first scheme
        first_scheme = schemes[0]
        score = self.eligibility_service.calculate_match_score(self.student_profile, first_scheme)
        
        assert isinstance(score, (int, float)), "Match score should be numeric"
        assert 0 <= score <= 100, f"Match score should be between 0 and 100, got {score}"
        
        print(f"✅ Match score calculation working correctly (score: {score})")
    
    def test_eligibility_reason_generation(self):
        """Test eligibility reason generation."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Test with first scheme
        first_scheme = schemes[0]
        reason = self.eligibility_service.generate_eligibility_reason(self.student_profile, first_scheme)
        
        assert isinstance(reason, str), "Eligibility reason should be a string"
        assert len(reason) > 0, "Eligibility reason should not be empty"
        
        print(f"✅ Eligibility reason generation working correctly")
    
    def test_recommendations_functionality(self):
        """Test recommendations functionality."""
        schemes = self.kb_service.get_all_schemes()
        if not schemes:
            pytest.skip("No schemes available for testing")
        
        # Get recommendations for student
        recommendations = self.eligibility_service.get_recommendations(
            self.student_profile, 
            schemes, 
            max_results=5
        )
        
        assert isinstance(recommendations, list), "Recommendations should be a list"
        assert len(recommendations) <= 5, "Should not exceed max_results"
        
        # Verify recommendations are sorted by match score
        if len(recommendations) > 1:
            for i in range(len(recommendations) - 1):
                assert recommendations[i].match_score >= recommendations[i + 1].match_score, \
                    "Recommendations should be sorted by match score (descending)"
        
        print(f"✅ Recommendations working correctly ({len(recommendations)} recommendations)")


class TestServiceIntegration:
    """Test integration between services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.kb_service = KnowledgeBaseService()
        self.eligibility_service = EligibilityService()
        
        self.test_profile = UserProfile(
            age=22,
            income=400000,
            category="General",
            occupation="student",
            state="Karnataka"
        )
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from data loading to eligibility checking."""
        # 1. Load schemes from knowledge base
        all_schemes = self.kb_service.get_all_schemes()
        assert len(all_schemes) > 0, "Failed to load schemes"
        
        # 2. Filter schemes by category
        education_schemes = self.kb_service.filter_by_category("education")
        
        # 3. Check eligibility for filtered schemes
        if education_schemes:
            eligible_schemes = self.eligibility_service.check_eligibility(
                self.test_profile, 
                education_schemes
            )
            
            assert len(eligible_schemes) == len(education_schemes), \
                "Should return eligibility results for all input schemes"
            
            # 4. Get top recommendations
            recommendations = self.eligibility_service.get_recommendations(
                self.test_profile,
                education_schemes,
                max_results=3
            )
            
            assert len(recommendations) <= 3, "Should not exceed max recommendations"
            
            print(f"✅ End-to-end workflow completed successfully")
            print(f"   - Loaded {len(all_schemes)} total schemes")
            print(f"   - Found {len(education_schemes)} education schemes")
            print(f"   - Generated {len(recommendations)} recommendations")
        else:
            print("⚠️  No education schemes found, but workflow completed")
    
    def test_data_consistency(self):
        """Test data consistency across services."""
        # Verify that all schemes have required fields for eligibility checking
        schemes = self.kb_service.get_all_schemes()
        
        for scheme in schemes[:5]:  # Test first 5 schemes
            # Verify eligibility object has required fields
            assert hasattr(scheme.eligibility, 'age'), f"Scheme {scheme.id} missing age criteria"
            assert hasattr(scheme.eligibility, 'income'), f"Scheme {scheme.id} missing income criteria"
            assert hasattr(scheme.eligibility, 'category'), f"Scheme {scheme.id} missing category criteria"
            assert hasattr(scheme.eligibility, 'occupation'), f"Scheme {scheme.id} missing occupation criteria"
            
            # Test that eligibility service can process the scheme
            try:
                score = self.eligibility_service.calculate_match_score(self.test_profile, scheme)
                assert isinstance(score, (int, float)), f"Invalid match score for scheme {scheme.id}"
            except Exception as e:
                pytest.fail(f"Eligibility service failed to process scheme {scheme.id}: {e}")
        
        print("✅ Data consistency verified across services")


def run_checkpoint_tests():
    """Run all checkpoint tests and provide summary."""
    print("🧪 Running Core Services Checkpoint Tests...")
    print("=" * 60)
    
    # Run tests using pytest
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_core_services.py", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print("🎉 All core services tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_checkpoint_tests()
    exit(0 if success else 1)