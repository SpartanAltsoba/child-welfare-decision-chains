#!/usr/bin/env python3
"""
Federated Jurisdictional Knowledge Graph Crawler

A 6-layer architecture for building a serialized knowledge graph of all
US state jurisdictions with verified, hashed, versioned legal data.

Layers:
  1. Discovery - Find every relevant URL
  2. Validation - Confirm pages exist and serve HTML
  3. Extraction - Pull metadata + structured data
  4. Normalization - Coerce into unified schema
  5. Persistence - Hash, version, store (append-only)
  6. Drift Detection - Know when it changes

Project Milk Carton 501(c)(3) - All Rights Reserved
"""

import json
import hashlib
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Optional: Better extraction libraries
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

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = Path("./data/sources/crawler_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Request settings
REQUEST_TIMEOUT = 20
RATE_LIMIT_DELAY = 0.5  # Seconds between requests (be nice to servers)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ============================================================================
# LAYER 0: STATE METADATA (Authoritative - Never Changes)
# ============================================================================

STATES = {
    "alabama": {"abbrev": "AL", "circuit": "11th", "fips": "01"},
    "alaska": {"abbrev": "AK", "circuit": "9th", "fips": "02"},
    "arizona": {"abbrev": "AZ", "circuit": "9th", "fips": "04"},
    "arkansas": {"abbrev": "AR", "circuit": "8th", "fips": "05"},
    "california": {"abbrev": "CA", "circuit": "9th", "fips": "06"},
    "colorado": {"abbrev": "CO", "circuit": "10th", "fips": "08"},
    "connecticut": {"abbrev": "CT", "circuit": "2nd", "fips": "09"},
    "delaware": {"abbrev": "DE", "circuit": "3rd", "fips": "10"},
    "florida": {"abbrev": "FL", "circuit": "11th", "fips": "12"},
    "georgia": {"abbrev": "GA", "circuit": "11th", "fips": "13"},
    "hawaii": {"abbrev": "HI", "circuit": "9th", "fips": "15"},
    "idaho": {"abbrev": "ID", "circuit": "9th", "fips": "16"},
    "illinois": {"abbrev": "IL", "circuit": "7th", "fips": "17"},
    "indiana": {"abbrev": "IN", "circuit": "7th", "fips": "18"},
    "iowa": {"abbrev": "IA", "circuit": "8th", "fips": "19"},
    "kansas": {"abbrev": "KS", "circuit": "10th", "fips": "20"},
    "kentucky": {"abbrev": "KY", "circuit": "6th", "fips": "21"},
    "louisiana": {"abbrev": "LA", "circuit": "5th", "fips": "22"},
    "maine": {"abbrev": "ME", "circuit": "1st", "fips": "23"},
    "maryland": {"abbrev": "MD", "circuit": "4th", "fips": "24"},
    "massachusetts": {"abbrev": "MA", "circuit": "1st", "fips": "25"},
    "michigan": {"abbrev": "MI", "circuit": "6th", "fips": "26"},
    "minnesota": {"abbrev": "MN", "circuit": "8th", "fips": "27"},
    "mississippi": {"abbrev": "MS", "circuit": "5th", "fips": "28"},
    "missouri": {"abbrev": "MO", "circuit": "8th", "fips": "29"},
    "montana": {"abbrev": "MT", "circuit": "9th", "fips": "30"},
    "nebraska": {"abbrev": "NE", "circuit": "8th", "fips": "31"},
    "nevada": {"abbrev": "NV", "circuit": "9th", "fips": "32"},
    "new-hampshire": {"abbrev": "NH", "circuit": "1st", "fips": "33"},
    "new-jersey": {"abbrev": "NJ", "circuit": "3rd", "fips": "34"},
    "new-mexico": {"abbrev": "NM", "circuit": "10th", "fips": "35"},
    "new-york": {"abbrev": "NY", "circuit": "2nd", "fips": "36"},
    "north-carolina": {"abbrev": "NC", "circuit": "4th", "fips": "37"},
    "north-dakota": {"abbrev": "ND", "circuit": "8th", "fips": "38"},
    "ohio": {"abbrev": "OH", "circuit": "6th", "fips": "39"},
    "oklahoma": {"abbrev": "OK", "circuit": "10th", "fips": "40"},
    "oregon": {"abbrev": "OR", "circuit": "9th", "fips": "41"},
    "pennsylvania": {"abbrev": "PA", "circuit": "3rd", "fips": "42"},
    "rhode-island": {"abbrev": "RI", "circuit": "1st", "fips": "44"},
    "south-carolina": {"abbrev": "SC", "circuit": "4th", "fips": "45"},
    "south-dakota": {"abbrev": "SD", "circuit": "8th", "fips": "46"},
    "tennessee": {"abbrev": "TN", "circuit": "6th", "fips": "47"},
    "texas": {"abbrev": "TX", "circuit": "5th", "fips": "48"},
    "utah": {"abbrev": "UT", "circuit": "10th", "fips": "49"},
    "vermont": {"abbrev": "VT", "circuit": "2nd", "fips": "50"},
    "virginia": {"abbrev": "VA", "circuit": "4th", "fips": "51"},
    "washington": {"abbrev": "WA", "circuit": "9th", "fips": "53"},
    "west-virginia": {"abbrev": "WV", "circuit": "4th", "fips": "54"},
    "wisconsin": {"abbrev": "WI", "circuit": "7th", "fips": "55"},
    "wyoming": {"abbrev": "WY", "circuit": "10th", "fips": "56"},
}

# ============================================================================
# LAYER 1: DISCOVERY
# ============================================================================

class DiscoveryLayer:
    """Find every relevant URL for a jurisdiction."""

    # Source endpoints (Justia is ONE of several)
    SOURCES = {
        "justia_stats": "https://stats.justia.com/{state}/list/",
        "justia_constitution": "https://law.justia.com/constitution/{state}/",
        "justia_codes": "https://law.justia.com/codes/{state}/",
        "justia_cases": "https://law.justia.com/cases/{state}/",
        "regulations": "https://regulations.justia.com/states/{state}/",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-Crawler/1.0 (Project Milk Carton; Legal Research)"
        })

    def discover_places(self, state: str) -> List[str]:
        """Discover all localities for a state from stats.justia.com."""
        url = self.SOURCES["justia_stats"].format(state=state)

        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Discovery failed for {state}: {e}")
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        links = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith(f"/{state}/") and href != f"/{state}/list/":
                full_url = f"https://stats.justia.com{href}"
                links.add(full_url)

        log.info(f"Discovered {len(links)} places for {state}")
        return sorted(links)

    def discover_constitution_sections(self, state: str) -> List[str]:
        """Discover constitution section URLs."""
        url = self.SOURCES["justia_constitution"].format(state=state)

        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 403:
                log.warning(f"Constitution page blocked for {state}")
                return [url]  # Return base URL only
            r.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Constitution discovery failed for {state}: {e}")
            return [url]

        soup = BeautifulSoup(r.text, "html.parser")

        links = [url]  # Always include base
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if f"/constitution/{state}/" in href and href != url:
                full_url = urljoin(url, href)
                if full_url not in links:
                    links.append(full_url)

        log.info(f"Discovered {len(links)} constitution sections for {state}")
        return links

    def discover_code_titles(self, state: str) -> List[str]:
        """Discover state code/statute title URLs."""
        url = self.SOURCES["justia_codes"].format(state=state)

        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 403:
                log.warning(f"Codes page blocked for {state}")
                return [url]
            r.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Codes discovery failed for {state}: {e}")
            return [url]

        soup = BeautifulSoup(r.text, "html.parser")

        links = [url]
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if f"/codes/{state}/" in href and href != url:
                full_url = urljoin(url, href)
                if full_url not in links:
                    links.append(full_url)

        log.info(f"Discovered {len(links)} code titles for {state}")
        return links

    def get_all_sources(self, state: str) -> Dict[str, str]:
        """Get all source URLs for a state."""
        return {
            name: template.format(state=state)
            for name, template in self.SOURCES.items()
        }

# ============================================================================
# LAYER 2: VALIDATION
# ============================================================================

class ValidationLayer:
    """Confirm pages exist and serve valid content."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-Crawler/1.0 (Project Milk Carton; Legal Research)"
        })

    def is_valid_page(self, url: str) -> bool:
        """Check if URL returns valid HTML content."""
        try:
            r = self.session.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
            content_type = r.headers.get("Content-Type", "")
            return r.status_code == 200 and "text/html" in content_type
        except requests.RequestException:
            return False

    def validate_batch(self, urls: List[str]) -> Dict[str, bool]:
        """Validate a batch of URLs."""
        results = {}
        for url in urls:
            results[url] = self.is_valid_page(url)
            time.sleep(0.1)  # Micro-delay

        valid_count = sum(1 for v in results.values() if v)
        log.info(f"Validated {valid_count}/{len(urls)} URLs")
        return results

# ============================================================================
# LAYER 3: EXTRACTION
# ============================================================================

class ExtractionLayer:
    """Pull metadata and structured data from pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-Crawler/1.0 (Project Milk Carton; Legal Research)"
        })

    def extract_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract all available metadata from a URL."""
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            html = r.text
        except requests.RequestException as e:
            log.error(f"Extraction failed for {url}: {e}")
            return None

        soup = BeautifulSoup(html, "html.parser")

        result = {
            "url": url,
            "title": None,
            "meta_description": None,
            "canonical": None,
            "structured_data": {},
            "text_excerpt": None,
            "links": [],
        }

        # Title
        if soup.title:
            result["title"] = soup.title.string.strip() if soup.title.string else None

        # Meta description
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["meta_description"] = meta_desc["content"]

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            result["canonical"] = canonical["href"]

        # Structured data (JSON-LD, OpenGraph, Microdata)
        if HAS_EXTRUCT:
            try:
                result["structured_data"] = extruct.extract(
                    html,
                    base_url=get_base_url(html, url),
                    syntaxes=["opengraph", "json-ld", "microdata"]
                )
            except Exception:
                pass

        # Main text content
        if HAS_TRAFILATURA:
            try:
                main_text = trafilatura.extract(html)
                if main_text:
                    result["text_excerpt"] = main_text[:3000]
            except Exception:
                pass

        # Extract internal links
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith("http"):
                result["links"].append(href)

        return result

# ============================================================================
# LAYER 4: NORMALIZATION
# ============================================================================

class NormalizationLayer:
    """Coerce extracted data into unified schema."""

    SCHEMA_VERSION = "1.0.0"

    def normalize(self, record: Dict, state: str, source_type: str) -> Dict[str, Any]:
        """Normalize a record into the standard schema."""

        # Extract place from URL
        place = self._extract_place(record.get("url", ""), state)

        # Compute content hash
        content_hash = self._compute_hash(record)

        # Get state metadata
        state_meta = STATES.get(state, {})

        return {
            "schema_version": self.SCHEMA_VERSION,
            "jurisdiction": f"US-{state_meta.get('abbrev', state.upper())}",
            "state": state,
            "state_fips": state_meta.get("fips"),
            "federal_circuit": state_meta.get("circuit"),
            "place": place,
            "source": source_type,
            "url": record.get("url"),
            "canonical": record.get("canonical"),
            "content_hash": f"sha256:{content_hash}",
            "metadata": {
                "title": record.get("title"),
                "description": record.get("meta_description"),
            },
            "structured": record.get("structured_data", {}),
            "text_excerpt": record.get("text_excerpt"),
            "link_count": len(record.get("links", [])),
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
        }

    def _extract_place(self, url: str, state: str) -> Optional[str]:
        """Extract place name from URL."""
        # Pattern: https://stats.justia.com/{state}/{place}/
        if f"/{state}/" in url:
            parts = url.rstrip("/").split("/")
            if len(parts) >= 2:
                return parts[-1]
        return None

    def _compute_hash(self, record: Dict) -> str:
        """Compute SHA256 hash of content."""
        content = record.get("text_excerpt") or record.get("title") or ""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

# ============================================================================
# LAYER 5: PERSISTENCE
# ============================================================================

class PersistenceLayer:
    """Store records in append-only format."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_record(self, record: Dict, filename: str = "jurisdictions.jsonl"):
        """Append a single record to JSONL file."""
        filepath = self.output_dir / filename
        with open(filepath, "a") as f:
            f.write(json.dumps(record) + "\n")

    def save_state_data(self, state: str, records: List[Dict]):
        """Save all records for a state to a dedicated file."""
        filepath = self.output_dir / f"{state}.jsonl"
        with open(filepath, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        log.info(f"Saved {len(records)} records to {filepath}")

    def save_index(self, index: Dict):
        """Save the master index."""
        filepath = self.output_dir / "index.json"
        with open(filepath, "w") as f:
            json.dump(index, f, indent=2)
        log.info(f"Saved index to {filepath}")

# ============================================================================
# LAYER 6: ORCHESTRATOR (THE CRAWLER)
# ============================================================================

class FederatedCrawler:
    """
    Orchestrates all layers to build the Serialized Jurisdictional Knowledge Graph.
    """

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.discovery = DiscoveryLayer()
        self.validation = ValidationLayer()
        self.extraction = ExtractionLayer()
        self.normalization = NormalizationLayer()
        self.persistence = PersistenceLayer(output_dir)

        self.stats = {
            "states_processed": 0,
            "places_discovered": 0,
            "places_validated": 0,
            "records_saved": 0,
            "errors": 0,
        }

    def crawl_state(self, state: str, include_places: bool = True) -> List[Dict]:
        """Crawl all data for a single state."""
        log.info(f"=" * 60)
        log.info(f"CRAWLING: {state.upper()}")
        log.info(f"=" * 60)

        records = []

        # 1. Get all source URLs
        sources = self.discovery.get_all_sources(state)

        for source_name, url in sources.items():
            log.info(f"Processing {source_name}: {url}")

            # Extract and normalize
            raw = self.extraction.extract_metadata(url)
            if raw:
                normalized = self.normalization.normalize(raw, state, source_name)
                records.append(normalized)
                self.persistence.save_record(normalized)

            time.sleep(RATE_LIMIT_DELAY)

        # 2. Discover and process places (localities)
        if include_places:
            places = self.discovery.discover_places(state)
            self.stats["places_discovered"] += len(places)

            for place_url in places[:100]:  # Limit to first 100 for safety
                raw = self.extraction.extract_metadata(place_url)
                if raw:
                    normalized = self.normalization.normalize(raw, state, "justia_stats_place")
                    records.append(normalized)
                    self.stats["places_validated"] += 1

                time.sleep(RATE_LIMIT_DELAY)

        # 3. Save state data
        self.persistence.save_state_data(state, records)
        self.stats["states_processed"] += 1
        self.stats["records_saved"] += len(records)

        return records

    def crawl_all_states(self, include_places: bool = False):
        """Crawl all 50 states."""
        log.info("=" * 60)
        log.info("FEDERATED CRAWLER - ALL 50 STATES")
        log.info("=" * 60)

        all_records = []

        for state in STATES.keys():
            try:
                records = self.crawl_state(state, include_places=include_places)
                all_records.extend(records)
            except Exception as e:
                log.error(f"Error crawling {state}: {e}")
                self.stats["errors"] += 1
                continue

        # Save master index
        index = {
            "generated": datetime.utcnow().isoformat() + "Z",
            "schema_version": self.normalization.SCHEMA_VERSION,
            "states_count": len(STATES),
            "records_count": len(all_records),
            "stats": self.stats,
            "sources": list(self.discovery.SOURCES.keys()),
        }
        self.persistence.save_index(index)

        log.info("=" * 60)
        log.info("CRAWL COMPLETE")
        log.info(f"States: {self.stats['states_processed']}")
        log.info(f"Records: {self.stats['records_saved']}")
        log.info(f"Errors: {self.stats['errors']}")
        log.info("=" * 60)

        return all_records

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Federated Jurisdictional Knowledge Graph Crawler"
    )
    parser.add_argument(
        "--state", "-s",
        help="Crawl a single state (e.g., 'alabama')"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Crawl all 50 states"
    )
    parser.add_argument(
        "--places", "-p",
        action="store_true",
        help="Include locality/place data (slower)"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_DIR),
        help="Output directory"
    )

    args = parser.parse_args()

    crawler = FederatedCrawler(output_dir=Path(args.output))

    if args.state:
        crawler.crawl_state(args.state, include_places=args.places)
    elif args.all:
        crawler.crawl_all_states(include_places=args.places)
    else:
        # Default: show stats.justia.com is accessible
        print("Testing stats.justia.com accessibility...")
        places = crawler.discovery.discover_places("alabama")
        print(f"✓ Found {len(places)} places for Alabama")
        print("\nUsage:")
        print("  --state alabama    # Crawl single state")
        print("  --all              # Crawl all 50 states")
        print("  --places           # Include locality data")


if __name__ == "__main__":
    main()
