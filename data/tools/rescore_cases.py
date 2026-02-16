#!/usr/bin/env python3
"""
Re-score ALL case law for child welfare relevance with EXPANDED keywords.

The original crawler missed many cases because the keyword detection was too narrow.
This script re-scores ALL cases with expanded keywords to catch:
- ALL state agency acronyms (IDHW, SCDSS, DSS, DCYF, OCS, DFCS, ACS, etc.)
- Broader "In re" patterns (full names, not just initials)
- Jane/John Doe patterns
- Department of Social Services variations
- More child welfare keywords

Usage:
    python rescore_cases.py --all           # Re-score all states
    python rescore_cases.py --state wyoming # Re-score single state
    python rescore_cases.py --dry-run       # Preview without writing
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Dict, Tuple

# ============================================================================
# PATHS
# ============================================================================

CASE_LAW_DIR = Path("./data/sources/case_law")

# ============================================================================
# EXPANDED CHILD WELFARE KEYWORDS
# ============================================================================

# State agency acronyms - EVERY state's child welfare agency
STATE_AGENCIES = [
    # Generic
    (r'\bDHR\b', 'DHR'),  # Dept Human Resources (AL, others)
    (r'\bDHHS\b', 'DHHS'),  # Dept Health Human Services
    (r'\bDHS\b', 'DHS'),  # Dept Human Services (many states)
    (r'\bDSS\b', 'DSS'),  # Dept Social Services (many states)
    (r'\bDCFS\b', 'DCFS'),  # Dept Children Family Services (IL, LA)
    (r'\bDCS\b', 'DCS'),  # Dept Child Services (IN, TN, AZ)
    (r'\bDCF\b', 'DCF'),  # Dept Children Families (CT, FL, NJ, VT)
    (r'\bDFPS\b', 'DFPS'),  # Dept Family Protective Services (TX)
    (r'\bCPS\b', 'CPS'),  # Child Protective Services
    (r'\bDCYF\b', 'DCYF'),  # Dept Children Youth Families (NH, RI, WA)
    (r'\bDFCS\b', 'DFCS'),  # Dept Family Children Services (GA)
    (r'\bOCS\b', 'OCS'),  # Office Child Services (AK)
    (r'\bDCPP\b', 'DCPP'),  # Div Child Protection Permanency (NJ)
    (r'\bDYFS\b', 'DYFS'),  # Div Youth Family Services (NJ old)
    (r'\bACS\b', 'ACS'),  # Admin Children Services (NYC)
    (r'\bCWS\b', 'CWS'),  # Child Welfare Services
    (r'\bOCFS\b', 'OCFS'),  # Office Children Family Services (NY)

    # State-specific full names
    (r'\bIdaho Department of Health and Welfare\b', 'IDHW'),
    (r'\bIDHW\b', 'IDHW'),  # Idaho
    (r'\bSCDSS\b', 'SCDSS'),  # South Carolina
    (r'\bSouth Carolina Department of Social Services\b', 'SCDSS'),
    (r'\bMDHS\b', 'MDHS'),  # Maryland
    (r'\bMaryland Department of Human Services\b', 'MDHS'),
    (r'\bCDSS\b', 'CDSS'),  # California
    (r'\bCalifornia Department of Social Services\b', 'CDSS'),
    (r'\bODHS\b', 'ODHS'),  # Oregon
    (r'\bOregon Department of Human Services\b', 'ODHS'),
    (r'\bODJFS\b', 'ODJFS'),  # Ohio
    (r'\bOhio Department of Job and Family Services\b', 'ODJFS'),
    (r'\bNCDHHS\b', 'NCDHHS'),  # North Carolina
    (r'\bDepartment of Family Services\b', 'DFS'),
    (r'\bDFS\b', 'DFS'),  # Wyoming, others
    (r'\bFamily Services\b', 'Family Services'),
    (r'\bDepartment of Social Services\b', 'DSS'),
    (r'\bDepartment of Human Resources\b', 'DHR'),
    (r'\bDepartment of Children and Families\b', 'DCF'),
    (r'\bDepartment of Children and Family Services\b', 'DCFS'),
    (r'\bChild Protective Services\b', 'CPS'),
    (r'\bDivision of Child and Family Services\b', 'DCFS'),
    (r'\bOffice of Children and Family Services\b', 'OCFS'),
]

# Judicial/procedural keywords
JUDICIAL_KEYWORDS = [
    (r'\bJuvenile Court\b', 'Juvenile Court'),
    (r'\bJuvenile\s*:\s*JU-', 'Juvenile docket'),
    (r'\bJU-\d{2}-\d+', 'JU case number'),
    (r'\bDN-\d+', 'DN case number'),  # Dependency case numbers
    (r'\bJD-\d+', 'JD case number'),  # Juvenile dependency
    (r'\bFC-\d+', 'FC case number'),  # Family court
    (r'\bdependency proceeding\b', 'dependency proceeding'),
    (r'\bchild dependency\b', 'child dependency'),
    (r'\bjuvenile dependency\b', 'juvenile dependency'),
]

# Termination and permanency
TPR_KEYWORDS = [
    (r'\btermination of parental rights\b', 'TPR'),
    (r'\bTPR\b', 'TPR'),
    (r'\bparental rights termination\b', 'TPR'),
    (r'\binvoluntary termination\b', 'involuntary TPR'),
    (r'\bpermanency plan\b', 'permanency'),
    (r'\bpermanency hearing\b', 'permanency'),
]

# Abuse/neglect
ABUSE_KEYWORDS = [
    (r'\bchild abuse\b', 'child abuse'),
    (r'\bchild neglect\b', 'child neglect'),
    (r'\babuse and neglect\b', 'abuse/neglect'),
    (r'\babused or neglected\b', 'abuse/neglect'),
    (r'\bchild maltreatment\b', 'maltreatment'),
    (r'\bsubstantiated\b', 'substantiated'),
    (r'\bfounded\b', 'founded'),
    (r'\bunfounded\b', 'unfounded'),
]

# Foster care and placement
PLACEMENT_KEYWORDS = [
    (r'\bfoster care\b', 'foster care'),
    (r'\bfoster parent\b', 'foster care'),
    (r'\bkinship care\b', 'kinship'),
    (r'\bkinship placement\b', 'kinship'),
    (r'\bout[- ]of[- ]home placement\b', 'placement'),
    (r'\brelative placement\b', 'placement'),
    (r'\bprotective custody\b', 'protective custody'),
    (r'\bemergency removal\b', 'emergency removal'),
    (r'\bemergency custody\b', 'emergency custody'),
]

# "In re" patterns - EXPANDED to catch more
IN_RE_PATTERNS = [
    # Two initials: "In re A.B."
    (r'\bIn re[:\s]+[A-Z]\.[A-Z]\.', 'In re initials'),
    # Three initials: "In re A.B.C."
    (r'\bIn re[:\s]+[A-Z]\.[A-Z]\.[A-Z]\.', 'In re initials'),
    # Single initial: "In re A."
    (r'\bIn re[:\s]+[A-Z]\.(?:\s|$|,)', 'In re initial'),
    # Full name with hyphen: "In re Teagan K.-O."
    (r'\bIn re[:\s]+[A-Z][a-z]+\s+[A-Z]\.-[A-Z]\.', 'In re name'),
    # Full first name + initial: "In re John D."
    (r'\bIn re[:\s]+[A-Z][a-z]+\s+[A-Z]\.', 'In re name'),
    # "In re the Child(ren)"
    (r'\bIn re[:\s]+(?:the\s+)?[Cc]hild(?:ren)?\b', 'In re child'),
    # "In re Minor"
    (r'\bIn re[:\s]+(?:the\s+)?[Mm]inor\b', 'In re minor'),
    # "In re Adoption"
    (r'\bIn re[:\s]+(?:the\s+)?[Aa]doption\b', 'In re adoption'),
    # "In re Guardianship"
    (r'\bIn re[:\s]+(?:the\s+)?[Gg]uardianship\b', 'In re guardianship'),
    # "In re Termination"
    (r'\bIn re[:\s]+(?:the\s+)?[Tt]ermination\b', 'In re TPR'),
    # "In re Interest of"
    (r'\bIn (?:re|the) [Ii]nterest of\b', 'In re interest'),
    # "In re Baby"
    (r'\bIn re[:\s]+[Bb]aby\b', 'In re baby'),
    # "In re Jane/John Doe"
    (r'\bIn re[:\s]+(?:Jane|John)\s+Doe\b', 'In re Doe'),
    # Generic any name after "In re"
    (r'\bIn re[:\s]+[A-Z][a-z]+\b', 'In re'),
]

# "Ex parte" patterns
EX_PARTE_PATTERNS = [
    (r'\bEx parte [A-Z]\.[A-Z]\.', 'Ex parte initials'),
    (r'\bEx parte [A-Z]\.[A-Z]\.[A-Z]\.', 'Ex parte initials'),
    (r'\bEx parte [A-Z][a-z]+\s+[A-Z]\.', 'Ex parte name'),
]

# "Matter of" patterns
MATTER_OF_PATTERNS = [
    (r'\b[Mm]atter of[:\s]+[A-Z]\.[A-Z]\.', 'Matter of initials'),
    (r'\b[Mm]atter of[:\s]+the\s+[Tt]ermination\b', 'Matter of TPR'),
    (r'\b[Mm]atter of[:\s]+the\s+[Aa]doption\b', 'Matter of adoption'),
    (r'\b[Mm]atter of[:\s]+[A-Z][a-z]+', 'Matter of'),
]

# Interest of patterns
INTEREST_OF_PATTERNS = [
    (r'\b[Ii]nterest of[:\s]+[A-Z]\.[A-Z]\.', 'Interest of initials'),
    (r'\b[Ii]nterest of[:\s]+[A-Z][a-z]+', 'Interest of'),
    (r'\b[Ii]nterest of[:\s]+(?:a\s+)?[Mm]inor', 'Interest of minor'),
]

# Doe patterns (anonymized parties)
DOE_PATTERNS = [
    (r'\bJane Doe\b', 'Jane Doe'),
    (r'\bJohn Doe\b', 'John Doe'),
    (r'\bBaby Doe\b', 'Baby Doe'),
    (r'\bJuvenile Doe\b', 'Juvenile Doe'),
    (r'\bMinor Doe\b', 'Minor Doe'),
    (r'\bDoe v\.\s+', 'Doe plaintiff'),
    (r'\bv\.\s+Doe\b', 'Doe defendant'),
]

# Other high-relevance
OTHER_HIGH = [
    (r'\bdependency\b', 'dependency'),
    (r'\bchild welfare\b', 'child welfare'),
    (r'\breasonable efforts\b', 'reasonable efforts'),
    (r'\bASFA\b', 'ASFA'),
    (r'\bMEPPA\b', 'MEPA'),
    (r'\bICWA\b', 'ICWA'),
    (r'\bIndian Child Welfare\b', 'ICWA'),
    (r'\b42 U\.?S\.?C\.?\s*§?\s*1983\b', '42 USC 1983'),
    (r'\b§\s*1983\b', '1983'),
    (r'\bSection 1983\b', '1983'),
    (r'\bconstitutional rights\b', 'constitutional'),
    (r'\bfourteenth amendment\b', '14th amendment'),
    (r'\bdue process\b', 'due process'),
]

# Medium relevance
MEDIUM_KEYWORDS = [
    (r'\bchild custody\b', 'child custody'),
    (r'\bminor child\b', 'minor child'),
    (r'\bparental rights\b', 'parental rights'),
    (r'\bguardianship\b', 'guardianship'),
    (r'\badoption\b', 'adoption'),
    (r'\breunification\b', 'reunification'),
    (r'\bpermanency\b', 'permanency'),
    (r'\bvisitation\b', 'visitation'),
    (r'\bparenting time\b', 'parenting time'),
    (r'\bbest interest of the child\b', 'best interest'),
]

# Compile all patterns
def compile_patterns():
    """Compile all regex patterns."""
    high = []
    for patterns in [STATE_AGENCIES, JUDICIAL_KEYWORDS, TPR_KEYWORDS,
                     ABUSE_KEYWORDS, PLACEMENT_KEYWORDS, IN_RE_PATTERNS,
                     EX_PARTE_PATTERNS, MATTER_OF_PATTERNS, INTEREST_OF_PATTERNS,
                     DOE_PATTERNS, OTHER_HIGH]:
        high.extend(patterns)

    high_compiled = [(re.compile(p, re.IGNORECASE), d) for p, d in high]
    medium_compiled = [(re.compile(p, re.IGNORECASE), d) for p, d in MEDIUM_KEYWORDS]

    return high_compiled, medium_compiled

CW_PATTERNS_HIGH, CW_PATTERNS_MEDIUM = compile_patterns()


def score_title(title: str) -> Tuple[float, List[str], str]:
    """Score case title for child welfare relevance with EXPANDED keywords."""
    if not title:
        return 0.0, [], None

    keywords = []

    # Check HIGH patterns
    for pattern, desc in CW_PATTERNS_HIGH:
        if pattern.search(title):
            if desc not in keywords:  # Avoid duplicates
                keywords.append(desc)

    if keywords:
        return 1.0, keywords, f"High: {', '.join(keywords[:5])}"

    # Check MEDIUM patterns
    for pattern, desc in CW_PATTERNS_MEDIUM:
        if pattern.search(title):
            if desc not in keywords:
                keywords.append(desc)

    if keywords:
        return 0.7, keywords, f"Medium: {', '.join(keywords[:3])}"

    return 0.0, [], None


def rescore_state(state: str, dry_run: bool = False) -> Dict:
    """Re-score all cases for a state with expanded keywords."""

    # Load all cases
    all_file = CASE_LAW_DIR / f"{state}_cases_crawled.jsonl"
    if not all_file.exists():
        print(f"No case file found: {all_file}")
        return None

    cases = []
    with open(all_file) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    original_cw = sum(1 for c in cases if c.get('child_welfare_relevant', False))

    # Re-score each case
    rescored = []
    for case in cases:
        title = case.get('title', '')
        confidence, keywords, reason = score_title(title)

        # Update the record
        case['child_welfare_relevant'] = confidence > 0
        case['child_welfare_confidence'] = confidence
        case['child_welfare_reason'] = reason
        case['child_welfare_keywords'] = keywords
        case['rescored_at'] = datetime.now(timezone.utc).isoformat()

        # Update priority
        if confidence >= 0.9:
            case['serialization_priority'] = 1
        elif confidence >= 0.5:
            case['serialization_priority'] = 2
        elif confidence > 0:
            case['serialization_priority'] = 3
        else:
            case['serialization_priority'] = 4

        rescored.append(case)

    new_cw = sum(1 for c in rescored if c.get('child_welfare_relevant', False))

    stats = {
        'state': state,
        'total_cases': len(cases),
        'original_cw': original_cw,
        'new_cw': new_cw,
        'added': new_cw - original_cw,
        'increase_pct': ((new_cw - original_cw) / max(original_cw, 1)) * 100
    }

    print(f"{state.upper()}: {original_cw} -> {new_cw} CW cases (+{stats['added']}, +{stats['increase_pct']:.1f}%)")

    if dry_run:
        return stats

    # Save updated files
    # All cases
    with open(all_file, 'w') as f:
        for case in rescored:
            f.write(json.dumps(case) + '\n')

    # CW cases only
    cw_file = CASE_LAW_DIR / f"{state}_cases_cw_crawled.jsonl"
    cw_cases = [c for c in rescored if c.get('child_welfare_relevant', False)]
    with open(cw_file, 'w') as f:
        for case in cw_cases:
            f.write(json.dumps(case) + '\n')

    return stats


def main():
    parser = argparse.ArgumentParser(description='Re-score case law with expanded CW keywords')
    parser.add_argument('--state', type=str, help='State slug (e.g., wyoming)')
    parser.add_argument('--all', action='store_true', help='Re-score all states')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')

    args = parser.parse_args()

    if not args.state and not args.all:
        parser.error("Must specify --state or --all")

    print(f"\n{'='*60}")
    print("RE-SCORING CASE LAW WITH EXPANDED KEYWORDS")
    print(f"{'='*60}")
    print(f"High-relevance patterns: {len(CW_PATTERNS_HIGH)}")
    print(f"Medium-relevance patterns: {len(CW_PATTERNS_MEDIUM)}")
    print()

    all_stats = []

    if args.all:
        # Get all state files
        state_files = sorted(CASE_LAW_DIR.glob("*_cases_crawled.jsonl"))
        for state_file in state_files:
            state = state_file.stem.replace('_cases_crawled', '')
            stats = rescore_state(state, args.dry_run)
            if stats:
                all_stats.append(stats)
    else:
        stats = rescore_state(args.state, args.dry_run)
        if stats:
            all_stats.append(stats)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_original = sum(s['original_cw'] for s in all_stats)
    total_new = sum(s['new_cw'] for s in all_stats)
    total_added = sum(s['added'] for s in all_stats)

    print(f"States processed: {len(all_stats)}")
    print(f"Original CW cases: {total_original}")
    print(f"New CW cases: {total_new}")
    print(f"Cases added: {total_added} (+{(total_added/max(total_original,1))*100:.1f}%)")

    if args.dry_run:
        print("\n[DRY RUN - No files modified]")
    else:
        print("\nFiles updated successfully!")


if __name__ == "__main__":
    main()
