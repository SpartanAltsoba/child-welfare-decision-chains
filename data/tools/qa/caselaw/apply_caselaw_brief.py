#!/usr/bin/env python3
"""Apply a verified case-law brief to a jurisdiction's node files (v1.1.0 case-law rebuild).

A brief is produced by research + adversarial verification against CourtListener opinion text. This script
never invents anything: it only writes what the brief carries, after validating its shape.

Usage:
  python3 apply_caselaw_brief.py <brief.json> [--apply]          # state brief -> data/states_chains/<ST>/<ST>_*.json
  python3 apply_caselaw_brief.py <brief_US.json> --federal [--apply]  # federal brief -> data/chains/cps/federal_baseline/*.json

Brief shape:
  {"state": "TX", "verified_date": "2026-09-20",
   "cases": [{"cluster_id": 4621173, "case_name": "In re N.G.", "citation": "577 S.W.3d 230 (Tex. 2019)",
              "court": "Texas Supreme Court", "court_id": "tex", "date_decided": "2019-05-17", "year": 2019,
              "url": "https://www.courtlistener.com/opinion/4398426/in-re-ng/", "holding": "...", "quote": "...",
              "relevance": {"OUT-04": "why it matters at this node", ...}}],
   "node_map": {"INP-01": [4621173, ...], ... all 42 ...}}

Each node's layers.case_law becomes:
  {"jurisdiction": ..., "method": ..., "verified_date": ..., "courtlistener_search_url": <kept>, "search_keywords": <kept>,
   "key_cases": [ {case_name, citation, court, year, date_decided, holding, relevance, quote, url, courtlistener_cluster_id} ... ]}
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REQ = ("cluster_id", "case_name", "citation", "court", "year", "date_decided", "url", "holding", "quote")
FAMILIES = {"INP": 12, "DEC": 6, "ACT": 6, "OUT": 6, "FAIL": 6, "PMC": 6}
ALL_NODES = [f"{fam}-{i:02d}" for fam, n in FAMILIES.items() for i in range(1, n + 1)]
METHOD = ("v1.1.0 case-law rebuild: authorities selected per decision point, each opinion retrieved from CourtListener "
          "and read; holding and quote taken from the opinion text; independently re-verified before release. "
          "Previous keyword-matched Justia listings were removed.")


def validate(brief):
    errs = []
    cases = {c["cluster_id"]: c for c in brief["cases"]}
    for c in brief["cases"]:
        for k in REQ:
            if not c.get(k) and c.get(k) != 0:
                errs.append(f"case {c.get('cluster_id')} missing {k}")
        if not isinstance(c.get("year"), int):
            errs.append(f"case {c.get('cluster_id')} year not int")
        if not str(c.get("url", "")).startswith("https://www.courtlistener.com/"):
            errs.append(f"case {c.get('cluster_id')} url not CourtListener")
        if len(str(c.get("quote", "")).split()) > 40:
            errs.append(f"case {c.get('cluster_id')} quote over 40 words")
    nm = brief["node_map"]
    for node in ALL_NODES:
        ids = nm.get(node) or []
        if not ids:
            print(f"WARNING: node {node} has no cases (layer will carry an explicit 'no verified authority' note)")
        for i in ids:
            if i not in cases:
                errs.append(f"node {node} references unknown case {i}")
    return errs


def entry_for(c, node):
    rel = c.get("relevance") or {}
    return {
        "case_name": c["case_name"],
        "citation": (c["citation"][len(c["case_name"]) + 2:] if c["citation"].startswith(c["case_name"] + ", ") else c["citation"]),
        "court": c["court"],
        "year": c["year"],
        "date_decided": c["date_decided"],
        "holding": c["holding"],
        "relevance": rel.get(node) or rel.get("*") or "",
        "quote": c["quote"],
        "url": c["url"],
        "courtlistener_cluster_id": c["cluster_id"],
    }


def rewrite_layer(d, brief, node_key):
    old = (d.get("layers") or {}).get("case_law") or {}
    cases = {c["cluster_id"]: c for c in brief["cases"]}
    new = {
        "jurisdiction": old.get("jurisdiction") or brief["state"],
        "method": METHOD,
        "verified_date": brief["verified_date"],
        "key_cases": [entry_for(cases[i], node_key) for i in brief["node_map"].get(node_key, [])],
    }
    if not new["key_cases"]:
        new["_note"] = "No verified on-point authority was found for this decision point in this jurisdiction as of verified_date; see the federal baseline node for the governing federal standard."
    for keep in ("courtlistener_search_url", "search_keywords"):
        if old.get(keep):
            new[keep] = old[keep]
    d.setdefault("layers", {})["case_law"] = new


def dump(path, d):
    with open(path, "w") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main():
    brief = json.load(open(sys.argv[1]))
    apply = "--apply" in sys.argv
    federal = "--federal" in sys.argv
    errs = validate(brief)
    if errs:
        print("BRIEF INVALID:", *errs[:20], sep="\n  ")
        sys.exit(1)
    st = brief["state"]
    touched = 0
    if federal:
        for f in sorted(glob.glob(os.path.join(ROOT, "data/chains/cps/federal_baseline/*_federal_*_nodes.json"))):
            doc = json.load(open(f))
            key = next(iter(doc))
            for n in doc[key]:
                nid = (n.get("node_id") or n.get("subnode") or n.get("id") or "")
                node_key = re.sub(r"^US_", "", str(nid))
                if node_key in brief["node_map"]:
                    rewrite_layer(n, brief, node_key)
                    touched += 1
            if apply:
                dump(f, doc)
    else:
        for f in sorted(glob.glob(os.path.join(ROOT, f"data/states_chains/{st}/{st}_*.json"))):
            d = json.load(open(f))
            if "node_id" not in d:
                continue
            node_key = d["node_id"].replace(f"{st}_", "")
            rewrite_layer(d, brief, node_key)
            touched += 1
            if apply:
                dump(f, d)
    n_cases = len(brief["cases"])
    per = [len(v) for v in brief["node_map"].values()]
    print(f"{st}: {'APPLIED' if apply else 'DRY RUN'} {touched} nodes | {n_cases} distinct cases | per node min {min(per)} max {max(per)}")


if __name__ == "__main__":
    main()
