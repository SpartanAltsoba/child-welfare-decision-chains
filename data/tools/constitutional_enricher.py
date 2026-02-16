#!/usr/bin/env python3
"""
Constitutional Enricher - Populates state constitutional files with case law

This tool enriches the state constitutional plane files with relevant case law
from the serialized case law leaves. It matches cases to constitutional provisions
based on keywords and populates the `key_cases` arrays.

The 5D system requires every legal plane to have linked source documents:
- Constitutional plane ✓ (has federal case law)
- Federal plane ✓ (has statutory citations)
- State constitutional plane ← THIS TOOL enriches these
- State statutory plane ✓ (linked via leaf_linker)
- Case law plane ✓ (linked via leaf_linker)

Usage:
    python constitutional_enricher.py --all           # Enrich all states
    python constitutional_enricher.py --state TX      # Enrich single state
    python constitutional_enricher.py --dry-run       # Preview without writing
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from collections import defaultdict

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path("./data")
STATE_CONST_DIR = BASE_DIR / "legal_planes/state_constitutional"
CASE_LAW_DIR = BASE_DIR / "sources/case_law"

# State code to slug mapping
STATE_SLUGS = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "DC": "district-of-columbia", "FL": "florida", "GA": "georgia", "HI": "hawaii",
    "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine",
    "MD": "maryland", "MA": "massachusetts", "MI": "michigan", "MN": "minnesota",
    "MS": "mississippi", "MO": "missouri", "MT": "montana", "NE": "nebraska",
    "NV": "nevada", "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico",
    "NY": "new-york", "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio",
    "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island",
    "SC": "south-carolina", "SD": "south-dakota", "TN": "tennessee", "TX": "texas",
    "UT": "utah", "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west-virginia", "WI": "wisconsin", "WY": "wyoming"
}

# ============================================================================
# CONSTITUTIONAL PROVISION KEYWORDS - TOPIC-BASED MATCHING
# CW cases are matched to constitutional provisions based on the action/topic,
# not just explicit constitutional language. E.g., all TPR cases inherently
# involve due process rights even if the case title doesn't say "due process".
# ============================================================================

PROVISION_KEYWORDS = {
    # Fourth Amendment - Search and Seizure
    # Any case involving removal, home visits, or investigation touches 4th amendment
    "SEARCH_SEIZURE": [
        # Explicit constitutional terms
        "fourth amendment", "4th amendment", "search", "seizure",
        "warrantless", "warrant", "exigent", "probable cause", "reasonable suspicion",
        "unlawful entry", "illegal search", "knock and announce",
        # Topic-based: any removal/entry case implicates 4th amendment
        "emergency removal", "protective custody", "removal", "removed",
        "home entry", "home visit", "investigation", "consent",
        "took custody", "taking custody", "seized"
    ],

    # Fourteenth Amendment - Due Process (Procedural)
    # Any case involving TPR, hearings, or procedure touches due process
    "DUE_PROCESS": [
        # Explicit constitutional terms
        "due process", "procedural due process", "notice", "hearing",
        "opportunity to be heard", "neutral decision", "fair hearing",
        "fundamental fairness", "deprivation", "liberty interest",
        "fourteenth amendment", "14th amendment",
        # Topic-based: any TPR/dependency case involves due process
        "termination of parental rights", "parental rights terminated",
        "termination", "TPR", "dependency", "adjudication",
        "permanency", "review hearing", "shelter care",
        "clear and convincing", "burden of proof"
    ],

    # Fourteenth Amendment - Substantive Due Process / Family Integrity
    # Any case about family preservation or reunification touches this
    "FAMILY_INTEGRITY": [
        # Explicit constitutional terms
        "substantive due process", "family integrity", "familial association",
        "parental rights", "fundamental right", "liberty interest",
        "care and custody", "control of children", "family relationship",
        "family unit", "parent-child relationship",
        # Topic-based: reunification/preservation cases
        "reunification", "reunify", "family preservation",
        "reasonable efforts", "return home", "best interest",
        "parent", "child", "custody", "visitation"
    ],

    # Equal Protection
    "EQUAL_PROTECTION": [
        "equal protection", "discrimination", "disparate treatment",
        "racial bias", "similarly situated", "classification",
        # Topic-based
        "ICWA", "Indian Child Welfare", "tribal", "native american",
        "disproportionality", "race", "ethnicity"
    ],

    # Fifth Amendment - Self-Incrimination
    "SELF_INCRIMINATION": [
        "fifth amendment", "5th amendment", "self-incrimination",
        "right to remain silent", "miranda", "compelled statement",
        "testimonial", "privilege against",
        # Topic-based
        "criminal referral", "criminal charges", "confession"
    ],

    # Right to Counsel
    "RIGHT_TO_COUNSEL": [
        "right to counsel", "legal representation",
        "sixth amendment", "6th amendment", "appointed counsel",
        "ineffective assistance",
        # Topic-based: any case mentioning representation
        "counsel", "attorney", "public defender", "GAL", "guardian ad litem",
        "CASA", "advocate"
    ],

    # First Amendment - Religion
    "RELIGION": [
        "first amendment", "1st amendment", "religious", "religion",
        "free exercise", "establishment clause", "faith-based",
        # Topic-based
        "church", "prayer", "spiritual", "faith"
    ],

    # Section 1983 - Civil Rights
    "SECTION_1983": [
        "1983", "section 1983", "42 u.s.c", "civil rights",
        "qualified immunity", "color of law", "constitutional violation",
        "deliberate indifference", "municipal liability", "monell",
        # Topic-based: any case alleging CPS wrongdoing
        "wrongful removal", "false report", "abuse of authority",
        "damages", "liability", "negligence", "failure to protect",
        "failure to investigate"
    ]
}

# Compile patterns
PROVISION_PATTERNS = {}
for provision, keywords in PROVISION_KEYWORDS.items():
    patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE) for kw in keywords]
    PROVISION_PATTERNS[provision] = patterns


class ConstitutionalEnricher:
    """Enriches state constitutional files with case law."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = defaultdict(int)
        self.case_cache: Dict[str, List[Dict]] = {}

    def load_cases(self, state_code: str) -> List[Dict]:
        """Load CW cases for a state."""
        if state_code in self.case_cache:
            return self.case_cache[state_code]

        slug = STATE_SLUGS.get(state_code, "").lower()
        if not slug:
            return []

        cw_file = CASE_LAW_DIR / f"{slug}_cases_cw_crawled.jsonl"

        cases = []
        if cw_file.exists():
            with open(cw_file) as f:
                for line in f:
                    if line.strip():
                        cases.append(json.loads(line))

        self.case_cache[state_code] = cases
        return cases

    def is_quality_cw_case(self, case: Dict) -> bool:
        """
        Filter out low-quality matches that are just "In re" without actual CW content.
        Returns True if the case appears to be a real CW case.
        """
        title = case.get('title', '').lower()
        reason = case.get('child_welfare_reason', '').lower()

        # "In re initials" = definitely CW case (anonymized child)
        if 'in re initials' in reason:
            return True

        # High-quality indicators (actual CW content)
        quality_indicators = [
            'child abuse', 'child neglect', 'dependency', 'dss', 'dcfs', 'dhs',
            'dfps', 'dfcs', 'cps', 'dcyf', 'cyfd', 'dcbs', 'odjfs', 'children services',
            'family services', 'foster', 'termination of parental rights', 'tpr',
            'parental rights', 'custody', 'abuse', 'neglect', 'minor child',
            'welfare of', 'protection of', 'dependency petition', 'adjudication',
            # Add state agency patterns
            'department of human', 'department of social', 'department of child',
            'child protective', 'family protective', 'children and families'
        ]

        for indicator in quality_indicators:
            if indicator in title or indicator in reason:
                return True

        # Check for child initials pattern (like "In re C.J.C." or "In re T.M.")
        initials_pattern = re.compile(r'in re [a-z]\.[a-z]\.?', re.IGNORECASE)
        if initials_pattern.search(title):
            return True

        # Single letter cases are also CW (like "In re A.B.")
        single_letter_pattern = re.compile(r'in re [a-z]\.[a-z]', re.IGNORECASE)
        if single_letter_pattern.search(title):
            return True

        # Interest of [initials] pattern
        if 'interest of' in title.lower():
            return True

        # Matter of [name/initials] pattern
        if 'matter of' in title.lower():
            return True

        # Reject cases that are just "In re [Name]" without CW indicators
        # These are likely other types of cases (commitment, election, etc.)
        if 'high: in re' in reason and 'initials' not in reason:
            cw_title_hints = ['minor', 'juvenile', 'child', 'adoption', 'guardianship', 'custody']
            if not any(hint in title for hint in cw_title_hints):
                return False

        return True

    def match_case_to_provisions(self, case: Dict) -> List[Tuple[str, int, List[str]]]:
        """
        Match a case to constitutional provisions.
        Returns list of (provision_type, score, matched_keywords)

        IMPORTANT: ALL CW cases inherently involve constitutional rights:
        - Every CW case involves DUE_PROCESS (parents have liberty interest in children)
        - Every CW case involves FAMILY_INTEGRITY (fundamental right to family)
        - Specific provisions (SEARCH_SEIZURE, SECTION_1983) require keyword matches
        """
        # Filter out low-quality matches
        if not self.is_quality_cw_case(case):
            return []

        title = case.get('title', '').lower()
        reason = case.get('child_welfare_reason', '').lower()
        text = f"{title} {reason}"

        matches = []

        # ALL CW cases get baseline constitutional relevance
        # Every CW case inherently involves due process and family integrity
        baseline_provisions = ['DUE_PROCESS', 'FAMILY_INTEGRITY']

        for provision_type, patterns in PROVISION_PATTERNS.items():
            score = 0
            matched_keywords = []

            # Check keyword matches
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
                    match = pattern.search(text)
                    if match:
                        matched_keywords.append(match.group())

            # If this is a baseline provision, give it minimum score of 1
            # (all CW cases involve these rights even without explicit keywords)
            if provision_type in baseline_provisions and score == 0:
                score = 1
                matched_keywords = ['child welfare case']

            if score > 0:
                matches.append((provision_type, score, matched_keywords))

        return matches

    def enrich_state(self, state_code: str) -> Dict:
        """Enrich a single state's constitutional file."""
        const_file = STATE_CONST_DIR / f"{state_code}_constitution.json"

        if not const_file.exists():
            print(f"  {state_code}: No constitution file found")
            return None

        # Load constitution
        with open(const_file) as f:
            const_data = json.load(f)

        # Load cases
        cases = self.load_cases(state_code)
        if not cases:
            print(f"  {state_code}: No CW cases found")
            return None

        print(f"  {state_code}: {len(cases)} CW cases available")

        # Match cases to provisions
        provision_cases: Dict[str, List[Dict]] = defaultdict(list)

        for case in cases:
            matches = self.match_case_to_provisions(case)

            for provision_type, score, matched_keywords in matches:
                provision_cases[provision_type].append({
                    "case_id": case.get('case_id', ''),
                    "title": case.get('title', ''),
                    "url": case.get('url', ''),
                    "year": case.get('year'),
                    "court": case.get('court_name', ''),
                    "citation": case.get('citation_full', case.get('citation', '')),
                    "relevance_score": score,
                    "matched_keywords": matched_keywords[:5],
                    "child_welfare_reason": case.get('child_welfare_reason', ''),
                    "provision_match": provision_type
                })

        # Sort each provision's cases by score and year
        for provision_type in provision_cases:
            provision_cases[provision_type].sort(
                key=lambda x: (-x['relevance_score'], -(x.get('year') or 0))
            )
            # Keep top 10
            provision_cases[provision_type] = provision_cases[provision_type][:10]

        # Update the constitution file
        total_linked = 0

        # Update relevant_provisions
        if 'relevant_provisions' in const_data:
            for provision in const_data['relevant_provisions']:
                prov_id = provision.get('provision_id', '')

                # Map provision_id to our keywords
                matched_type = None
                if 'SEARCH_SEIZURE' in prov_id:
                    matched_type = 'SEARCH_SEIZURE'
                elif 'DUE_PROCESS' in prov_id or 'DUE_COURSE' in prov_id:
                    matched_type = 'DUE_PROCESS'
                elif 'FAMILY' in prov_id or 'INTEGRITY' in prov_id:
                    matched_type = 'FAMILY_INTEGRITY'
                elif 'EQUAL' in prov_id:
                    matched_type = 'EQUAL_PROTECTION'
                elif 'SELF_INCRIM' in prov_id or '5A' in prov_id or 'FIFTH' in prov_id:
                    matched_type = 'SELF_INCRIMINATION'
                elif 'COUNSEL' in prov_id or '6A' in prov_id or 'SIXTH' in prov_id:
                    matched_type = 'RIGHT_TO_COUNSEL'
                elif 'RELIGION' in prov_id or '1A' in prov_id or 'FIRST' in prov_id:
                    matched_type = 'RELIGION'

                if matched_type and matched_type in provision_cases:
                    provision['key_cases'] = provision_cases[matched_type]
                    total_linked += len(provision_cases[matched_type])
                    self.stats['provisions_enriched'] += 1

        # Also populate state_supreme_court_cps_cases with all unique cases
        all_cases = []
        seen_ids = set()
        for prov_cases in provision_cases.values():
            for case in prov_cases:
                if case['case_id'] not in seen_ids:
                    all_cases.append(case)
                    seen_ids.add(case['case_id'])

        # Sort by year (most recent first)
        all_cases.sort(key=lambda x: -(x.get('year') or 0))
        const_data['state_supreme_court_cps_cases'] = all_cases[:20]  # Top 20

        # Add section 1983 cases separately
        if 'SECTION_1983' in provision_cases:
            const_data['section_1983_cases'] = provision_cases['SECTION_1983']
            total_linked += len(provision_cases['SECTION_1983'])

        # Update metadata
        if '_metadata' not in const_data:
            const_data['_metadata'] = {}
        const_data['_metadata']['case_law_enriched'] = datetime.now(timezone.utc).isoformat()
        const_data['_metadata']['enricher_version'] = "1.0.0"
        const_data['_metadata']['cases_analyzed'] = len(cases)
        const_data['_metadata']['cases_linked'] = total_linked
        const_data['_metadata']['requires_case_law_enrichment'] = False

        self.stats['cases_linked'] += total_linked
        self.stats['states_enriched'] += 1

        print(f"    Linked {total_linked} cases to provisions")

        if not self.dry_run:
            with open(const_file, 'w') as f:
                json.dump(const_data, f, indent=2)

        return const_data

    def enrich_all_states(self):
        """Enrich all state constitutional files."""
        for state_code in sorted(STATE_SLUGS.keys()):
            const_file = STATE_CONST_DIR / f"{state_code}_constitution.json"
            if const_file.exists():
                self.enrich_state(state_code)

    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print("CONSTITUTIONAL ENRICHMENT COMPLETE")
        print(f"{'='*60}")
        print(f"States enriched:      {self.stats['states_enriched']}")
        print(f"Provisions enriched:  {self.stats['provisions_enriched']}")
        print(f"Cases linked:         {self.stats['cases_linked']}")
        if self.dry_run:
            print("\n[DRY RUN - No files were modified]")


def main():
    parser = argparse.ArgumentParser(description="Enrich state constitutional files with case law")
    parser.add_argument('--state', type=str, help="State code (e.g., TX)")
    parser.add_argument('--all', action='store_true', help="Process all states")
    parser.add_argument('--dry-run', action='store_true', help="Preview without writing")

    args = parser.parse_args()

    if not args.state and not args.all:
        parser.error("Must specify --state or --all")

    print(f"\n{'='*60}")
    print("CONSTITUTIONAL ENRICHMENT")
    print("Linking CW case law to state constitutional provisions")
    print(f"{'='*60}\n")

    enricher = ConstitutionalEnricher(dry_run=args.dry_run)

    if args.all:
        enricher.enrich_all_states()
    else:
        enricher.enrich_state(args.state.upper())

    enricher.print_summary()


if __name__ == "__main__":
    main()
