#!/usr/bin/env python3
"""
Generate comprehensive legal resource links for ALL 50 states.
Matches the Alabama structure with state constitution, codes, admin rules,
state courts, federal courts, and resources.

Project Milk Carton 501(c)(3) - All Rights Reserved
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

# Output directory
OUTPUT_DIR = Path("./data/sources")

# State metadata: (name, abbrev, federal_circuit, district_courts)
# District courts format: list of (district_name, url_slug)
STATE_METADATA = {
    "alabama": {
        "name": "Alabama",
        "abbrev": "AL",
        "circuit": "11th",
        "circuit_slug": "eleventh-circuit",
        "districts": [
            ("Middle District", "alabama/middle-district"),
            ("Northern District", "alabama/northern-district"),
            ("Southern District", "alabama/southern-district"),
        ],
        "court_of_appeals_civil": True,
        "court_of_appeals_criminal": True,
    },
    "alaska": {
        "name": "Alaska",
        "abbrev": "AK",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Alaska", "alaska"),
        ],
        "court_of_appeals": True,  # Combined appeals court
    },
    "arizona": {
        "name": "Arizona",
        "abbrev": "AZ",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Arizona", "arizona"),
        ],
        "court_of_appeals": True,
    },
    "arkansas": {
        "name": "Arkansas",
        "abbrev": "AR",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("Eastern District", "arkansas/eastern-district"),
            ("Western District", "arkansas/western-district"),
        ],
        "court_of_appeals": True,
    },
    "california": {
        "name": "California",
        "abbrev": "CA",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("Central District", "california/central-district"),
            ("Eastern District", "california/eastern-district"),
            ("Northern District", "california/northern-district"),
            ("Southern District", "california/southern-district"),
        ],
        "court_of_appeal": True,  # CA uses singular "Court of Appeal"
    },
    "colorado": {
        "name": "Colorado",
        "abbrev": "CO",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("District of Colorado", "colorado"),
        ],
        "court_of_appeals": True,
    },
    "connecticut": {
        "name": "Connecticut",
        "abbrev": "CT",
        "circuit": "2nd",
        "circuit_slug": "second-circuit",
        "districts": [
            ("District of Connecticut", "connecticut"),
        ],
        "appellate_court": True,
    },
    "delaware": {
        "name": "Delaware",
        "abbrev": "DE",
        "circuit": "3rd",
        "circuit_slug": "third-circuit",
        "districts": [
            ("District of Delaware", "delaware"),
        ],
        # Delaware has no intermediate appellate court
    },
    "florida": {
        "name": "Florida",
        "abbrev": "FL",
        "circuit": "11th",
        "circuit_slug": "eleventh-circuit",
        "districts": [
            ("Middle District", "florida/middle-district"),
            ("Northern District", "florida/northern-district"),
            ("Southern District", "florida/southern-district"),
        ],
        "district_court_of_appeal": True,  # FL uses district courts of appeal
    },
    "georgia": {
        "name": "Georgia",
        "abbrev": "GA",
        "circuit": "11th",
        "circuit_slug": "eleventh-circuit",
        "districts": [
            ("Middle District", "georgia/middle-district"),
            ("Northern District", "georgia/northern-district"),
            ("Southern District", "georgia/southern-district"),
        ],
        "court_of_appeals": True,
    },
    "hawaii": {
        "name": "Hawaii",
        "abbrev": "HI",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Hawaii", "hawaii"),
        ],
        "intermediate_court_of_appeals": True,
    },
    "idaho": {
        "name": "Idaho",
        "abbrev": "ID",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Idaho", "idaho"),
        ],
        "court_of_appeals": True,
    },
    "illinois": {
        "name": "Illinois",
        "abbrev": "IL",
        "circuit": "7th",
        "circuit_slug": "seventh-circuit",
        "districts": [
            ("Central District", "illinois/central-district"),
            ("Northern District", "illinois/northern-district"),
            ("Southern District", "illinois/southern-district"),
        ],
        "appellate_court": True,
    },
    "indiana": {
        "name": "Indiana",
        "abbrev": "IN",
        "circuit": "7th",
        "circuit_slug": "seventh-circuit",
        "districts": [
            ("Northern District", "indiana/northern-district"),
            ("Southern District", "indiana/southern-district"),
        ],
        "court_of_appeals": True,
    },
    "iowa": {
        "name": "Iowa",
        "abbrev": "IA",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("Northern District", "iowa/northern-district"),
            ("Southern District", "iowa/southern-district"),
        ],
        "court_of_appeals": True,
    },
    "kansas": {
        "name": "Kansas",
        "abbrev": "KS",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("District of Kansas", "kansas"),
        ],
        "court_of_appeals": True,
    },
    "kentucky": {
        "name": "Kentucky",
        "abbrev": "KY",
        "circuit": "6th",
        "circuit_slug": "sixth-circuit",
        "districts": [
            ("Eastern District", "kentucky/eastern-district"),
            ("Western District", "kentucky/western-district"),
        ],
        "court_of_appeals": True,
    },
    "louisiana": {
        "name": "Louisiana",
        "abbrev": "LA",
        "circuit": "5th",
        "circuit_slug": "fifth-circuit",
        "districts": [
            ("Eastern District", "louisiana/eastern-district"),
            ("Middle District", "louisiana/middle-district"),
            ("Western District", "louisiana/western-district"),
        ],
        "court_of_appeal": True,  # LA uses singular
    },
    "maine": {
        "name": "Maine",
        "abbrev": "ME",
        "circuit": "1st",
        "circuit_slug": "first-circuit",
        "districts": [
            ("District of Maine", "maine"),
        ],
        # Maine has no intermediate appellate court (Supreme Judicial Court only)
    },
    "maryland": {
        "name": "Maryland",
        "abbrev": "MD",
        "circuit": "4th",
        "circuit_slug": "fourth-circuit",
        "districts": [
            ("District of Maryland", "maryland"),
        ],
        "court_of_special_appeals": True,  # MD's intermediate court
    },
    "massachusetts": {
        "name": "Massachusetts",
        "abbrev": "MA",
        "circuit": "1st",
        "circuit_slug": "first-circuit",
        "districts": [
            ("District of Massachusetts", "massachusetts"),
        ],
        "appeals_court": True,
    },
    "michigan": {
        "name": "Michigan",
        "abbrev": "MI",
        "circuit": "6th",
        "circuit_slug": "sixth-circuit",
        "districts": [
            ("Eastern District", "michigan/eastern-district"),
            ("Western District", "michigan/western-district"),
        ],
        "court_of_appeals": True,
    },
    "minnesota": {
        "name": "Minnesota",
        "abbrev": "MN",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("District of Minnesota", "minnesota"),
        ],
        "court_of_appeals": True,
    },
    "mississippi": {
        "name": "Mississippi",
        "abbrev": "MS",
        "circuit": "5th",
        "circuit_slug": "fifth-circuit",
        "districts": [
            ("Northern District", "mississippi/northern-district"),
            ("Southern District", "mississippi/southern-district"),
        ],
        "court_of_appeals": True,
    },
    "missouri": {
        "name": "Missouri",
        "abbrev": "MO",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("Eastern District", "missouri/eastern-district"),
            ("Western District", "missouri/western-district"),
        ],
        "court_of_appeals": True,
    },
    "montana": {
        "name": "Montana",
        "abbrev": "MT",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Montana", "montana"),
        ],
        # Montana has no intermediate appellate court
    },
    "nebraska": {
        "name": "Nebraska",
        "abbrev": "NE",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("District of Nebraska", "nebraska"),
        ],
        "court_of_appeals": True,
    },
    "nevada": {
        "name": "Nevada",
        "abbrev": "NV",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Nevada", "nevada"),
        ],
        "court_of_appeals": True,
    },
    "new-hampshire": {
        "name": "New Hampshire",
        "abbrev": "NH",
        "circuit": "1st",
        "circuit_slug": "first-circuit",
        "districts": [
            ("District of New Hampshire", "new-hampshire"),
        ],
        # NH has no intermediate appellate court
    },
    "new-jersey": {
        "name": "New Jersey",
        "abbrev": "NJ",
        "circuit": "3rd",
        "circuit_slug": "third-circuit",
        "districts": [
            ("District of New Jersey", "new-jersey"),
        ],
        "appellate_division": True,  # NJ uses Superior Court, Appellate Division
    },
    "new-mexico": {
        "name": "New Mexico",
        "abbrev": "NM",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("District of New Mexico", "new-mexico"),
        ],
        "court_of_appeals": True,
    },
    "new-york": {
        "name": "New York",
        "abbrev": "NY",
        "circuit": "2nd",
        "circuit_slug": "second-circuit",
        "districts": [
            ("Eastern District", "new-york/eastern-district"),
            ("Northern District", "new-york/northern-district"),
            ("Southern District", "new-york/southern-district"),
            ("Western District", "new-york/western-district"),
        ],
        "appellate_division": True,  # NY has Appellate Division
    },
    "north-carolina": {
        "name": "North Carolina",
        "abbrev": "NC",
        "circuit": "4th",
        "circuit_slug": "fourth-circuit",
        "districts": [
            ("Eastern District", "north-carolina/eastern-district"),
            ("Middle District", "north-carolina/middle-district"),
            ("Western District", "north-carolina/western-district"),
        ],
        "court_of_appeals": True,
    },
    "north-dakota": {
        "name": "North Dakota",
        "abbrev": "ND",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("District of North Dakota", "north-dakota"),
        ],
        # ND has no intermediate appellate court (recently added Court of Appeals)
        "court_of_appeals": True,
    },
    "ohio": {
        "name": "Ohio",
        "abbrev": "OH",
        "circuit": "6th",
        "circuit_slug": "sixth-circuit",
        "districts": [
            ("Northern District", "ohio/northern-district"),
            ("Southern District", "ohio/southern-district"),
        ],
        "court_of_appeals": True,  # OH has district courts of appeal
    },
    "oklahoma": {
        "name": "Oklahoma",
        "abbrev": "OK",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("Eastern District", "oklahoma/eastern-district"),
            ("Northern District", "oklahoma/northern-district"),
            ("Western District", "oklahoma/western-district"),
        ],
        "court_of_civil_appeals": True,
        "court_of_criminal_appeals": True,
    },
    "oregon": {
        "name": "Oregon",
        "abbrev": "OR",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("District of Oregon", "oregon"),
        ],
        "court_of_appeals": True,
    },
    "pennsylvania": {
        "name": "Pennsylvania",
        "abbrev": "PA",
        "circuit": "3rd",
        "circuit_slug": "third-circuit",
        "districts": [
            ("Eastern District", "pennsylvania/eastern-district"),
            ("Middle District", "pennsylvania/middle-district"),
            ("Western District", "pennsylvania/western-district"),
        ],
        "superior_court": True,  # PA's intermediate appellate court
        "commonwealth_court": True,  # PA also has Commonwealth Court
    },
    "rhode-island": {
        "name": "Rhode Island",
        "abbrev": "RI",
        "circuit": "1st",
        "circuit_slug": "first-circuit",
        "districts": [
            ("District of Rhode Island", "rhode-island"),
        ],
        # RI has no intermediate appellate court
    },
    "south-carolina": {
        "name": "South Carolina",
        "abbrev": "SC",
        "circuit": "4th",
        "circuit_slug": "fourth-circuit",
        "districts": [
            ("District of South Carolina", "south-carolina"),
        ],
        "court_of_appeals": True,
    },
    "south-dakota": {
        "name": "South Dakota",
        "abbrev": "SD",
        "circuit": "8th",
        "circuit_slug": "eighth-circuit",
        "districts": [
            ("District of South Dakota", "south-dakota"),
        ],
        # SD has no intermediate appellate court
    },
    "tennessee": {
        "name": "Tennessee",
        "abbrev": "TN",
        "circuit": "6th",
        "circuit_slug": "sixth-circuit",
        "districts": [
            ("Eastern District", "tennessee/eastern-district"),
            ("Middle District", "tennessee/middle-district"),
            ("Western District", "tennessee/western-district"),
        ],
        "court_of_appeals": True,
        "court_of_criminal_appeals": True,
    },
    "texas": {
        "name": "Texas",
        "abbrev": "TX",
        "circuit": "5th",
        "circuit_slug": "fifth-circuit",
        "districts": [
            ("Eastern District", "texas/eastern-district"),
            ("Northern District", "texas/northern-district"),
            ("Southern District", "texas/southern-district"),
            ("Western District", "texas/western-district"),
        ],
        "court_of_appeals": True,  # TX has multiple district courts of appeals
        "court_of_criminal_appeals": True,
    },
    "utah": {
        "name": "Utah",
        "abbrev": "UT",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("District of Utah", "utah"),
        ],
        "court_of_appeals": True,
    },
    "vermont": {
        "name": "Vermont",
        "abbrev": "VT",
        "circuit": "2nd",
        "circuit_slug": "second-circuit",
        "districts": [
            ("District of Vermont", "vermont"),
        ],
        # VT has no intermediate appellate court
    },
    "virginia": {
        "name": "Virginia",
        "abbrev": "VA",
        "circuit": "4th",
        "circuit_slug": "fourth-circuit",
        "districts": [
            ("Eastern District", "virginia/eastern-district"),
            ("Western District", "virginia/western-district"),
        ],
        "court_of_appeals": True,
    },
    "washington": {
        "name": "Washington",
        "abbrev": "WA",
        "circuit": "9th",
        "circuit_slug": "ninth-circuit",
        "districts": [
            ("Eastern District", "washington/eastern-district"),
            ("Western District", "washington/western-district"),
        ],
        "court_of_appeals": True,
    },
    "west-virginia": {
        "name": "West Virginia",
        "abbrev": "WV",
        "circuit": "4th",
        "circuit_slug": "fourth-circuit",
        "districts": [
            ("Northern District", "west-virginia/northern-district"),
            ("Southern District", "west-virginia/southern-district"),
        ],
        # WV recently added intermediate appellate court
        "intermediate_court_of_appeals": True,
    },
    "wisconsin": {
        "name": "Wisconsin",
        "abbrev": "WI",
        "circuit": "7th",
        "circuit_slug": "seventh-circuit",
        "districts": [
            ("Eastern District", "wisconsin/eastern-district"),
            ("Western District", "wisconsin/western-district"),
        ],
        "court_of_appeals": True,
    },
    "wyoming": {
        "name": "Wyoming",
        "abbrev": "WY",
        "circuit": "10th",
        "circuit_slug": "tenth-circuit",
        "districts": [
            ("District of Wyoming", "wyoming"),
        ],
        # WY has no intermediate appellate court
    },
    "district-of-columbia": {
        "name": "District of Columbia",
        "abbrev": "DC",
        "circuit": "DC",
        "circuit_slug": "dc-circuit",
        "districts": [
            ("District of Columbia", "district-of-columbia"),
        ],
        "court_of_appeals": True,
    },
}

def generate_state_links(state_key: str, metadata: Dict) -> Dict:
    """Generate comprehensive legal resource links for a state."""

    state_name = metadata["name"]
    state_abbrev = metadata["abbrev"]
    state_slug = state_key  # URL-friendly name

    result = {
        "state": state_name,
        "abbreviation": state_abbrev,
        "slug": state_slug,
        "generated": "2025-12-23",
        "copyright": "Project Milk Carton 501(c)(3) - All Rights Reserved",
        "sources": {}
    }

    # 1. State Constitution
    result["sources"]["constitution"] = {
        "name": f"{state_name} Constitution",
        "url": f"https://law.justia.com/constitution/{state_slug}/",
        "description": f"Full text of the {state_name} State Constitution with all articles and amendments"
    }

    # 2. State Codes/Statutes
    result["sources"]["statutes"] = {
        "name": f"{state_name} Statutes",
        "url": f"https://law.justia.com/codes/{state_slug}/",
        "description": f"Complete {state_name} statutory code organized by title/chapter"
    }

    # 3. Administrative Code/Regulations
    result["sources"]["regulations"] = {
        "name": f"{state_name} Administrative Code",
        "url": f"https://regulations.justia.com/states/{state_slug}/",
        "description": f"{state_name} administrative rules and regulations by agency"
    }

    # 4. State Supreme Court
    result["sources"]["supreme_court"] = {
        "name": f"{state_name} Supreme Court",
        "url": f"https://law.justia.com/cases/{state_slug}/supreme-court/",
        "description": f"Published opinions from the {state_name} Supreme Court"
    }

    # 5. State Appellate Courts (varies by state)
    appellate_courts = []

    # Alabama-style split appellate courts
    if metadata.get("court_of_appeals_civil"):
        appellate_courts.append({
            "name": f"{state_name} Court of Civil Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-civil-appeals/",
            "type": "civil_appeals"
        })
    if metadata.get("court_of_appeals_criminal"):
        appellate_courts.append({
            "name": f"{state_name} Court of Criminal Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-criminal-appeals/",
            "type": "criminal_appeals"
        })

    # Oklahoma/Texas style
    if metadata.get("court_of_civil_appeals"):
        appellate_courts.append({
            "name": f"{state_name} Court of Civil Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-civil-appeals/",
            "type": "civil_appeals"
        })
    if metadata.get("court_of_criminal_appeals") and not metadata.get("court_of_appeals_criminal"):
        appellate_courts.append({
            "name": f"{state_name} Court of Criminal Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-criminal-appeals/",
            "type": "criminal_appeals"
        })

    # Unified Court of Appeals
    if metadata.get("court_of_appeals") and not (metadata.get("court_of_appeals_civil") or metadata.get("court_of_civil_appeals")):
        appellate_courts.append({
            "name": f"{state_name} Court of Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-appeals/",
            "type": "appeals"
        })

    # California-style Court of Appeal
    if metadata.get("court_of_appeal"):
        appellate_courts.append({
            "name": f"{state_name} Court of Appeal",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-appeal/",
            "type": "appeals"
        })

    # Florida-style District Court of Appeal
    if metadata.get("district_court_of_appeal"):
        appellate_courts.append({
            "name": f"{state_name} District Courts of Appeal",
            "url": f"https://law.justia.com/cases/{state_slug}/district-court-of-appeal/",
            "type": "appeals"
        })

    # Connecticut/Illinois/NY style Appellate Court/Division
    if metadata.get("appellate_court"):
        appellate_courts.append({
            "name": f"{state_name} Appellate Court",
            "url": f"https://law.justia.com/cases/{state_slug}/appellate-court/",
            "type": "appeals"
        })
    if metadata.get("appellate_division"):
        appellate_courts.append({
            "name": f"{state_name} Appellate Division",
            "url": f"https://law.justia.com/cases/{state_slug}/appellate-division/",
            "type": "appeals"
        })

    # Massachusetts-style Appeals Court
    if metadata.get("appeals_court"):
        appellate_courts.append({
            "name": f"{state_name} Appeals Court",
            "url": f"https://law.justia.com/cases/{state_slug}/appeals-court/",
            "type": "appeals"
        })

    # Maryland Court of Special Appeals
    if metadata.get("court_of_special_appeals"):
        appellate_courts.append({
            "name": f"{state_name} Court of Special Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/court-of-special-appeals/",
            "type": "appeals"
        })

    # Pennsylvania Superior Court
    if metadata.get("superior_court"):
        appellate_courts.append({
            "name": f"{state_name} Superior Court",
            "url": f"https://law.justia.com/cases/{state_slug}/superior-court/",
            "type": "appeals"
        })
    if metadata.get("commonwealth_court"):
        appellate_courts.append({
            "name": f"{state_name} Commonwealth Court",
            "url": f"https://law.justia.com/cases/{state_slug}/commonwealth-court/",
            "type": "appeals"
        })

    # Hawaii/West Virginia Intermediate Court of Appeals
    if metadata.get("intermediate_court_of_appeals"):
        appellate_courts.append({
            "name": f"{state_name} Intermediate Court of Appeals",
            "url": f"https://law.justia.com/cases/{state_slug}/intermediate-court-of-appeals/",
            "type": "appeals"
        })

    result["sources"]["appellate_courts"] = appellate_courts

    # 6. Federal Circuit Court
    circuit = metadata["circuit"]
    circuit_slug = metadata["circuit_slug"]
    result["sources"]["federal_circuit"] = {
        "name": f"U.S. Court of Appeals for the {circuit} Circuit",
        "url": f"https://law.justia.com/cases/federal/appellate-courts/{circuit_slug}/",
        "circuit": circuit,
        "description": f"Federal appellate court with jurisdiction over {state_name}"
    }

    # 7. Federal District Courts
    district_courts = []
    for district_name, district_slug in metadata["districts"]:
        district_courts.append({
            "name": f"U.S. District Court, {district_name}",
            "url": f"https://law.justia.com/cases/federal/district-courts/{district_slug}/",
            "slug": district_slug
        })
    result["sources"]["federal_districts"] = district_courts

    # 8. State Resources Hub
    result["sources"]["resources"] = {
        "name": f"{state_name} Legal Resources",
        "url": f"https://www.justia.com/lawyers/{state_slug}/",
        "alt_url": f"https://law.justia.com/codes/{state_slug}/",
        "description": f"General {state_name} legal information, counties, and resources"
    }

    # 9. Child Welfare specific resources (childwelfare.gov)
    result["sources"]["child_welfare"] = {
        "name": f"{state_name} Child Welfare Resources",
        "base_url": "https://www.childwelfare.gov/topics/systemwide/laws-policies/state/",
        "topics": [
            {
                "name": "Mandatory Reporting",
                "url": f"https://www.childwelfare.gov/topics/systemwide/laws-policies/state/?CWIGFunctionsaction=statestatutes:main.getResults&statestatutesSearch.statesSelect={state_abbrev}&statestatutesSearch.topicsSelect=1"
            },
            {
                "name": "Definitions of Child Abuse",
                "url": f"https://www.childwelfare.gov/topics/systemwide/laws-policies/state/?CWIGFunctionsaction=statestatutes:main.getResults&statestatutesSearch.statesSelect={state_abbrev}&statestatutesSearch.topicsSelect=2"
            },
            {
                "name": "Immunity for Reporters",
                "url": f"https://www.childwelfare.gov/topics/systemwide/laws-policies/state/?CWIGFunctionsaction=statestatutes:main.getResults&statestatutesSearch.statesSelect={state_abbrev}&statestatutesSearch.topicsSelect=3"
            },
        ]
    }

    return result


def generate_all_states() -> Dict[str, Dict]:
    """Generate links for all 50 states + DC."""

    all_states = {}

    for state_key, metadata in STATE_METADATA.items():
        print(f"Generating links for {metadata['name']}...")
        all_states[state_key] = generate_state_links(state_key, metadata)

    return all_states


def write_state_files(all_states: Dict[str, Dict]):
    """Write individual state JSON files and master index."""

    # Create output directories
    states_dir = OUTPUT_DIR / "state_legal_links"
    states_dir.mkdir(parents=True, exist_ok=True)

    # Write individual state files
    for state_key, state_data in all_states.items():
        state_file = states_dir / f"{state_key}.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)
        print(f"  Wrote {state_file}")

    # Write master index
    index_file = OUTPUT_DIR / "all_state_legal_links.json"
    master_index = {
        "generated": "2025-12-23",
        "copyright": "Project Milk Carton 501(c)(3) - All Rights Reserved",
        "description": "Comprehensive legal resource links for all 50 states and DC",
        "source_patterns": {
            "constitution": "https://law.justia.com/constitution/{state}/",
            "statutes": "https://law.justia.com/codes/{state}/",
            "regulations": "https://regulations.justia.com/states/{state}/",
            "supreme_court": "https://law.justia.com/cases/{state}/supreme-court/",
            "appellate_courts": "https://law.justia.com/cases/{state}/{court-type}/",
            "federal_circuit": "https://law.justia.com/cases/federal/appellate-courts/{circuit}/",
            "federal_district": "https://law.justia.com/cases/federal/district-courts/{state}/{district}/",
        },
        "state_count": len(all_states),
        "states": all_states
    }

    with open(index_file, "w") as f:
        json.dump(master_index, f, indent=2)
    print(f"\nWrote master index: {index_file}")

    # Also write a simplified text version (like Alabama format)
    txt_file = OUTPUT_DIR / "all_state_legal_links.txt"
    with open(txt_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("COMPREHENSIVE LEGAL RESOURCE INDEX - ALL 50 STATES + DC\n")
        f.write("Project Milk Carton 501(c)(3) - All Rights Reserved\n")
        f.write("Generated: 2025-12-23\n")
        f.write("=" * 80 + "\n\n")

        for state_key, state_data in sorted(all_states.items()):
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"{state_data['state'].upper()} ({state_data['abbreviation']})\n")
            f.write("=" * 80 + "\n\n")

            sources = state_data["sources"]

            # Constitution
            f.write(f"STATE CONSTITUTION:\n")
            f.write(f"  {sources['constitution']['url']}\n\n")

            # Statutes
            f.write(f"STATE STATUTES:\n")
            f.write(f"  {sources['statutes']['url']}\n\n")

            # Regulations
            f.write(f"ADMINISTRATIVE CODE:\n")
            f.write(f"  {sources['regulations']['url']}\n\n")

            # Supreme Court
            f.write(f"STATE SUPREME COURT:\n")
            f.write(f"  {sources['supreme_court']['url']}\n\n")

            # Appellate Courts
            if sources.get('appellate_courts'):
                f.write(f"STATE APPELLATE COURTS:\n")
                for court in sources['appellate_courts']:
                    f.write(f"  {court['name']}:\n")
                    f.write(f"    {court['url']}\n")
                f.write("\n")

            # Federal Circuit
            f.write(f"FEDERAL CIRCUIT COURT ({sources['federal_circuit']['circuit']} Circuit):\n")
            f.write(f"  {sources['federal_circuit']['url']}\n\n")

            # Federal Districts
            f.write(f"FEDERAL DISTRICT COURTS:\n")
            for district in sources['federal_districts']:
                f.write(f"  {district['name']}:\n")
                f.write(f"    {district['url']}\n")
            f.write("\n")

            # Child Welfare
            f.write(f"CHILD WELFARE RESOURCES:\n")
            for topic in sources['child_welfare']['topics']:
                f.write(f"  {topic['name']}:\n")
                f.write(f"    {topic['url']}\n")
            f.write("\n")

    print(f"Wrote text version: {txt_file}")


def main():
    print("=" * 60)
    print("GENERATING COMPREHENSIVE LEGAL LINKS FOR ALL 50 STATES + DC")
    print("=" * 60)
    print()

    # Generate all state links
    all_states = generate_all_states()

    print(f"\nGenerated links for {len(all_states)} states/territories")

    # Write output files
    write_state_files(all_states)

    print("\n" + "=" * 60)
    print("DONE! All state legal links generated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
