#!/usr/bin/env python3
"""
Script to generate comprehensive mock data for government schemes.
Based on the original Databricks implementation with 30+ schemes.
"""

import json
import random
import numpy as np

def generate_mock_embedding(text, dimension=384):
    """Generate a mock embedding based on text content."""
    # Use text hash as seed for reproducible embeddings
    seed = hash(text) % (2**32)
    np.random.seed(seed)
    
    # Generate normalized random vector
    embedding = np.random.normal(0, 0.3, dimension)
    # Normalize to unit vector
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    
    return embedding.tolist()

# Comprehensive scheme data based on original Databricks implementation
schemes_data = [
    # CENTRAL GOVERNMENT SCHEMES
    {
        "id": "pm-scholarship-001",
        "name": "PM Scholarship Scheme",
        "description": "Financial assistance for students pursuing higher education in engineering, medical, and other professional courses. Provides up to ₹36,000 per year for tuition fees and ₹20,000 for maintenance allowance.",
        "eligibility": {"age": "18-25", "income": "< 6 lakh", "category": "All", "occupation": "student"},
        "documents": ["Aadhaar Card", "Income Certificate", "Marksheet", "Bank Account Details"],
        "state": "Central",
        "category": "education",
        "keywords": "student scholarship education higher engineering medical professional tuition fees"
    },
    {
        "id": "pm-kisan-samman-002",
        "name": "PM Kisan Samman Nidhi",
        "description": "Direct income support of ₹6,000 per year to small and marginal farmers across India in three equal installments.",
        "eligibility": {"age": "18+", "income": "All", "category": "Small and marginal farmers", "occupation": "farmer"},
        "documents": ["Aadhaar Card", "Land Records", "Bank Account", "Farmer Registration"],
        "state": "Central",
        "category": "agriculture",
        "keywords": "farmer income support agriculture kisan samman nidhi direct benefit"
    },
    {
        "id": "ayushman-bharat-003",
        "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
        "description": "Health insurance scheme providing coverage up to ₹5 lakh per family per year for secondary and tertiary care hospitalization.",
        "eligibility": {"age": "All", "income": "BPL families", "category": "Below Poverty Line", "occupation": "All"},
        "documents": ["Aadhaar Card", "Ration Card", "Family ID", "Income Certificate"],
        "state": "Central",
        "category": "health",
        "keywords": "health insurance hospitalization medical coverage ayushman bharat jan arogya"
    },
    {
        "id": "pmay-urban-004",
        "name": "Pradhan Mantri Awas Yojana - Urban",
        "description": "Housing scheme for economically weaker sections and low-income groups in urban areas with interest subsidy and direct assistance.",
        "eligibility": {"age": "18+", "income": "< 18 lakh", "category": "EWS/LIG/MIG", "occupation": "All"},
        "documents": ["Aadhaar Card", "Income Certificate", "Property Documents", "Bank Account"],
        "state": "Central",
        "category": "housing",
        "keywords": "housing urban affordable pmay awas yojana interest subsidy"
    },
    {
        "id": "mudra-yojana-005",
        "name": "Pradhan Mantri MUDRA Yojana",
        "description": "Micro-finance scheme providing loans up to ₹10 lakh for small businesses and entrepreneurship development.",
        "eligibility": {"age": "18+", "income": "All", "category": "Micro entrepreneurs", "occupation": "entrepreneur"},
        "documents": ["Aadhaar Card", "Business Plan", "Address Proof", "Bank Account"],
        "state": "Central",
        "category": "employment",
        "keywords": "micro finance loan business entrepreneur mudra startup funding"
    },

    # KARNATAKA STATE SCHEMES - EDUCATION
    {
        "id": "vidyasiri-scholarship-006",
        "name": "Vidyasiri Scholarship",
        "description": "Financial assistance to economically backward students pursuing pre-university and degree courses in Karnataka",
        "eligibility": {"age": "17-25", "income": "< 2.5 lakh", "category": "All", "occupation": "student"},
        "documents": ["Aadhaar", "Income Certificate", "Caste Certificate", "Fee Receipt", "Bank Passbook"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "student scholarship education degree pre-university vidyasiri"
    },
    {
        "id": "vidyagama-scheme-007",
        "name": "Vidyagama Scheme",
        "description": "Bridge course program for students in government schools to improve learning outcomes and reduce dropout rates",
        "eligibility": {"age": "6-14", "income": "All", "category": "Government school students", "occupation": "student"},
        "documents": ["School ID Card", "Aadhaar"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "education government school learning dropout vidyagama"
    },
    {
        "id": "kaushalya-karnataka-008",
        "name": "Kaushalya Karnataka",
        "description": "Skill development initiative for youth providing vocational training in various sectors",
        "eligibility": {"age": "18-35", "income": "All", "category": "Karnataka youth", "occupation": "All"},
        "documents": ["Aadhaar", "Educational Certificate", "Address Proof"],
        "state": "Karnataka",
        "category": "skill_development",
        "keywords": "skill training vocational youth employment kaushalya"
    },
    {
        "id": "arivu-education-loan-009",
        "name": "Arivu Education Loan Scheme",
        "description": "Interest subsidy on education loans for students pursuing higher education within Karnataka",
        "eligibility": {"age": "18-30", "income": "< 8 lakh", "category": "All", "occupation": "student"},
        "documents": ["Aadhaar", "Income Certificate", "Admission Letter", "Loan Sanction Letter"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "education loan subsidy higher education arivu"
    },

    # KARNATAKA AGRICULTURE SCHEMES
    {
        "id": "raitha-shakti-010",
        "name": "Raitha Shakti",
        "description": "Financial assistance and support to farmers for sustainable agriculture practices and equipment",
        "eligibility": {"age": "18+", "income": "All", "category": "Farmers", "occupation": "farmer"},
        "documents": ["Aadhaar", "Land Records", "Bank Account", "Farmer Registration"],
        "state": "Karnataka",
        "category": "agriculture",
        "keywords": "farmer agriculture financial assistance equipment raitha shakti"
    },
    {
        "id": "krishi-bhagya-011",
        "name": "Krishi Bhagya Yojana",
        "description": "Scheme to improve irrigation facilities and provide micro-irrigation systems to farmers",
        "eligibility": {"age": "18+", "income": "All", "category": "Farmers with land", "occupation": "farmer"},
        "documents": ["Aadhaar", "Land Documents", "Bank Account", "Application Form"],
        "state": "Karnataka",
        "category": "agriculture",
        "keywords": "irrigation micro-irrigation farmer agriculture krishi bhagya"
    },
    {
        "id": "bhoochetana-scheme-012",
        "name": "Bhoochetana Scheme",
        "description": "Soil health management program to improve soil fertility and crop productivity",
        "eligibility": {"age": "18+", "income": "All", "category": "All farmers", "occupation": "farmer"},
        "documents": ["Aadhaar", "Land Records", "Farmer ID"],
        "state": "Karnataka",
        "category": "agriculture",
        "keywords": "soil health fertility crop productivity bhoochetana farmer"
    },
    {
        "id": "raitha-bandhu-013",
        "name": "Raitha Bandhu Scheme",
        "description": "Zero-interest crop loans for small and marginal farmers in Karnataka",
        "eligibility": {"age": "18-70", "income": "All", "category": "Small and marginal farmers", "occupation": "farmer"},
        "documents": ["Aadhaar", "Land Documents", "Bank Account", "Farmer Certificate"],
        "state": "Karnataka",
        "category": "agriculture",
        "keywords": "crop loan zero interest farmer credit raitha bandhu"
    },

    # KARNATAKA HEALTH SCHEMES
    {
        "id": "vajpayee-arogya-014",
        "name": "Vajpayee Arogya Shree",
        "description": "Free health insurance coverage for BPL families for secondary and tertiary care hospitalization",
        "eligibility": {"age": "All", "income": "BPL families", "category": "Below Poverty Line", "occupation": "All"},
        "documents": ["Aadhaar", "BPL Card", "Ration Card", "Family Card"],
        "state": "Karnataka",
        "category": "health",
        "keywords": "health insurance hospitalization bpl medical vajpayee arogya"
    },
    {
        "id": "sanjeevani-scheme-015",
        "name": "Sanjeevani Scheme",
        "description": "Free emergency medical services and ambulance facilities across Karnataka",
        "eligibility": {"age": "All", "income": "All", "category": "All", "occupation": "All"},
        "documents": ["Emergency contact"],
        "state": "Karnataka",
        "category": "health",
        "keywords": "emergency ambulance medical services sanjeevani 108"
    },
    {
        "id": "mathru-purna-016",
        "name": "Mathru Purna Scheme",
        "description": "Nutritional support and financial assistance to pregnant and lactating mothers",
        "eligibility": {"age": "18-45", "income": "< 12 lakh", "category": "Pregnant women", "occupation": "All"},
        "documents": ["Aadhaar", "Pregnancy Certificate", "Medical Records", "Bank Account"],
        "state": "Karnataka",
        "category": "health",
        "keywords": "pregnant women maternal nutrition health mathru purna"
    },

    # KARNATAKA HOUSING SCHEMES
    {
        "id": "basava-vasati-017",
        "name": "Basava Vasati Yojana",
        "description": "Housing scheme for economically weaker sections and slum dwellers in urban areas",
        "eligibility": {"age": "18+", "income": "< 5 lakh", "category": "EWS and slum dwellers", "occupation": "All"},
        "documents": ["Aadhaar", "Income Certificate", "Address Proof", "Slum Certificate if applicable"],
        "state": "Karnataka",
        "category": "housing",
        "keywords": "housing urban slum ews affordable basava vasati"
    },
    {
        "id": "grameena-ashraya-018",
        "name": "Grameena Ashraya Yojana",
        "description": "Rural housing scheme providing financial assistance for construction of houses in rural Karnataka",
        "eligibility": {"age": "18+", "income": "BPL families", "category": "Rural poor", "occupation": "All"},
        "documents": ["Aadhaar", "BPL Card", "Land Documents", "Bank Account"],
        "state": "Karnataka",
        "category": "housing",
        "keywords": "housing rural construction financial assistance grameena ashraya"
    },

    # WOMEN EMPOWERMENT SCHEMES
    {
        "id": "stree-shakti-019",
        "name": "Stree Shakti Scheme",
        "description": "Support for women self-help groups through credit linkage and capacity building",
        "eligibility": {"age": "18+", "income": "All", "category": "Women SHG members", "occupation": "All"},
        "documents": ["Aadhaar", "SHG Registration", "Bank Account"],
        "state": "Karnataka",
        "category": "women_empowerment",
        "keywords": "women empowerment shg self help group credit stree shakti"
    },
    {
        "id": "bhagyalakshmi-020",
        "name": "Bhagyalakshmi Scheme",
        "description": "Financial assistance scheme for girl child covering education, health and marriage expenses",
        "eligibility": {"age": "0-18", "income": "< 2 lakh", "category": "Girl child from BPL families", "occupation": "All"},
        "documents": ["Birth Certificate", "BPL Card", "Aadhaar of parents", "Bank Account"],
        "state": "Karnataka",
        "category": "women_empowerment",
        "keywords": "girl child education financial assistance bhagyalakshmi"
    },
    {
        "id": "sandhya-suraksha-021",
        "name": "Sandhya Suraksha Scheme",
        "description": "Pension scheme for widows and destitute women in Karnataka",
        "eligibility": {"age": "18+", "income": "BPL families", "category": "Widows and destitute women", "occupation": "All"},
        "documents": ["Aadhaar", "Widow Certificate", "Income Certificate", "Bank Account"],
        "state": "Karnataka",
        "category": "women_empowerment",
        "keywords": "pension widow women destitute sandhya suraksha"
    },

    # EMPLOYMENT SCHEMES
    {
        "id": "karnataka-yuva-nidhi-022",
        "name": "Karnataka Yuva Nidhi",
        "description": "Unemployment allowance for educated youth seeking employment in Karnataka",
        "eligibility": {"age": "18-28", "income": "< 8 lakh", "category": "Graduates", "occupation": "unemployed"},
        "documents": ["Aadhaar", "Degree Certificate", "Income Certificate", "Bank Account"],
        "state": "Karnataka",
        "category": "employment",
        "keywords": "unemployment allowance youth educated graduate yuva nidhi"
    },
    {
        "id": "namma-bengaluru-023",
        "name": "Namma Bengaluru Foundation Employment",
        "description": "Job placement and skill training for urban youth in Bengaluru",
        "eligibility": {"age": "18-35", "income": "All", "category": "Bengaluru residents", "occupation": "All"},
        "documents": ["Aadhaar", "Address Proof", "Educational Certificate"],
        "state": "Karnataka",
        "category": "employment",
        "keywords": "employment job placement skill training bengaluru urban youth"
    },
    {
        "id": "karnataka-entrepreneur-024",
        "name": "Karnataka Entrepreneurship Development Programme",
        "description": "Support for entrepreneurs including training, mentorship and financial assistance for startups",
        "eligibility": {"age": "21-45", "income": "All", "category": "Aspiring entrepreneurs", "occupation": "entrepreneur"},
        "documents": ["Aadhaar", "Business Plan", "Educational Certificate", "Address Proof"],
        "state": "Karnataka",
        "category": "employment",
        "keywords": "entrepreneur startup business training financial assistance"
    },

    # SOCIAL WELFARE SCHEMES
    {
        "id": "sandhya-suraksha-yojana-025",
        "name": "Sandhya Suraksha Yojana",
        "description": "Monthly pension for senior citizens above 60 years from BPL families",
        "eligibility": {"age": "60+", "income": "BPL families", "category": "Senior citizens", "occupation": "All"},
        "documents": ["Aadhaar", "Age Proof", "BPL Card", "Bank Account"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "pension senior citizen elderly bpl sandhya suraksha"
    },
    {
        "id": "indira-canteen-026",
        "name": "Indira Canteen Scheme",
        "description": "Subsidized meals for economically weaker sections at affordable prices in urban areas",
        "eligibility": {"age": "All", "income": "All", "category": "All", "occupation": "All"},
        "documents": ["No documents required"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "food subsidy affordable meal urban indira canteen"
    },
    {
        "id": "ashraya-scheme-027",
        "name": "Ashraya Scheme",
        "description": "Comprehensive social security for people living below poverty line including pension and housing",
        "eligibility": {"age": "All", "income": "BPL families", "category": "Below Poverty Line", "occupation": "All"},
        "documents": ["Aadhaar", "BPL Card", "Income Certificate", "Bank Account"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "social security bpl pension housing ashraya"
    },
    {
        "id": "annabhagya-yojana-028",
        "name": "Annabhagya Yojana",
        "description": "Subsidized rice and food grains to BPL and Antyodaya families in Karnataka",
        "eligibility": {"age": "All", "income": "BPL and Antyodaya families", "category": "Below Poverty Line", "occupation": "All"},
        "documents": ["Aadhaar", "Ration Card", "BPL Card"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "food grain rice subsidy bpl ration annabhagya"
    },

    # DISABILITY WELFARE
    {
        "id": "rajeev-gandhi-vidyarthi-029",
        "name": "Rajeev Gandhi Vidyarthi Nidhi",
        "description": "Financial assistance for students with disabilities for education and mobility aids",
        "eligibility": {"age": "5-25", "income": "< 2.5 lakh", "category": "Students with disabilities", "occupation": "student"},
        "documents": ["Aadhaar", "Disability Certificate", "Income Certificate", "School Certificate"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "disability student education financial assistance rajeev gandhi"
    },
    {
        "id": "niramaya-health-030",
        "name": "Niramaya Health Insurance Scheme",
        "description": "Health insurance coverage for persons with disabilities for medical treatment and surgeries",
        "eligibility": {"age": "All", "income": "< 3 lakh", "category": "Persons with disabilities", "occupation": "All"},
        "documents": ["Aadhaar", "Disability Certificate", "Income Certificate", "Medical Records"],
        "state": "Karnataka",
        "category": "health",
        "keywords": "disability health insurance medical treatment niramaya"
    },

    # TRANSPORT & INFRASTRUCTURE
    {
        "id": "namma-metro-free-031",
        "name": "Namma Metro Free Travel",
        "description": "Free metro travel for visually impaired persons and senior citizens in Bengaluru",
        "eligibility": {"age": "All for visually impaired, 60+ for senior citizens", "income": "All", "category": "Visually impaired and senior citizens", "occupation": "All"},
        "documents": ["Aadhaar", "Disability Certificate or Age Proof"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "metro transport free travel bengaluru senior citizen visually impaired"
    },
    {
        "id": "bmtc-varisena-032",
        "name": "BMTC Varisena Pass",
        "description": "Concessional bus pass for senior citizens in Bengaluru city buses",
        "eligibility": {"age": "60+", "income": "All", "category": "Senior citizens", "occupation": "All"},
        "documents": ["Aadhaar", "Age Proof", "Passport Photo"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "bus pass senior citizen transport bengaluru bmtc varisena"
    },

    # MINORITY WELFARE
    {
        "id": "pre-matric-minority-033",
        "name": "Pre-Matric Scholarship for Minorities Karnataka",
        "description": "Scholarship for students from minority communities for education from Class 1 to 10",
        "eligibility": {"age": "6-16", "income": "< 2.5 lakh", "category": "Minority communities", "occupation": "student"},
        "documents": ["Aadhaar", "Income Certificate", "Community Certificate", "School Certificate"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "scholarship minority education student pre-matric"
    },
    {
        "id": "post-matric-minority-034",
        "name": "Post-Matric Scholarship for Minorities Karnataka",
        "description": "Financial assistance for minority students pursuing higher education after Class 10",
        "eligibility": {"age": "16-30", "income": "< 2.5 lakh", "category": "Minority communities", "occupation": "student"},
        "documents": ["Aadhaar", "Income Certificate", "Community Certificate", "College Fee Receipt"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "scholarship minority higher education post-matric"
    },

    # SC/ST WELFARE
    {
        "id": "post-matric-sc-st-035",
        "name": "Post-Matric Scholarship for SC/ST",
        "description": "Financial assistance for SC/ST students for higher education in Karnataka",
        "eligibility": {"age": "16-35", "income": "< 2.5 lakh", "category": "SC/ST", "occupation": "student"},
        "documents": ["Aadhaar", "Caste Certificate", "Income Certificate", "College Fee Receipt"],
        "state": "Karnataka",
        "category": "education",
        "keywords": "scholarship sc st higher education post-matric"
    },

    # DIGITAL INITIATIVES
    {
        "id": "seva-sindhu-036",
        "name": "Seva Sindhu Portal Services",
        "description": "Online platform for accessing 700+ government services including certificates and applications",
        "eligibility": {"age": "All", "income": "All", "category": "All", "occupation": "All"},
        "documents": ["Aadhaar", "Mobile Number", "Email ID"],
        "state": "Karnataka",
        "category": "social_welfare",
        "keywords": "digital online services certificate application seva sindhu"
    }
]

# Generate embeddings for all schemes
print(f"Generating embeddings for {len(schemes_data)} schemes...")

for scheme in schemes_data:
    # Create embedding text from name, description, and keywords
    embedding_text = f"{scheme['name']} {scheme['description']} {scheme['keywords']}"
    scheme['embedding'] = generate_mock_embedding(embedding_text)

# Create the final JSON structure
output_data = {"schemes": schemes_data}

# Write to file
with open('data/schemes.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {len(schemes_data)} schemes with embeddings")
print(f"Categories: {len(set(s['category'] for s in schemes_data))}")
print(f"States: {set(s['state'] for s in schemes_data)}")
print(f"Sample embedding dimension: {len(schemes_data[0]['embedding'])}")