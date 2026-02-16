#!/usr/bin/env python3
"""
Case Law Processor with Title-Based Scoring

Takes browser-extracted data (text+url or title+url) and:
1. Parses ALL case URLs
2. Scores based on TITLE content for child welfare relevance
3. Saves complete dataset with CW flagging

Input format (from browser console):
[
    {"text": "Case Title Here", "url": "https://..."},
    ...
]
OR
[
    {"title": "Case Title Here", "url": "https://..."},
    ...
]
"""

import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

# ============================================================================
# CHILD WELFARE KEYWORDS FOR TITLE SCORING
# ============================================================================

# HIGH confidence - definitely child welfare
CW_KEYWORDS_HIGH = [
    # DHR / CPS agencies
    (r'\bDHR\b', 'Department of Human Resources'),
    (r'\bDepartment of Human Resources\b', 'DHR'),
    (r'\bDCFS\b', 'Dept of Children & Family Services'),
    (r'\bDCS\b', 'Dept of Child Services'),
    (r'\bDCF\b', 'Dept of Children & Families'),
    (r'\bDFPS\b', 'Dept of Family & Protective Services'),
    (r'\bCPS\b', 'Child Protective Services'),
    (r'\bChild Protective Services\b', 'CPS'),

    # Juvenile dependency
    (r'\bJuvenile Court\b', 'Juvenile Court'),
    (r'\bJuvenile\s*:\s*JU-', 'Juvenile docket'),
    (r'\bJU-\d{2}-\d+', 'Juvenile case number'),

    # Termination of parental rights
    (r'\btermination of parental rights\b', 'TPR'),
    (r'\bTPR\b', 'Termination of Parental Rights'),
    (r'\bparental rights terminated\b', 'TPR'),

    # Dependency proceedings
    (r'\bdependency\b', 'dependency'),
    (r'\bdependent child\b', 'dependent child'),

    # Foster care
    (r'\bfoster care\b', 'foster care'),
    (r'\bfoster parent\b', 'foster parent'),
    (r'\bfoster placement\b', 'foster placement'),

    # Abuse/neglect
    (r'\bchild abuse\b', 'child abuse'),
    (r'\bchild neglect\b', 'child neglect'),
    (r'\babused child\b', 'abused child'),
    (r'\bneglected child\b', 'neglected child'),

    # In re initials (common in CW cases)
    (r'\bIn re[:\s]+[A-Z]\.[A-Z]\.', 'In re [initials]'),
    (r'\bEx parte [A-Z]\.[A-Z]\.', 'Ex parte [initials]'),
]

# MEDIUM confidence - likely child welfare
CW_KEYWORDS_MEDIUM = [
    (r'\bchild custody\b', 'child custody'),
    (r'\bcustody of.*child', 'custody of child'),
    (r'\bminor child\b', 'minor child'),
    (r'\bparental rights\b', 'parental rights'),
    (r'\bguardianship\b', 'guardianship'),
    (r'\badoption\b', 'adoption'),
    (r'\breunification\b', 'reunification'),
    (r'\bpermanency\b', 'permanency'),
    (r'\bICWA\b', 'Indian Child Welfare Act'),
    (r'\bchild welfare\b', 'child welfare'),
    (r'\bchildren\s*and\s*families\b', 'children and families'),
    (r'\bminor\b.*\bremoval\b', 'minor removal'),
    (r'\bplacement\b.*\bchild', 'child placement'),
]

# LOW confidence - tangentially related
CW_KEYWORDS_LOW = [
    (r'\bdivorce\b.*\bchild', 'divorce with child'),
    (r'\bchild support\b', 'child support'),
    (r'\bvisitation\b', 'visitation'),
    (r'\bfamily court\b', 'family court'),
    (r'\bdomestic relations\b', 'domestic relations'),
]

# Compile patterns
CW_PATTERNS_HIGH = [(re.compile(p, re.IGNORECASE), desc) for p, desc in CW_KEYWORDS_HIGH]
CW_PATTERNS_MEDIUM = [(re.compile(p, re.IGNORECASE), desc) for p, desc in CW_KEYWORDS_MEDIUM]
CW_PATTERNS_LOW = [(re.compile(p, re.IGNORECASE), desc) for p, desc in CW_KEYWORDS_LOW]

# State mappings
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

COURT_TYPES = {
    'supreme-court': {'name': 'Supreme Court', 'level': 'supreme'},
    'court-of-appeals': {'name': 'Court of Appeals', 'level': 'appellate'},
    'court-of-civil-appeals': {'name': 'Court of Civil Appeals', 'level': 'appellate'},
    'court-of-criminal-appeals': {'name': 'Court of Criminal Appeals', 'level': 'appellate'},
    'civil-appeals': {'name': 'Civil Court of Appeals', 'level': 'appellate'},
    'criminal-appeals': {'name': 'Criminal Court of Appeals', 'level': 'appellate'},
}

# ============================================================================
# DATA STRUCTURE
# ============================================================================

@dataclass
class CaseRecord:
    url: str
    url_hash: str
    domain: str
    state: str
    state_abbrev: str
    resource_type: str
    resource_subtype: str
    court_name: str
    court_level: str
    category: str
    year: int
    case_id: str
    citation: str
    citation_full: str
    title: str
    parties: Optional[str]
    child_welfare_relevant: bool
    child_welfare_confidence: float
    child_welfare_reason: Optional[str]
    child_welfare_keywords: List[str]
    serialization_priority: int
    metadata_source: str
    extracted_at: str
    content_hash: Optional[str]


def parse_case_url(url: str) -> Optional[Dict]:
    """Parse case URL pattern."""
    if not url.endswith('.html'):
        return None
    if 'law.justia.com/cases/' not in url:
        return None

    pattern = r'law\.justia\.com/cases/([^/]+)/([^/]+)/(\d{4})/([^/]+)\.html'
    match = re.search(pattern, url)
    if not match:
        return None

    state_slug = match.group(1)
    court_slug = match.group(2)
    year = int(match.group(3))
    case_id = match.group(4)

    if state_slug not in STATE_SLUGS:
        return None

    court_info = COURT_TYPES.get(court_slug, {'name': court_slug.replace('-', ' ').title(), 'level': 'unknown'})

    return {
        'state': state_slug,
        'state_abbrev': STATE_SLUGS[state_slug],
        'court_slug': court_slug,
        'court_name': court_info['name'],
        'court_level': court_info['level'],
        'year': year,
        'case_id': case_id,
    }


def score_title_for_child_welfare(title: str) -> Tuple[float, List[str], str]:
    """Score case title for child welfare relevance."""
    if not title:
        return 0.0, [], None

    keywords_found = []

    # Check HIGH patterns
    for pattern, desc in CW_PATTERNS_HIGH:
        if pattern.search(title):
            keywords_found.append(desc)

    if keywords_found:
        return 1.0, keywords_found, "High-confidence: " + ", ".join(keywords_found[:3])

    # Check MEDIUM patterns
    for pattern, desc in CW_PATTERNS_MEDIUM:
        if pattern.search(title):
            keywords_found.append(desc)

    if keywords_found:
        return 0.7, keywords_found, "Medium-confidence: " + ", ".join(keywords_found[:3])

    # Check LOW patterns
    for pattern, desc in CW_PATTERNS_LOW:
        if pattern.search(title):
            keywords_found.append(desc)

    if keywords_found:
        return 0.3, keywords_found, "Low-confidence: " + ", ".join(keywords_found[:3])

    return 0.0, [], None


def process_browser_data(file_path: str, state_filter: Optional[str] = None) -> List[CaseRecord]:
    """
    Process browser-extracted data file.

    Handles files with one or two JSON arrays:
    - First array: All links {text, url}
    - Second array (optional): Filtered CW cases {title, url}
    """
    with open(file_path) as f:
        content = f.read()

    # Split on ][ to find multiple arrays
    # Be careful with regex to handle whitespace
    parts = re.split(r'\]\s*\[', content)

    all_items = []

    for i, part in enumerate(parts):
        # Fix the JSON array brackets
        if i == 0:
            part = part + ']'
        elif i == len(parts) - 1:
            part = '[' + part
        else:
            part = '[' + part + ']'

        try:
            items = json.loads(part)
            all_items.extend(items)
        except json.JSONDecodeError:
            continue

    # Build URL -> title mapping (later items override earlier)
    url_to_title = {}
    for item in all_items:
        url = item.get('url', '')
        title = item.get('title') or item.get('text', '')
        if url and title:
            url_to_title[url] = title

    # Process all case URLs
    records = []
    seen = set()

    for url, title in url_to_title.items():
        if url in seen:
            continue
        seen.add(url)

        parsed = parse_case_url(url)
        if not parsed:
            continue

        if state_filter and parsed['state'] != state_filter:
            continue

        # Score title for child welfare
        confidence, keywords, reason = score_title_for_child_welfare(title)

        # Create citation
        citation = f"{parsed['state_abbrev']} {parsed['court_name']} {parsed['case_id']}"
        citation_full = f"{parsed['state'].replace('-', ' ').title()} {parsed['court_name']} Case {parsed['case_id']} ({parsed['year']})"

        # Priority based on confidence
        if confidence >= 0.9:
            priority = 1
        elif confidence >= 0.5:
            priority = 2
        elif confidence > 0:
            priority = 3
        else:
            priority = 4

        record = CaseRecord(
            url=url,
            url_hash=hashlib.sha256(url.encode()).hexdigest()[:16],
            domain='law.justia.com',
            state=parsed['state'],
            state_abbrev=parsed['state_abbrev'],
            resource_type='case_law',
            resource_subtype=parsed['court_slug'].replace('-', '_'),
            court_name=parsed['court_name'],
            court_level=parsed['court_level'],
            category='judicial',
            year=parsed['year'],
            case_id=parsed['case_id'],
            citation=citation,
            citation_full=citation_full,
            title=title,
            parties=None,
            child_welfare_relevant=confidence > 0,
            child_welfare_confidence=confidence,
            child_welfare_reason=reason,
            child_welfare_keywords=keywords,
            serialization_priority=priority,
            metadata_source='browser_extraction',
            extracted_at=datetime.now(timezone.utc).isoformat(),
            content_hash=None,
        )
        records.append(record)

    return records


def save_cases(records: List[CaseRecord], output_dir: Path, state: str, court: str = None):
    """Save case records to JSONL files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"_{court}" if court else ""

    # All cases
    all_file = output_dir / f"{state}{suffix}_cases_all.jsonl"
    with open(all_file, 'w') as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + '\n')

    # Child welfare cases
    cw_records = [r for r in records if r.child_welfare_relevant]
    cw_file = output_dir / f"{state}{suffix}_cases_cw.jsonl"
    with open(cw_file, 'w') as f:
        for r in cw_records:
            f.write(json.dumps(asdict(r)) + '\n')

    # Summary
    summary = {
        'state': state,
        'court': court,
        'total_cases': len(records),
        'child_welfare_cases': len(cw_records),
        'by_priority': defaultdict(int),
        'by_year': defaultdict(int),
        'cw_keywords_found': defaultdict(int),
        'extracted_at': datetime.now(timezone.utc).isoformat(),
    }

    for r in records:
        summary['by_priority'][str(r.serialization_priority)] += 1
        summary['by_year'][str(r.year)] += 1
        for kw in r.child_welfare_keywords:
            summary['cw_keywords_found'][kw] += 1

    # Convert defaultdicts to regular dicts for JSON
    summary['by_priority'] = dict(summary['by_priority'])
    summary['by_year'] = dict(summary['by_year'])
    summary['cw_keywords_found'] = dict(summary['cw_keywords_found'])

    summary_file = output_dir / f"{state}{suffix}_cases_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    parser = argparse.ArgumentParser(description='Process browser-extracted case data')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file from browser')
    parser.add_argument('--state', '-s', required=True, help='State slug')
    parser.add_argument('--court', '-c', help='Court slug (e.g., supreme-court)')
    parser.add_argument('--output', '-o',
                        default='./data/sources/case_law/',
                        help='Output directory')

    args = parser.parse_args()

    print(f"Processing {args.input}...")
    records = process_browser_data(args.input, args.state)

    print(f"Found {len(records)} case records")

    output_dir = Path(args.output)
    summary = save_cases(records, output_dir, args.state, args.court)

    print(f"\n{'='*60}")
    print(f"RESULTS: {args.state.upper()} {args.court or ''}")
    print(f"{'='*60}")
    print(f"Total cases: {summary['total_cases']}")
    print(f"Child welfare: {summary['child_welfare_cases']}")
    print(f"\nBy priority:")
    for p, c in sorted(summary['by_priority'].items()):
        labels = {1: 'Critical CW', 2: 'High CW', 3: 'Low CW', 4: 'General'}
        print(f"  Priority {p} ({labels.get(int(p), '')}): {c}")

    if summary['cw_keywords_found']:
        print(f"\nChild welfare keywords found:")
        for kw, c in sorted(summary['cw_keywords_found'].items(), key=lambda x: -x[1]):
            print(f"  {kw}: {c}")

    print(f"\nSaved to: {output_dir}")


if __name__ == '__main__':
    main()
