#!/usr/bin/env python3
"""
Build comprehensive childwelfare.gov sitemap with all states and statute topics.
"""

import json
import re

# All states/territories/tribes from the sitemap
STATES = {
    "AL": {"name": "Alabama", "slug": "alabama"},
    "AK": {"name": "Alaska", "slug": "alaska"},
    "AZ": {"name": "Arizona", "slug": "arizona"},
    "AR": {"name": "Arkansas", "slug": "arkansas"},
    "CA": {"name": "California", "slug": "california"},
    "CO": {"name": "Colorado", "slug": "colorado"},
    "CT": {"name": "Connecticut", "slug": "connecticut"},
    "DE": {"name": "Delaware", "slug": "delaware"},
    "DC": {"name": "District of Columbia", "slug": "district-columbia"},
    "FL": {"name": "Florida", "slug": "florida"},
    "GA": {"name": "Georgia", "slug": "georgia"},
    "HI": {"name": "Hawaii", "slug": "hawaii"},
    "ID": {"name": "Idaho", "slug": "idaho"},
    "IL": {"name": "Illinois", "slug": "illinois"},
    "IN": {"name": "Indiana", "slug": "indiana"},
    "IA": {"name": "Iowa", "slug": "iowa"},
    "KS": {"name": "Kansas", "slug": "kansas"},
    "KY": {"name": "Kentucky", "slug": "kentucky"},
    "LA": {"name": "Louisiana", "slug": "louisiana"},
    "ME": {"name": "Maine", "slug": "maine"},
    "MD": {"name": "Maryland", "slug": "maryland"},
    "MA": {"name": "Massachusetts", "slug": "massachusetts"},
    "MI": {"name": "Michigan", "slug": "michigan"},
    "MN": {"name": "Minnesota", "slug": "minnesota"},
    "MS": {"name": "Mississippi", "slug": "mississippi"},
    "MO": {"name": "Missouri", "slug": "missouri"},
    "MT": {"name": "Montana", "slug": "montana"},
    "NE": {"name": "Nebraska", "slug": "nebraska"},
    "NV": {"name": "Nevada", "slug": "nevada"},
    "NH": {"name": "New Hampshire", "slug": "new-hampshire"},
    "NJ": {"name": "New Jersey", "slug": "new-jersey"},
    "NM": {"name": "New Mexico", "slug": "new-mexico"},
    "NY": {"name": "New York", "slug": "new-york"},
    "NC": {"name": "North Carolina", "slug": "north-carolina"},
    "ND": {"name": "North Dakota", "slug": "north-dakota"},
    "OH": {"name": "Ohio", "slug": "ohio"},
    "OK": {"name": "Oklahoma", "slug": "oklahoma"},
    "OR": {"name": "Oregon", "slug": "oregon"},
    "PA": {"name": "Pennsylvania", "slug": "pennsylvania"},
    "RI": {"name": "Rhode Island", "slug": "rhode-island"},
    "SC": {"name": "South Carolina", "slug": "south-carolina"},
    "SD": {"name": "South Dakota", "slug": "south-dakota"},
    "TN": {"name": "Tennessee", "slug": "tennessee"},
    "TX": {"name": "Texas", "slug": "texas"},
    "UT": {"name": "Utah", "slug": "utah"},
    "VT": {"name": "Vermont", "slug": "vermont"},
    "VA": {"name": "Virginia", "slug": "virginia"},
    "WA": {"name": "Washington", "slug": "washington"},
    "WV": {"name": "West Virginia", "slug": "west-virginia"},
    "WI": {"name": "Wisconsin", "slug": "wisconsin"},
    "WY": {"name": "Wyoming", "slug": "wyoming"},
}

TERRITORIES = {
    "AS": {"name": "American Samoa", "slug": "american-samoa"},
    "GU": {"name": "Guam", "slug": "guam"},
    "MP": {"name": "Northern Mariana Islands", "slug": "northern-mariana-islands"},
    "PR": {"name": "Puerto Rico", "slug": "puerto-rico"},
    "VI": {"name": "Virgin Islands", "slug": "virgin-islands"},
}

# Key state statute topics that have per-state pages
STATUTE_TOPICS = [
    {
        "topic_slug": "mandatory-reporting-child-abuse-and-neglect",
        "topic_name": "Mandatory Reporting of Child Abuse and Neglect",
        "description": "Who is required to report suspected child abuse/neglect"
    },
    {
        "topic_slug": "definitions-child-abuse-and-neglect", 
        "topic_name": "Definitions of Child Abuse and Neglect",
        "description": "Legal definitions of abuse and neglect in state law"
    },
    {
        "topic_slug": "making-and-screening-reports-child-abuse-and-neglect",
        "topic_name": "Making and Screening Reports of Child Abuse and Neglect", 
        "description": "How reports are made and screened"
    },
    {
        "topic_slug": "immunity-persons-who-report-child-abuse-and-neglect",
        "topic_name": "Immunity for Persons Who Report Child Abuse and Neglect",
        "description": "Legal protection for mandated reporters"
    },
    {
        "topic_slug": "grounds-involuntary-termination-parental-rights",
        "topic_name": "Grounds for Involuntary Termination of Parental Rights",
        "description": "Legal grounds for TPR proceedings"
    },
    {
        "topic_slug": "court-hearings-permanent-placement-children",
        "topic_name": "Court Hearings for Permanent Placement of Children",
        "description": "Court procedures for permanent placement"
    },
    {
        "topic_slug": "extension-foster-care-beyond-age-18",
        "topic_name": "Extension of Foster Care Beyond Age 18",
        "description": "Extended foster care provisions"
    },
    {
        "topic_slug": "responding-youth-missing-foster-care",
        "topic_name": "Responding to Youth Missing from Foster Care",
        "description": "Protocols for missing foster youth"
    },
    {
        "topic_slug": "consent-adoption",
        "topic_name": "Consent to Adoption",
        "description": "Consent requirements for adoption"
    },
    {
        "topic_slug": "access-adoption-records",
        "topic_name": "Access to Adoption Records",
        "description": "Rules for accessing adoption records"
    },
    {
        "topic_slug": "adoption-and-guardianship-assistance",
        "topic_name": "Adoption and Guardianship Assistance",
        "description": "Financial assistance for adoptive/guardian families"
    },
    {
        "topic_slug": "background-checks-prospective-foster-adoptive-and-kinship-caregivers",
        "topic_name": "Background Checks for Prospective Foster, Adoptive, and Kinship Caregivers",
        "description": "Background check requirements"
    },
    {
        "topic_slug": "child-witnesses-domestic-violence",
        "topic_name": "Child Witnesses to Domestic Violence",
        "description": "Legal provisions for child witnesses"
    },
    {
        "topic_slug": "case-planning-families-involved-child-welfare-agencies",
        "topic_name": "Case Planning for Families Involved with Child Welfare Agencies",
        "description": "Case planning requirements"
    },
    {
        "topic_slug": "cross-reporting-among-agencies-respond-child-abuse-and-neglect",
        "topic_name": "Cross-Reporting Among Agencies that Respond to Child Abuse and Neglect",
        "description": "Inter-agency reporting requirements"
    },
    {
        "topic_slug": "disclosure-confidential-child-abuse-and-neglect-records",
        "topic_name": "Disclosure of Confidential Child Abuse and Neglect Records",
        "description": "Confidentiality rules for CPS records"
    },
    {
        "topic_slug": "use-safety-and-risk-assessment-child-protection-cases",
        "topic_name": "Use of Safety and Risk Assessment in Child Protection Cases",
        "description": "Risk assessment requirements"
    },
    {
        "topic_slug": "definitions-domestic-violence",
        "topic_name": "Definitions of Domestic Violence",
        "description": "Legal definitions of domestic violence"
    },
    {
        "topic_slug": "completing-intercountry-adoptions-not-finalized-abroad",
        "topic_name": "Completing Intercountry Adoptions Not Finalized Abroad",
        "description": "Intercountry adoption procedures"
    },
    {
        "topic_slug": "court-jurisdiction-and-venue-adoption-petitions",
        "topic_name": "Court Jurisdiction and Venue for Adoption Petitions",
        "description": "Court jurisdiction for adoption"
    },
    {
        "topic_slug": "determining-best-interests-child",
        "topic_name": "Determining the Best Interests of the Child",
        "description": "Best interests determination factors"
    },
    {
        "topic_slug": "responding-child-victims-human-trafficking",
        "topic_name": "Responding to Child Victims of Human Trafficking",
        "description": "Protocols for trafficking victims"
    },
    {
        "topic_slug": "definitions-human-trafficking",
        "topic_name": "Definitions of Human Trafficking",
        "description": "Legal definitions of human trafficking"
    },
]

# Topic pages (not state-specific)
TOPIC_PAGES = [
    {"url": "https://www.childwelfare.gov/topics/safety-and-risk/definitions-child-abuse-and-neglect/", "name": "Definitions of Child Abuse and Neglect"},
    {"url": "https://www.childwelfare.gov/topics/safety-and-risk/mandated-reporting/", "name": "Mandated Reporting"},
    {"url": "https://www.childwelfare.gov/topics/safety-and-risk/trafficking-and-sexual-exploitation/", "name": "Trafficking and Sexual Exploitation"},
    {"url": "https://www.childwelfare.gov/topics/courts/", "name": "Courts"},
    {"url": "https://www.childwelfare.gov/topics/permanency/adoption/", "name": "Adoption"},
    {"url": "https://www.childwelfare.gov/topics/permanency/foster-care/", "name": "Foster Care"},
    {"url": "https://www.childwelfare.gov/topics/permanency/kinship-care/", "name": "Kinship Care"},
    {"url": "https://www.childwelfare.gov/topics/prevention/", "name": "Prevention"},
    {"url": "https://www.childwelfare.gov/topics/funding-laws-and-policies/laws-and-policies/", "name": "Laws and Policies"},
    {"url": "https://www.childwelfare.gov/topics/casework-practice/", "name": "Casework Practice"},
]

def build_sitemap():
    """Build complete sitemap structure."""
    
    sitemap = {
        "source": "childwelfare.gov",
        "generated_by": "PMC Spider Sitemap Builder",
        "base_urls": {
            "state_landing": "https://www.childwelfare.gov/resources/states-territories-tribes/{code}/",
            "state_statutes_search": "https://www.childwelfare.gov/resources/states-territories-tribes/state-statutes/",
            "statute_resource": "https://www.childwelfare.gov/resources/{topic_slug}-{state_slug}/"
        },
        "states": {},
        "territories": {},
        "statute_topics": STATUTE_TOPICS,
        "topic_pages": TOPIC_PAGES,
        "statistics": {}
    }
    
    # Build state entries with all statute URLs
    for code, info in STATES.items():
        state_entry = {
            "code": code,
            "name": info["name"],
            "slug": info["slug"],
            "landing_page": f"https://www.childwelfare.gov/resources/states-territories-tribes/{code.lower()}/",
            "statutes": {}
        }
        
        # Generate all statute topic URLs for this state
        for topic in STATUTE_TOPICS:
            state_entry["statutes"][topic["topic_slug"]] = {
                "name": topic["topic_name"],
                "url": f"https://www.childwelfare.gov/resources/{topic['topic_slug']}-{info['slug']}/"
            }
        
        sitemap["states"][code] = state_entry
    
    # Build territory entries
    for code, info in TERRITORIES.items():
        terr_entry = {
            "code": code,
            "name": info["name"],
            "slug": info["slug"],
            "landing_page": f"https://www.childwelfare.gov/resources/states-territories-tribes/{code.lower()}/",
            "statutes": {}
        }
        
        for topic in STATUTE_TOPICS:
            terr_entry["statutes"][topic["topic_slug"]] = {
                "name": topic["topic_name"],
                "url": f"https://www.childwelfare.gov/resources/{topic['topic_slug']}-{info['slug']}/"
            }
        
        sitemap["territories"][code] = terr_entry
    
    # Statistics
    sitemap["statistics"] = {
        "total_states": len(STATES),
        "total_territories": len(TERRITORIES),
        "total_statute_topics": len(STATUTE_TOPICS),
        "total_statute_urls": len(STATES) * len(STATUTE_TOPICS) + len(TERRITORIES) * len(STATUTE_TOPICS),
        "total_topic_pages": len(TOPIC_PAGES)
    }
    
    return sitemap

if __name__ == "__main__":
    sitemap = build_sitemap()
    
    output_path = "./data/sources/childwelfare_comprehensive_sitemap.json"
    with open(output_path, 'w') as f:
        json.dump(sitemap, f, indent=2)
    
    print(f"=== COMPREHENSIVE SITEMAP BUILT ===")
    print(f"States: {sitemap['statistics']['total_states']}")
    print(f"Territories: {sitemap['statistics']['total_territories']}")
    print(f"Statute Topics: {sitemap['statistics']['total_statute_topics']}")
    print(f"Total Statute URLs: {sitemap['statistics']['total_statute_urls']}")
    print(f"Saved to: {output_path}")
    
    # Print example for Texas
    print(f"\n=== TEXAS EXAMPLE ===")
    tx = sitemap["states"]["TX"]
    print(f"Landing: {tx['landing_page']}")
    for topic_slug, topic_data in list(tx["statutes"].items())[:5]:
        print(f"  {topic_data['name']}: {topic_data['url']}")
