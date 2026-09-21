# Case-law layer: how it is built and verified (v1.1.0)

Every decision node carries `layers.case_law.key_cases`. From v1.1.0 each entry is an authority selected for that
decision point, retrieved from [CourtListener](https://www.courtlistener.com/) and read, with:

| field | meaning |
|---|---|
| `case_name` | as the court styles it |
| `citation` | official reporter citation, Bluebook form (slip form if the cluster has no reporter cite) |
| `court`, `year`, `date_decided` | from the CourtListener cluster |
| `holding` | one sentence: what the court decided on the point that matters at this node |
| `quote` | an exact passage (≤ 30 words) from the majority opinion that carries the rule |
| `relevance` | why this authority matters at this decision point |
| `url`, `courtlistener_cluster_id` | where to read the opinion |

The layer also records `method` and `verified_date`.

## Pipeline (`pipeline.py`)

1. **Research.** For each of the 42 decision points, targeted searches in the jurisdiction's highest court, then its
   intermediate appellate court, then the U.S. Supreme Court and the jurisdiction's federal circuit where the point is
   federal. Every candidate opinion is retrieved and read. No authority is written from memory.
2. **Adversarial verification.** An independent pass refetches every cluster and opinion and tries to refute each entry:
   the citation must match the cluster, the quote must be an exact substring of the majority opinion and the court's
   own statement of the rule with its qualifications, the holding must not invert or overstate, and each mapping to a
   decision point must be on point. It also names leading authorities that are missing.
3. **Reconcile.** Rejected entries and mappings are removed; corrected citations applied.
4. **Supplement.** The named missing authorities are retrieved and read; decision points left with fewer than two
   authorities are researched again. **Re-verify** and **reconcile** run on the additions.
5. `apply_caselaw_brief.py` writes the brief into the node files. `validate_touched.py` gates the result.

The same code runs locally on a Claude plan or in GitHub Actions on an API key (`caselaw-rebuild.yml`, manual
dispatch only; it opens a pull request and never writes to `main`).

## What v1.0.x carried

Keyword-matched Justia opinion listings (2020–2025) with synthetic citations and no holdings, pasted into every node
of a jurisdiction regardless of topic. Those entries were removed in v1.1.0.

## Known limits

Coverage per decision point is what published authority supports; a node with fewer than two authorities, or none,
says so in `_note`. CourtListener coverage of some state intermediate courts is incomplete. Quotes are verified
against CourtListener's text of the opinion; pin cites are not carried. This is legal information, not legal advice.
