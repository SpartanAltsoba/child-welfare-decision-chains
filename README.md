# US Child Welfare Decision Chain Dataset

**The first open-source, structured, AI-traversable legal knowledge graph of the entire US child protective services system.**

2,854 files | 2,142 decision nodes | 51 jurisdictions | Every step from report to outcome

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

---

## What Is This?

When Child Protective Services knocks on a family's door, what happens next is governed by a complex web of constitutional law, federal statutes, state law, administrative rules, and case law. No single resource maps this entire system in a structured, machine-readable format.

**Until now.**

This dataset maps every CPS decision point — from the initial report to the final outcome — across all 50 states and DC. Every node includes real statute citations, source URLs, constitutional constraints, and cross-references to related decision points.

It is organized along two axes:

### Vertical Axis: Legal Authority (Who Governs)

```
CONSTITUTIONAL PLANE ──── U.S. Constitution (4th, 14th Amendment)
        │                 Supreme: Cannot be violated by any lower authority
        │                 Remedy: 42 U.S.C. § 1983 civil rights lawsuit
        ▼
FEDERAL PLANE ─────────── CAPTA, ASFA, Title IV-E, ICWA, FFPSA
        │                 Floor: States can exceed but not go below
        │                 Consequence: Loss of federal funding
        ▼
STATE CONSTITUTIONAL ──── State constitutions (may exceed federal floor)
        │
        ▼
STATE STATUTORY ────────── State child welfare statutes
        │
        ▼
ADMINISTRATIVE RULES ──── State agency regulations and SOPs
        │
        ▼
CASE LAW ──────────────── Court decisions interpreting all of the above
```

### Horizontal Axis: Decision Flow (What Happens)

```
REPORT ─→ SCREEN ─→ INVESTIGATE ─→ ACT ─→ OUTCOME ─→ OVERSIGHT
                                     │
                                     ▼
                                  FAILURE ─→ § 1983 LAWSUIT
```

Each jurisdiction has **42 decision nodes**:

| Family | Nodes | Examples |
|--------|-------|---------|
| **INP** (Input) | 12 | Mandatory report, anonymous tip, LE referral, emergency custody |
| **DEC** (Decision) | 6 | Screen-in/out, investigation track, removal decision |
| **ACT** (Action) | 6 | Removal, in-home services, foster care, kinship placement |
| **OUT** (Outcome) | 6 | Reunification, TPR, adoption, guardianship, emancipation |
| **FAIL** (Failure) | 6 | Failure to investigate, unlawful removal, fatality after contact |
| **PMC** (Oversight) | 6 | CFSR monitoring, OIG audit, citizen review panels, FOIA |

**Total: 51 jurisdictions x 42 nodes = 2,142 decision nodes**

---

## Why Does This Matter?

- **For families:** Know your rights at every step of a CPS encounter. Know what the agency must do, what they can't do, and what happens when they violate the rules.
- **For attorneys:** Structured access to cross-state comparison of child welfare law. Instant identification of constitutional violations.
- **For researchers:** Machine-readable dataset for studying CPS outcomes, policy differences, and systemic failures across jurisdictions.
- **For journalists:** Trace the money. Every node tracks funding incentives (Title IV-E reimbursement, adoption incentives) and flags perverse incentives against family preservation.
- **For AI developers:** Build tools that help families navigate the system. The schema is designed for LLM traversal with LEAF tool call hooks for real-time data integration.
- **For legislators:** See exactly how your state compares to every other state and the federal floor. Identify compliance gaps.

---

## Dataset Structure

```
data/
├── schemas/                           # JSON Schema validation (the blueprint)
│   ├── extended_decision_chain.schema.json    # 1,020-line node schema
│   └── evaluation_capsule.schema.json         # Evaluation/scoring schema
│
├── legal_planes/                      # Vertical axis: legal authority hierarchy
│   ├── constitutional_plane.json      # U.S. Constitution constraints
│   ├── federal_plane.json             # Federal statutory floor (CAPTA, ASFA, etc.)
│   ├── administrative_structure.json  # State vs county administration (41/9/2 split)
│   ├── state_constitutional/          # State constitutions (TX, CA complete; 49 needed)
│   └── administrative_rules/          # State admin code (51 states complete)
│
├── chains/                            # Federal baselines (the trunk)
│   ├── cps/federal_baseline/          # 6 files: INP, DEC, ACT, OUT, FAIL, PMC nodes
│   └── missing_persons/               # Missing children chain + state clearinghouses
│
├── states_chains/                     # State-specific branches (the leaves)
│   ├── AK/ (43 files)                 # Alaska: 42 nodes + backfill
│   ├── AL/ (43 files)                 # Alabama
│   ├── ...                            # ... every state
│   └── WY/ (43 files)                 # Wyoming
│
├── ccdf_chains/                       # Child Care Development Fund data
│   ├── federal_ccdf.json              # Federal CCDF framework
│   ├── ALL_STATES_CCDF.json           # Aggregate
│   └── states/                        # 51 state-specific CCDF files
│
├── sources/                           # Provenance chain (where the data came from)
│   ├── case_law/                      # 153 files: CourtListener court decisions by state
│   ├── legal_framework/               # 102 files: Extracted legal frameworks (JSON + TXT)
│   ├── crawler_output/                # 53 files: Raw crawler output per state
│   ├── labeled_index/                 # 157 files: Labeled/categorized child welfare data
│   ├── state_sources.json             # Authoritative URL for every state
│   ├── state_constitution_links.txt   # Constitutional source URLs
│   └── mandatory-reporting-all-states.pdf  # Federal source document
│
├── reference/                         # Lookup tables
│   ├── us_states.json                 # State codes, names, coordinates, timezones
│   └── state_county_map.json          # County mapping by state
│
├── tools/                             # Dataset maintenance scripts
│   ├── case_law_crawler.py            # Crawl CourtListener for state case law
│   ├── legal_framework_crawler.py     # Crawl state legislature websites
│   ├── constitutional_enricher.py     # Enrich constitutional plane data
│   ├── leaf_linker.py                 # Link state chains to federal baselines
│   └── ... (13 Python tools total)
│
└── DATASET_ARCHITECTURE.md            # Complete technical documentation (520 lines)
```

---

## Node Schema

Every decision node follows a rigorous schema (`data/schemas/extended_decision_chain.schema.json`). Key fields:

```json
{
  "node_id": "TX_INP-01",
  "state": "TX",
  "node_family": "INP",
  "trigger_name": "Mandatory Report",
  "layers": {
    "constitutional": { "constraints_triggered": [...], "alignment": "aligned" },
    "federal": { "requirements_applicable": [...] },
    "state_constitutional": { "provisions_triggered": [...] },
    "state_statutory": { "primary_citations": [{ "citation_text": "...", "source_url": "..." }] },
    "administrative_rule": { "citations": [...] },
    "case_law": { "controlling_cases": [...] }
  },
  "burden_of_proof": { "standard": "reasonable_suspicion", "who_bears_burden": "agency" },
  "timeline_requirements": [{ "deadline": "72 hours", "consequence_of_miss": "..." }],
  "violation_consequences": [{ "remedies_available": ["section_1983", "motion_to_dismiss"] }],
  "funding_incentives": { "title_iv_e_applicable": true, "perverse_incentive_warning": "..." },
  "notice_requirements": [{ "who_must_be_notified": ["parent"], "timing": "..." }],
  "door_scenarios": [{ "legal_authority_to_enter": "none_without_consent", "parent_rights_at_moment": [...] }],
  "cross_references": { "triggered_by": [...], "leads_to": [...], "failure_modes": [...] }
}
```

The schema supports:
- **Burden of proof** tracking at every decision point
- **Door scenarios** — what happens when CPS shows up, what rights you have
- **Funding incentive** analysis — follow the money, flag perverse incentives
- **Violation consequences** — specific remedies (1983, habeas corpus, motion to dismiss)
- **Preemption analysis** — federal vs state conflict resolution
- **LEAF tool calls** — hooks for AI systems to query live databases at specific nodes
- **Cross-references** — how nodes connect (triggers, blocks, oversees, appeals)

---

## Quick Start

### Browse the Data

Pick a state and topic:

```bash
# Texas mandatory reporting law
cat data/states_chains/TX/TX_INP-01.json | python3 -m json.tool

# California emergency removal decision
cat data/states_chains/CA/CA_DEC-04.json | python3 -m json.tool

# Federal constitutional constraints
cat data/legal_planes/constitutional_plane.json | python3 -m json.tool

# Compare: How does Nevada differ from the federal floor?
diff <(cat data/chains/cps/federal_baseline/1_federal_inp_nodes.json | python3 -m json.tool) \
     <(cat data/states_chains/NV/NV_INP-01.json | python3 -m json.tool)
```

### Load in Python

```python
import json
from pathlib import Path

DATA = Path("data")

# Load a state node
with open(DATA / "states_chains/TX/TX_INP-01.json") as f:
    node = json.load(f)

print(f"Node: {node['node_id']}")
print(f"Topic: {node['trigger_name']}")
print(f"State law: {node['layers']['state_statutory']['primary_citations'][0]['citation_text']}")
print(f"Source: {node['layers']['state_statutory']['primary_citations'][0]['source_url']}")

# Load the constitutional plane
with open(DATA / "legal_planes/constitutional_plane.json") as f:
    constitution = json.load(f)

# Load all nodes for a state
state = "CA"
state_dir = DATA / "states_chains" / state
nodes = {}
for f in state_dir.glob("*.json"):
    if "backfill" not in f.name:
        with open(f) as fh:
            node = json.load(fh)
            nodes[node["node_id"]] = node

print(f"Loaded {len(nodes)} nodes for {state}")
```

### Validate Against Schema

```python
import json
import jsonschema

with open("data/schemas/extended_decision_chain.schema.json") as f:
    schema = json.load(f)

with open("data/states_chains/TX/TX_INP-01.json") as f:
    node = json.load(f)

jsonschema.validate(node, schema)  # Raises if invalid
print("Valid!")
```

---

## Known Gaps

| Gap | Status | How to Help |
|-----|--------|-------------|
| State constitutional planes | **49 of 51 missing** (only TX, CA done) | Pick a state, fill in the template |
| Some state nodes missing URLs | Partial | Add source URLs to existing citations |
| Case law needs expansion | Ongoing | Add relevant state supreme court decisions |
| Administrative rules incomplete | Some states thin | Add state admin code citations |

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to help fill these gaps.

---

## Data Sources

All data is sourced from public, authoritative sources:

- [Child Welfare Information Gateway](https://www.childwelfare.gov) (HHS)
- [Cornell Legal Information Institute](https://www.law.cornell.edu) (Federal statutes)
- [CourtListener](https://www.courtlistener.com) (Court opinions, via RECAP/Free Law Project)
- State legislature websites (Primary statutory text)
- [National Conference of State Legislatures](https://www.ncsl.org) (Policy comparisons)
- HHS AFCARS/CFSR data (Child welfare outcome statistics)

---

## Citation

If you use this dataset in research, please cite:

```bibtex
@dataset{pmc_cw_chains_2025,
  title     = {US Child Welfare Decision Chain Dataset},
  author    = {Project Milk Carton},
  year      = {2025},
  publisher = {GitHub},
  url       = {https://github.com/SpartanAltsoba/child-welfare-decision-chains},
  note      = {2,142 decision nodes across 51 US jurisdictions, CC BY-SA 4.0}
}
```

---

## License

This dataset is released under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).

You are free to use, share, and adapt this data for any purpose, including commercial use, as long as you:
1. Credit Project Milk Carton
2. Release any modifications under the same license

---

## About Project Milk Carton

[Project Milk Carton](https://projectmilkcarton.org) is a 501(c)(3) nonprofit (EIN: 33-1323547) dedicated to child welfare transparency and missing children awareness.

We believe that every family has the right to understand the legal system that can separate them. This dataset exists to make that system visible, auditable, and accountable.

**Website:** https://projectmilkcarton.org
**Donate:** https://www.paypal.com/donate/?hosted_button_id=YM2DVT2V6FDSE
**Telegram:** https://t.me/ProjectMilkCarton
**X/Twitter:** https://x.com/P_MilkCarton

---

*Shining light on the missing.*
