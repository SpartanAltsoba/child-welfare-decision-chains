#!/usr/bin/env python3
"""Assemble the v1.0.1 release: CHANGELOG.md, version strings, MANIFEST.json.

Usage: python3 release_v1_0_1.py <changelog_dir> [--write]
  changelog_dir holds one <ST>.md per jurisdiction (release-note prose written and verified per state).
Dry run prints what would change; --write applies it. Run build_manifest.py last (this script calls it).
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
VERSION = "1.0.1"
TODAY = datetime.date.today().isoformat()

KNOWN_ISSUES = """### Known issues carried to v1.1.0 (not corrected in this release)

- **Case-law layer relevance.** `layers.case_law.key_cases` was keyword-matched at build time and attaches off-topic opinions in many jurisdictions (verified examples in AR, DE, GA, HI, IA, IN, KS, KY). A dedicated case-law pass with human-readable relevance checks is planned.
- **Schema shape mismatch (pre-existing since v1.0.0).** `layers.constitutional.*` and `layers.federal.*` entries are strings where `extended_decision_chain.schema.json` expects objects, and `notice_requirements[].who_must_be_notified` carries values outside the schema's enum. Files did not validate at v1.0.0 and still do not; the schema and data will be reconciled in v1.1.0.
- **Backfill poster URLs.** `<ST>_backfill.json` files carry NCMEC poster links that change over time; they are not maintained as citations.
- **Administrative-rule citations.** Several jurisdictions cite regulation index pages or a superseded agency; deep links to the current rule sections are a v1.1.0 item.
- **Justia links.** law.justia.com and regulations.justia.com return HTTP 403 to automated fetches (Cloudflare challenge) but load in a browser. They are live and were left in place; they are not verifiable by script.
- **Full per-jurisdiction list.** Every item the verifiers judged out of scope for a correction release, with the reason, is in `data/tools/qa/carried_to_v1.1.0.json`.
"""

METHOD = """### How this release was produced

Every jurisdiction was re-researched by an AI writer against first-party sources (state code, agency pages, agency policy manuals), then challenged by an independent adversarial verifier that refetched every cited URL and attempted to refute each claim; changes that failed verification were reverted. Dataset-wide corrections were applied by `data/tools/qa/apply_verified_v1_0_1.py` from `verified_agency.json` and `url_fixes.json` (both committed, with provenance). The manifest is rebuilt by the committed `data/tools/qa/build_manifest.py`, which documents the root-hash formula. Project Milk Carton reviewed and released.
"""


def read_changelogs(d):
    parts = []
    for f in sorted(glob.glob(os.path.join(d, "*.md"))):
        parts.append(open(f).read().strip())
    return "\n\n".join(parts)


def build_changelog(changelog_dir, manifest):
    per = read_changelogs(changelog_dir)
    body = f"""# Changelog

All notable changes to the US Child Welfare Decision Chain Dataset. Versioning follows the policy in README.md (PATCH = corrections, URL updates, source revisions).

## v{VERSION} — {TODAY}

Correction release. No new jurisdictions or node types. {manifest['file_count']} files, root hash `{manifest['root_hash']}`.

### Dataset-wide corrections

- **Agency website.** Every one of the 2,142 state node files pointed `state_agency.website` at the state legislature. Corrected to the child welfare agency's own site in all 51 jurisdictions.
- **Agency name, acronym, hotline.** Corrected to the agency's current name and published reporting number in every jurisdiction (378 files carried a wrong or misleading hotline: a customer-service line, a director's office line, a county number, or an unpublished routing number). Jurisdictions with no statewide hotline now say so and point to the county or tribal office.
- **Template timelines relabeled.** The twelve `timeline_requirements` entries were identical in all 51 jurisdictions and labeled `state_statute`, `court_rule` or `admin_rule`. They are national template ranges, not citations to any state's law, and are now labeled `template_estimate` (2,754 entries). Where a jurisdiction's actual deadline was verified, the template entry was replaced with the cited state rule (see per-jurisdiction notes).
- **Citation repairs.** Oklahoma's primary statutory citation pointed at a 1986 insurance opinion (OSCN CiteID 10000); corrected to 10A O.S. § 1-2-101 (CiteID 455989). Rhode Island's citation host (rilin.state.ri.us) is dead; replaced with rilegislature.gov. Dead legislature "folio" deep links replaced with live official links in several jurisdictions.
- **Schema.** `timeline_requirement.source` gains the additive value `template_estimate`.
- **Reproducible manifest.** `data/tools/qa/build_manifest.py` is committed with a documented root-hash formula. (The v1.0.0 manifest generator was never committed; its root hash stands as a historical value.)

### Per-jurisdiction corrections

{per}

{KNOWN_ISSUES}
{METHOD}
## v1.0.0 — 2026-04-26

Initial public release: 2,142 decision nodes across 51 jurisdictions.
"""
    return body


def bump_versions(write):
    changes = []

    def sub(path, pattern, repl, count=0):
        p = os.path.join(ROOT, path)
        s = open(p).read()
        n, k = re.subn(pattern, repl, s, count=count, flags=re.M)
        if k:
            changes.append((path, pattern[:40], k))
            if write:
                open(p, "w").write(n)

    sub("README.md", r"version-1\.0\.0-blue", f"version-{VERSION}-blue")
    sub("README.md", r"releases/tag/v1\.0\.0", f"releases/tag/v{VERSION}")
    sub("README.md", r"\*\*v1\.0\.0 release:\*\*", f"**v{VERSION} release:**")
    sub("README.md", r"\(Version 1\.0\.0\)", f"(Version {VERSION})")
    sub("README.md", r"The current release is \*\*v1\.0\.0\*\*", f"The current release is **v{VERSION}** (see [CHANGELOG.md](./CHANGELOG.md))")
    sub("CITATION.cff", r'^version: "1\.0\.0"', f'version: "{VERSION}"')
    sub("CITATION.cff", r"\(v1\.0\.0\)", f"(v{VERSION})")
    sub("CITATION.cff", r"^date-released: .*$", f'date-released: "{TODAY}"')
    sub("PROVENANCE.md", r"\| Version \(current release\) \| v1\.0\.0 \|", f"| Version (current release) | v{VERSION} |")
    sub("PROVENANCE.md", r"Cite the version \(`v1\.0\.0`\)", f"Cite the version (`v{VERSION}`)")
    return changes


def main():
    changelog_dir = sys.argv[1]
    write = "--write" in sys.argv
    os.chdir(ROOT)
    # 1. manifest (dry or write) — needs final data tree
    out = subprocess.run([sys.executable, "data/tools/qa/build_manifest.py", VERSION] + (["--write"] if write else []), capture_output=True, text=True).stdout
    print(out.strip())
    manifest = json.load(open("MANIFEST.json")) if write else None
    if manifest is None:
        m = re.search(r"(\d+) files, root_hash ([0-9a-f]{64})", out)
        manifest = {"file_count": int(m.group(1)), "root_hash": m.group(2)}
    # 1b. carried-to-v1.1.0 list becomes a committed artifact
    carry_src = os.path.join(os.path.dirname(changelog_dir), "results", "v1_1_0_carry.json")
    if os.path.exists(carry_src):
        carry = json.load(open(carry_src))
        art = {"_about": "Items found during the v1.0.1 verification passes that were out of scope for a correction release (case-law relevance, schema shape, backfill URLs, administrative-rule deep links, items needing fields the schema lacks). Verifier wording, per jurisdiction. Input to the v1.1.0 pass.",
               "generated": TODAY, "jurisdictions": carry}
        if write:
            with open("data/tools/qa/carried_to_v1.1.0.json", "w") as fh:
                json.dump(art, fh, indent=1, ensure_ascii=False); fh.write("\n")
        print(f"carried_to_v1.1.0.json: {sum(len(v) for v in carry.values())} items across {len(carry)} jurisdictions ({'written' if write else 'dry run'})")
    # 2. changelog
    cl = build_changelog(changelog_dir, manifest)
    if write:
        open("CHANGELOG.md", "w").write(cl)
    print(f"CHANGELOG.md: {len(cl.splitlines())} lines ({'written' if write else 'dry run'})")
    # 3. version strings
    for path, pat, k in bump_versions(write):
        print(f"  {path}: {k} × {pat}")
    # 4. provenance root hash line for this version
    p = os.path.join(ROOT, "PROVENANCE.md")
    s = open(p).read()
    if f"v{VERSION} root_hash" not in s:
        s2 = s.replace("v1.0.0 root_hash: ac684eaaf7912f24c6e98a35d90232eedddd2da8777e07888f38e5ea6a6bca7e",
                       f"v1.0.0 root_hash: ac684eaaf7912f24c6e98a35d90232eedddd2da8777e07888f38e5ea6a6bca7e   (historical; generator not committed)\nv{VERSION} root_hash: {manifest['root_hash']}   (data/tools/qa/build_manifest.py)")
        if write and s2 != s:
            open(p, "w").write(s2)
        print("PROVENANCE.md: root hash line", "written" if write else "would be added")
    if write:
        # manifest again so it covers the final CHANGELOG-independent data tree (data/ only, unchanged by step 2-4) — recompute to be safe
        print(subprocess.run([sys.executable, "data/tools/qa/build_manifest.py", VERSION, "--write"], capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    main()
