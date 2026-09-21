#!/usr/bin/env python3
"""Write the v1.1.0 changelog section body from the committed briefs (counts are computed, prose is fixed)."""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
briefs = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(HERE, "briefs", "*.json")))}
rows = []; total_cases = 0; empties = []
for st, b in briefs.items():
    per = [len(v) for v in b["node_map"].values()]; total_cases += len(b["cases"])
    e = [k for k, v in b["node_map"].items() if not v]; empties += [f"{st} {k}" for k in e]
    rows.append(f"| {st} | {len(b['cases'])} | {min(per)}–{max(per)} | {b['verified_date']} |")
body = f"""Feature release (MINOR): the case-law layer was rebuilt for every jurisdiction and added to the federal baseline. No jurisdictions or node types were added or removed.

### Case-law layer rebuilt

- **What was wrong.** In v1.0.x, `layers.case_law.key_cases` held recent Justia opinion listings selected by title keywords, with synthetic citations, no holdings, and the same list pasted into every node of a jurisdiction regardless of topic. Many entries were unrelated to child welfare.
- **What it is now.** Each decision point carries authorities selected for that point. Every opinion was retrieved from CourtListener and read; `holding` and `quote` come from the majority opinion text; `citation` is the official reporter citation in Bluebook form; `relevance` says why the authority matters at that node; `url` and `courtlistener_cluster_id` point to the opinion. The layer records `method` and `verified_date`. A node with no verified on-point authority says so in `_note` rather than carrying a placeholder.
- **How it was verified.** An independent adversarial pass refetched every cluster and opinion and attempted to refute each entry (citation match, exact-quote check against the majority opinion, holding not inverted or overstated, on-point for the node); rejected entries were removed. A supplement pass retrieved the leading authorities the verifier named as missing and re-verified them. Method and tooling: `data/tools/qa/caselaw/README.md`; the reconciled briefs and per-node digests are committed under `data/tools/qa/caselaw/briefs/` for provenance.
- **New fields** (additive, within case entries): `holding`, `quote`, `relevance`, `date_decided`, `url`, `courtlistener_cluster_id`; on the layer: `method`, `verified_date`, `_note`. These follow the schema's `case_law_reference` shape.
- **Federal baseline** nodes, which had no case-law layer, now carry the U.S. Supreme Court and circuit authorities that govern each decision point nationally.

| Jurisdiction | Authorities | Per node | Verified |
|---|---|---|---|
{chr(10).join(rows)}

Total: {total_cases:,} verified authorities across {len(briefs)} jurisdictions.{(" Decision points with no verified on-point authority (stated in the node): " + ", ".join(empties) + ".") if empties else ""}

### Also in this release

- `data/tools/qa/release.py` and `build_manifest.py` produce the manifest and version strings for every release.
- `.github/workflows/caselaw-rebuild.yml` (manual dispatch only) runs the same pipeline in CI and opens a pull request; it never writes to `main`.

### Known issues carried forward

- **Schema shape mismatch (pre-existing since v1.0.0).** `layers.constitutional.*` and `layers.federal.*` entries are strings where the schema expects objects, and `notice_requirements[].who_must_be_notified` carries values outside the schema's enum. Data and schema will be reconciled in a later release.
- **Administrative-rule citations** in several jurisdictions still point at regulation index pages rather than the rule section.
- **Backfill poster URLs** (`<ST>_backfill.json`) are not maintained as citations.
- CourtListener coverage of some intermediate appellate courts is incomplete; where a jurisdiction's published authority on a point is thin, the node says so.
"""
open(os.path.join(HERE, "RELEASE_NOTES_v1.1.0.md"), "w").write(body)
print(f"release notes: {len(briefs)} jurisdictions, {total_cases} authorities, {len(empties)} empty nodes")
