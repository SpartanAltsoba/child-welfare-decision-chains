# Backlog for v1.2.0

Items carried out of the v1.0.1 verification passes that remain open after v1.1.0 (case-law items are resolved by v1.1.0 and removed here). 455 per-jurisdiction items are listed in `docs/carried_to_v1.2.0.json` in the verifiers' words.

## Cross-cutting

1. **Schema alignment (pre-existing since v1.0.0).** `layers.constitutional.*` and `layers.federal.*` entries are strings where `extended_decision_chain.schema.json` expects objects; `notice_requirements[].who_must_be_notified` carries values outside the schema's enum. Reconcile data and schema; then enforce validation in CI.
2. **Administrative-rule deep links.** Several jurisdictions cite regulation index pages or a superseded agency in `layers.administrative_rule`; replace with the current rule sections, verified.
3. **Decision points with no verified authority** (stated in the node): ND OUT-04, WY INP-04, IA INP-04, IA OUT-04, RI INP-05, ME INP-04. A targeted search of trial-level and unpublished authority, or a note that none exists, would close them.
4. **Citation normalization across jurisdictions.** The same opinion is occasionally cited to different reporters (e.g. Wallis v. Spencer, 193 F.3d 1054 (1999) vs. 202 F.3d 1126 (2000, amended)); prefer one form per case.
5. **Backfill poster URLs** (`<ST>_backfill.json`): decide whether to maintain or retire them.
6. **Quarterly case-law re-verification** via `.github/workflows/caselaw-rebuild.yml` (manual dispatch; requires the `COURTLISTENER_TOKEN` secret, not yet set).
