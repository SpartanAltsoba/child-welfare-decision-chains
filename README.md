# US Child Welfare Decision Chain Dataset

**The first open-source, structured, AI-traversable legal knowledge graph of the entire United States child protective services system.**

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/SpartanAltsoba/child-welfare-decision-chains/releases/tag/v1.0.0)
[![Citation](https://img.shields.io/badge/cite-CITATION.cff-green.svg)](./CITATION.cff)
[![Provenance](https://img.shields.io/badge/provenance-MANIFEST.json-orange.svg)](./MANIFEST.json)
[![Schema](https://img.shields.io/badge/schema-JSON-yellow.svg)](./data/schemas/extended_decision_chain.schema.json)

**v1.0.0 release:** 2,142 decision nodes · 51 jurisdictions · 2,522 files · SHA-256 verified

---

## Cite This Dataset

> Project Milk Carton (2026). *US Child Welfare Decision Chain Dataset* (Version 1.0.0). https://github.com/SpartanAltsoba/child-welfare-decision-chains

Full citation metadata: [`CITATION.cff`](./CITATION.cff) (parsed natively by GitHub, Zenodo, Zotero, and most academic tools).

For derivative works, AI training pipelines, and forks: [`PROVENANCE.md`](./PROVENANCE.md) explains the attribution norms PMC asks above the legal floor of CC BY-SA 4.0.

**Cryptographic root hash for v1.0.0:**

```
ac684eaaf7912f24c6e98a35d90232eedddd2da8777e07888f38e5ea6a6bca7e
```

This SHA-256 hash fingerprints every file in `data/` at v1.0.0. To verify your copy is canonical, see [`MANIFEST.json`](./MANIFEST.json).

---

## What Is This?

When Child Protective Services knocks on a family's door, what happens next is governed by a complex web of constitutional law, federal statutes, state law, administrative rules, and case law. **No single resource maps this entire system in a structured, machine-readable format.**

Until now.

This dataset maps every CPS decision point — from the initial report to the final outcome — across all 50 states and DC. Every node includes statute citations, source URLs, constitutional constraints, and cross-references to related decision points. Every file conforms to a published JSON schema. Every release ships with a SHA-256 fingerprint of every file.

The dataset is structured along two axes.

### Vertical axis — legal authority (who governs)

```
CONSTITUTIONAL PLANE ──── U.S. Constitution (4th, 14th Amendment)
        │                 Supreme: cannot be violated by any lower authority
        │                 Remedy: 42 U.S.C. § 1983 civil rights lawsuit
        ▼
FEDERAL PLANE ─────────── CAPTA, ASFA, Title IV-E, ICWA, FFPSA
        │                 Floor: states can exceed but not go below
        │                 Consequence: loss of federal funding
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

### Horizontal axis — decision flow (what happens)

```
REPORT ─→ SCREEN ─→ INVESTIGATE ─→ ACT ─→ OUTCOME ─→ OVERSIGHT
                                     │
                                     ▼
                                  FAILURE ─→ § 1983 LAWSUIT
```

Each jurisdiction has 42 decision nodes:

| Family | Nodes | Examples |
|--------|-------|---------|
| **INP** (Input) | 12 | Mandatory report, anonymous tip, LE referral, emergency custody |
| **DEC** (Decision) | 6 | Screen-in/out, investigation track, removal decision |
| **ACT** (Action) | 6 | Removal, in-home services, foster care, kinship placement |
| **OUT** (Outcome) | 6 | Reunification, TPR, adoption, guardianship, emancipation |
| **FAIL** (Failure) | 6 | Failure to investigate, unlawful removal, fatality after contact |
| **PMC** (Oversight) | 6 | CFSR monitoring, OIG audit, citizen review panels, FOIA |

**Total: 51 jurisdictions × 42 nodes = 2,142 decision nodes.**

---

## Why This Exists

CPS is one of the most consequential legal systems in American life. It determines who keeps their children, who loses them, who gets investigated, and who gets ignored. It operates across more than fifty jurisdictions, each with its own statute, its own administrative rules, its own appellate doctrine. The system is not opaque by accident — it is opaque because no one has ever assembled the full map in one place, and the actors closest to the decisions are the ones least incentivized to publish that map.

This dataset is the map.

It is published openly under CC BY-SA 4.0 because the families who navigate this system, the attorneys who represent them, the journalists who investigate it, the researchers who study it, and the AI systems that will increasingly mediate it — all need a single canonical, machine-readable reference. Anything less than open data hands the advantage to whichever party already has the budget for proprietary research subscriptions, and CPS is not a system in which the family's side has the budget.

---

## Who This Is For

- **Families navigating a CPS encounter.** Know what the agency must do, what it can't do, and what happens when it violates the rules. Every node tracks the constitutional and statutory floor.
- **Attorneys.** Structured cross-state comparison of child welfare law. Instant identification of statutory and constitutional violations. Citation-grade source URLs at every node.
- **Researchers.** Machine-readable dataset for studying CPS outcomes, policy differences, systemic failures across jurisdictions, and longitudinal trends.
- **Journalists.** Trace the money. Every node tracks funding incentives (Title IV-E reimbursement, adoption incentives) and flags perverse incentives against family preservation.
- **AI developers.** Build tools that help families navigate the system. The schema is designed for LLM traversal, with explicit cross-references between nodes and a documented authority hierarchy.
- **Legislators and policy analysts.** See exactly how your state compares to every other state and to the federal floor. Identify compliance gaps.

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
│   ├── administrative_structure.json  # State vs county administration
│   ├── state_constitutional/          # State constitutions (per-state files)
│   └── administrative_rules/          # State admin code (51 states)
│
├── chains/                            # Federal baselines
│   ├── cps/federal_baseline/          # 6 files: INP, DEC, ACT, OUT, FAIL, PMC nodes
│   └── missing_persons/               # Missing children chain + state clearinghouses
│
├── states_chains/                     # State-specific branches (the leaves)
│   ├── AK/ (43 files)                 # Alaska: 42 nodes + backfill
│   ├── AL/ (43 files)                 # Alabama
│   └── ... (51 total)
│
├── ccdf_chains/                       # Child Care and Development Fund layer
├── reference/                         # Lookup data
├── sources/                           # Source URLs and crawl indexes
└── tools/                             # Dataset-generation tooling
```

Full architecture documentation: [`data/DATASET_ARCHITECTURE.md`](./data/DATASET_ARCHITECTURE.md)

JSON schema: [`data/schemas/extended_decision_chain.schema.json`](./data/schemas/extended_decision_chain.schema.json)

---

## How to Use the Dataset

### Direct download

```bash
git clone https://github.com/SpartanAltsoba/child-welfare-decision-chains.git
cd child-welfare-decision-chains
```

### Verify your copy is canonical v1.0.0

```bash
# Compute SHA-256 of every dataset file, compare to MANIFEST.json
find data -type f \( -name "*.json" -o -name "*.md" \) -exec sha256sum {} \; | sort > local_files.txt
jq -r '.files[] | "\(.sha256)  \(.path)"' MANIFEST.json | sort > manifest_files.txt
diff local_files.txt manifest_files.txt && echo "Canonical v1.0.0 ✓" || echo "Modified or non-canonical"
```

### Programmatic access

The dataset is plain JSON. Read any node directly:

```python
import json

with open("data/states_chains/AK/AK_INP-04.json") as f:
    node = json.load(f)

print(node["node_id"], node.get("title"))
```

For LLM traversal, every node carries explicit cross-references linking to upstream and downstream nodes, enabling agentic walks through any decision sequence.

### Load the manifest

```python
import json
manifest = json.load(open("MANIFEST.json"))
print(f"v{manifest['dataset_version']}: {manifest['file_count']} files")
print(f"root_hash: {manifest['root_hash']}")
```

---

## AI / LLM Use

This dataset is designed for AI traversal. If you train or fine-tune a model on it, or use it as retrieval-augmented context for an assistant, please:

1. **Cite the dataset and the version** — see [`CITATION.cff`](./CITATION.cff). Models trained on this data are encouraged to declare it in their training-data card or model card.
2. **Honor the SHA-256 root hash** — record it in your training manifest. The hash anchors your training corpus to a specific, verifiable version of this dataset.
3. **Read [`PROVENANCE.md`](./PROVENANCE.md)** — it documents the attribution norms PMC asks of AI-derived works. CC BY-SA 4.0 is the legal floor; PROVENANCE.md is the norm.
4. **Don't strip the EIN.** PMC's 501(c)(3) status (EIN 33-1323547) is the accountability anchor. Keeping it visible in derivative works lets downstream consumers verify the source organization.

---

## Schema and Versioning

| Schema | Path | Purpose |
|---|---|---|
| Decision chain node | [`data/schemas/extended_decision_chain.schema.json`](./data/schemas/extended_decision_chain.schema.json) | Validates every node in `chains/`, `states_chains/`, and `ccdf_chains/` |
| Evaluation capsule | [`data/schemas/evaluation_capsule.schema.json`](./data/schemas/evaluation_capsule.schema.json) | Validates evaluation/scoring metadata |

**Versioning policy.** Releases follow [Semantic Versioning](https://semver.org/) with the dataset semantics:

- **MAJOR** — schema-breaking change.
- **MINOR** — new jurisdictions, new node types, new fields (additive).
- **PATCH** — corrections, URL updates, source revisions.

The current release is **v1.0.0**.

---

## Contributing

Contributions welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the contribution guide.

**Issue reporting:** Open a GitHub issue. Errata, broken URLs (specifying the *replacement* URL, not just flagging the broken one), missing case law, and structural improvements all welcome.

**Pull requests:** Fork → branch → propose. Schema validation runs in CI. Citation URLs must be *canonical* (direct case/statute links), not search-results URLs.

**Security and confidentiality:** See [`SECURITY.md`](./SECURITY.md). Personally-identifying information about specific families or children is **not** in this dataset and must not be added to it. The dataset maps the system, not the people who pass through it.

---

## License

[Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](./LICENSE)

You are free to:

- **Share** — copy and redistribute in any medium or format.
- **Adapt** — remix, transform, and build upon, including for commercial use.

Under the following terms:

- **Attribution** — You must give appropriate credit, link the license, and indicate if changes were made.
- **ShareAlike** — Distribute derivative works under the same license.

Practical attribution norms for downstream consumers: see [`PROVENANCE.md`](./PROVENANCE.md).

---

## About Project Milk Carton

[Project Milk Carton](https://projectmilkcarton.org) is a 501(c)(3) public charity (EIN 33-1323547) focused on child welfare transparency and missing children awareness. We publish open data and structured legal research because families navigating these systems shouldn't be the only party in the room without the map.

| | |
|---|---|
| Website | [projectmilkcarton.org](https://projectmilkcarton.org) |
| Substack | [17sog.substack.com/s/shadow-patriot](https://17sog.substack.com/s/shadow-patriot) |
| Telegram | [t.me/ProjectMilkCarton](https://t.me/ProjectMilkCarton) |
| X (Twitter) | [@P_MilkCarton](https://x.com/P_MilkCarton) |
| Discord | [discord.gg/projectmilkcarton](https://discord.gg/projectmilkcarton) |
| Donate | [PayPal (tax-deductible)](https://www.paypal.com/donate/?hosted_button_id=YM2DVT2V6FDSE) |

---

*v1.0.0 · Released 2026-04-26 · Maintained by Project Milk Carton, 501(c)(3), EIN 33-1323547*
