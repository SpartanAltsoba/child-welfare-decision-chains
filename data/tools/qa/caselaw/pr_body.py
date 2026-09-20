#!/usr/bin/env python3
"""Build the pull-request body for a case-law batch from the per-jurisdiction digests (kept under GitHub's size limit)."""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
states = [s.strip().upper() for s in sys.argv[1].split(",") if s.strip()]
LIMIT = 60000
parts = [f"## v1.1.0 case-law layer — {', '.join(states)}", "",
         "Every authority below was retrieved from CourtListener and its opinion read; holdings and quotes come from the opinion text; "
         "an independent adversarial pass refetched each case and refuted what it could; a supplement pass closed coverage gaps; "
         "rejected entries were removed before this pull request was opened. Previous keyword-matched listings were replaced. "
         "Method: `data/tools/qa/caselaw/README.md`. Full digests are attached to the workflow run as artifacts.", ""]
for st in states:
    p = os.path.join(HERE, "briefs", f"{st}.md")
    if not os.path.exists(p):
        parts += [f"### {st}", "_no brief produced_", ""]; continue
    txt = open(p).read()
    parts += [txt.replace("# ", "### ", 1), ""]
body = "\n".join(parts)
if len(body) > LIMIT:
    body = body[:LIMIT - 200] + "\n\n_(digest truncated; the complete digests are in the run artifacts)_\n"
body += "\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
print(body)
