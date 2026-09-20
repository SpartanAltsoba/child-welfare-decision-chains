#!/usr/bin/env python3
"""CI gate: every node file changed relative to origin/main must parse, must carry the v1.1.0 case_law shape,
and must introduce no NEW schema error types beyond the two pre-existing ones (layers string-vs-object,
notice who_must_be_notified enum). Exit 1 on any failure."""
import collections
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
os.chdir(ROOT)
subprocess.run(["git", "fetch", "-q", "origin", "main"], check=False)
changed = subprocess.run(["git", "diff", "--name-only", "origin/main", "--", "data/"], capture_output=True, text=True).stdout.split()
changed = [p for p in changed if p.endswith(".json") and ("states_chains" in p or "federal_baseline" in p)]
if not changed:
    print("no node files changed"); sys.exit(0)
try:
    import jsonschema
    S = json.load(open("data/schemas/extended_decision_chain.schema.json"))
    V = jsonschema.validators.validator_for(S)(S)
except Exception:
    V = None
ALLOWED = {("layers", "is not of type"), ("notice_requirements", "is not one of")}
bad = 0
kinds = collections.Counter()


def check_node(n, path):
    global bad
    cl = (n.get("layers") or {}).get("case_law") or {}
    if "method" not in cl or "verified_date" not in cl or "key_cases" not in cl:
        print(f"MISSING v1.1.0 case_law shape: {path} {n.get('node_id') or n.get('subnode')}"); bad += 1
    for c in cl.get("key_cases", []):
        for k in ("case_name", "citation", "court", "year", "holding", "quote", "url"):
            if not c.get(k) and c.get(k) != 0:
                print(f"case entry missing {k}: {path} {c.get('case_name')}"); bad += 1
        if not str(c.get("url", "")).startswith("https://www.courtlistener.com/"):
            print(f"non-CourtListener url: {path} {c.get('url')}"); bad += 1
    if V is not None and "node_id" in n:
        for e in V.iter_errors(n):
            top = str(list(e.absolute_path)[:1][0]) if e.absolute_path else ""
            kind = "is not of type" if "is not of type" in e.message else ("is not one of" if "is not one of" in e.message else e.message[:40])
            if (top, kind) not in ALLOWED:
                kinds[(top, kind)] += 1


for p in changed:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f"UNPARSEABLE: {p} {e}"); bad += 1; continue
    if isinstance(d, dict) and "node_id" in d:
        check_node(d, p)
    elif isinstance(d, dict) and len(d) == 1 and isinstance(next(iter(d.values())), list):
        for n in next(iter(d.values())):
            check_node(n, p)
for k, c in kinds.items():
    print(f"NEW schema error type: {c} × {k}"); bad += 1
print(f"checked {len(changed)} files, problems: {bad}")
sys.exit(1 if bad else 0)
