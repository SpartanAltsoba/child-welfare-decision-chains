# ARIA Dataset - ROOT TO FRUIT

The `dataset/` directory contains the curated legal knowledge base that ARIA reads from (not generates).

## Overview

**2,142 decision nodes** organized hierarchically:
- 42 node types × 51 jurisdictions (50 states + DC)
- Constitutional → Federal → State → Case Law → Outcomes

## Directory Structure

```
dataset/
├── child_welfare_data/           # Main dataset
│   ├── legal_planes/             # Legal hierarchy (vertical authority)
│   ├── chains/                   # Decision workflows (horizontal flow)
│   ├── states_chains/            # 51 state-specific branches
│   ├── schemas/                  # JSON validation schemas
│   ├── reference/                # Lookup data
│   └── DATASET_ARCHITECTURE.md   # Complete documentation
├── core/                         # Core decision data
├── persona/                      # System persona definitions
├── safety/                       # Safety guardrails
├── wellness/                     # Wellness check data
└── home/                         # Home automation data
```

## The Two Axes

### Vertical Axis: Legal Hierarchy (Authority)

```
CONSTITUTIONAL PLANE (Supreme)
        │
        ▼
FEDERAL PLANE (Floor - minimum requirements)
        │
        ▼
STATE PLANE (Can exceed, not go below)
        │
        ▼
CASE LAW PLANE (Judicial interpretation)
```

### Horizontal Axis: Decision Flow (Process)

```
INPUT → DECISION → ACTION → OUTCOME → OVERSIGHT
 INP-*    DEC-*     ACT-*     OUT-*     PMC-*
```

## Node Types (42 per jurisdiction)

| Type | Count | Description |
|------|-------|-------------|
| INP-* | 12 | Input/Intake nodes |
| DEC-* | 6 | Decision nodes |
| ACT-* | 6 | Action nodes |
| OUT-* | 6 | Outcome nodes |
| FAIL-* | 6 | Failure/Appeal nodes |
| PMC-* | 6 | Oversight nodes |

## Legal Planes

| File | Purpose |
|------|---------|
| `constitutional_plane.json` | U.S. Constitution constraints |
| `federal_plane.json` | Federal statutes (CAPTA, ASFA, etc.) |
| `state_constitutional/` | State constitutions |

## States Chains

Each state has 42 JSON files mapping federal requirements to state-specific law:

```
states_chains/TX/
├── TX_INP_01.json  # Intake procedures
├── TX_INP_02.json  # Who must report
├── TX_DEC_01.json  # Investigation decisions
└── ... (42 files)
```

## Constitutional Constraints

Key constitutional protections tracked:
- `CONST_4A_SEIZURE` - Child removal = seizure
- `CONST_4A_SEARCH` - Home visit = search
- `CONST_14A_PROCEDURAL_DP` - Notice + hearing required
- `CONST_14A_SUBSTANTIVE_DP` - Family integrity right
- `CONST_14A_EQUAL_PROTECTION` - No discrimination

## Usage by ARIA

ARIA is a **Smart Librarian** - it reads from this dataset, not generates:

```python
# Node loading
nodes = load_nodes(state="TX", query_type="mandatory_reporting")

# Response is formatted from dataset, not hallucinated
response = format_from_nodes(nodes)
```

## Data Sources

- Child Welfare Information Gateway
- State statutes (via PMC Spider)
- CourtListener (case law)
- CFSR/AFCARS (HHS data)
- OpenStates (legislation)
