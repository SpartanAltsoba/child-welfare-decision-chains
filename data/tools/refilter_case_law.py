#!/usr/bin/env python3
"""
Re-filter case law data to remove false positives.

The original filter marked "In re Estate", "In re Trust" cases as child-welfare-relevant.
This script properly filters for ACTUAL child welfare cases.

Usage:
    python refilter_case_law.py --state nevada
    python refilter_case_law.py --all
"""

import json
import re
import argparse
from pathlib import Path

CASE_LAW_DIR = Path("./data/sources/case_law")

# FALSE POSITIVE patterns - these should NOT be marked as child welfare relevant
FALSE_POSITIVE_PATTERNS = [
    re.compile(r'\bEstate\s+of\b', re.IGNORECASE),
    re.compile(r'\bTrust\b', re.IGNORECASE),
    re.compile(r'\bRevocable\s+Trust\b', re.IGNORECASE),
    re.compile(r'\bFamily\s+Trust\b', re.IGNORECASE),
    re.compile(r'\bLiving\s+Trust\b', re.IGNORECASE),
    re.compile(r'\bBankruptcy\b', re.IGNORECASE),
    re.compile(r'\bProbate\b', re.IGNORECASE),
    re.compile(r'\bWill\s+of\b', re.IGNORECASE),
    re.compile(r'\bDecedent\b', re.IGNORECASE),
    re.compile(r'\bInheritance\b', re.IGNORECASE),
    re.compile(r'\bSuccession\b', re.IGNORECASE),
    re.compile(r'\bTestamentary\b', re.IGNORECASE),
]

# TRUE POSITIVE patterns - these ARE child welfare relevant
TRUE_POSITIVE_PATTERNS = [
    (re.compile(r'\bDHR\b', re.IGNORECASE), 'DHR'),
    (re.compile(r'\bDCFS\b', re.IGNORECASE), 'DCFS'),
    (re.compile(r'\bDCS\b', re.IGNORECASE), 'DCS'),
    (re.compile(r'\bDCF\b', re.IGNORECASE), 'DCF'),
    (re.compile(r'\bDFPS\b', re.IGNORECASE), 'DFPS'),
    (re.compile(r'\bCPS\b', re.IGNORECASE), 'CPS'),
    (re.compile(r'\bChild Protective Services\b', re.IGNORECASE), 'CPS'),
    (re.compile(r'\bJuvenile Court\b', re.IGNORECASE), 'Juvenile'),
    (re.compile(r'\btermination of parental rights\b', re.IGNORECASE), 'TPR'),
    (re.compile(r'\bTPR\b', re.IGNORECASE), 'TPR'),
    (re.compile(r'\bdependency\b', re.IGNORECASE), 'dependency'),
    (re.compile(r'\bfoster care\b', re.IGNORECASE), 'foster care'),
    (re.compile(r'\bchild abuse\b', re.IGNORECASE), 'child abuse'),
    (re.compile(r'\bchild neglect\b', re.IGNORECASE), 'child neglect'),
    (re.compile(r'\badoption\b', re.IGNORECASE), 'adoption'),
    (re.compile(r'\bguardianship\b', re.IGNORECASE), 'guardianship'),
    (re.compile(r'\breunification\b', re.IGNORECASE), 'reunification'),
    (re.compile(r'\bpermanency\b', re.IGNORECASE), 'permanency'),
    (re.compile(r'\bICWA\b', re.IGNORECASE), 'ICWA'),
    (re.compile(r'\bchild welfare\b', re.IGNORECASE), 'child welfare'),
    (re.compile(r'\bchild custody\b', re.IGNORECASE), 'custody'),
    (re.compile(r'\bparental rights\b', re.IGNORECASE), 'parental rights'),
    (re.compile(r'\bminor child\b', re.IGNORECASE), 'minor child'),
    # "In re" with initials like "In re A.B." or "In re J.D.C."
    (re.compile(r'\bIn\s+re[:\s]+[A-Z]\.[A-Z]\.', re.IGNORECASE), 'In re child initials'),
    (re.compile(r'\bEx\s+parte\s+[A-Z]\.[A-Z]\.', re.IGNORECASE), 'Ex parte child'),
]


def is_false_positive(title: str) -> bool:
    """Check if a case title is a false positive (estate, trust, bankruptcy, etc.)"""
    for pattern in FALSE_POSITIVE_PATTERNS:
        if pattern.search(title):
            return True
    return False


def get_cw_relevance(title: str) -> tuple:
    """Check if a case is truly child-welfare-relevant and return keywords."""
    if not title:
        return False, 0.0, [], None

    # First check for false positives
    if is_false_positive(title):
        return False, 0.0, [], "Excluded: estate/trust/probate case"

    # Then check for true positives
    keywords = []
    for pattern, keyword in TRUE_POSITIVE_PATTERNS:
        if pattern.search(title):
            keywords.append(keyword)

    if keywords:
        confidence = 1.0 if len(keywords) >= 2 else 0.8
        return True, confidence, keywords, f"Child welfare: {', '.join(keywords[:3])}"

    return False, 0.0, [], None


def refilter_state(state: str):
    """Re-filter case law for a single state."""
    crawled_file = CASE_LAW_DIR / f"{state}_cases_crawled.jsonl"
    cw_file = CASE_LAW_DIR / f"{state}_cases_cw_crawled.jsonl"

    if not crawled_file.exists():
        print(f"  Skipping {state}: no crawled file")
        return 0, 0

    cw_cases = []
    total = 0

    with open(crawled_file, 'r') as f:
        for line in f:
            total += 1
            try:
                case = json.loads(line.strip())
                title = case.get('title', '')

                is_relevant, confidence, keywords, reason = get_cw_relevance(title)

                if is_relevant:
                    case['child_welfare_relevant'] = True
                    case['child_welfare_confidence'] = confidence
                    case['child_welfare_keywords'] = keywords
                    case['child_welfare_reason'] = reason
                    cw_cases.append(case)

            except json.JSONDecodeError:
                continue

    # Write filtered CW file
    with open(cw_file, 'w') as f:
        for case in cw_cases:
            f.write(json.dumps(case) + '\n')

    print(f"  {state}: {len(cw_cases)}/{total} cases are child-welfare-relevant")
    return len(cw_cases), total


def main():
    parser = argparse.ArgumentParser(description='Re-filter case law for child welfare relevance')
    parser.add_argument('--state', help='State to filter (e.g., nevada)')
    parser.add_argument('--all', action='store_true', help='Filter all states')
    args = parser.parse_args()

    if args.all:
        states = [f.stem.replace('_cases_crawled', '')
                  for f in CASE_LAW_DIR.glob('*_cases_crawled.jsonl')]
    elif args.state:
        states = [args.state.lower().replace(' ', '-')]
    else:
        print("Usage: python refilter_case_law.py --state nevada")
        print("       python refilter_case_law.py --all")
        return

    print(f"Re-filtering {len(states)} states...")

    total_cw = 0
    total_all = 0

    for state in sorted(states):
        cw, all_cases = refilter_state(state)
        total_cw += cw
        total_all += all_cases

    print(f"\nTotal: {total_cw}/{total_all} child-welfare-relevant cases")


if __name__ == '__main__':
    main()
