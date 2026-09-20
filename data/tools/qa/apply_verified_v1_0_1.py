#!/usr/bin/env python3
"""v1.0.1 Layer A — deterministic corrections from fleet-verified data (19 SEP 2026).

Inputs (committed alongside this script):
  verified_agency.json   per-state agency name / acronym / website / hotline, each fetched and verified
  url_fixes.json         exact-URL and dead-host replacements, each verified
Changes made to every state node file:
  1. state_agency.{name,acronym,website,hotline} <- verified values (website was the legislature in all 51 states)
  2. every URL string anywhere in the file passed through url_fixes (exact match, then host swap)
  3. timeline_requirements entries that are the 12-item national template get source="template_estimate"
     (they were labeled state_statute / court_rule / admin_rule, which was false for every state)
Usage: python3 apply_verified_v1_0_1.py [--apply]   (default is a dry run that only reports)
"""
import json, glob, os, sys, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
V = json.load(open(os.path.join(HERE, "verified_agency.json")))
U = json.load(open(os.path.join(HERE, "url_fixes.json")))
TEMPLATE = {("Permanency hearing","12 months"),("TPR filing","15 of 22 months"),("Safety decision","Immediate upon contact"),
            ("Disposition finding","30-60 days"),("Missing child report","Immediate"),("NCMEC notification","24 hours"),
            ("Emergency removal hearing","24-72 hours"),("Case plan development","30-60 days"),("Initial response time","24-72 hours"),
            ("Investigation completion","30-60 days"),("Appeal deadline","30 days"),("1983 statute of limitations","2-3 years")}
def fix_url(u):
    if u in U["exact"]: return U["exact"][u]
    for bad, good in U["hosts"].items():
        if f"://{bad}/" in u or u.endswith(f"://{bad}"): return u.replace(f"://{bad}", f"://{good}", 1)
    return u
def walk_urls(o, stats):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and v.startswith("http"):
                nv = fix_url(v)
                if nv != v: o[k] = nv; stats["urls_fixed"] += 1
            else: walk_urls(v, stats)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and v.startswith("http"):
                nv = fix_url(v)
                if nv != v: o[i] = nv; stats["urls_fixed"] += 1
            else: walk_urls(v, stats)
def main(apply):
    stats = collections.Counter(); touched = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "data/states_chains/*/*.json"))):
        n = json.load(open(f)); st = n.get("state"); before = json.dumps(n, sort_keys=True)
        if st in V and isinstance(n.get("state_agency"), dict):
            for k in ("name", "acronym", "website", "hotline"):
                if V[st].get(k) and n["state_agency"].get(k) != V[st][k]:
                    n["state_agency"][k] = V[st][k]; stats[f"agency.{k}"] += 1
        walk_urls(n, stats)
        for t in n.get("timeline_requirements") or []:
            if (t.get("requirement_name"), t.get("deadline")) in TEMPLATE and t.get("source") in ("state_statute", "court_rule", "admin_rule"):
                t["source"] = "template_estimate"; stats["timeline_relabeled"] += 1
        if json.dumps(n, sort_keys=True) != before:
            touched += 1
            if apply:
                json.dump(n, open(f, "w"), indent=2, ensure_ascii=False); open(f, "a").write("\n")
    print(("APPLIED" if apply else "DRY RUN"), "| files changed:", touched, "|", dict(stats))
if __name__ == "__main__": main("--apply" in sys.argv)
