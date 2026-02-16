#!/usr/bin/env python3
"""
Case Law Crawler - Automated extraction of ALL case law with titles

Uses Playwright (headless browser) to bypass Cloudflare and extract:
- All case URLs from each year page
- Case titles from link text
- Score each for child welfare relevance

For each state:
    - Supreme Court (all years)
    - Court of Civil Appeals (all years)
    - Court of Criminal Appeals (all years)

Usage:
    python case_law_crawler.py --state alabama
    python case_law_crawler.py --all
    python case_law_crawler.py --state alabama --court supreme-court --year 2025
"""

import json
import re
import hashlib
import argparse
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://law.justia.com"
OUTPUT_DIR = Path("./data/sources/case_law")

# Years to crawl (adjust as needed)
YEAR_RANGE = range(2020, 2026)  # 2020-2025

# Courts to crawl per state
COURTS = [
    "supreme-court",
    "court-of-appeals-civil",      # Alabama, some states
    "court-of-appeals-criminal",   # Alabama, some states
    "court-of-civil-appeals",      # Other states
    "court-of-criminal-appeals",   # Other states
    "court-of-appeals",            # Generic appeals court
]

# State slugs
STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new-hampshire", "new-jersey",
    "new-mexico", "new-york", "north-carolina", "north-dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west-virginia", "wisconsin", "wyoming"
]

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
    "wisconsin": "WI", "wyoming": "WY"
}

# ============================================================================
# CHILD WELFARE SCORING
# ============================================================================

CW_KEYWORDS_HIGH = [
    (r'\bDHR\b', 'DHR'),
    (r'\bDepartment of Human Resources\b', 'DHR'),
    (r'\bDCFS\b', 'DCFS'),
    (r'\bDCS\b', 'DCS'),
    (r'\bDCF\b', 'DCF'),
    (r'\bDFPS\b', 'DFPS'),
    (r'\bCPS\b', 'CPS'),
    (r'\bChild Protective Services\b', 'CPS'),
    (r'\bJuvenile Court\b', 'Juvenile Court'),
    (r'\bJuvenile\s*:\s*JU-', 'Juvenile docket'),
    (r'\bJU-\d{2}-\d+', 'JU case number'),
    (r'\btermination of parental rights\b', 'TPR'),
    (r'\bTPR\b', 'TPR'),
    (r'\bdependency\b', 'dependency'),
    (r'\bfoster care\b', 'foster care'),
    (r'\bchild abuse\b', 'child abuse'),
    (r'\bchild neglect\b', 'child neglect'),
    (r'\bIn re[:\s]+[A-Z]\.[A-Z]\.', 'In re initials'),
    (r'\bEx parte [A-Z]\.[A-Z]\.', 'Ex parte initials'),
]

CW_KEYWORDS_MEDIUM = [
    (r'\bchild custody\b', 'child custody'),
    (r'\bminor child\b', 'minor child'),
    (r'\bparental rights\b', 'parental rights'),
    (r'\bguardianship\b', 'guardianship'),
    (r'\badoption\b', 'adoption'),
    (r'\breunification\b', 'reunification'),
    (r'\bpermanency\b', 'permanency'),
    (r'\bICWA\b', 'ICWA'),
    (r'\bchild welfare\b', 'child welfare'),
]

CW_PATTERNS_HIGH = [(re.compile(p, re.IGNORECASE), d) for p, d in CW_KEYWORDS_HIGH]
CW_PATTERNS_MEDIUM = [(re.compile(p, re.IGNORECASE), d) for p, d in CW_KEYWORDS_MEDIUM]


def score_title(title: str) -> Tuple[float, List[str], str]:
    """Score case title for child welfare relevance."""
    if not title:
        return 0.0, [], None

    keywords = []

    for pattern, desc in CW_PATTERNS_HIGH:
        if pattern.search(title):
            keywords.append(desc)

    if keywords:
        return 1.0, keywords, f"High: {', '.join(keywords[:3])}"

    for pattern, desc in CW_PATTERNS_MEDIUM:
        if pattern.search(title):
            keywords.append(desc)

    if keywords:
        return 0.7, keywords, f"Medium: {', '.join(keywords[:3])}"

    return 0.0, [], None


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
    child_welfare_relevant: bool
    child_welfare_confidence: float
    child_welfare_reason: Optional[str]
    child_welfare_keywords: List[str]
    serialization_priority: int
    metadata_source: str
    extracted_at: str


# ============================================================================
# CRAWLER
# ============================================================================

class CaseLawCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.stats = defaultdict(int)

    async def start(self):
        """Start the browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        print("Browser started")

    async def stop(self):
        """Stop the browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Browser stopped")

    async def extract_cases_from_page(self, url: str, state: str, court: str, year: int) -> List[CaseRecord]:
        """Extract all case links from a year page."""
        records = []
        page = await self.context.new_page()

        try:
            print(f"  Fetching: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait for content to load
            await page.wait_for_timeout(2000)

            # Check for Cloudflare challenge
            content = await page.content()
            if 'challenge-running' in content or 'cf-browser-verification' in content:
                print(f"    Cloudflare challenge detected, waiting...")
                await page.wait_for_timeout(10000)
                content = await page.content()

            # Check if we got blocked (403 page or empty)
            if 'Access denied' in content or 'Error 1015' in content:
                print(f"    BLOCKED: Rate limited, will retry later")
                self.stats['blocked'] += 1
                return []

            # Extract all links with text
            links = await page.evaluate('''() => {
                return [...document.querySelectorAll('a[href]')]
                    .map(a => ({
                        text: a.innerText.trim(),
                        url: a.href
                    }))
                    .filter(item => item.text.length > 0 && item.url.includes('.html'))
            }''')

            # Filter for case URLs
            case_pattern = re.compile(rf'/cases/{state}/{court}/\d{{4}}/[^/]+\.html$')

            for link in links:
                url = link['url']
                title = link['text']

                if not case_pattern.search(url):
                    continue

                # Extract case ID
                case_id = url.split('/')[-1].replace('.html', '')

                # Score for child welfare
                confidence, keywords, reason = score_title(title)

                # Priority
                if confidence >= 0.9:
                    priority = 1
                elif confidence >= 0.5:
                    priority = 2
                elif confidence > 0:
                    priority = 3
                else:
                    priority = 4

                # Court info
                court_name = court.replace('-', ' ').title()
                if 'supreme' in court:
                    level = 'supreme'
                elif 'appeal' in court:
                    level = 'appellate'
                else:
                    level = 'unknown'

                record = CaseRecord(
                    url=url,
                    url_hash=hashlib.sha256(url.encode()).hexdigest()[:16],
                    domain='law.justia.com',
                    state=state,
                    state_abbrev=STATE_ABBREVS.get(state, state.upper()[:2]),
                    resource_type='case_law',
                    resource_subtype=court.replace('-', '_'),
                    court_name=court_name,
                    court_level=level,
                    category='judicial',
                    year=year,
                    case_id=case_id,
                    citation=f"{STATE_ABBREVS.get(state, state.upper()[:2])} {court_name} {case_id}",
                    citation_full=f"{state.replace('-', ' ').title()} {court_name} Case {case_id} ({year})",
                    title=title,
                    child_welfare_relevant=confidence > 0,
                    child_welfare_confidence=confidence,
                    child_welfare_reason=reason,
                    child_welfare_keywords=keywords,
                    serialization_priority=priority,
                    metadata_source='playwright_crawl',
                    extracted_at=datetime.now(timezone.utc).isoformat(),
                )
                records.append(record)

            self.stats['pages_crawled'] += 1
            self.stats['cases_found'] += len(records)
            cw_count = sum(1 for r in records if r.child_welfare_relevant)
            self.stats['cw_cases'] += cw_count

            print(f"    Found {len(records)} cases, {cw_count} child welfare")

        except PlaywrightTimeout:
            print(f"    TIMEOUT: {url}")
            self.stats['timeouts'] += 1
        except Exception as e:
            print(f"    ERROR: {url} - {e}")
            self.stats['errors'] += 1
        finally:
            await page.close()

        return records

    async def crawl_state(self, state: str, courts: List[str] = None, years: range = None, restart_browser: bool = True) -> List[CaseRecord]:
        """Crawl all case law for a state."""
        courts = courts or COURTS
        years = years or YEAR_RANGE
        all_records = []
        request_count = 0

        print(f"\n{'='*60}")
        print(f"CRAWLING: {state.upper()}")
        print(f"{'='*60}")

        for court in courts:
            for year in years:
                url = f"{BASE_URL}/cases/{state}/{court}/{year}/"
                records = await self.extract_cases_from_page(url, state, court, year)
                all_records.extend(records)
                request_count += 1

                # Restart browser context after EVERY request to avoid Cloudflare fingerprinting
                if restart_browser:
                    print(f"    Restarting browser to avoid detection...")
                    await self.context.close()
                    await asyncio.sleep(2)
                    self.context = await self.browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        viewport={'width': 1920, 'height': 1080}
                    )

                # Rate limiting - longer delay to avoid Cloudflare
                import random
                delay = random.uniform(5, 10)
                print(f"    Waiting {delay:.1f}s...")
                await asyncio.sleep(delay)

        return all_records


def save_results(records: List[CaseRecord], state: str):
    """Save crawl results."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not records:
        print(f"No records to save for {state}")
        return

    # All cases
    all_file = OUTPUT_DIR / f"{state}_cases_crawled.jsonl"
    with open(all_file, 'w') as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + '\n')

    # Child welfare only
    cw_records = [r for r in records if r.child_welfare_relevant]
    cw_file = OUTPUT_DIR / f"{state}_cases_cw_crawled.jsonl"
    with open(cw_file, 'w') as f:
        for r in cw_records:
            f.write(json.dumps(asdict(r)) + '\n')

    # Summary
    summary = {
        'state': state,
        'total_cases': len(records),
        'child_welfare_cases': len(cw_records),
        'by_court': defaultdict(int),
        'by_year': defaultdict(int),
        'by_priority': defaultdict(int),
        'crawled_at': datetime.now(timezone.utc).isoformat(),
    }

    for r in records:
        summary['by_court'][r.court_name] += 1
        summary['by_year'][str(r.year)] += 1
        summary['by_priority'][str(r.serialization_priority)] += 1

    summary['by_court'] = dict(summary['by_court'])
    summary['by_year'] = dict(summary['by_year'])
    summary['by_priority'] = dict(summary['by_priority'])

    summary_file = OUTPUT_DIR / f"{state}_cases_crawled_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved {len(records)} cases to {all_file}")
    print(f"Saved {len(cw_records)} CW cases to {cw_file}")


async def main():
    parser = argparse.ArgumentParser(description='Crawl case law from Justia')
    parser.add_argument('--state', '-s', help='State to crawl (e.g., alabama)')
    parser.add_argument('--all', action='store_true', help='Crawl all states')
    parser.add_argument('--court', '-c', help='Specific court (e.g., supreme-court)')
    parser.add_argument('--year', '-y', type=int, help='Specific year')
    parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
    parser.add_argument('--visible', action='store_true', help='Show browser window')

    args = parser.parse_args()

    if args.visible:
        args.headless = False

    crawler = CaseLawCrawler(headless=args.headless)

    try:
        await crawler.start()

        if args.all:
            states = STATES
        elif args.state:
            states = [args.state]
        else:
            print("ERROR: Specify --state STATE or --all")
            return

        courts = [args.court] if args.court else None
        years = range(args.year, args.year + 1) if args.year else None

        for state in states:
            records = await crawler.crawl_state(state, courts, years)
            save_results(records, state)

        print(f"\n{'='*60}")
        print("CRAWL COMPLETE")
        print(f"{'='*60}")
        print(f"Pages crawled: {crawler.stats['pages_crawled']}")
        print(f"Cases found: {crawler.stats['cases_found']}")
        print(f"Child welfare cases: {crawler.stats['cw_cases']}")
        print(f"Timeouts: {crawler.stats['timeouts']}")
        print(f"Errors: {crawler.stats['errors']}")

    finally:
        await crawler.stop()


if __name__ == '__main__':
    asyncio.run(main())
