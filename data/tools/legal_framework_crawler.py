#!/usr/bin/env python3
"""
LEGAL FRAMEWORK CRAWLER - Full 6-Layer Architecture

Generates Alabama-style legal resource index for ALL 50 states:
  - State Constitution (all sections)
  - State Codes (all titles)
  - Administrative Code (all titles)
  - Supreme Court (all years)
  - Civil Appeals (all years)
  - Criminal Appeals (all years)
  - Federal Circuit Court
  - Federal District Courts
  - Counties/Cities/Metros

Layers:
  1. Discovery - Find every relevant URL
  2. Validation - Confirm page exists & serves HTML
  3. Extraction - Pull metadata + structured data
  4. Normalization - Coerce into unified schema
  5. Persistence - Hash, version, store (append-only)
  6. Drift Detection - Know when it changes

Project Milk Carton 501(c)(3) - All Rights Reserved
"""

import json
import hashlib
import asyncio
import aiohttp
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from urllib.parse import urljoin
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

# Optional libraries
try:
    import extruct
    from w3lib.html import get_base_url
    HAS_EXTRUCT = True
except ImportError:
    HAS_EXTRUCT = False

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    import tldextract
    HAS_TLDEXTRACT = True
except ImportError:
    HAS_TLDEXTRACT = False

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = Path("./data/sources/legal_framework")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 20
RATE_LIMIT_DELAY = 0.25
MAX_CONCURRENT = 5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ============================================================================
# LAYER 0: AUTHORITATIVE STATE METADATA
# ============================================================================

@dataclass
class StateMetadata:
    """Complete metadata for a US state."""
    name: str
    slug: str
    abbrev: str
    fips: str
    circuit: str
    circuit_slug: str
    districts: List[Tuple[str, str]]  # (name, url_slug)
    appellate_courts: List[str]  # court slugs
    code_title_range: Tuple[int, int]  # (min, max) title numbers
    admin_title_range: Tuple[int, int]  # (min, max) admin title numbers
    case_year_range: Tuple[int, int]  # (min, max) years


# Complete state metadata - this is the source of truth
STATES: Dict[str, StateMetadata] = {
    "alabama": StateMetadata(
        name="Alabama", slug="alabama", abbrev="AL", fips="01",
        circuit="11th", circuit_slug="eleventh-circuit",
        districts=[
            ("Middle District", "alabama/middle-district"),
            ("Northern District", "alabama/northern-district"),
            ("Southern District", "alabama/southern-district"),
        ],
        appellate_courts=["court-of-civil-appeals", "court-of-criminal-appeals"],
        code_title_range=(1, 45),
        admin_title_range=(20, 950),
        case_year_range=(1845, 2025),
    ),
    "alaska": StateMetadata(
        name="Alaska", slug="alaska", abbrev="AK", fips="02",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Alaska", "alaska")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 47),
        admin_title_range=(1, 20),
        case_year_range=(1959, 2025),
    ),
    "arizona": StateMetadata(
        name="Arizona", slug="arizona", abbrev="AZ", fips="04",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Arizona", "arizona")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 49),
        admin_title_range=(1, 20),
        case_year_range=(1912, 2025),
    ),
    "arkansas": StateMetadata(
        name="Arkansas", slug="arkansas", abbrev="AR", fips="05",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[
            ("Eastern District", "arkansas/eastern-district"),
            ("Western District", "arkansas/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 28),
        admin_title_range=(1, 200),
        case_year_range=(1836, 2025),
    ),
    "california": StateMetadata(
        name="California", slug="california", abbrev="CA", fips="06",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[
            ("Central District", "california/central-district"),
            ("Eastern District", "california/eastern-district"),
            ("Northern District", "california/northern-district"),
            ("Southern District", "california/southern-district"),
        ],
        appellate_courts=["court-of-appeal"],
        code_title_range=(1, 30),  # CA uses named codes not numbered
        admin_title_range=(1, 25),
        case_year_range=(1850, 2025),
    ),
    "colorado": StateMetadata(
        name="Colorado", slug="colorado", abbrev="CO", fips="08",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[("District of Colorado", "colorado")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 44),
        admin_title_range=(1, 12),
        case_year_range=(1876, 2025),
    ),
    "connecticut": StateMetadata(
        name="Connecticut", slug="connecticut", abbrev="CT", fips="09",
        circuit="2nd", circuit_slug="second-circuit",
        districts=[("District of Connecticut", "connecticut")],
        appellate_courts=["appellate-court"],
        code_title_range=(1, 54),
        admin_title_range=(1, 31),
        case_year_range=(1785, 2025),
    ),
    "delaware": StateMetadata(
        name="Delaware", slug="delaware", abbrev="DE", fips="10",
        circuit="3rd", circuit_slug="third-circuit",
        districts=[("District of Delaware", "delaware")],
        appellate_courts=[],  # No intermediate appellate court
        code_title_range=(1, 31),
        admin_title_range=(1, 30),
        case_year_range=(1792, 2025),
    ),
    "florida": StateMetadata(
        name="Florida", slug="florida", abbrev="FL", fips="12",
        circuit="11th", circuit_slug="eleventh-circuit",
        districts=[
            ("Middle District", "florida/middle-district"),
            ("Northern District", "florida/northern-district"),
            ("Southern District", "florida/southern-district"),
        ],
        appellate_courts=["district-court-of-appeal"],
        code_title_range=(1, 50),
        admin_title_range=(1, 69),
        case_year_range=(1846, 2025),
    ),
    "georgia": StateMetadata(
        name="Georgia", slug="georgia", abbrev="GA", fips="13",
        circuit="11th", circuit_slug="eleventh-circuit",
        districts=[
            ("Middle District", "georgia/middle-district"),
            ("Northern District", "georgia/northern-district"),
            ("Southern District", "georgia/southern-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 53),
        admin_title_range=(1, 700),
        case_year_range=(1846, 2025),
    ),
    "hawaii": StateMetadata(
        name="Hawaii", slug="hawaii", abbrev="HI", fips="15",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Hawaii", "hawaii")],
        appellate_courts=["intermediate-court-of-appeals"],
        code_title_range=(1, 29),
        admin_title_range=(1, 20),
        case_year_range=(1959, 2025),
    ),
    "idaho": StateMetadata(
        name="Idaho", slug="idaho", abbrev="ID", fips="16",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Idaho", "idaho")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 74),
        admin_title_range=(1, 60),
        case_year_range=(1890, 2025),
    ),
    "illinois": StateMetadata(
        name="Illinois", slug="illinois", abbrev="IL", fips="17",
        circuit="7th", circuit_slug="seventh-circuit",
        districts=[
            ("Central District", "illinois/central-district"),
            ("Northern District", "illinois/northern-district"),
            ("Southern District", "illinois/southern-district"),
        ],
        appellate_courts=["appellate-court"],
        code_title_range=(1, 820),  # IL uses chapter numbers
        admin_title_range=(1, 99),
        case_year_range=(1819, 2025),
    ),
    "indiana": StateMetadata(
        name="Indiana", slug="indiana", abbrev="IN", fips="18",
        circuit="7th", circuit_slug="seventh-circuit",
        districts=[
            ("Northern District", "indiana/northern-district"),
            ("Southern District", "indiana/southern-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 36),
        admin_title_range=(1, 900),
        case_year_range=(1817, 2025),
    ),
    "iowa": StateMetadata(
        name="Iowa", slug="iowa", abbrev="IA", fips="19",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[
            ("Northern District", "iowa/northern-district"),
            ("Southern District", "iowa/southern-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 16),
        admin_title_range=(1, 900),
        case_year_range=(1839, 2025),
    ),
    "kansas": StateMetadata(
        name="Kansas", slug="kansas", abbrev="KS", fips="20",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[("District of Kansas", "kansas")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 84),
        admin_title_range=(1, 130),
        case_year_range=(1859, 2025),
    ),
    "kentucky": StateMetadata(
        name="Kentucky", slug="kentucky", abbrev="KY", fips="21",
        circuit="6th", circuit_slug="sixth-circuit",
        districts=[
            ("Eastern District", "kentucky/eastern-district"),
            ("Western District", "kentucky/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 530),  # KY uses chapter numbers
        admin_title_range=(1, 900),
        case_year_range=(1792, 2025),
    ),
    "louisiana": StateMetadata(
        name="Louisiana", slug="louisiana", abbrev="LA", fips="22",
        circuit="5th", circuit_slug="fifth-circuit",
        districts=[
            ("Eastern District", "louisiana/eastern-district"),
            ("Middle District", "louisiana/middle-district"),
            ("Western District", "louisiana/western-district"),
        ],
        appellate_courts=["court-of-appeal"],
        code_title_range=(1, 56),
        admin_title_range=(1, 99),
        case_year_range=(1813, 2025),
    ),
    "maine": StateMetadata(
        name="Maine", slug="maine", abbrev="ME", fips="23",
        circuit="1st", circuit_slug="first-circuit",
        districts=[("District of Maine", "maine")],
        appellate_courts=[],  # Supreme Judicial Court only
        code_title_range=(1, 39),
        admin_title_range=(1, 99),
        case_year_range=(1820, 2025),
    ),
    "maryland": StateMetadata(
        name="Maryland", slug="maryland", abbrev="MD", fips="24",
        circuit="4th", circuit_slug="fourth-circuit",
        districts=[("District of Maryland", "maryland")],
        appellate_courts=["court-of-special-appeals"],
        code_title_range=(1, 30),
        admin_title_range=(1, 36),
        case_year_range=(1658, 2025),
    ),
    "massachusetts": StateMetadata(
        name="Massachusetts", slug="massachusetts", abbrev="MA", fips="25",
        circuit="1st", circuit_slug="first-circuit",
        districts=[("District of Massachusetts", "massachusetts")],
        appellate_courts=["appeals-court"],
        code_title_range=(1, 280),  # MA uses chapter numbers
        admin_title_range=(1, 990),
        case_year_range=(1761, 2025),
    ),
    "michigan": StateMetadata(
        name="Michigan", slug="michigan", abbrev="MI", fips="26",
        circuit="6th", circuit_slug="sixth-circuit",
        districts=[
            ("Eastern District", "michigan/eastern-district"),
            ("Western District", "michigan/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 800),  # MI uses act numbers
        admin_title_range=(1, 500),
        case_year_range=(1836, 2025),
    ),
    "minnesota": StateMetadata(
        name="Minnesota", slug="minnesota", abbrev="MN", fips="27",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[("District of Minnesota", "minnesota")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 650),  # MN uses chapter numbers
        admin_title_range=(1, 9600),
        case_year_range=(1858, 2025),
    ),
    "mississippi": StateMetadata(
        name="Mississippi", slug="mississippi", abbrev="MS", fips="28",
        circuit="5th", circuit_slug="fifth-circuit",
        districts=[
            ("Northern District", "mississippi/northern-district"),
            ("Southern District", "mississippi/southern-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 99),
        admin_title_range=(1, 50),
        case_year_range=(1818, 2025),
    ),
    "missouri": StateMetadata(
        name="Missouri", slug="missouri", abbrev="MO", fips="29",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[
            ("Eastern District", "missouri/eastern-district"),
            ("Western District", "missouri/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 700),  # MO uses chapter numbers
        admin_title_range=(1, 20),
        case_year_range=(1821, 2025),
    ),
    "montana": StateMetadata(
        name="Montana", slug="montana", abbrev="MT", fips="30",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Montana", "montana")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 90),
        admin_title_range=(1, 50),
        case_year_range=(1889, 2025),
    ),
    "nebraska": StateMetadata(
        name="Nebraska", slug="nebraska", abbrev="NE", fips="31",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[("District of Nebraska", "nebraska")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 90),
        admin_title_range=(1, 500),
        case_year_range=(1867, 2025),
    ),
    "nevada": StateMetadata(
        name="Nevada", slug="nevada", abbrev="NV", fips="32",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Nevada", "nevada")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 720),  # NV uses chapter numbers
        admin_title_range=(1, 700),
        case_year_range=(1865, 2025),
    ),
    "new-hampshire": StateMetadata(
        name="New Hampshire", slug="new-hampshire", abbrev="NH", fips="33",
        circuit="1st", circuit_slug="first-circuit",
        districts=[("District of New Hampshire", "new-hampshire")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 680),  # NH uses chapter numbers
        admin_title_range=(1, 500),
        case_year_range=(1816, 2025),
    ),
    "new-jersey": StateMetadata(
        name="New Jersey", slug="new-jersey", abbrev="NJ", fips="34",
        circuit="3rd", circuit_slug="third-circuit",
        districts=[("District of New Jersey", "new-jersey")],
        appellate_courts=["appellate-division"],
        code_title_range=(1, 59),
        admin_title_range=(1, 19),
        case_year_range=(1789, 2025),
    ),
    "new-mexico": StateMetadata(
        name="New Mexico", slug="new-mexico", abbrev="NM", fips="35",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[("District of New Mexico", "new-mexico")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 77),
        admin_title_range=(1, 20),
        case_year_range=(1912, 2025),
    ),
    "new-york": StateMetadata(
        name="New York", slug="new-york", abbrev="NY", fips="36",
        circuit="2nd", circuit_slug="second-circuit",
        districts=[
            ("Eastern District", "new-york/eastern-district"),
            ("Northern District", "new-york/northern-district"),
            ("Southern District", "new-york/southern-district"),
            ("Western District", "new-york/western-district"),
        ],
        appellate_courts=["appellate-division"],
        code_title_range=(1, 100),  # NY uses named laws
        admin_title_range=(1, 23),
        case_year_range=(1791, 2025),
    ),
    "north-carolina": StateMetadata(
        name="North Carolina", slug="north-carolina", abbrev="NC", fips="37",
        circuit="4th", circuit_slug="fourth-circuit",
        districts=[
            ("Eastern District", "north-carolina/eastern-district"),
            ("Middle District", "north-carolina/middle-district"),
            ("Western District", "north-carolina/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 168),  # NC uses chapter numbers
        admin_title_range=(1, 27),
        case_year_range=(1778, 2025),
    ),
    "north-dakota": StateMetadata(
        name="North Dakota", slug="north-dakota", abbrev="ND", fips="38",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[("District of North Dakota", "north-dakota")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 65),
        admin_title_range=(1, 100),
        case_year_range=(1889, 2025),
    ),
    "ohio": StateMetadata(
        name="Ohio", slug="ohio", abbrev="OH", fips="39",
        circuit="6th", circuit_slug="sixth-circuit",
        districts=[
            ("Northern District", "ohio/northern-district"),
            ("Southern District", "ohio/southern-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 58),
        admin_title_range=(1, 5200),
        case_year_range=(1821, 2025),
    ),
    "oklahoma": StateMetadata(
        name="Oklahoma", slug="oklahoma", abbrev="OK", fips="40",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[
            ("Eastern District", "oklahoma/eastern-district"),
            ("Northern District", "oklahoma/northern-district"),
            ("Western District", "oklahoma/western-district"),
        ],
        appellate_courts=["court-of-civil-appeals", "court-of-criminal-appeals"],
        code_title_range=(1, 85),
        admin_title_range=(1, 800),
        case_year_range=(1907, 2025),
    ),
    "oregon": StateMetadata(
        name="Oregon", slug="oregon", abbrev="OR", fips="41",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[("District of Oregon", "oregon")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 850),  # OR uses chapter numbers
        admin_title_range=(1, 900),
        case_year_range=(1859, 2025),
    ),
    "pennsylvania": StateMetadata(
        name="Pennsylvania", slug="pennsylvania", abbrev="PA", fips="42",
        circuit="3rd", circuit_slug="third-circuit",
        districts=[
            ("Eastern District", "pennsylvania/eastern-district"),
            ("Middle District", "pennsylvania/middle-district"),
            ("Western District", "pennsylvania/western-district"),
        ],
        appellate_courts=["superior-court", "commonwealth-court"],
        code_title_range=(1, 75),
        admin_title_range=(1, 58),
        case_year_range=(1754, 2025),
    ),
    "rhode-island": StateMetadata(
        name="Rhode Island", slug="rhode-island", abbrev="RI", fips="44",
        circuit="1st", circuit_slug="first-circuit",
        districts=[("District of Rhode Island", "rhode-island")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 46),
        admin_title_range=(1, 50),
        case_year_range=(1828, 2025),
    ),
    "south-carolina": StateMetadata(
        name="South Carolina", slug="south-carolina", abbrev="SC", fips="45",
        circuit="4th", circuit_slug="fourth-circuit",
        districts=[("District of South Carolina", "south-carolina")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 63),
        admin_title_range=(1, 130),
        case_year_range=(1783, 2025),
    ),
    "south-dakota": StateMetadata(
        name="South Dakota", slug="south-dakota", abbrev="SD", fips="46",
        circuit="8th", circuit_slug="eighth-circuit",
        districts=[("District of South Dakota", "south-dakota")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 62),
        admin_title_range=(1, 100),
        case_year_range=(1889, 2025),
    ),
    "tennessee": StateMetadata(
        name="Tennessee", slug="tennessee", abbrev="TN", fips="47",
        circuit="6th", circuit_slug="sixth-circuit",
        districts=[
            ("Eastern District", "tennessee/eastern-district"),
            ("Middle District", "tennessee/middle-district"),
            ("Western District", "tennessee/western-district"),
        ],
        appellate_courts=["court-of-appeals", "court-of-criminal-appeals"],
        code_title_range=(1, 71),
        admin_title_range=(1, 1700),
        case_year_range=(1796, 2025),
    ),
    "texas": StateMetadata(
        name="Texas", slug="texas", abbrev="TX", fips="48",
        circuit="5th", circuit_slug="fifth-circuit",
        districts=[
            ("Eastern District", "texas/eastern-district"),
            ("Northern District", "texas/northern-district"),
            ("Southern District", "texas/southern-district"),
            ("Western District", "texas/western-district"),
        ],
        appellate_courts=["court-of-appeals", "court-of-criminal-appeals"],
        code_title_range=(1, 30),  # TX uses named codes
        admin_title_range=(1, 43),
        case_year_range=(1846, 2025),
    ),
    "utah": StateMetadata(
        name="Utah", slug="utah", abbrev="UT", fips="49",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[("District of Utah", "utah")],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 78),
        admin_title_range=(1, 1000),
        case_year_range=(1896, 2025),
    ),
    "vermont": StateMetadata(
        name="Vermont", slug="vermont", abbrev="VT", fips="50",
        circuit="2nd", circuit_slug="second-circuit",
        districts=[("District of Vermont", "vermont")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 33),
        admin_title_range=(1, 25),
        case_year_range=(1789, 2025),
    ),
    "virginia": StateMetadata(
        name="Virginia", slug="virginia", abbrev="VA", fips="51",
        circuit="4th", circuit_slug="fourth-circuit",
        districts=[
            ("Eastern District", "virginia/eastern-district"),
            ("Western District", "virginia/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 67),
        admin_title_range=(1, 24),
        case_year_range=(1730, 2025),
    ),
    "washington": StateMetadata(
        name="Washington", slug="washington", abbrev="WA", fips="53",
        circuit="9th", circuit_slug="ninth-circuit",
        districts=[
            ("Eastern District", "washington/eastern-district"),
            ("Western District", "washington/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 91),
        admin_title_range=(1, 500),
        case_year_range=(1889, 2025),
    ),
    "west-virginia": StateMetadata(
        name="West Virginia", slug="west-virginia", abbrev="WV", fips="54",
        circuit="4th", circuit_slug="fourth-circuit",
        districts=[
            ("Northern District", "west-virginia/northern-district"),
            ("Southern District", "west-virginia/southern-district"),
        ],
        appellate_courts=["intermediate-court-of-appeals"],
        code_title_range=(1, 62),
        admin_title_range=(1, 200),
        case_year_range=(1863, 2025),
    ),
    "wisconsin": StateMetadata(
        name="Wisconsin", slug="wisconsin", abbrev="WI", fips="55",
        circuit="7th", circuit_slug="seventh-circuit",
        districts=[
            ("Eastern District", "wisconsin/eastern-district"),
            ("Western District", "wisconsin/western-district"),
        ],
        appellate_courts=["court-of-appeals"],
        code_title_range=(1, 999),  # WI uses chapter numbers
        admin_title_range=(1, 900),
        case_year_range=(1836, 2025),
    ),
    "wyoming": StateMetadata(
        name="Wyoming", slug="wyoming", abbrev="WY", fips="56",
        circuit="10th", circuit_slug="tenth-circuit",
        districts=[("District of Wyoming", "wyoming")],
        appellate_courts=[],  # Supreme Court only
        code_title_range=(1, 42),
        admin_title_range=(1, 100),
        case_year_range=(1890, 2025),
    ),
}

# Child welfare relevant titles by state
CHILD_WELFARE_TITLES = {
    "alabama": [12, 26, 38],  # Courts, Infants, Public Welfare
    "alaska": [25, 47],  # Juveniles, Welfare
    "arizona": [8, 13, 46],  # Child Safety, Courts, Welfare
    "california": ["fam", "wic"],  # Family Code, Welfare & Institutions
    "florida": [39, 63],  # Social Services, Minors
    "texas": ["fam", "hum"],  # Family, Human Resources
    # Add more as discovered
}

# ============================================================================
# LAYER 1: DISCOVERY
# ============================================================================

class DiscoveryLayer:
    """
    Find every relevant URL for a state's legal framework.
    Generates URLs based on known patterns - validation happens in Layer 2.
    """

    # URL patterns
    PATTERNS = {
        "constitution_base": "https://law.justia.com/constitution/{state}/",
        "codes_base": "https://law.justia.com/codes/{state}/",
        "codes_title": "https://law.justia.com/codes/{state}/title-{title}/",
        "admin_base": "https://regulations.justia.com/states/{state}/",
        "admin_title": "https://regulations.justia.com/states/{state}/title-{title}/",
        "supreme_court_base": "https://law.justia.com/cases/{state}/supreme-court/",
        "supreme_court_year": "https://law.justia.com/cases/{state}/supreme-court/{year}/",
        "appellate_base": "https://law.justia.com/cases/{state}/{court}/",
        "appellate_year": "https://law.justia.com/cases/{state}/{court}/{year}/",
        "federal_circuit": "https://law.justia.com/cases/federal/appellate-courts/{circuit}/",
        "federal_district": "https://law.justia.com/cases/federal/district-courts/{district}/",
        "stats_list": "https://stats.justia.com/{state}/list/",
        "stats_place": "https://stats.justia.com/{state}/{place}/",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-LegalCrawler/2.0 (Project Milk Carton; Child Safety Research)"
        })

    def discover_all(self, state: StateMetadata) -> Dict[str, List[str]]:
        """Discover all URLs for a state's legal framework."""
        log.info(f"Discovering URLs for {state.name}...")

        urls = {
            "constitution": self._discover_constitution(state),
            "codes": self._discover_codes(state),
            "admin": self._discover_admin_rules(state),
            "supreme_court": self._discover_supreme_court(state),
            "appellate_courts": self._discover_appellate_courts(state),
            "federal_circuit": self._discover_federal_circuit(state),
            "federal_districts": self._discover_federal_districts(state),
            "localities": [],  # Populated by discover_localities()
        }

        total = sum(len(v) for v in urls.values())
        log.info(f"Discovered {total} URLs for {state.name}")

        return urls

    def _discover_constitution(self, state: StateMetadata) -> List[str]:
        """Generate constitution URLs."""
        urls = [self.PATTERNS["constitution_base"].format(state=state.slug)]
        return urls

    def _discover_codes(self, state: StateMetadata) -> List[str]:
        """Generate state code/statute URLs."""
        urls = [self.PATTERNS["codes_base"].format(state=state.slug)]

        min_title, max_title = state.code_title_range
        for title in range(min_title, max_title + 1):
            urls.append(self.PATTERNS["codes_title"].format(
                state=state.slug, title=title
            ))

        # Handle special codes (e.g., title-10a, title-13a for Alabama)
        special_titles = ["10a", "13a", "26a", "38a"]
        for title in special_titles:
            urls.append(self.PATTERNS["codes_title"].format(
                state=state.slug, title=title
            ))

        return urls

    def _discover_admin_rules(self, state: StateMetadata) -> List[str]:
        """Generate administrative code URLs."""
        urls = [self.PATTERNS["admin_base"].format(state=state.slug)]

        min_title, max_title = state.admin_title_range
        # Admin titles often have gaps, so generate common ones
        titles = list(range(min_title, min(max_title + 1, 1000)))

        for title in titles:
            urls.append(self.PATTERNS["admin_title"].format(
                state=state.slug, title=title
            ))

        return urls

    def _discover_supreme_court(self, state: StateMetadata) -> List[str]:
        """Generate supreme court case URLs by year."""
        urls = [self.PATTERNS["supreme_court_base"].format(state=state.slug)]

        min_year, max_year = state.case_year_range
        for year in range(min_year, max_year + 1):
            urls.append(self.PATTERNS["supreme_court_year"].format(
                state=state.slug, year=year
            ))

        return urls

    def _discover_appellate_courts(self, state: StateMetadata) -> List[str]:
        """Generate appellate court URLs by year."""
        urls = []

        min_year, max_year = state.case_year_range
        # Appellate courts usually start later than supreme courts
        appellate_start = max(min_year, 1960)

        for court in state.appellate_courts:
            urls.append(self.PATTERNS["appellate_base"].format(
                state=state.slug, court=court
            ))
            for year in range(appellate_start, max_year + 1):
                urls.append(self.PATTERNS["appellate_year"].format(
                    state=state.slug, court=court, year=year
                ))

        return urls

    def _discover_federal_circuit(self, state: StateMetadata) -> List[str]:
        """Generate federal circuit court URLs."""
        return [self.PATTERNS["federal_circuit"].format(circuit=state.circuit_slug)]

    def _discover_federal_districts(self, state: StateMetadata) -> List[str]:
        """Generate federal district court URLs."""
        urls = []
        for name, slug in state.districts:
            urls.append(self.PATTERNS["federal_district"].format(district=slug))
        return urls

    def discover_localities(self, state: StateMetadata) -> List[str]:
        """Discover all localities from stats.justia.com (the open endpoint)."""
        url = self.PATTERNS["stats_list"].format(state=state.slug)

        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Locality discovery failed for {state.name}: {e}")
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        localities = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith(f"/{state.slug}/") and href != f"/{state.slug}/list/":
                place = href.strip("/").split("/")[-1]
                localities.append(self.PATTERNS["stats_place"].format(
                    state=state.slug, place=place
                ))

        log.info(f"Discovered {len(localities)} localities for {state.name}")
        return localities


# ============================================================================
# LAYER 2: VALIDATION
# ============================================================================

class ValidationLayer:
    """
    Validate URLs exist and serve expected content.
    Kill bad URLs early to save time.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-LegalCrawler/2.0 (Project Milk Carton)"
        })
        self.valid_cache: Dict[str, bool] = {}

    def is_valid(self, url: str) -> bool:
        """Check if URL returns valid HTML."""
        if url in self.valid_cache:
            return self.valid_cache[url]

        try:
            r = self.session.head(url, allow_redirects=True, timeout=15)
            content_type = r.headers.get("Content-Type", "")
            is_valid = r.status_code == 200 and "text/html" in content_type
        except requests.RequestException:
            is_valid = False

        self.valid_cache[url] = is_valid
        return is_valid

    def validate_batch(self, urls: List[str], sample_size: int = 10) -> Dict[str, bool]:
        """Validate a sample of URLs to check if pattern works."""
        sample = urls[:sample_size] if len(urls) > sample_size else urls
        results = {}

        for url in sample:
            results[url] = self.is_valid(url)
            time.sleep(0.1)

        valid_count = sum(1 for v in results.values() if v)
        log.info(f"Validated {valid_count}/{len(sample)} sample URLs")

        return results


# ============================================================================
# LAYER 3: EXTRACTION
# ============================================================================

class ExtractionLayer:
    """
    Extract metadata and structured data from pages.
    Uses extruct, trafilatura, and BeautifulSoup.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-LegalCrawler/2.0 (Project Milk Carton)"
        })

    def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract all metadata from a URL."""
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            html = r.text
        except requests.RequestException as e:
            return None

        soup = BeautifulSoup(html, "html.parser")

        result = {
            "url": url,
            "title": None,
            "meta_description": None,
            "canonical": None,
            "structured_data": {},
            "text_excerpt": None,
            "internal_links": [],
            "h1_text": None,
        }

        # Title
        if soup.title and soup.title.string:
            result["title"] = soup.title.string.strip()

        # Meta description
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["meta_description"] = meta_desc["content"]

        # Canonical
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            result["canonical"] = canonical["href"]

        # H1
        h1 = soup.find("h1")
        if h1:
            result["h1_text"] = h1.get_text(strip=True)

        # Structured data
        if HAS_EXTRUCT:
            try:
                result["structured_data"] = extruct.extract(
                    html,
                    base_url=get_base_url(html, url),
                    syntaxes=["opengraph", "json-ld", "microdata"]
                )
            except Exception:
                pass

        # Main text
        if HAS_TRAFILATURA:
            try:
                main_text = trafilatura.extract(html)
                if main_text:
                    result["text_excerpt"] = main_text[:3000]
            except Exception:
                pass

        # Internal links (for discovering more resources)
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith("/") or "justia.com" in href:
                result["internal_links"].append(href)

        return result


# ============================================================================
# LAYER 4: NORMALIZATION
# ============================================================================

@dataclass
class NormalizedRecord:
    """Unified schema for all legal resources."""
    jurisdiction: str  # e.g., "US-AL"
    state: str  # e.g., "alabama"
    state_fips: str  # e.g., "01"
    federal_circuit: str  # e.g., "11th"
    resource_type: str  # constitution, code, admin, case, locality
    resource_id: str  # e.g., "title-26" or "2024"
    source: str  # justia_law, justia_stats, regulations
    url: str
    canonical: Optional[str]
    content_hash: str
    metadata: Dict[str, Any]
    structured: Dict[str, Any]
    child_welfare_relevant: bool
    retrieved_at: str


class NormalizationLayer:
    """Coerce extracted data into unified schema."""

    SCHEMA_VERSION = "2.0.0"

    def normalize(
        self,
        raw: Dict[str, Any],
        state: StateMetadata,
        resource_type: str,
        resource_id: str,
    ) -> NormalizedRecord:
        """Normalize extracted data into unified schema."""

        # Compute content hash
        content = raw.get("text_excerpt") or raw.get("title") or raw.get("url", "")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        # Determine source
        url = raw.get("url", "")
        if "stats.justia.com" in url:
            source = "justia_stats"
        elif "regulations.justia.com" in url:
            source = "justia_regulations"
        else:
            source = "justia_law"

        # Check child welfare relevance
        child_welfare_relevant = self._is_child_welfare_relevant(
            state.slug, resource_type, resource_id, raw
        )

        return NormalizedRecord(
            jurisdiction=f"US-{state.abbrev}",
            state=state.slug,
            state_fips=state.fips,
            federal_circuit=state.circuit,
            resource_type=resource_type,
            resource_id=resource_id,
            source=source,
            url=url,
            canonical=raw.get("canonical"),
            content_hash=f"sha256:{content_hash}",
            metadata={
                "title": raw.get("title"),
                "description": raw.get("meta_description"),
                "h1": raw.get("h1_text"),
            },
            structured=raw.get("structured_data", {}),
            child_welfare_relevant=child_welfare_relevant,
            retrieved_at=datetime.utcnow().isoformat() + "Z",
        )

    def _is_child_welfare_relevant(
        self,
        state: str,
        resource_type: str,
        resource_id: str,
        raw: Dict,
    ) -> bool:
        """Determine if resource is relevant to child welfare."""
        # Check if title is in child welfare list
        if state in CHILD_WELFARE_TITLES:
            cw_titles = CHILD_WELFARE_TITLES[state]
            for cw_title in cw_titles:
                if str(cw_title) in str(resource_id):
                    return True

        # Check keywords in text
        cw_keywords = [
            "child", "minor", "juvenile", "abuse", "neglect", "welfare",
            "protective", "dependency", "custody", "foster", "adoption",
            "parental", "guardian", "dhs", "dcfs", "cps", "family"
        ]

        text = (raw.get("text_excerpt") or "").lower()
        title = (raw.get("title") or "").lower()

        for keyword in cw_keywords:
            if keyword in text or keyword in title:
                return True

        return False


# ============================================================================
# LAYER 5: PERSISTENCE
# ============================================================================

class PersistenceLayer:
    """Store records in append-only format with versioning."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_record(self, record: NormalizedRecord, filename: str = "all_resources.jsonl"):
        """Append a single record to JSONL file."""
        filepath = self.output_dir / filename
        with open(filepath, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def save_state_urls(self, state: str, urls: Dict[str, List[str]]):
        """Save discovered URLs for a state (Alabama-style format)."""
        filepath = self.output_dir / f"{state}_legal_framework.txt"

        with open(filepath, "w") as f:
            f.write(f"{'='*80}\n")
            f.write(f"{state.upper()} LEGAL FRAMEWORK\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Project Milk Carton 501(c)(3) - All Rights Reserved\n")
            f.write(f"{'='*80}\n\n")

            # Constitution
            if urls.get("constitution"):
                f.write(f"{urls['constitution'][0]}\n")
                f.write("[\n")
                for url in urls["constitution"][1:]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Codes
            if urls.get("codes"):
                f.write(f"\n{state.title()} State Codes\n")
                f.write("[\n")
                for url in urls["codes"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Admin Rules
            if urls.get("admin"):
                f.write(f"\n{state.title()} Administrative Code\n")
                f.write("[\n")
                for url in urls["admin"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Supreme Court
            if urls.get("supreme_court"):
                f.write(f"\nSupreme Court of {state.title()} Decisions\n")
                f.write("[\n")
                for url in urls["supreme_court"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Appellate Courts
            if urls.get("appellate_courts"):
                f.write(f"\n{state.title()} Appellate Court Decisions\n")
                f.write("[\n")
                for url in urls["appellate_courts"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Federal Circuit
            if urls.get("federal_circuit"):
                f.write(f"\nFederal Circuit Court\n")
                f.write("[\n")
                for url in urls["federal_circuit"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Federal Districts
            if urls.get("federal_districts"):
                f.write(f"\nFederal District Courts\n")
                f.write("[\n")
                for url in urls["federal_districts"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

            # Localities
            if urls.get("localities"):
                f.write(f"\n{state.title()} Localities\n")
                f.write("[\n")
                for url in urls["localities"]:
                    f.write(f'    "{url}",\n')
                f.write("]\n")

        total_urls = sum(len(v) for v in urls.values())
        log.info(f"Saved {total_urls} URLs to {filepath}")
        return filepath

    def save_state_json(self, state: str, urls: Dict[str, List[str]]):
        """Save discovered URLs as JSON."""
        filepath = self.output_dir / f"{state}_legal_framework.json"

        data = {
            "state": state,
            "generated": datetime.utcnow().isoformat() + "Z",
            "copyright": "Project Milk Carton 501(c)(3) - All Rights Reserved",
            "schema_version": "2.0.0",
            "url_counts": {k: len(v) for k, v in urls.items()},
            "total_urls": sum(len(v) for v in urls.values()),
            "urls": urls,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        log.info(f"Saved JSON to {filepath}")
        return filepath


# ============================================================================
# LAYER 6: DRIFT DETECTION
# ============================================================================

class DriftDetectionLayer:
    """Detect changes in resources over time."""

    def __init__(self, output_dir: Path):
        self.hash_file = output_dir / "content_hashes.json"
        self.hashes = self._load_hashes()

    def _load_hashes(self) -> Dict[str, str]:
        """Load existing hashes."""
        if self.hash_file.exists():
            with open(self.hash_file) as f:
                return json.load(f)
        return {}

    def save_hashes(self):
        """Save current hashes."""
        with open(self.hash_file, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def check_drift(self, url: str, new_hash: str) -> Optional[str]:
        """Check if content has changed. Returns old hash if drifted."""
        old_hash = self.hashes.get(url)
        if old_hash and old_hash != new_hash:
            log.warning(f"DRIFT DETECTED: {url}")
            return old_hash

        self.hashes[url] = new_hash
        return None


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class LegalFrameworkCrawler:
    """
    Full 6-layer orchestrator for building the Legal Framework Index.
    """

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.discovery = DiscoveryLayer()
        self.validation = ValidationLayer()
        self.extraction = ExtractionLayer()
        self.normalization = NormalizationLayer()
        self.persistence = PersistenceLayer(output_dir)
        self.drift = DriftDetectionLayer(output_dir)

    def generate_state_framework(self, state_slug: str) -> Dict[str, List[str]]:
        """Generate complete legal framework URLs for a state."""
        if state_slug not in STATES:
            raise ValueError(f"Unknown state: {state_slug}")

        state = STATES[state_slug]

        # Discover all URLs
        urls = self.discovery.discover_all(state)

        # Discover localities (from open endpoint)
        urls["localities"] = self.discovery.discover_localities(state)

        # Save in both formats
        self.persistence.save_state_urls(state_slug, urls)
        self.persistence.save_state_json(state_slug, urls)

        return urls

    def generate_all_states(self):
        """Generate legal framework for ALL 50 states."""
        log.info("=" * 60)
        log.info("GENERATING LEGAL FRAMEWORK FOR ALL 50 STATES")
        log.info("=" * 60)

        all_stats = {}

        for state_slug in STATES.keys():
            log.info(f"\n{'='*60}")
            log.info(f"Processing: {state_slug.upper()}")
            log.info(f"{'='*60}")

            try:
                urls = self.generate_state_framework(state_slug)
                all_stats[state_slug] = {
                    "total": sum(len(v) for v in urls.values()),
                    "constitution": len(urls.get("constitution", [])),
                    "codes": len(urls.get("codes", [])),
                    "admin": len(urls.get("admin", [])),
                    "supreme_court": len(urls.get("supreme_court", [])),
                    "appellate": len(urls.get("appellate_courts", [])),
                    "federal": len(urls.get("federal_circuit", [])) + len(urls.get("federal_districts", [])),
                    "localities": len(urls.get("localities", [])),
                }
            except Exception as e:
                log.error(f"Error processing {state_slug}: {e}")
                continue

            time.sleep(RATE_LIMIT_DELAY)

        # Save summary
        summary_file = OUTPUT_DIR / "all_states_summary.json"
        with open(summary_file, "w") as f:
            json.dump({
                "generated": datetime.utcnow().isoformat() + "Z",
                "states_count": len(all_stats),
                "total_urls": sum(s["total"] for s in all_stats.values()),
                "stats": all_stats,
            }, f, indent=2)

        log.info(f"\n{'='*60}")
        log.info("COMPLETE!")
        log.info(f"Total states: {len(all_stats)}")
        log.info(f"Total URLs: {sum(s['total'] for s in all_stats.values()):,}")
        log.info(f"{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Legal Framework Crawler - Generate Alabama-style legal indices"
    )
    parser.add_argument("--state", "-s", help="Generate for single state")
    parser.add_argument("--all", "-a", action="store_true", help="Generate for ALL 50 states")
    parser.add_argument("--output", "-o", default=str(OUTPUT_DIR), help="Output directory")

    args = parser.parse_args()

    crawler = LegalFrameworkCrawler(output_dir=Path(args.output))

    if args.state:
        crawler.generate_state_framework(args.state)
    elif args.all:
        crawler.generate_all_states()
    else:
        print("Usage:")
        print("  --state alabama    Generate for single state")
        print("  --all              Generate for ALL 50 states")


if __name__ == "__main__":
    main()
