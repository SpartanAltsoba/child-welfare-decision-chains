Feature release (MINOR): the case-law layer was rebuilt for every jurisdiction and added to the federal baseline. No jurisdictions or node types were added or removed.

### Case-law layer rebuilt

- **What was wrong.** In v1.0.x, `layers.case_law.key_cases` held recent Justia opinion listings selected by title keywords, with synthetic citations, no holdings, and the same list pasted into every node of a jurisdiction regardless of topic. Many entries were unrelated to child welfare.
- **What it is now.** Each decision point carries authorities selected for that point. Every opinion was retrieved from CourtListener and read; `holding` and `quote` come from the majority opinion text; `citation` is the official reporter citation in Bluebook form; `relevance` says why the authority matters at that node; `url` and `courtlistener_cluster_id` point to the opinion. The layer records `method` and `verified_date`. A node with no verified on-point authority says so in `_note` rather than carrying a placeholder.
- **How it was verified.** An independent adversarial pass refetched every cluster and opinion and attempted to refute each entry (citation match, exact-quote check against the majority opinion, holding not inverted or overstated, on-point for the node); rejected entries were removed. A supplement pass retrieved the leading authorities the verifier named as missing and re-verified them. Method and tooling: `data/tools/qa/caselaw/README.md`; the reconciled briefs and per-node digests are committed under `data/tools/qa/caselaw/briefs/` for provenance.
- **New fields** (additive, within case entries): `holding`, `quote`, `relevance`, `date_decided`, `url`, `courtlistener_cluster_id`; on the layer: `method`, `verified_date`, `_note`. These follow the schema's `case_law_reference` shape.
- **Federal baseline** nodes, which had no case-law layer, now carry the U.S. Supreme Court and circuit authorities that govern each decision point nationally.

| Jurisdiction | Authorities | Per node | Verified |
|---|---|---|---|
| AK | 45 | 1–7 | 2026-09-20 |
| AL | 41 | 2–6 | 2026-09-20 |
| AR | 48 | 1–6 | 2026-09-20 |
| AZ | 63 | 2–9 | 2026-09-20 |
| CA | 57 | 2–6 | 2026-09-20 |
| CO | 40 | 1–6 | 2026-09-20 |
| CT | 46 | 1–6 | 2026-09-20 |
| DC | 47 | 1–6 | 2026-09-20 |
| DE | 38 | 1–6 | 2026-09-20 |
| FL | 45 | 1–6 | 2026-09-20 |
| GA | 41 | 1–6 | 2026-09-20 |
| HI | 41 | 1–6 | 2026-09-20 |
| IA | 42 | 0–6 | 2026-09-20 |
| ID | 42 | 1–6 | 2026-09-20 |
| IL | 53 | 1–6 | 2026-09-20 |
| IN | 50 | 1–6 | 2026-09-20 |
| KS | 49 | 2–6 | 2026-09-20 |
| KY | 47 | 1–6 | 2026-09-20 |
| LA | 36 | 1–6 | 2026-09-20 |
| MA | 59 | 1–7 | 2026-09-20 |
| MD | 45 | 1–6 | 2026-09-20 |
| ME | 45 | 0–6 | 2026-09-20 |
| MI | 42 | 1–6 | 2026-09-20 |
| MN | 50 | 2–6 | 2026-09-20 |
| MO | 42 | 2–8 | 2026-09-20 |
| MS | 45 | 1–6 | 2026-09-20 |
| MT | 51 | 1–6 | 2026-09-20 |
| NC | 45 | 1–6 | 2026-09-20 |
| ND | 43 | 0–9 | 2026-09-20 |
| NE | 46 | 1–7 | 2026-09-20 |
| NH | 42 | 2–6 | 2026-09-21 |
| NJ | 48 | 1–9 | 2026-09-21 |
| NM | 52 | 1–6 | 2026-09-21 |
| NV | 51 | 2–17 | 2026-09-20 |
| NY | 43 | 2–6 | 2026-09-21 |
| OH | 54 | 2–6 | 2026-09-21 |
| OK | 57 | 1–9 | 2026-09-21 |
| OR | 45 | 1–7 | 2026-09-21 |
| PA | 47 | 1–9 | 2026-09-21 |
| RI | 50 | 0–7 | 2026-09-21 |
| SC | 50 | 2–6 | 2026-09-21 |
| SD | 50 | 2–6 | 2026-09-21 |
| TN | 48 | 2–6 | 2026-09-21 |
| TX | 47 | 1–14 | 2026-09-20 |
| US | 41 | 3–6 | 2026-09-20 |
| UT | 50 | 2–6 | 2026-09-21 |
| VA | 49 | 2–6 | 2026-09-21 |
| VT | 47 | 2–8 | 2026-09-21 |
| WA | 47 | 1–6 | 2026-09-21 |
| WI | 54 | 1–6 | 2026-09-21 |
| WV | 45 | 2–6 | 2026-09-21 |
| WY | 46 | 0–6 | 2026-09-20 |

Total: 2,447 verified authorities across 52 jurisdictions. Decision points with no verified on-point authority (stated in the node): IA INP-04, IA OUT-04, ME INP-04, ND OUT-04, RI INP-05, WY INP-04.

### Also in this release

- `data/tools/qa/release.py` and `build_manifest.py` produce the manifest and version strings for every release.
- `.github/workflows/caselaw-rebuild.yml` (manual dispatch only) runs the same pipeline in CI and opens a pull request; it never writes to `main`.

### Known issues carried forward

- **Schema shape mismatch (pre-existing since v1.0.0).** `layers.constitutional.*` and `layers.federal.*` entries are strings where the schema expects objects, and `notice_requirements[].who_must_be_notified` carries values outside the schema's enum. Data and schema will be reconciled in a later release.
- **Administrative-rule citations** in several jurisdictions still point at regulation index pages rather than the rule section.
- **Backfill poster URLs** (`<ST>_backfill.json`) are not maintained as citations.
- CourtListener coverage of some intermediate appellate courts is incomplete; where a jurisdiction's published authority on a point is thin, the node says so.
