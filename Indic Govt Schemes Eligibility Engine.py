# Databricks notebook source
# DBTITLE 1,Step 1: Load or Create Mock Delta Table
# Step 1: Load Government Schemes from Knowledge Base or Create In-Memory
# Try to read from gov_schemes_kb table, fallback to in-memory data if not accessible

try:
    df = spark.read.table("gov_schemes_kb")
    print(f"✓ Successfully loaded {df.count()} schemes from gov_schemes_kb table\n")
    data_source = "gov_schemes_kb Delta table"
except Exception as e:
    print(f"⚠️ Could not access gov_schemes_kb table: {e}")
    print("✓ Creating schemes data in-memory for testing...\n")
    
    # Create in-memory data with Central schemes (applicable to all states)
    schemes_data = [
        {
            "name": "PM Scholarship Scheme",
            "description": "Financial assistance for wards of Ex-Servicemen and Ex-Coast Guard personnel for pursuing higher education",
            "eligibility": {"age": "18-25", "income": "< 6 lakh", "category": "All", "occupation": "student"},
            "documents": ["Aadhaar", "Income Certificate", "Marksheet", "Ex-Servicemen Certificate"],
            "state": "Central",
            "keywords": "student scholarship education ex-servicemen",
            "category": "education"
        },
        {
            "name": "National Means cum Merit Scholarship",
            "description": "Scholarship for meritorious students from economically weaker sections to prevent dropouts at class 8th level",
            "eligibility": {"age": "13-16", "income": "< 3.5 lakh", "category": "All", "occupation": "student"},
            "documents": ["Aadhaar", "Income Certificate", "Class 7th Marksheet"],
            "state": "Central",
            "keywords": "scholarship merit student class 8 economically weaker",
            "category": "education"
        },
        {
            "name": "Pre Matric Scholarship for Minorities",
            "description": "Financial assistance to students from minority communities for education from Class 1 to 10",
            "eligibility": {"age": "6-16", "income": "< 1 lakh", "category": "Minority communities", "occupation": "student"},
            "documents": ["Aadhaar", "Income Certificate", "Community Certificate", "School Certificate"],
            "state": "Central",
            "keywords": "minority student scholarship pre-matric",
            "category": "education"
        },
        {
            "name": "Post Matric Scholarship for OBC Students",
            "description": "Financial assistance to OBC students for pursuing studies beyond matriculation or secondary stage",
            "eligibility": {"age": "16-30", "income": "< 2.5 lakh", "category": "OBC", "occupation": "student"},
            "documents": ["Aadhaar", "Income Certificate", "OBC Certificate", "Admission Proof"],
            "state": "Central",
            "keywords": "obc student scholarship post-matric higher education",
            "category": "education"
        },
        {
            "name": "Pradhan Mantri Kaushal Vikas Yojana",
            "description": "Skill development training program for Indian youth",
            "eligibility": {"age": "15-45", "income": "All", "category": "All", "occupation": "All"},
            "documents": ["Aadhaar", "Educational Certificate", "Bank Account"],
            "state": "Central",
            "keywords": "skill training employment youth vocational",
            "category": "employment"
        },
        {
            "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
            "description": "Health insurance scheme providing coverage of Rs 5 lakh per family per year for secondary and tertiary care hospitalization",
            "eligibility": {"age": "All", "income": "Low income", "category": "BPL families", "occupation": "All"},
            "documents": ["Aadhaar", "Ration Card", "SECC Data"],
            "state": "Central",
            "keywords": "health insurance hospitalization medical ayushman bharat",
            "category": "health"
        },
        {
            "name": "PM Kisan Samman Nidhi",
            "description": "Income support of Rs 6000 per year to all landholding farmer families in three equal installments",
            "eligibility": {"age": "18+", "income": "All", "category": "Landholding farmers", "occupation": "farmer"},
            "documents": ["Aadhaar", "Land Ownership Papers", "Bank Account"],
            "state": "Central",
            "keywords": "farmer agriculture income support kisan",
            "category": "agriculture"
        },
        {
            "name": "Pradhan Mantri Mudra Yojana",
            "description": "Loans up to Rs 10 lakh to small businesses and micro enterprises",
            "eligibility": {"age": "18+", "income": "All", "category": "Non-corporate small businesses", "occupation": "self-employed"},
            "documents": ["Aadhaar", "Business Plan", "Address Proof", "Bank Account"],
            "state": "Central",
            "keywords": "loan business entrepreneurship mudra self-employed",
            "category": "employment"
        }
    ]
    
    df = spark.createDataFrame(schemes_data)
    print(f"✓ Created {df.count()} Central government schemes in-memory")
    data_source = "in-memory data (Central schemes)"

print(f"\nData Source: {data_source}")
print(f"Total Schemes: {df.count()}")
print("\nScheme distribution by category:")
df.groupBy("category").count().orderBy("count", ascending=False).show(truncate=False)
print("\nSample schemes:")
df.select("name", "state", "category").show(5, truncate=False)

# COMMAND ----------

# DBTITLE 1,Step 2: Define User Input Schema
# Step 2: Define User Input Schema
user_input = {
    "age": 20,
    "income": 200000,
    "category": "OBC",
    "occupation": "student",
    "state": "Karnataka"
}

print("User Profile:")
for key, value in user_input.items():
    print(f"  {key}: {value}")

# COMMAND ----------

# DBTITLE 1,Step 3: Build Eligibility Logic with Spark Filtering
# Step 3: Build Eligibility Logic for Knowledge Base Schema
from pyspark.sql.functions import col, lower, trim, udf
from pyspark.sql.types import BooleanType, IntegerType, StructType, StructField
import re

def parse_age_range(age_str):
    """Parse age string like '18-25', '60+', '0-18' into (min, max)"""
    if not age_str or age_str.lower() == 'all':
        return (0, 150)  # No age restriction
    
    # Handle '60+' format
    if '+' in age_str:
        min_age = int(re.findall(r'\d+', age_str)[0])
        return (min_age, 150)
    
    # Handle range like '18-25'
    ages = re.findall(r'\d+', age_str)
    if len(ages) >= 2:
        return (int(ages[0]), int(ages[1]))
    elif len(ages) == 1:
        return (int(ages[0]), int(ages[0]))
    
    return (0, 150)

def parse_income_limit(income_str):
    """Parse income string like '< 6 lakh', 'BPL families', 'All' into numeric limit"""
    if not income_str or income_str.lower() == 'all':
        return 999999999  # No income restriction
    
    income_str_lower = income_str.lower()
    
    # Handle BPL, low income as low limits
    if 'bpl' in income_str_lower or 'low income' in income_str_lower:
        return 200000  # Approximate BPL threshold
    
    # Extract numeric value and convert lakhs to actual amount
    numbers = re.findall(r'\d+\.?\d*', income_str)
    if numbers:
        value = float(numbers[0])
        if 'lakh' in income_str_lower:
            return int(value * 100000)
        elif 'crore' in income_str_lower:
            return int(value * 10000000)
        else:
            return int(value)
    
    return 999999999  # Default: no restriction

def check_eligibility(df, user):
    """
    Apply eligibility filters based on user profile.
    Works with knowledge base schema where eligibility is a MapType.
    """
    
    # Collect all schemes and filter in Python (easier for complex parsing)
    all_schemes = df.collect()
    eligible_schemes = []
    
    for scheme_row in all_schemes:
        scheme = scheme_row.asDict()
        eligibility = scheme['eligibility']
        
        # Parse and check age
        age_min, age_max = parse_age_range(eligibility.get('age', 'All'))
        if not (age_min <= user['age'] <= age_max):
            continue
        
        # Parse and check income
        income_limit = parse_income_limit(eligibility.get('income', 'All'))
        if user['income'] > income_limit:
            continue
        
        # Check category
        category_str = eligibility.get('category', 'All')
        if category_str.lower() != 'all':
            # Check if user's category is mentioned in the eligibility
            if user['category'].lower() not in category_str.lower():
                # Also check if it's a specific group like "Girl child", "Women", etc.
                # For now, if not "All" and user category not found, skip
                # unless it's a universal category
                if 'all' not in category_str.lower():
                    continue
        
        # Check occupation
        occupation_str = eligibility.get('occupation', 'All')
        if occupation_str.lower() != 'all':
            if user['occupation'].lower() not in occupation_str.lower():
                continue
        
        # Check state (Central schemes apply to all states)
        if scheme['state'].lower() != 'central' and scheme['state'].lower() != user['state'].lower():
            continue
        
        # If all checks passed, add to eligible list
        eligible_schemes.append(scheme)
    
    # Convert back to DataFrame
    if eligible_schemes:
        return spark.createDataFrame(eligible_schemes)
    else:
        # Return empty DataFrame with same schema
        return spark.createDataFrame([], df.schema)

# Apply filtering
eligible_schemes_df = check_eligibility(df, user_input)
print(f"\nFound {eligible_schemes_df.count()} eligible schemes")
if eligible_schemes_df.count() > 0:
    eligible_schemes_df.select("name", "category", "state").show(truncate=False)

# COMMAND ----------

# DBTITLE 1,Step 4 & 5: Add Reason Generator and Convert to JSON
# Step 4 & 5: Reason Generator + JSON Conversion
import json

def generate_eligibility_reason(scheme, user):
    """
    Generate human-readable eligibility reason.
    Works with knowledge base schema.
    """
    reasons = []
    eligibility = scheme['eligibility']
    
    # Age eligibility
    age_str = eligibility.get('age', 'All')
    if age_str and age_str.lower() != 'all':
        age_min, age_max = parse_age_range(age_str)
        if age_min <= user['age'] <= age_max:
            reasons.append(f"age {user['age']} matches requirement ({age_str})")
    
    # Income eligibility
    income_str = eligibility.get('income', 'All')
    if income_str and income_str.lower() != 'all':
        income_limit = parse_income_limit(income_str)
        if user['income'] <= income_limit:
            reasons.append(f"income ₹{user['income']:,} meets requirement ({income_str})")
    
    # Category match
    category_str = eligibility.get('category', 'All')
    if category_str.lower() == 'all' or user['category'].lower() in category_str.lower():
        reasons.append(f"category '{user['category']}' is eligible")
    
    # Occupation match
    occupation_str = eligibility.get('occupation', 'All')
    if occupation_str.lower() == 'all' or user['occupation'].lower() in occupation_str.lower():
        reasons.append(f"occupation '{user['occupation']}' matches")
    
    # State match
    if scheme['state'].lower() == 'central':
        reasons.append(f"Central scheme (applicable in all states including {user['state']})")
    elif scheme['state'].lower() == user['state'].lower():
        reasons.append(f"applicable in {user['state']}")
    
    return "Eligible because: " + ", ".join(reasons)


def calculate_match_score(scheme, user):
    """
    Calculate a match score (0-100) based on how well the user fits the scheme.
    """
    score = 0
    eligibility = scheme['eligibility']
    
    # Age score (20 points)
    age_str = eligibility.get('age', 'All')
    if age_str and age_str.lower() != 'all':
        age_min, age_max = parse_age_range(age_str)
        age_mid = (age_min + age_max) / 2
        age_range = age_max - age_min if age_max > age_min else 1
        age_deviation = abs(user['age'] - age_mid) / age_range
        score += (1 - min(age_deviation, 1)) * 20
    else:
        score += 10  # Universal age = medium score
    
    # Income score (30 points) - lower income = higher priority for social schemes
    income_str = eligibility.get('income', 'All')
    if income_str and income_str.lower() != 'all':
        income_limit = parse_income_limit(income_str)
        if income_limit < 999999999:
            income_ratio = user['income'] / income_limit if income_limit > 0 else 1
            score += (1 - min(income_ratio, 1)) * 30
        else:
            score += 15
    else:
        score += 15
    
    # Category match (25 points)
    category_str = eligibility.get('category', 'All')
    if category_str.lower() == 'all':
        score += 15
    elif user['category'].lower() in category_str.lower():
        score += 25
    
    # Occupation match (25 points)
    occupation_str = eligibility.get('occupation', 'All')
    if occupation_str.lower() == 'all':
        score += 15
    elif user['occupation'].lower() in occupation_str.lower():
        score += 25
    
    return round(min(score, 100), 2)


def get_eligible_schemes(user):
    """
    Main function to get eligible schemes with reasons.
    Returns JSON-compatible list of schemes.
    """
    # Apply eligibility filtering
    filtered_df = check_eligibility(df, user)
    
    # Convert to list of dictionaries
    schemes_list = filtered_df.collect()
    
    # Build result with reasons
    results = []
    for row in schemes_list:
        scheme_dict = row.asDict()
        
        # Generate eligibility reason
        reason = generate_eligibility_reason(scheme_dict, user)
        
        # Format output following shared schema
        result = {
            "name": scheme_dict["name"],
            "description": scheme_dict["description"],
            "eligibility": scheme_dict["eligibility"],  # Keep as dict
            "documents": scheme_dict["documents"],
            "state": scheme_dict["state"],
            "category": scheme_dict["category"],
            "keywords": scheme_dict["keywords"],
            "eligibility_reason": reason,
            "match_score": calculate_match_score(scheme_dict, user)
        }
        results.append(result)
    
    # Sort by match score (highest first)
    results.sort(key=lambda x: x["match_score"], reverse=True)
    
    return results

print("✓ Eligibility engine functions defined")

# COMMAND ----------

# DBTITLE 1,Step 6: Test the Eligibility Engine
# Step 6: Test the eligibility engine
print("="*60)
print("ELIGIBILITY ENGINE TEST")
print("="*60)
print("\nUser Profile:")
for key, value in user_input.items():
    print(f"  {key}: {value}")

# Get eligible schemes
eligible_schemes = get_eligible_schemes(user_input)

print(f"\n\n{'='*60}")
print(f"FOUND {len(eligible_schemes)} ELIGIBLE SCHEMES")
print(f"{'='*60}\n")

# Display results
for i, scheme in enumerate(eligible_schemes, 1):
    print(f"\n{i}. {scheme['name']}")
    print(f"   Match Score: {scheme['match_score']}/100")
    print(f"   Category: {scheme['category']} | State: {scheme['state']}")
    print(f"   Description: {scheme['description']}")
    print(f"   {scheme['eligibility_reason']}")
    print(f"   Required Documents: {', '.join(scheme['documents'])}")
    print(f"   {'-'*55}")

# Show JSON output
print("\n\nJSON Output (for API response):")
print(json.dumps(eligible_schemes, indent=2, ensure_ascii=False))

# COMMAND ----------

# DBTITLE 1,Step 7 (Optional): Recommendation Logic for Similar Schemes
# Step 7: Recommendation Logic - Find Similar Schemes
def get_recommended_schemes(user, include_other_states=True, max_recommendations=5):
    """
    Get recommended schemes even if user doesn't fully qualify.
    Relaxes some criteria to suggest similar schemes.
    """
    
    # Get already eligible schemes to exclude them
    eligible_df = check_eligibility(df, user)
    eligible_names = [row.name for row in eligible_df.select("name").collect()]
    
    # Collect all schemes and score them
    all_schemes = df.collect()
    recommendations = []
    
    for scheme_row in all_schemes:
        scheme = scheme_row.asDict()
        
        # Skip already eligible schemes
        if scheme['name'] in eligible_names:
            continue
        
        eligibility = scheme['eligibility']
        reasons = []
        is_relevant = False
        
        # Check age (strict - must match)
        age_str = eligibility.get('age', 'All')
        age_min, age_max = parse_age_range(age_str)
        if not (age_min <= user['age'] <= age_max):
            continue  # Age must match
        
        # Check category (strict - must match or be All)
        category_str = eligibility.get('category', 'All')
        if category_str.lower() != 'all':
            if user['category'].lower() not in category_str.lower():
                continue  # Category must match
        
        # Relaxed income check
        income_str = eligibility.get('income', 'All')
        income_limit = parse_income_limit(income_str)
        if user['income'] > income_limit:
            if user['income'] <= income_limit * 1.3:  # Within 30% over limit
                reasons.append(f"income slightly above limit ({income_str})")
                is_relevant = True
            else:
                continue  # Too far over income limit
        
        # Check occupation (can be relaxed)
        occupation_str = eligibility.get('occupation', 'All')
        if occupation_str.lower() != 'all' and user['occupation'].lower() not in occupation_str.lower():
            reasons.append(f"designed for {occupation_str} (consider if applicable)")
            is_relevant = True
        
        # Check state (can be different)
        if scheme['state'].lower() != 'central':
            if scheme['state'].lower() != user['state'].lower():
                if include_other_states:
                    reasons.append(f"available in {scheme['state']} (check for similar state scheme)")
                    is_relevant = True
                else:
                    continue
        else:
            is_relevant = True  # Central schemes are always relevant
        
        if is_relevant:
            recommendation_reason = "Similar scheme" + (" - " + ", ".join(reasons) if reasons else "")
            
            result = {
                "name": scheme["name"],
                "description": scheme["description"],
                "eligibility": scheme["eligibility"],
                "documents": scheme["documents"],
                "state": scheme["state"],
                "category": scheme["category"],
                "keywords": scheme["keywords"],
                "recommendation_reason": recommendation_reason
            }
            recommendations.append(result)
    
    # Sort by relevance (Central schemes first, then by category match)
    recommendations.sort(key=lambda x: (x['state'].lower() == 'central', user['occupation'].lower() in x['eligibility'].get('occupation', '').lower()), reverse=True)
    
    return recommendations[:max_recommendations]

# Test recommendations
recommendations = get_recommended_schemes(user_input, include_other_states=True)

print(f"\n{'='*60}")
print(f"FOUND {len(recommendations)} RECOMMENDED SCHEMES")
print(f"{'='*60}\n")

for i, scheme in enumerate(recommendations[:5], 1):
    print(f"{i}. {scheme['name']}")
    print(f"   Category: {scheme['category']} | State: {scheme['state']}")
    print(f"   {scheme['recommendation_reason']}")
    print(f"   {'-'*55}")

# COMMAND ----------

# DBTITLE 1,API-Ready Function: Complete Eligibility Endpoint
# Complete API-Ready Function for /eligibility endpoint
from datetime import datetime

def eligibility_api(user_profile: dict) -> dict:
    """
    Main API function for /eligibility endpoint.
    
    Input: user_profile dict with keys: age, income, category, occupation, state
    Output: dict with eligible_schemes, recommendations, and metadata
    """
    
    try:
        # Validate input
        required_fields = ["age", "income", "category", "occupation", "state"]
        for field in required_fields:
            if field not in user_profile:
                return {
                    "status": "error",
                    "message": f"Missing required field: {field}",
                    "timestamp": datetime.now().isoformat()
                }
        
        # Get eligible schemes
        eligible = get_eligible_schemes(user_profile)
        
        # Get recommendations
        recommended = get_recommended_schemes(user_profile, include_other_states=True, max_recommendations=5)
        
        # Build response
        response = {
            "status": "success",
            "user_profile": user_profile,
            "results": {
                "eligible_schemes_count": len(eligible),
                "eligible_schemes": eligible,
                "recommended_schemes_count": len(recommended),
                "recommended_schemes": recommended
            },
            "metadata": {
                "total_schemes_in_kb": df.count(),
                "knowledge_base_table": "gov_schemes_kb",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Test the API function
print("\n" + "="*60)
print("TESTING API ENDPOINT: /eligibility")
print("="*60 + "\n")

api_response = eligibility_api(user_input)
print(json.dumps(api_response, indent=2, ensure_ascii=False))