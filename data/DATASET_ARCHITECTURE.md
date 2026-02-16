# ARIA Child Welfare Dataset Architecture

## Complete Directory Structure and Relationships

**Last Updated:** 2025-12-22
**Author:** PMC Spider Documentation
**Purpose:** Training PMC Spider to understand and populate this dataset correctly

---

## Directory Tree

```
./data/
│
├── schemas/                              # VALIDATION RULES
│   ├── extended_decision_chain.schema.json
│   └── evaluation_capsule.schema.json
│
├── legal_planes/                         # LEGAL HIERARCHY (vertical authority)
│   ├── constitutional_plane.json         # U.S. Constitution (SUPREME)
│   ├── federal_plane.json                # Federal statutes (FLOOR)
│   ├── administrative_structure.json     # State vs County admin
│   └── state_constitutional/             # State constitutions (49 MISSING!)
│       ├── _TEMPLATE.json
│       ├── CA_constitution.json
│       └── TX_constitution.json
│
├── chains/                               # DECISION WORKFLOWS (horizontal flow)
│   ├── cps/federal_baseline/             # CPS Federal TRUNK
│   │   ├── 1_federal_inp_nodes.json      # 12 INPUT nodes
│   │   ├── 2_federal_dec_nodes.json      # 6 DECISION nodes
│   │   ├── 3_federal_act_nodes.json      # 6 ACTION nodes
│   │   ├── 4_federal_out_nodes.json      # 6 OUTCOME nodes
│   │   ├── 5_federal_fail_nodes.json     # 6 FAILURE nodes
│   │   └── 6_federal_pmc_nodes.json      # 6 OVERSIGHT nodes
│   │
│   └── missing_persons/                  # Missing Children Chain
│       ├── federal_baseline/federal_baseline.json
│       ├── pmc_community_standard/pmc_community_standard.json
│       └── state_clearinghouses.json
│
├── states_chains/                        # STATE BRANCHES (51 states × 42 nodes)
│   ├── AK/ (42 files)
│   ├── AL/ (42 files)
│   ├── ...
│   └── WY/ (42 files)
│
└── reference/                            # LOOKUP DATA
    ├── state_county_map.json
    └── us_states.json
```

---

## THE TWO AXES: VERTICAL AUTHORITY + HORIZONTAL FLOW

### VERTICAL AXIS: Legal Hierarchy (Who Governs)

```
┌─────────────────────────────────────────────────────────────────┐
│  CONSTITUTIONAL PLANE (constitutional_plane.json)               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  SUPREME LAW - Cannot be violated by any lower authority        │
│                                                                 │
│  Constraints:                                                   │
│  • CONST_4A_SEIZURE - Child removal = seizure                   │
│  • CONST_4A_SEARCH - Home visit = search                        │
│  • CONST_14A_PROCEDURAL_DP - Notice + hearing required          │
│  • CONST_14A_SUBSTANTIVE_DP - Family integrity right            │
│  • CONST_14A_EQUAL_PROTECTION - No discrimination               │
│  • CONST_5A_SELF_INCRIMINATION - Right to silence               │
│  • CONST_6A_COUNSEL - Right to attorney (criminal)              │
│  • CONST_1A_RELIGION - Religious freedom                        │
│                                                                 │
│  Remedy for violation: 42 U.S.C. § 1983 civil rights lawsuit    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ constrains
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FEDERAL PLANE (federal_plane.json)                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  FLOOR - Minimum requirements for federal funding               │
│                                                                 │
│  Requirements:                                                  │
│  • FED_CAPTA - Child Abuse Prevention & Treatment Act           │
│  • FED_ASFA - Adoption and Safe Families Act                    │
│  • FED_IV_E - Title IV-E funding structure                      │
│  • FED_ICWA - Indian Child Welfare Act                          │
│  • FED_FFPSA - Family First Prevention Services                 │
│  • FED_MEPA - Multiethnic Placement Act                         │
│  • FED_CFSR - Child & Family Services Reviews                   │
│  • FED_VICAA - Victims of Child Abuse Act                       │
│                                                                 │
│  Consequence of non-compliance: Loss of federal funding         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ states can EXCEED but not go BELOW
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE CONSTITUTIONAL PLANE (state_constitutional/*.json)       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  CAN EXCEED FEDERAL - Additional protections                    │
│                                                                 │
│  Example (Texas):                                               │
│  • Tex. Const. art. I, § 9 - Search/seizure (= federal)         │
│  • Tex. Const. art. I, § 19 - Due course of law (= federal)     │
│  • Tex. Const. art. I, § 13 - Jury trial for TPR (EXCEEDS!)     │
│  • Tex. Fam. Code § 107.013 - Right to counsel (EXCEEDS!)       │
│                                                                 │
│  STATUS: Only TX and CA completed. 49 states MISSING!           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ determines who decides
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ADMINISTRATIVE STRUCTURE (administrative_structure.json)       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  WHO ADMINISTERS - State agency vs County agency                │
│                                                                 │
│  State-Administered (41 states):                                │
│  TX, FL, AK, AL, AR, AZ, CT, DC, DE, GA, HI, IA, ID, IL...      │
│  → Centralized policy, state employees                          │
│                                                                 │
│  County-Administered (9 states):                                │
│  CA, CO, MN, NC, ND, NY, OH, PA, VA                             │
│  → Decentralized, county variation                              │
│                                                                 │
│  Hybrid (2 states):                                             │
│  NV, WI                                                         │
│  → Split responsibilities                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### HORIZONTAL AXIS: Decision Flow (What Happens)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         FEDERAL BASELINE (THE TRUNK)                         │
│                    chains/cps/federal_baseline/*.json                        │
└──────────────────────────────────────────────────────────────────────────────┘

REPORT RECEIVED                                                    OVERSIGHT
     │                                                                 │
     ▼                                                                 │
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│   INP   │───▶│   DEC   │───▶│   ACT   │───▶│   OUT   │    │   PMC   │
│ (Input) │    │(Decision│    │(Action) │    │(Outcome)│    │(Oversee)│
│         │    │         │    │         │    │         │    │         │
│ 12 nodes│    │ 6 nodes │    │ 6 nodes │    │ 6 nodes │    │ 6 nodes │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                    │              │              │              │
                    │              │              │              │
                    ▼              ▼              ▼              │
               ┌─────────────────────────────────────────┐       │
               │              FAIL (Failure)             │◀──────┘
               │                 6 nodes                 │  monitors
               │   When things go wrong → §1983 lawsuit  │
               └─────────────────────────────────────────┘


INP (Input) - 12 ways a case ENTERS:
├── INP-01: Mandatory Report (teacher, doctor)
├── INP-02: Voluntary/Third-Party Report
├── INP-03: Law Enforcement Referral
├── INP-04: Court-Ordered Referral
├── INP-05: Self-Report/Guardian Request
├── INP-06: Anonymous Tip/Hotline
├── INP-07: Medical Disclosure
├── INP-08: Educational Disclosure
├── INP-09: Systemic Audit/Oversight Trigger
├── INP-10: Agency Escalation (Screen → Investigate)
├── INP-11: Federal/Tribal Jurisdiction (ICWA)
└── INP-12: Emergency Protective Custody

DEC (Decision) - 6 decision points:
├── DEC-01: Screen-In vs Screen-Out
├── DEC-02: Investigation Track Selection
├── DEC-03: Differential Response Path
├── DEC-04: Emergency Removal Decision
├── DEC-05: Substantiation Finding
└── DEC-06: Court Petition Decision

ACT (Action) - 6 actions agency takes:
├── ACT-01: Removal/Protective Custody
├── ACT-02: In-Home Services
├── ACT-03: Foster Care Placement
├── ACT-04: Relative/Kinship Placement
├── ACT-05: Criminal Referral
└── ACT-06: Case Closure

OUT (Outcome) - 6 outcomes for the child:
├── OUT-01: Reunification with Family
├── OUT-02: Termination of Parental Rights (TPR)
├── OUT-03: Adoption
├── OUT-04: Guardianship
├── OUT-05: Emancipation
└── OUT-06: Transfer to Adult Services

FAIL (Failure) - 6 failure modes:
├── FAIL-01: Failure to Investigate
├── FAIL-02: Unlawful Removal/Due Process Violation
├── FAIL-03: Placement Failure/Abuse in Care
├── FAIL-04: Fatality After Contact
├── FAIL-05: Wrongful TPR
└── FAIL-06: Systemic Non-Compliance

PMC (Oversight) - 6 oversight mechanisms:
├── PMC-01: CFSR Monitoring
├── PMC-02: OIG/Single Audit
├── PMC-03: CAPTA Citizen Review Panels
├── PMC-04: Protect Our Kids Act Compliance
├── PMC-05: FOIA/Transparency Enforcement
└── PMC-06: Project Milk Carton AI Layer ← THIS IS ARIA
```

---

## TRACING THE PATH: AK_PMC-06 to FEDERAL_INP-01

### VERTICAL PATH (Authority Chain):

```
AK_PMC-06.json (Alaska PMC Spider AI Layer)
     │
     │ governed by
     ▼
constitutional_plane.json
├── CONST_14A_PROCEDURAL_DP (due process for oversight)
├── CONST_5A_SELF_INCRIMINATION (protection for parents)
└── 42 U.S.C. § 1983 (remedy for violations)
     │
     │ funded by
     ▼
federal_plane.json
├── FED_CAPTA (42 U.S.C. § 5106a(c)) - Citizen Review Panels
├── FED_CFSR (45 CFR Part 1355) - Performance monitoring
└── FED_IV_E (42 U.S.C. §§ 670-679c) - Funding at risk
     │
     │ exceeds (if applicable)
     ▼
state_constitutional/AK_constitution.json (MISSING - needs creation)
     │
     │ administered by
     ▼
administrative_structure.json
└── Alaska = State-Administered (Office of Children's Services)
```

### HORIZONTAL PATH (Decision Flow):

```
AK_PMC-06 (Alaska Oversight - Project Milk Carton AI)
     │
     │ linked_fail: "ALL" - monitors ALL failure modes
     ▼
┌────────────────────────────────────────────────────────────────┐
│ AK_FAIL-01 through AK_FAIL-06                                  │
│ ├── FAIL-01 ← triggered by failures in DEC-01, DEC-02          │
│ ├── FAIL-02 ← triggered by failures in DEC-04, ACT-01          │
│ ├── FAIL-03 ← triggered by failures in ACT-03, ACT-04          │
│ ├── FAIL-04 ← triggered by failures in ALL nodes               │
│ ├── FAIL-05 ← triggered by failures in OUT-02                  │
│ └── FAIL-06 ← triggered by failures in PMC-01, PMC-03          │
└────────────────────────────────────────────────────────────────┘
     │
     │ failures occur when
     ▼
┌────────────────────────────────────────────────────────────────┐
│ AK_ACT-01 through AK_ACT-06                                    │
│ Actions taken by Alaska OCS                                    │
│ ├── ACT-01: Emergency removal under Alaska Stat. § 47.10.142   │
│ └── ...                                                        │
└────────────────────────────────────────────────────────────────┘
     │
     │ actions result from
     ▼
┌────────────────────────────────────────────────────────────────┐
│ AK_DEC-01 through AK_DEC-06                                    │
│ Decisions made by Alaska OCS                                   │
│ ├── DEC-04: Emergency removal decision                         │
│ └── ...                                                        │
└────────────────────────────────────────────────────────────────┘
     │
     │ decisions triggered by
     ▼
┌────────────────────────────────────────────────────────────────┐
│ AK_INP-01 through AK_INP-12                                    │
│ How cases enter Alaska system                                  │
│ ├── INP-01: Mandatory report → Alaska hotline 1-800-478-4444   │
│ ├── INP-06: Anonymous tip → same hotline                       │
│ ├── INP-12: Emergency custody → Alaska Stat. § 47.10.142       │
│ └── ...                                                        │
└────────────────────────────────────────────────────────────────┘
     │
     │ inherits from
     ▼
┌────────────────────────────────────────────────────────────────┐
│ FEDERAL BASELINE                                               │
│ chains/cps/federal_baseline/1_federal_inp_nodes.json           │
│                                                                │
│ Contains:                                                      │
│ • Federal statutory authority (CAPTA, ASFA, IV-E)              │
│ • Constitutional constraints (4th, 14th Amendment)             │
│ • URLs to law.cornell.edu for each statute                     │
│ • Triggering events and reporting obligations                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WHAT'S MISSING (PMC Spider's Job)

### 1. State Constitutional Files (49 states missing)

```
legal_planes/state_constitutional/
├── _TEMPLATE.json      ✓ EXISTS
├── CA_constitution.json ✓ EXISTS
├── TX_constitution.json ✓ EXISTS
├── AK_constitution.json ✗ MISSING
├── AL_constitution.json ✗ MISSING
├── ... (46 more)        ✗ MISSING
└── WY_constitution.json ✗ MISSING
```

**PMC Spider must crawl each state legislature site and extract:**

- State constitution URL
- Search and seizure provisions
- Due process provisions
- Any provisions that EXCEED federal floor
- State supreme court cases interpreting these provisions

### 2. State Node Citations (2,142 nodes incomplete)

Current state nodes have:

```json
"statutory_authority": {
  "state": ["Alaska Code Title 47, Chapter 17"]  ← STRING ONLY
}
```

Should have:

```json
"layers": {
  "state_statutory": {
    "primary_citations": [
      {
        "citation_text": "Alaska Stat. § 47.17.020",
        "source_url": "https://www.akleg.gov/basis/statutes.asp#47.17.020",
        "authority_type": "state_statute",
        "last_verified": "2025-12-22"
      }
    ]
  }
}
```

### 3. Missing Data Per Node

Each state node should have (per schema):

| Field                           | Status       | What's Needed                              |
| ------------------------------- | ------------ | ------------------------------------------ |
| `layers.constitutional`       | Partial      | Link to constitutional_plane constraints   |
| `layers.state_constitutional` | MISSING      | State constitution provisions              |
| `layers.federal`              | Partial      | Federal requirement citations with URLs    |
| `layers.state_statutory`      | MISSING URLS | Actual statute URLs from state legislature |
| `layers.administrative_rule`  | MISSING      | State admin code citations                 |
| `layers.case_law`             | MISSING      | State court decisions from CourtListener   |
| `layers.policy_sop`           | MISSING      | Agency policy manual URLs                  |
| `burden_of_proof`             | MISSING      | Standard + statutory basis                 |
| `timeline_requirements`       | MISSING      | State-specific deadlines                   |
| `notice_requirements`         | MISSING      | State due process requirements             |
| `door_scenarios`              | MISSING      | What happens when CPS shows up             |
| `cross_references`            | MISSING      | Links between nodes                        |

---

## PMC SPIDER TRAINING DATA REQUIREMENTS

PMC Spider should be trained to:

1. **Navigate to state legislature websites**

   - Extract statute URLs for child protection codes
   - Get actual citation format (e.g., "Alaska Stat. § 47.17.020")
   - Verify URL returns actual statute text
2. **Query CourtListener API**

   - Find state supreme court cases on child welfare
   - Extract case name, citation, holding, URL
   - Match cases to relevant nodes
3. **Crawl childwelfare.gov**

   - Get state-by-state statutory compilations
   - Extract mandatory reporter definitions
   - Get investigation timelines
   - Get TPR grounds
4. **Populate the schema correctly**

   - Use `layers.state_statutory.primary_citations[]` format
   - Include `source_url` for every citation
   - Add `last_verified` dates
   - Build `cross_references` between nodes
5. **NEVER hallucinate**

   - Only use URLs that actually exist
   - Only use citations from official sources
   - Validate state matches (Texas data → Texas nodes)

---

## FILE RELATIONSHIPS DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SCHEMAS                                       │
│               (Define what every file must contain)                     │
│                                                                         │
│  extended_decision_chain.schema.json ──────────────────────────────────┐│
│  evaluation_capsule.schema.json ─────────────────────────────────────┐ ││
└──────────────────────────────────────────────────────────────────────┼─┼┘
                                                                       │ │
                validates                                              │ │
                    │                                                  │ │
┌───────────────────┼──────────────────────────────────────────────────┼─┼─┐
│                   ▼                                                  │ │ │
│  ┌────────────────────────────────────────────────────────────────┐  │ │ │
│  │                    LEGAL PLANES                                │  │ │ │
│  │              (Authority hierarchy)                             │  │ │ │
│  │                                                                │  │ │ │
│  │  constitutional_plane.json ◀───────────────────────────────────┼──┼─┘ │
│  │         │                                                      │  │   │
│  │         │ constrains                                           │  │   │
│  │         ▼                                                      │  │   │
│  │  federal_plane.json ◀──────────────────────────────────────────┼──┘   │
│  │         │                                                      │      │
│  │         │ funded by                                            │      │
│  │         ▼                                                      │      │
│  │  state_constitutional/*.json                                   │      │
│  │         │                                                      │      │
│  │         │ administered by                                      │      │
│  │         ▼                                                      │      │
│  │  administrative_structure.json                                 │      │
│  └────────────────────────────────────────────────────────────────┘      │
│                   │                                                      │
│                   │ applies to                                           │
│                   ▼                                                      │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │              FEDERAL BASELINES                                 │      │
│  │           (The trunk of the tree)                              │      │
│  │                                                                │      │
│  │  chains/cps/federal_baseline/                                  │      │
│  │  ├── 1_federal_inp_nodes.json (12 input triggers)              │      │
│  │  ├── 2_federal_dec_nodes.json (6 decisions)                    │      │
│  │  ├── 3_federal_act_nodes.json (6 actions)                      │      │
│  │  ├── 4_federal_out_nodes.json (6 outcomes)                     │      │
│  │  ├── 5_federal_fail_nodes.json (6 failures)                    │      │
│  │  └── 6_federal_pmc_nodes.json (6 oversight)                    │      │
│  │                                                                │      │
│  │  chains/missing_persons/                                       │      │
│  │  ├── federal_baseline/federal_baseline.json                    │      │
│  │  ├── pmc_community_standard/pmc_community_standard.json        │      │
│  │  └── state_clearinghouses.json (51 states)                     │      │
│  └────────────────────────────────────────────────────────────────┘      │
│                   │                                                      │
│                   │ branches into                                        │
│                   ▼                                                      │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │                 STATE CHAINS                                   │      │
│  │          (The leaves of the tree)                              │      │
│  │                                                                │      │
│  │  states_chains/                                                │      │
│  │  ├── AK/ (42 files: AK_INP-01 through AK_PMC-06)               │      │
│  │  ├── AL/ (42 files)                                            │      │
│  │  ├── ... (49 more states)                                      │      │
│  │  └── WY/ (42 files)                                            │      │
│  │                                                                │      │
│  │  Each file inherits from federal baseline and adds:            │      │
│  │  • State statute citations with URLs                           │      │
│  │  • State case law                                              │      │
│  │  • State agency info (hotlines, websites)                      │      │
│  │  • State-specific timelines                                    │      │
│  │  • Cross-references to other nodes                             │      │
│  └────────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │                   REFERENCE DATA                               │      │
│  │                                                                │      │
│  │  reference/                                                    │      │
│  │  ├── state_county_map.json (counties per state)                │      │
│  │  └── us_states.json (state codes/names)                        │      │
│  └────────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## SUMMARY

| Folder                                         | Purpose                       | Status              |
| ---------------------------------------------- | ----------------------------- | ------------------- |
| `schemas/`                                   | Defines validation rules      | ✓ Complete         |
| `legal_planes/constitutional_plane.json`     | U.S. Constitution constraints | ✓ Complete         |
| `legal_planes/federal_plane.json`            | Federal statutory floor       | ✓ Complete         |
| `legal_planes/administrative_structure.json` | State vs County admin         | ✓ Complete         |
| `legal_planes/state_constitutional/`         | State constitutions           | ✗ Only 2/51        |
| `chains/cps/federal_baseline/`               | Federal CPS decision chain    | ✓ Complete         |
| `chains/missing_persons/`                    | Missing children chain        | ✓ Complete         |
| `states_chains/`                             | State-specific nodes          | ✗ Shell files only |
| `reference/`                                 | Lookup data                   | ✓ Complete         |

**PMC Spider's mission:** Crawl state sources and populate `states_chains/` with REAL data including statute URLs, case law, timelines, and cross-references per the `extended_decision_chain.schema.json` specification.
