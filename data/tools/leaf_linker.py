#!/usr/bin/env python3
"""
Leaf Linker - Connects source documents (leaves) to chain nodes

This tool systematically populates the `layers` section of each state node
with actual source documents from our crawled data:

1. case_law.key_cases      ← from sources/case_law/{state}_cases_cw_crawled.jsonl
2. state_statutory         ← from sources/labeled_index/{state}_labeled.jsonl (type=code)
3. administrative_rule     ← from sources/labeled_index/{state}_labeled.jsonl (type=admin_rule)

Usage:
    python leaf_linker.py --state AL           # Link leaves for Alabama only
    python leaf_linker.py --all                # Link leaves for all states
    python leaf_linker.py --dry-run --state AL # Preview without writing
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
from collections import defaultdict

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path("./data")
STATES_CHAINS_DIR = BASE_DIR / "states_chains"
CASE_LAW_DIR = BASE_DIR / "sources/case_law"
LABELED_INDEX_DIR = BASE_DIR / "sources/labeled_index"
LEGAL_FRAMEWORK_DIR = BASE_DIR / "sources/legal_framework"

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

# Node type to relevant keywords mapping (what cases are relevant to each node type)
NODE_KEYWORDS = {
    "INP": ["mandatory reporter", "hotline", "intake", "report", "referral", "disclosure"],
    "DEC": ["screen", "investigation", "substantiated", "founded", "unfounded",
            "emergency removal", "removal", "court petition", "differential response"],
    "ACT": ["removal", "protective custody", "foster care", "kinship", "placement",
            "in-home services", "case plan", "criminal referral", "closure"],
    "OUT": ["reunification", "termination of parental rights", "TPR", "adoption",
            "guardianship", "emancipation", "permanency"],
    "FAIL": ["failure to investigate", "wrongful removal", "due process", "abuse in care",
             "fatality", "wrongful TPR", "non-compliance", "1983", "civil rights"],
    "PMC": ["oversight", "CFSR", "audit", "citizen review", "transparency", "FOIA"]
}


class LeafLinker:
    """Links source documents (leaves) to chain nodes."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = defaultdict(int)

        # Load all source data
        self.case_law_by_state: Dict[str, List[Dict]] = {}
        self.labeled_urls_by_state: Dict[str, List[Dict]] = {}

    def load_case_law(self, state_code: str) -> List[Dict]:
        """Load child welfare case law for a state."""
        if state_code in self.case_law_by_state:
            return self.case_law_by_state[state_code]

        slug = STATE_SLUGS.get(state_code, "").lower()
        if not slug:
            return []

        # Try CW-specific file first, then all cases
        cw_file = CASE_LAW_DIR / f"{slug}_cases_cw_crawled.jsonl"
        all_file = CASE_LAW_DIR / f"{slug}_cases_crawled.jsonl"

        cases = []

        # Load CW cases (priority)
        if cw_file.exists():
            with open(cw_file) as f:
                for line in f:
                    if line.strip():
                        cases.append(json.loads(line))

        self.case_law_by_state[state_code] = cases
        return cases

    def load_labeled_urls(self, state_code: str) -> List[Dict]:
        """Load labeled URLs for a state."""
        if state_code in self.labeled_urls_by_state:
            return self.labeled_urls_by_state[state_code]

        slug = STATE_SLUGS.get(state_code, "").lower()
        if not slug:
            return []

        labeled_file = LABELED_INDEX_DIR / f"{slug}_labeled.jsonl"
        child_welfare_file = LABELED_INDEX_DIR / f"{slug}_child_welfare.jsonl"

        urls = []

        # Load child welfare URLs first (priority)
        if child_welfare_file.exists():
            with open(child_welfare_file) as f:
                for line in f:
                    if line.strip():
                        urls.append(json.loads(line))

        # Then load all labeled URLs
        if labeled_file.exists():
            seen_urls = {u['url'] for u in urls}
            with open(labeled_file) as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('url') not in seen_urls:
                            urls.append(record)

        self.labeled_urls_by_state[state_code] = urls
        return urls

    def match_cases_to_node(self, cases: List[Dict], node_data: Dict) -> List[Dict]:
        """Match cases to a node - ALL CW cases are relevant to ALL nodes in 5D system."""
        node_type = node_data.get('node_family', '')
        subnode = node_data.get('subnode', '')

        # Get keywords from the node for scoring (not filtering)
        search_keywords = []
        if 'layers' in node_data and 'case_law' in node_data['layers']:
            search_keywords = node_data['layers']['case_law'].get('search_keywords', [])

        # Add node-type specific keywords
        node_keywords = NODE_KEYWORDS.get(node_type, [])
        all_keywords = set(kw.lower() for kw in search_keywords + node_keywords)

        # Get trigger name for matching
        trigger_name = node_data.get('trigger_name', '').lower()

        # Score ALL cases - don't filter, just rank
        scored = []
        for case in cases:
            title = case.get('title', '').lower()
            reason = case.get('child_welfare_reason', '').lower()

            # Start with base score from CW confidence
            score = case.get('child_welfare_confidence', 0.5)
            matched_keywords = []

            # Boost score for keyword matches
            for kw in all_keywords:
                if kw in title or kw in reason:
                    score += 1
                    matched_keywords.append(kw)

            # Also check trigger name words
            for word in trigger_name.split():
                if len(word) > 3 and word in title:
                    score += 0.5

            scored.append({
                "case_id": case.get('case_id', ''),
                "title": case.get('title', ''),
                "url": case.get('url', ''),
                "year": case.get('year'),
                "court": case.get('court_name', ''),
                "citation": case.get('citation_full', case.get('citation', '')),
                "relevance_score": score,
                "matched_keywords": matched_keywords[:5] if matched_keywords else ['child welfare'],
                "child_welfare_reason": case.get('child_welfare_reason', '')
            })

        # Sort by: keyword matches first, then by year (most recent first)
        scored.sort(key=lambda x: (-x['relevance_score'], -(x.get('year') or 0)))
        return scored[:10]  # Top 10 most relevant cases

    def match_statutes_to_node(self, urls: List[Dict], node_data: Dict) -> List[Dict]:
        """Match statute URLs to a node."""
        matched = []

        for url_data in urls:
            resource_type = url_data.get('resource_type', '')

            # Only include codes/statutes
            if resource_type not in ['code', 'statute', 'statutes']:
                continue

            # Check if child welfare related
            if not url_data.get('child_welfare_relevant', False):
                # Still include if it's in a CW title
                title = url_data.get('title', '').lower()
                if not any(kw in title for kw in ['child', 'juvenile', 'family', 'welfare', 'abuse', 'neglect']):
                    continue

            matched.append({
                "citation_text": url_data.get('title', url_data.get('url', '')),
                "source_url": url_data.get('url', ''),
                "authority_type": "state_statute",
                "last_verified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "deep_link": True,
                "title_code": url_data.get('title_code', ''),
                "chapter": url_data.get('chapter', '')
            })

        return matched[:20]  # Top 20 statutes

    def match_admin_rules_to_node(self, urls: List[Dict], node_data: Dict) -> List[Dict]:
        """Match admin rule URLs to a node."""
        matched = []

        for url_data in urls:
            resource_type = url_data.get('resource_type', '')

            # Only include admin rules
            if resource_type not in ['admin_rule', 'admin_rules', 'regulation', 'regulations']:
                continue

            matched.append({
                "title": url_data.get('title', ''),
                "url": url_data.get('url', ''),
                "authority_type": "administrative_rule",
                "last_verified": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            })

        return matched[:10]  # Top 10 admin rules

    def link_node(self, node_file: Path) -> Dict:
        """Link leaves to a single node file."""
        with open(node_file) as f:
            node_data = json.load(f)

        state_code = node_data.get('state', '')
        if not state_code or state_code == "United States":
            return node_data  # Skip federal baseline nodes

        # Load source data for this state
        cases = self.load_case_law(state_code)
        urls = self.load_labeled_urls(state_code)

        # Ensure layers structure exists
        if 'layers' not in node_data:
            node_data['layers'] = {}

        # Link case law
        if 'case_law' not in node_data['layers']:
            node_data['layers']['case_law'] = {
                "search_keywords": [],
                "key_cases": [],
                "jurisdiction": f"{state_code} state courts"
            }

        matched_cases = self.match_cases_to_node(cases, node_data)
        if matched_cases:
            node_data['layers']['case_law']['key_cases'] = matched_cases
            self.stats['cases_linked'] += len(matched_cases)

        # Link state statutory (only if empty or minimal)
        if 'state_statutory' not in node_data['layers']:
            node_data['layers']['state_statutory'] = {"primary_citations": []}

        existing_citations = len(node_data['layers']['state_statutory'].get('primary_citations', []))
        if existing_citations < 5:
            matched_statutes = self.match_statutes_to_node(urls, node_data)
            if matched_statutes:
                # Merge with existing, avoiding duplicates
                existing_urls = {c.get('source_url') for c in node_data['layers']['state_statutory'].get('primary_citations', [])}
                for statute in matched_statutes:
                    if statute['source_url'] not in existing_urls:
                        node_data['layers']['state_statutory']['primary_citations'].append(statute)
                        self.stats['statutes_linked'] += 1

        # Link admin rules (only if empty or minimal)
        if 'administrative_rule' not in node_data['layers']:
            node_data['layers']['administrative_rule'] = {"regulations_applicable": []}

        existing_rules = len(node_data['layers']['administrative_rule'].get('regulations_applicable', []))
        if existing_rules < 3:
            matched_rules = self.match_admin_rules_to_node(urls, node_data)
            if matched_rules:
                existing_urls = {r.get('url') for r in node_data['layers']['administrative_rule'].get('regulations_applicable', [])}
                for rule in matched_rules:
                    if rule['url'] not in existing_urls:
                        node_data['layers']['administrative_rule']['regulations_applicable'].append(rule)
                        self.stats['admin_rules_linked'] += 1

        # Update metadata
        if '_metadata' not in node_data:
            node_data['_metadata'] = {}
        node_data['_metadata']['leaves_linked'] = datetime.now(timezone.utc).isoformat()
        node_data['_metadata']['leaf_linker_version'] = "1.0.0"

        self.stats['nodes_processed'] += 1

        return node_data

    def link_state(self, state_code: str):
        """Link all leaves for a state."""
        state_dir = STATES_CHAINS_DIR / state_code
        if not state_dir.exists():
            print(f"State directory not found: {state_dir}")
            return

        print(f"\n{'='*60}")
        print(f"LINKING: {state_code}")
        print(f"{'='*60}")

        # Load source data
        cases = self.load_case_law(state_code)
        urls = self.load_labeled_urls(state_code)
        print(f"  Loaded {len(cases)} CW cases")
        print(f"  Loaded {len(urls)} labeled URLs")

        # Process each node file
        node_files = sorted(state_dir.glob("*.json"))
        for node_file in node_files:
            node_data = self.link_node(node_file)

            if not self.dry_run:
                with open(node_file, 'w') as f:
                    json.dump(node_data, f, indent=2)

            # Count linked items
            case_count = len(node_data.get('layers', {}).get('case_law', {}).get('key_cases', []))
            print(f"  {node_file.name}: {case_count} cases linked")

        print(f"  Total: {len(node_files)} nodes processed")

    def link_all_states(self):
        """Link leaves for all states."""
        for state_code in sorted(STATE_SLUGS.keys()):
            state_dir = STATES_CHAINS_DIR / state_code
            if state_dir.exists():
                self.link_state(state_code)

    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print("LEAF LINKING COMPLETE")
        print(f"{'='*60}")
        print(f"Nodes processed:     {self.stats['nodes_processed']}")
        print(f"Cases linked:        {self.stats['cases_linked']}")
        print(f"Statutes linked:     {self.stats['statutes_linked']}")
        print(f"Admin rules linked:  {self.stats['admin_rules_linked']}")
        if self.dry_run:
            print("\n[DRY RUN - No files were modified]")


def main():
    parser = argparse.ArgumentParser(description="Link source documents to chain nodes")
    parser.add_argument('--state', type=str, help="State code (e.g., AL)")
    parser.add_argument('--all', action='store_true', help="Process all states")
    parser.add_argument('--dry-run', action='store_true', help="Preview without writing")

    args = parser.parse_args()

    if not args.state and not args.all:
        parser.error("Must specify --state or --all")

    linker = LeafLinker(dry_run=args.dry_run)

    if args.all:
        linker.link_all_states()
    else:
        linker.link_state(args.state.upper())

    linker.print_summary()


if __name__ == "__main__":
    main()
