#!/usr/bin/env python3
"""
Case Law Extractor & Scorer

Takes URLs extracted from browser console (F12) and:
1. Filters for actual case URLs
2. Extracts case metadata from URL pattern
3. Scores for child welfare relevance
4. Saves to labeled dataset

Usage:
    # Process URLs from file
    python case_extractor.py --input urls.json --state alabama

    # Process URLs from stdin
    cat urls.json | python case_extractor.py --state alabama
"""

import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

# ============================================================================
# CHILD WELFARE KEYWORDS FOR CASE SCORING
# ============================================================================

# High-confidence keywords (strong indicator of child welfare case)
CW_KEYWORDS_HIGH = [
    # Dependency/CPS
    r'\bdependency\b',
    r'\bchild\s*protective\b',
    r'\bCPS\b',
    r'\bDCFS\b',
    r'\bDHR\b',
    r'\bDCS\b',
    r'\bDCF\b',
    r'\bDFPS\b',
    r'\bDSS\b',

    # Termination of parental rights
    r'\btermination\s*of\s*parental\s*rights?\b',
    r'\bTPR\b',
    r'\bparental\s*rights?\s*terminat',

    # Foster care
    r'\bfoster\s*care\b',
    r'\bfoster\s*parent',
    r'\bfoster\s*child',
    r'\bfoster\s*placement',

    # Abuse/neglect
    r'\bchild\s*abuse\b',
    r'\bchild\s*neglect\b',
    r'\babused\s*child',
    r'\bneglected\s*child',
    r'\bchild\s*maltreatment\b',

    # Juvenile dependency
    r'\bjuvenile\s*depend',
    r'\bdependent\s*child',
    r'\bdependent\s*minor',

    # Adoption from foster care
    r'\badoption\b.*\bfoster\b',
    r'\bfoster\b.*\badoption\b',

    # Guardianship
    r'\bguardianship\b.*\bchild',
    r'\bchild.*\bguardianship\b',

    # Specific case types
    r'\bIn\s*re\s*[A-Z]\.[A-Z]\.?\b',  # In re J.D., In re A.B.
    r'\bIn\s*re\s*the\s*Matter\s*of\b',
    r'\bIn\s*the\s*Interest\s*of\b',
]

# Medium-confidence keywords (may indicate child welfare)
CW_KEYWORDS_MEDIUM = [
    r'\bjuvenile\b',
    r'\bminor\s*child',
    r'\bcustody\b.*\bchild',
    r'\bchild\b.*\bcustody\b',
    r'\bparental\s*rights?\b',
    r'\bremoval\b.*\bchild',
    r'\bplacement\b.*\bchild',
    r'\bkinship\b',
    r'\breunification\b',
    r'\bcase\s*plan\b',
    r'\bpermanency\b',
    r'\bICWA\b',  # Indian Child Welfare Act
    r'\bIndian\s*Child\s*Welfare\b',
    r'\bSAFE\s*families\b',
    r'\bMEPA\b',  # Multiethnic Placement Act
    r'\bASFA\b',  # Adoption and Safe Families Act
]

# Low-confidence keywords (tangentially related)
CW_KEYWORDS_LOW = [
    r'\bdomestic\s*relations\b',
    r'\bfamily\s*court\b',
    r'\bfamily\s*law\b',
    r'\bdivorce\b.*\bchild',
    r'\bchild\s*support\b',
    r'\bvisitation\b',
    r'\bchild\s*welfare\b',
    r'\bwelfare\s*department\b',
    r'\bsocial\s*services\b',
    r'\bsocial\s*worker\b',
    r'\bcaseworker\b',
]

# Compile patterns
CW_PATTERNS_HIGH = [re.compile(p, re.IGNORECASE) for p in CW_KEYWORDS_HIGH]
CW_PATTERNS_MEDIUM = [re.compile(p, re.IGNORECASE) for p in CW_KEYWORDS_MEDIUM]
CW_PATTERNS_LOW = [re.compile(p, re.IGNORECASE) for p in CW_KEYWORDS_LOW]

# ============================================================================
# COURT MAPPINGS
# ============================================================================

COURT_TYPES = {
    'supreme-court': {'name': 'Supreme Court', 'level': 'supreme', 'category': 'judicial'},
    'court-of-appeals': {'name': 'Court of Appeals', 'level': 'appellate', 'category': 'judicial'},
    'court-of-civil-appeals': {'name': 'Court of Civil Appeals', 'level': 'appellate', 'category': 'judicial'},
    'court-of-criminal-appeals': {'name': 'Court of Criminal Appeals', 'level': 'appellate', 'category': 'judicial'},
    'civil-appeals': {'name': 'Civil Court of Appeals', 'level': 'appellate', 'category': 'judicial'},
    'criminal-appeals': {'name': 'Criminal Court of Appeals', 'level': 'appellate', 'category': 'judicial'},
    'appellate-court': {'name': 'Appellate Court', 'level': 'appellate', 'category': 'judicial'},
    'appeals-court': {'name': 'Appeals Court', 'level': 'appellate', 'category': 'judicial'},
    'district-court': {'name': 'District Court', 'level': 'trial', 'category': 'judicial'},
    'superior-court': {'name': 'Superior Court', 'level': 'trial', 'category': 'judicial'},
    'circuit-court': {'name': 'Circuit Court', 'level': 'trial', 'category': 'judicial'},
    'family-court': {'name': 'Family Court', 'level': 'trial', 'category': 'judicial'},
    'juvenile-court': {'name': 'Juvenile Court', 'level': 'trial', 'category': 'judicial'},
    'probate-court': {'name': 'Probate Court', 'level': 'trial', 'category': 'judicial'},
}

# State name mappings
STATE_SLUGS = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new-hampshire': 'NH', 'new-jersey': 'NJ', 'new-mexico': 'NM', 'new-york': 'NY',
    'north-carolina': 'NC', 'north-dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode-island': 'RI', 'south-carolina': 'SC',
    'south-dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west-virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY'
}

# ============================================================================
# DATA STRUCTURE
# ============================================================================

@dataclass
class CaseRecord:
    """Individual case record with metadata and scoring."""
    url: str
    url_hash: str
    domain: str
    state: str
    state_abbrev: str
    resource_type: str  # "case_law"
    resource_subtype: str  # "supreme_court", "civil_appeals", etc.
    court_name: str
    court_level: str  # "supreme", "appellate", "trial"
    category: str  # "judicial"
    year: int
    case_id: str  # e.g., "sc-2024-0437"
    citation: str
    citation_full: str
    title: Optional[str]  # Case name if available
    parties: Optional[str]  # Parties if available
    child_welfare_relevant: bool
    child_welfare_confidence: float  # 0.0 to 1.0
    child_welfare_reason: Optional[str]
    child_welfare_keywords: List[str]  # Keywords found
    serialization_priority: int  # 1=critical, 5=low
    metadata_source: str  # "url_pattern", "page_extraction"
    extracted_at: str
    content_hash: Optional[str]


# ============================================================================
# URL PARSER
# ============================================================================

def parse_case_url(url: str) -> Optional[Dict]:
    """
    Parse a case URL and extract metadata.

    URL patterns:
    - https://law.justia.com/cases/alabama/supreme-court/2025/sc-2024-0437.html
    - https://law.justia.com/cases/california/court-of-appeal/2024/a123456.html
    """
    # Must be a .html case URL
    if not url.endswith('.html'):
        return None

    # Must be from law.justia.com/cases/
    if 'law.justia.com/cases/' not in url:
        return None

    # Parse URL pattern
    # /cases/{state}/{court}/{year}/{case_id}.html
    pattern = r'law\.justia\.com/cases/([^/]+)/([^/]+)/(\d{4})/([^/]+)\.html'
    match = re.search(pattern, url)

    if not match:
        return None

    state_slug = match.group(1)
    court_slug = match.group(2)
    year = int(match.group(3))
    case_id = match.group(4)

    # Validate state
    if state_slug not in STATE_SLUGS:
        return None

    # Get court info
    court_info = COURT_TYPES.get(court_slug, {
        'name': court_slug.replace('-', ' ').title(),
        'level': 'unknown',
        'category': 'judicial'
    })

    return {
        'url': url,
        'state': state_slug,
        'state_abbrev': STATE_SLUGS[state_slug],
        'court_slug': court_slug,
        'court_name': court_info['name'],
        'court_level': court_info['level'],
        'category': court_info['category'],
        'year': year,
        'case_id': case_id,
    }


def score_for_child_welfare(text: str) -> Tuple[float, List[str], str]:
    """
    Score text for child welfare relevance.

    Returns:
        (confidence, keywords_found, reason)
    """
    if not text:
        return 0.0, [], None

    keywords_found = []

    # Check high-confidence patterns
    for pattern in CW_PATTERNS_HIGH:
        matches = pattern.findall(text)
        if matches:
            keywords_found.extend(matches)

    if keywords_found:
        return 1.0, keywords_found, "High-confidence child welfare keywords"

    # Check medium-confidence patterns
    for pattern in CW_PATTERNS_MEDIUM:
        matches = pattern.findall(text)
        if matches:
            keywords_found.extend(matches)

    if keywords_found:
        return 0.7, keywords_found, "Medium-confidence child welfare keywords"

    # Check low-confidence patterns
    for pattern in CW_PATTERNS_LOW:
        matches = pattern.findall(text)
        if matches:
            keywords_found.extend(matches)

    if keywords_found:
        return 0.3, keywords_found, "Low-confidence child welfare keywords"

    return 0.0, [], None


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

def extract_cases_from_urls(urls: List[str], state: Optional[str] = None) -> List[CaseRecord]:
    """
    Extract case records from a list of URLs.

    Args:
        urls: List of URLs (from browser console)
        state: Optional state filter

    Returns:
        List of CaseRecord objects
    """
    records = []
    seen = set()

    for url in urls:
        # Skip duplicates
        if url in seen:
            continue
        seen.add(url)

        # Parse URL
        parsed = parse_case_url(url)
        if not parsed:
            continue

        # Filter by state if specified
        if state and parsed['state'] != state:
            continue

        # Create citation
        case_id = parsed['case_id']
        citation = f"{parsed['state_abbrev']} {parsed['court_name']} {case_id}"
        citation_full = f"{parsed['state'].replace('-', ' ').title()} {parsed['court_name']} Case {case_id} ({parsed['year']})"

        # Score for child welfare (based on case_id pattern for now)
        # In re cases are often child welfare
        score_text = case_id + " " + citation_full
        confidence, keywords, reason = score_for_child_welfare(score_text)

        # URL hash
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        # Determine serialization priority
        if confidence >= 0.9:
            priority = 1
        elif confidence >= 0.5:
            priority = 2
        elif confidence > 0:
            priority = 3
        else:
            priority = 4  # All case law is still valuable

        record = CaseRecord(
            url=url,
            url_hash=url_hash,
            domain='law.justia.com',
            state=parsed['state'],
            state_abbrev=parsed['state_abbrev'],
            resource_type='case_law',
            resource_subtype=parsed['court_slug'].replace('-', '_'),
            court_name=parsed['court_name'],
            court_level=parsed['court_level'],
            category=parsed['category'],
            year=parsed['year'],
            case_id=case_id,
            citation=citation,
            citation_full=citation_full,
            title=None,  # To be filled from page content
            parties=None,  # To be filled from page content
            child_welfare_relevant=confidence > 0,
            child_welfare_confidence=confidence,
            child_welfare_reason=reason,
            child_welfare_keywords=keywords,
            serialization_priority=priority,
            metadata_source='url_pattern',
            extracted_at=datetime.now(timezone.utc).isoformat(),
            content_hash=None,
        )

        records.append(record)

    return records


def save_cases(records: List[CaseRecord], output_dir: Path, state: str):
    """Save case records to JSONL files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # All cases
    all_file = output_dir / f"{state}_cases.jsonl"
    with open(all_file, 'w') as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + '\n')

    # Child welfare cases only
    cw_records = [r for r in records if r.child_welfare_relevant]
    if cw_records:
        cw_file = output_dir / f"{state}_cases_child_welfare.jsonl"
        with open(cw_file, 'w') as f:
            for r in cw_records:
                f.write(json.dumps(asdict(r)) + '\n')

    # Summary
    summary = {
        'state': state,
        'total_cases': len(records),
        'child_welfare_cases': len(cw_records),
        'by_court': {},
        'by_year': {},
        'extracted_at': datetime.now(timezone.utc).isoformat(),
    }

    for r in records:
        court = r.court_name
        year = str(r.year)
        summary['by_court'][court] = summary['by_court'].get(court, 0) + 1
        summary['by_year'][year] = summary['by_year'].get(year, 0) + 1

    summary_file = output_dir / f"{state}_cases_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    parser = argparse.ArgumentParser(description='Extract and score case law from URLs')
    parser.add_argument('--input', '-i', help='Input JSON file with URLs')
    parser.add_argument('--state', '-s', required=True, help='State slug (e.g., alabama)')
    parser.add_argument('--output', '-o', default='./data/sources/case_law/',
                        help='Output directory')

    args = parser.parse_args()

    # Read URLs
    if args.input:
        with open(args.input) as f:
            urls = json.load(f)
    else:
        import sys
        urls = json.load(sys.stdin)

    print(f"Processing {len(urls)} URLs for {args.state}...")

    # Extract cases
    records = extract_cases_from_urls(urls, args.state)

    print(f"Found {len(records)} valid case URLs")

    # Save
    output_dir = Path(args.output)
    summary = save_cases(records, output_dir, args.state)

    print(f"\n=== RESULTS ===")
    print(f"Total cases: {summary['total_cases']}")
    print(f"Child welfare cases: {summary['child_welfare_cases']}")
    print(f"\nBy court:")
    for court, count in sorted(summary['by_court'].items(), key=lambda x: -x[1]):
        print(f"  {court}: {count}")
    print(f"\nSaved to: {output_dir}")


if __name__ == '__main__':
    main()
