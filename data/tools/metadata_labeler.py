#!/usr/bin/env python3
"""
METADATA LABELER - Precise URL Classification for Serialization

Parses every URL and labels it with:
  - resource_type: constitution, code, admin_rule, supreme_court_case, etc.
  - jurisdiction: US-AL, US-TX, etc.
  - citation: Title 26, Section 5101, Case No. SC-2024-0437, etc.
  - title: Human-readable title
  - child_welfare_relevant: True/False with confidence score
  - serialization_priority: 1-5 (how important for child safety)

This creates the INDEX needed to serialize every law.

Project Milk Carton 501(c)(3) - All Rights Reserved
"""

import json
import re
import hashlib
import asyncio
import aiohttp
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from urllib.parse import urlparse, unquote
import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_DIR = Path("./data/sources/legal_framework")
OUTPUT_DIR = Path("./data/sources/labeled_index")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 20
RATE_LIMIT_DELAY = 0.3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ============================================================================
# CHILD WELFARE TITLE MAPPINGS - THE GOLD
# This is where child welfare laws live in each state
# ============================================================================

CHILD_WELFARE_CODES = {
    # State: {title/chapter: description}
    "alabama": {
        "12": "Courts - Juvenile Proceedings",
        "26": "Infants and Incompetents - CHILD WELFARE PRIMARY",
        "26a": "Child Abuse Reporting",
        "38": "Public Welfare - DHR",
        "38a": "Child Care Facilities",
    },
    "alaska": {
        "47": "Welfare, Social Services and Institutions - CHILD WELFARE PRIMARY",
        "25": "Marital and Domestic Relations",
        "18": "Health, Safety, Housing - Child Abuse Reporting",
    },
    "arizona": {
        "8": "Child Safety - DCS - CHILD WELFARE PRIMARY",
        "13": "Criminal Code - Child Abuse Crimes",
        "25": "Marital and Domestic Relations",
        "36": "Public Health and Safety",
        "46": "Welfare",
    },
    "arkansas": {
        "9": "Family Law - Juveniles - CHILD WELFARE PRIMARY",
        "12": "Courts - Juvenile Division",
        "20": "Public Health and Welfare",
    },
    "california": {
        "wic": "Welfare and Institutions Code - CHILD WELFARE PRIMARY",
        "fam": "Family Code",
        "pen": "Penal Code - Child Abuse Crimes",
        "health": "Health and Safety Code",
    },
    "colorado": {
        "19": "Children's Code - CHILD WELFARE PRIMARY",
        "26": "Human Services Code",
        "14": "Domestic Matters",
    },
    "connecticut": {
        "17a": "Social Services - DCF - CHILD WELFARE PRIMARY",
        "46b": "Family Law",
        "17b": "Social Services - DSS",
    },
    "delaware": {
        "13": "Domestic Relations - CHILD WELFARE PRIMARY",
        "16": "Health and Safety - Child Abuse",
        "31": "Welfare",
    },
    "florida": {
        "39": "Proceedings Relating to Children - CHILD WELFARE PRIMARY",
        "63": "Adoption",
        "383": "Maternal and Child Health",
        "409": "Social and Economic Assistance - DCF",
        "984": "Children and Families in Need of Services",
        "985": "Juvenile Justice",
    },
    "georgia": {
        "15": "Courts - Juvenile Courts",
        "19": "Domestic Relations - CHILD WELFARE PRIMARY",
        "49": "Social Services - DFCS",
    },
    "hawaii": {
        "587a": "Child Protective Act - CHILD WELFARE PRIMARY",
        "571": "Family Courts",
        "346": "Social Services - DHS",
        "350": "Child Abuse",
    },
    "idaho": {
        "16": "Child Protective Act - CHILD WELFARE PRIMARY",
        "32": "Domestic Relations",
        "39": "Health and Safety",
        "56": "Public Assistance",
    },
    "illinois": {
        "325": "Children (ILCS 325) - DCFS - CHILD WELFARE PRIMARY",
        "705": "Courts - Juvenile Court Act",
        "750": "Families",
        "20": "Executive Branch - DCFS",
    },
    "indiana": {
        "31": "Family Law and Juvenile Law - CHILD WELFARE PRIMARY",
        "35": "Criminal Law - Child Abuse",
        "12": "Human Services - DCS",
    },
    "iowa": {
        "232": "Juvenile Justice - CHILD WELFARE PRIMARY",
        "234": "Child and Family Services - DHS",
        "235a": "Child Abuse - Mandatory Reporting",
        "237": "Foster Care",
        "238": "Adoption",
    },
    "kansas": {
        "38": "Minors - CHILD WELFARE PRIMARY",
        "23": "Marriage and Domestic Relations",
        "65": "Public Health - Child Abuse Reporting",
    },
    "kentucky": {
        "199": "Adoption - CHFS",
        "600": "Unified Juvenile Code - CHILD WELFARE PRIMARY",
        "620": "Dependency, Neglect, Abuse",
        "625": "Termination of Parental Rights",
    },
    "louisiana": {
        "chc": "Children's Code - CHILD WELFARE PRIMARY",
        "rs-14": "Criminal Law - Crimes Against Children",
        "rs-46": "Public Welfare and Assistance",
    },
    "maine": {
        "22": "Health and Welfare - DHHS - CHILD WELFARE PRIMARY",
        "18-c": "Domestic Relations",
        "34-b": "Behavioral Health",
    },
    "maryland": {
        "fl": "Family Law - CHILD WELFARE PRIMARY",
        "cts": "Courts - Juvenile Causes",
        "hg": "Health - Child Abuse Reporting",
    },
    "massachusetts": {
        "119": "Protection of Children - DCF - CHILD WELFARE PRIMARY",
        "210": "Adoption",
        "18c": "Child Abuse Prevention",
    },
    "michigan": {
        "712a": "Juvenile Code - CHILD WELFARE PRIMARY",
        "722": "Children - DHHS",
        "750": "Michigan Penal Code - Child Abuse",
    },
    "minnesota": {
        "260": "Juvenile Court Act",
        "260c": "Child Protection - CHILD WELFARE PRIMARY",
        "260e": "Child Maltreatment Reporting",
        "256": "Human Services - DHS",
    },
    "mississippi": {
        "43": "Public Welfare - DHS - CHILD WELFARE PRIMARY",
        "93": "Domestic Relations",
        "97": "Crimes - Child Abuse",
    },
    "missouri": {
        "210": "Child Protection and Reformation - CHILD WELFARE PRIMARY",
        "211": "Juvenile Courts",
        "453": "Adoption",
        "452": "Dissolution of Marriage",
    },
    "montana": {
        "41": "Minors - CHILD WELFARE PRIMARY",
        "42": "Adoption",
        "52": "Family Services - DPHHS",
    },
    "nebraska": {
        "43": "Infants and Juveniles - CHILD WELFARE PRIMARY",
        "28": "Crimes - Child Abuse",
        "68": "Public Assistance - DHHS",
    },
    "nevada": {
        "432": "Services for Children - DCFS",
        "432b": "Child Welfare Services - CHILD WELFARE PRIMARY",
        "127": "Adoption",
        "128": "Termination of Parental Rights",
    },
    "new-hampshire": {
        "169-c": "Child Protection Act - CHILD WELFARE PRIMARY",
        "169-b": "Delinquent Children",
        "170-c": "Adoption",
        "161": "Human Services - DCYF",
    },
    "new-jersey": {
        "9": "Children - Juvenile Code - CHILD WELFARE PRIMARY",
        "30": "Institutions and Agencies - DCF",
        "2a": "Administration of Civil and Criminal Justice",
    },
    "new-mexico": {
        "32a": "Children's Code - CHILD WELFARE PRIMARY",
        "40": "Domestic Affairs",
        "27": "Human Services Department - CYFD",
    },
    "new-york": {
        "ssl": "Social Services Law - OCFS - CHILD WELFARE PRIMARY",
        "fca": "Family Court Act",
        "drl": "Domestic Relations Law",
    },
    "north-carolina": {
        "7b": "Juvenile Code - DSS - CHILD WELFARE PRIMARY",
        "48": "Adoption",
        "50": "Divorce and Alimony",
        "110": "Child Care Facilities",
        "131d": "Social Services",
    },
    "north-dakota": {
        "27": "Judicial Branch - Juvenile Court",
        "50": "Human Services - CHILD WELFARE PRIMARY",
        "14": "Domestic Relations",
    },
    "ohio": {
        "2151": "Juvenile Courts - CHILD WELFARE PRIMARY",
        "5101": "Job and Family Services - PCSA",
        "5103": "Placement of Children",
        "5153": "County Children Services",
    },
    "oklahoma": {
        "10a": "Children and Juvenile Code - CHILD WELFARE PRIMARY",
        "21": "Crimes - Child Abuse",
        "56": "Poor Persons - DHS",
    },
    "oregon": {
        "419b": "Juvenile Code - Dependency - CHILD WELFARE PRIMARY",
        "418": "Child Care",
        "109": "Parent and Child",
    },
    "pennsylvania": {
        "23": "Domestic Relations - CHILD WELFARE PRIMARY",
        "42": "Judiciary - Juvenile Matters",
        "55": "Public Welfare",
        "62": "Human Services Code",
    },
    "rhode-island": {
        "40": "Human Services - DCYF - CHILD WELFARE PRIMARY",
        "14": "Domestic Relations",
        "15": "Adoption",
    },
    "south-carolina": {
        "63": "South Carolina Children's Code - CHILD WELFARE PRIMARY",
        "43": "Social Services - DSS",
    },
    "south-dakota": {
        "26": "Courts - Juvenile Proceedings - CHILD WELFARE PRIMARY",
        "25": "Domestic Relations",
        "28": "Public Health - Child Abuse Reporting",
    },
    "tennessee": {
        "37": "Juveniles - DCS - CHILD WELFARE PRIMARY",
        "36": "Domestic Relations",
        "71": "Welfare",
    },
    "texas": {
        "fam": "Family Code - DFPS - CHILD WELFARE PRIMARY",
        "hum": "Human Resources Code",
        "pen": "Penal Code - Child Abuse",
    },
    "utah": {
        "80": "Child Welfare Services - DCFS - CHILD WELFARE PRIMARY",
        "78a": "Judiciary - Juvenile Court",
        "62a": "Utah Human Services Code",
    },
    "vermont": {
        "33": "Human Services - DCF - CHILD WELFARE PRIMARY",
        "15": "Domestic Relations",
    },
    "virginia": {
        "16.1": "Courts - Juvenile and Domestic Relations - CHILD WELFARE PRIMARY",
        "63.2": "Welfare - DSS",
        "22.1": "Education",
    },
    "washington": {
        "13": "Juvenile Courts and Juvenile Offenders",
        "26": "Domestic Relations - CHILD WELFARE PRIMARY",
        "74": "Public Assistance - DCYF",
        "43": "State Government - Child Abuse Reporting",
    },
    "west-virginia": {
        "49": "Child Welfare - DHHR - CHILD WELFARE PRIMARY",
        "48": "Domestic Relations",
    },
    "wisconsin": {
        "48": "Children's Code - DCF - CHILD WELFARE PRIMARY",
        "938": "Juvenile Justice Code",
        "767": "Actions Affecting Family",
    },
    "wyoming": {
        "14": "Children - DFS - CHILD WELFARE PRIMARY",
        "20": "Domestic Relations",
        "35": "Public Health",
    },
}

# Admin rule titles that relate to child welfare
CHILD_WELFARE_ADMIN = {
    "alabama": [660, 670, 680],  # DHR rules
    "california": [22, 31],  # DSS regulations
    "florida": ["65c"],  # DCF rules
    "texas": [40, 700],  # DFPS rules
    # Add more as discovered
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LabeledURL:
    """Fully labeled URL ready for serialization."""
    url: str
    url_hash: str
    domain: str
    state: str
    state_abbrev: str
    resource_type: str  # constitution, code_title, code_section, admin_rule, case_year, case_specific, locality
    resource_subtype: Optional[str]  # e.g., "supreme_court", "civil_appeals", etc.
    citation: str  # e.g., "Title 26", "2024", "SC-2024-0437"
    citation_full: str  # e.g., "Alabama Code Title 26"
    title: Optional[str]  # Extracted or derived title
    description: Optional[str]
    child_welfare_relevant: bool
    child_welfare_confidence: float  # 0.0 to 1.0
    child_welfare_reason: Optional[str]  # Why it's relevant
    serialization_priority: int  # 1=critical, 5=low
    metadata_source: str  # "url_pattern", "live_extraction", "derived"
    extracted_at: Optional[str]
    content_hash: Optional[str]


# ============================================================================
# URL PARSER - THE BRAIN
# ============================================================================

class URLParser:
    """
    Parse URLs and extract precise metadata.
    This is where the magic happens.
    """

    # Regex patterns for URL parsing
    PATTERNS = {
        "constitution_base": re.compile(r"law\.justia\.com/constitution/([^/]+)/?$"),
        "constitution_section": re.compile(r"law\.justia\.com/constitution/([^/]+)/([^/]+)\.html?$"),
        "codes_base": re.compile(r"law\.justia\.com/codes/([^/]+)/?$"),
        "codes_title": re.compile(r"law\.justia\.com/codes/([^/]+)/title-([^/]+)/?$"),
        "codes_chapter": re.compile(r"law\.justia\.com/codes/([^/]+)/title-([^/]+)/chapter-([^/]+)/?$"),
        "codes_section": re.compile(r"law\.justia\.com/codes/([^/]+)/([^/]+)/([^/]+)\.html?$"),
        "admin_base": re.compile(r"regulations\.justia\.com/states/([^/]+)/?$"),
        "admin_title": re.compile(r"regulations\.justia\.com/states/([^/]+)/title-([^/]+)/?$"),
        "supreme_court_base": re.compile(r"law\.justia\.com/cases/([^/]+)/supreme-court/?$"),
        "supreme_court_year": re.compile(r"law\.justia\.com/cases/([^/]+)/supreme-court/(\d{4})/?$"),
        "supreme_court_case": re.compile(r"law\.justia\.com/cases/([^/]+)/supreme-court/(\d{4})/([^/]+)\.html?$"),
        "appellate_base": re.compile(r"law\.justia\.com/cases/([^/]+)/([^/]+)/?$"),
        "appellate_year": re.compile(r"law\.justia\.com/cases/([^/]+)/([^/]+)/(\d{4})/?$"),
        "appellate_case": re.compile(r"law\.justia\.com/cases/([^/]+)/([^/]+)/(\d{4})/([^/]+)\.html?$"),
        "federal_circuit": re.compile(r"law\.justia\.com/cases/federal/appellate-courts/([^/]+)/?"),
        "federal_district": re.compile(r"law\.justia\.com/cases/federal/district-courts/([^/]+)/?"),
        "stats_list": re.compile(r"stats\.justia\.com/([^/]+)/list/?$"),
        "stats_place": re.compile(r"stats\.justia\.com/([^/]+)/([^/]+)/?$"),
    }

    STATE_ABBREVS = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
        "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
        "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
        "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM", "new-york": "NY",
        "north-carolina": "NC", "north-dakota": "ND", "ohio": "OH", "oklahoma": "OK",
        "oregon": "OR", "pennsylvania": "PA", "rhode-island": "RI", "south-carolina": "SC",
        "south-dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA", "west-virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY",
    }

    def parse(self, url: str) -> LabeledURL:
        """Parse a URL and return fully labeled metadata."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        parsed = urlparse(url)
        domain = parsed.netloc

        # Default values
        state = ""
        resource_type = "unknown"
        resource_subtype = None
        citation = ""
        citation_full = ""
        title = None
        child_welfare_relevant = False
        child_welfare_confidence = 0.0
        child_welfare_reason = None
        priority = 5

        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(url)
            if match:
                result = self._process_match(pattern_name, match, url)
                if result:
                    state = result.get("state", "")
                    resource_type = result.get("resource_type", "unknown")
                    resource_subtype = result.get("resource_subtype")
                    citation = result.get("citation", "")
                    citation_full = result.get("citation_full", "")
                    title = result.get("title")

                    # Check child welfare relevance
                    cw = self._check_child_welfare(state, resource_type, citation, url)
                    child_welfare_relevant = cw["relevant"]
                    child_welfare_confidence = cw["confidence"]
                    child_welfare_reason = cw["reason"]
                    priority = cw["priority"]
                    break

        state_abbrev = self.STATE_ABBREVS.get(state, "")

        return LabeledURL(
            url=url,
            url_hash=url_hash,
            domain=domain,
            state=state,
            state_abbrev=state_abbrev,
            resource_type=resource_type,
            resource_subtype=resource_subtype,
            citation=citation,
            citation_full=citation_full,
            title=title,
            description=None,
            child_welfare_relevant=child_welfare_relevant,
            child_welfare_confidence=child_welfare_confidence,
            child_welfare_reason=child_welfare_reason,
            serialization_priority=priority,
            metadata_source="url_pattern",
            extracted_at=None,
            content_hash=None,
        )

    def _process_match(self, pattern_name: str, match: re.Match, url: str) -> Dict:
        """Process a regex match and extract structured data."""
        groups = match.groups()

        if pattern_name == "constitution_base":
            state = groups[0]
            return {
                "state": state,
                "resource_type": "constitution",
                "resource_subtype": "base",
                "citation": "Constitution",
                "citation_full": f"{state.title()} Constitution",
                "title": f"{state.title()} State Constitution",
            }

        elif pattern_name == "constitution_section":
            state, section_id = groups
            return {
                "state": state,
                "resource_type": "constitution",
                "resource_subtype": "section",
                "citation": section_id,
                "citation_full": f"{state.title()} Const. {section_id}",
                "title": f"{state.title()} Constitution Section {section_id}",
            }

        elif pattern_name == "codes_base":
            state = groups[0]
            return {
                "state": state,
                "resource_type": "code",
                "resource_subtype": "base",
                "citation": "Codes",
                "citation_full": f"{state.title()} State Codes",
                "title": f"{state.title()} Statutes",
            }

        elif pattern_name == "codes_title":
            state, title_num = groups
            return {
                "state": state,
                "resource_type": "code",
                "resource_subtype": "title",
                "citation": f"title-{title_num}",
                "citation_full": f"{state.title()} Code Title {title_num}",
                "title": self._get_title_name(state, title_num),
            }

        elif pattern_name == "admin_base":
            state = groups[0]
            return {
                "state": state,
                "resource_type": "admin_rule",
                "resource_subtype": "base",
                "citation": "Admin Code",
                "citation_full": f"{state.title()} Administrative Code",
                "title": f"{state.title()} Administrative Regulations",
            }

        elif pattern_name == "admin_title":
            state, title_num = groups
            return {
                "state": state,
                "resource_type": "admin_rule",
                "resource_subtype": "title",
                "citation": f"title-{title_num}",
                "citation_full": f"{state.title()} Admin. Code Title {title_num}",
                "title": f"{state.title()} Administrative Rule Title {title_num}",
            }

        elif pattern_name == "supreme_court_base":
            state = groups[0]
            return {
                "state": state,
                "resource_type": "case_law",
                "resource_subtype": "supreme_court",
                "citation": "Supreme Court",
                "citation_full": f"{state.title()} Supreme Court Decisions",
                "title": f"{state.title()} Supreme Court",
            }

        elif pattern_name == "supreme_court_year":
            state, year = groups
            return {
                "state": state,
                "resource_type": "case_law",
                "resource_subtype": "supreme_court_year",
                "citation": year,
                "citation_full": f"{state.title()} Supreme Court {year}",
                "title": f"{state.title()} Supreme Court Decisions - {year}",
            }

        elif pattern_name == "supreme_court_case":
            state, year, case_id = groups
            return {
                "state": state,
                "resource_type": "case_law",
                "resource_subtype": "supreme_court_case",
                "citation": case_id,
                "citation_full": f"{state.title()} Sup. Ct. {case_id} ({year})",
                "title": f"Case {case_id}",
            }

        elif pattern_name == "appellate_base":
            state, court = groups
            return {
                "state": state,
                "resource_type": "case_law",
                "resource_subtype": court,
                "citation": court,
                "citation_full": f"{state.title()} {court.replace('-', ' ').title()}",
                "title": f"{state.title()} {court.replace('-', ' ').title()}",
            }

        elif pattern_name == "appellate_year":
            state, court, year = groups
            return {
                "state": state,
                "resource_type": "case_law",
                "resource_subtype": f"{court}_year",
                "citation": year,
                "citation_full": f"{state.title()} {court.replace('-', ' ').title()} {year}",
                "title": f"{state.title()} {court.replace('-', ' ').title()} - {year}",
            }

        elif pattern_name == "federal_circuit":
            circuit = groups[0]
            return {
                "state": "",
                "resource_type": "federal_case",
                "resource_subtype": "circuit",
                "citation": circuit,
                "citation_full": f"U.S. Court of Appeals, {circuit.replace('-', ' ').title()}",
                "title": f"{circuit.replace('-', ' ').title()} Court of Appeals",
            }

        elif pattern_name == "federal_district":
            district = groups[0]
            # Extract state from district path
            state = district.split("/")[0] if "/" in district else district
            return {
                "state": state,
                "resource_type": "federal_case",
                "resource_subtype": "district",
                "citation": district,
                "citation_full": f"U.S. District Court, {district.replace('/', ' ').replace('-', ' ').title()}",
                "title": f"Federal District Court - {district}",
            }

        elif pattern_name == "stats_list":
            state = groups[0]
            return {
                "state": state,
                "resource_type": "locality",
                "resource_subtype": "index",
                "citation": "localities",
                "citation_full": f"{state.title()} Localities Index",
                "title": f"{state.title()} Cities, Counties, and Places",
            }

        elif pattern_name == "stats_place":
            state, place = groups
            place_name = place.replace("-", " ").replace("_", " ").title()
            return {
                "state": state,
                "resource_type": "locality",
                "resource_subtype": "place",
                "citation": place,
                "citation_full": f"{place_name}, {state.title()}",
                "title": place_name,
            }

        return {}

    def _get_title_name(self, state: str, title_num: str) -> str:
        """Get human-readable title name if known."""
        if state in CHILD_WELFARE_CODES:
            if title_num in CHILD_WELFARE_CODES[state]:
                desc = CHILD_WELFARE_CODES[state][title_num]
                return f"Title {title_num}: {desc}"
        return f"Title {title_num}"

    def _check_child_welfare(self, state: str, resource_type: str, citation: str, url: str) -> Dict:
        """Check if resource is relevant to child welfare."""
        relevant = False
        confidence = 0.0
        reason = None
        priority = 5

        # Check if this is a known child welfare title
        if state in CHILD_WELFARE_CODES:
            cw_titles = CHILD_WELFARE_CODES[state]
            # Extract title number from citation
            title_match = re.search(r"title-?(\d+[a-z]?)", citation.lower())
            if title_match:
                title_num = title_match.group(1)
                if title_num in cw_titles:
                    relevant = True
                    confidence = 1.0
                    reason = f"Direct child welfare title: {cw_titles[title_num]}"
                    priority = 1 if "PRIMARY" in cw_titles[title_num] else 2

        # Check for child welfare keywords in URL
        cw_keywords = ["child", "juvenile", "minor", "family", "welfare", "abuse",
                       "neglect", "custody", "foster", "adoption", "dcf", "dcs",
                       "cps", "dfps", "dcyf", "dhs", "protective"]

        url_lower = url.lower()
        for keyword in cw_keywords:
            if keyword in url_lower:
                if not relevant:
                    relevant = True
                    confidence = max(confidence, 0.7)
                    reason = f"Child welfare keyword in URL: {keyword}"
                    priority = min(priority, 3)
                break

        # Courts/cases related to children
        if resource_type == "case_law":
            if "juvenile" in url_lower or "family" in url_lower:
                relevant = True
                confidence = max(confidence, 0.8)
                reason = "Juvenile/Family court cases"
                priority = min(priority, 2)

        return {
            "relevant": relevant,
            "confidence": confidence,
            "reason": reason,
            "priority": priority if relevant else 5,
        }


# ============================================================================
# LIVE METADATA EXTRACTOR - For open endpoints
# ============================================================================

class LiveMetadataExtractor:
    """Extract live metadata from accessible URLs."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-MetadataExtractor/1.0 (Project Milk Carton)"
        })

    def extract(self, url: str) -> Optional[Dict]:
        """Extract metadata from a live URL."""
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            html = r.text
        except requests.RequestException:
            return None

        soup = BeautifulSoup(html, "html.parser")

        result = {
            "title": None,
            "description": None,
            "h1": None,
            "content_hash": None,
        }

        # Title
        if soup.title and soup.title.string:
            result["title"] = soup.title.string.strip()

        # Meta description
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]

        # H1
        h1 = soup.find("h1")
        if h1:
            result["h1"] = h1.get_text(strip=True)

        # Content hash
        if HAS_TRAFILATURA:
            try:
                main_text = trafilatura.extract(html)
                if main_text:
                    result["content_hash"] = hashlib.sha256(
                        main_text.encode()
                    ).hexdigest()[:16]
            except Exception:
                pass

        return result


# ============================================================================
# MAIN LABELER
# ============================================================================

class MetadataLabeler:
    """
    Main orchestrator for labeling all URLs.
    """

    def __init__(self, input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.parser = URLParser()
        self.extractor = LiveMetadataExtractor()

    def label_state(self, state: str) -> List[LabeledURL]:
        """Label all URLs for a state."""
        json_file = self.input_dir / f"{state}_legal_framework.json"
        if not json_file.exists():
            log.error(f"No framework file for {state}")
            return []

        with open(json_file) as f:
            data = json.load(f)

        urls = data.get("urls", {})
        all_urls = []
        for category, url_list in urls.items():
            all_urls.extend(url_list)

        log.info(f"Labeling {len(all_urls)} URLs for {state}...")

        labeled = []
        for url in all_urls:
            label = self.parser.parse(url)
            labeled.append(label)

        # Extract live metadata for accessible URLs (stats.justia.com)
        stats_urls = [l for l in labeled if l.domain == "stats.justia.com"]
        log.info(f"Extracting live metadata from {len(stats_urls)} accessible URLs...")

        for i, label in enumerate(stats_urls[:50]):  # Limit to first 50 for now
            live_data = self.extractor.extract(label.url)
            if live_data:
                label.title = live_data.get("title") or label.title
                label.description = live_data.get("description")
                label.content_hash = live_data.get("content_hash")
                label.metadata_source = "live_extraction"
                label.extracted_at = datetime.utcnow().isoformat() + "Z"

            if (i + 1) % 10 == 0:
                log.info(f"  Extracted {i + 1}/{min(50, len(stats_urls))}")
            time.sleep(RATE_LIMIT_DELAY)

        # Save results
        self._save_state_labels(state, labeled)

        return labeled

    def _save_state_labels(self, state: str, labeled: List[LabeledURL]):
        """Save labeled URLs for a state."""
        # Save as JSONL
        jsonl_file = self.output_dir / f"{state}_labeled.jsonl"
        with open(jsonl_file, "w") as f:
            for label in labeled:
                f.write(json.dumps(asdict(label)) + "\n")

        # Save child welfare subset
        cw_file = self.output_dir / f"{state}_child_welfare.jsonl"
        cw_count = 0
        with open(cw_file, "w") as f:
            for label in labeled:
                if label.child_welfare_relevant:
                    f.write(json.dumps(asdict(label)) + "\n")
                    cw_count += 1

        # Save summary
        summary = {
            "state": state,
            "generated": datetime.utcnow().isoformat() + "Z",
            "total_urls": len(labeled),
            "child_welfare_urls": cw_count,
            "by_type": {},
            "by_priority": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        }

        for label in labeled:
            rt = label.resource_type
            summary["by_type"][rt] = summary["by_type"].get(rt, 0) + 1
            summary["by_priority"][label.serialization_priority] += 1

        summary_file = self.output_dir / f"{state}_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        log.info(f"Saved {state}: {len(labeled)} total, {cw_count} child welfare")

    def label_all_states(self):
        """Label all 50 states."""
        log.info("=" * 60)
        log.info("LABELING ALL 50 STATES")
        log.info("=" * 60)

        all_summaries = {}
        total_urls = 0
        total_cw = 0

        for state in self.parser.STATE_ABBREVS.keys():
            try:
                labeled = self.label_state(state)
                cw_count = sum(1 for l in labeled if l.child_welfare_relevant)
                all_summaries[state] = {
                    "total": len(labeled),
                    "child_welfare": cw_count,
                }
                total_urls += len(labeled)
                total_cw += cw_count
            except Exception as e:
                log.error(f"Error labeling {state}: {e}")
                continue

        # Save master summary
        master_summary = {
            "generated": datetime.utcnow().isoformat() + "Z",
            "total_urls_labeled": total_urls,
            "total_child_welfare_urls": total_cw,
            "states": all_summaries,
        }

        master_file = self.output_dir / "all_states_labeled_summary.json"
        with open(master_file, "w") as f:
            json.dump(master_summary, f, indent=2)

        log.info("=" * 60)
        log.info("COMPLETE!")
        log.info(f"Total URLs labeled: {total_urls:,}")
        log.info(f"Child welfare URLs: {total_cw:,}")
        log.info("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Metadata Labeler")
    parser.add_argument("--state", "-s", help="Label single state")
    parser.add_argument("--all", "-a", action="store_true", help="Label all states")

    args = parser.parse_args()

    labeler = MetadataLabeler()

    if args.state:
        labeler.label_state(args.state)
    elif args.all:
        labeler.label_all_states()
    else:
        print("Usage:")
        print("  --state alabama    Label single state")
        print("  --all              Label all 50 states")


if __name__ == "__main__":
    main()
