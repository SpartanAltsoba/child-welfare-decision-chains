#!/usr/bin/env python3
"""v1.1.0 case-law rebuild pipeline — one implementation, two homes.

Per jurisdiction: research -> adversarial verify -> reconcile -> supplement -> re-verify -> reconcile.
Agents work only from CourtListener opinion text; every stage returns structured JSON; this script writes the
brief and digest, and (with --apply) rewrites layers.case_law through apply_caselaw_brief.py.

Runs on the Claude Agent SDK (>= 0.2.157; older versions return no structured output with the current CLI). With ANTHROPIC_API_KEY set (GitHub Actions) it bills the key; without it,
locally, it uses the logged-in Claude Code plan. Same prompts, same checks, same output.

Usage:
  COURTLISTENER_TOKEN=... python3 pipeline.py --states AK,AL --briefs data/tools/qa/caselaw/briefs [--apply] [--parallel 3]
Env: CASELAW_MODEL (default opus), CASELAW_BUDGET_USD per stage (default 25; API only), CASELAW_MAX_TURNS (default 150).
"""
import argparse
import asyncio
import datetime
import json
import os
import subprocess
import sys

# The Agent SDK launches the Claude Code CLI as a child process. Inside an interactive Claude Code session the CLI
# refuses to start ("cannot be launched inside another Claude Code session"); the documented bypass is to drop the
# session marker for the child. Harmless in CI, where it is not set.
for _v in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"):
    os.environ.pop(_v, None)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
import prompts  # noqa: E402

TOPICS = os.path.join(HERE, "node_topics.json")
COURTS = os.path.join(HERE, "courtlistener_courts.json")
MODEL = os.environ.get("CASELAW_MODEL", "opus")
BUDGET = float(os.environ.get("CASELAW_BUDGET_USD", "25"))
MAX_TURNS = int(os.environ.get("CASELAW_MAX_TURNS", "150"))


def log(st, msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {st}: {msg}", flush=True)


async def run_stage(st, label, prompt, schema, effort="high"):
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
    opts = ClaudeAgentOptions(
        model=MODEL, effort=effort, max_turns=MAX_TURNS, max_budget_usd=BUDGET,
        allowed_tools=["Bash", "Read"], permission_mode="bypassPermissions", cwd=ROOT,
        env={"COURTLISTENER_TOKEN": os.environ.get("COURTLISTENER_TOKEN", "")},
        output_format={"type": "json_schema", "schema": schema},
        system_prompt="You are a meticulous legal research agent. Follow the instructions exactly and return only the structured object.",
    )
    contract = ("\n\nOUTPUT CONTRACT: your final message must be ONLY one JSON object matching this JSON Schema — "
                "no prose before or after it, no code fences:\n" + json.dumps(schema))
    result = None
    async for m in query(prompt=prompt + contract, options=opts):
        if isinstance(m, ResultMessage):
            result = m
    if result is None or result.is_error:
        raise RuntimeError(f"{st} {label}: stage failed ({getattr(result, 'subtype', 'no result')})")
    out = result.structured_output
    if out is None:
        out = extract_json(result.result or "")
        if out is None:
            raise RuntimeError(f"{st} {label}: no structured output and no JSON object in the final message")
    try:
        import jsonschema
        jsonschema.validate(out, schema)
    except ImportError:
        pass
    except Exception as e:
        raise RuntimeError(f"{st} {label}: output does not match the schema: {str(e)[:200]}")
    log(st, f"{label} done — {result.num_turns} turns, ${result.total_cost_usd or 0:.2f}")
    return out


def extract_json(text):
    """Pull the largest JSON object out of a message (handles code fences and leading prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
    try:
        return json.loads(text[start:text.rfind("}") + 1])
    except json.JSONDecodeError:
        return None


def normalize(brief):
    for c in brief["cases"]:
        if c["citation"].startswith(c["case_name"] + ", "):
            c["citation"] = c["citation"][len(c["case_name"]) + 2:]
    ids = {c["cluster_id"] for c in brief["cases"]}
    for k, v in brief["node_map"].items():
        brief["node_map"][k] = [i for i in v if i in ids]
    return brief


def apply_verdict(brief, verdict):
    bad = {v["cluster_id"] for v in verdict["case_verdicts"] if not v.get("ok")}
    fixes = {v["cluster_id"]: v for v in verdict["case_verdicts"] if v.get("ok")}
    brief["cases"] = [c for c in brief["cases"] if c["cluster_id"] not in bad]
    for c in brief["cases"]:
        f = fixes.get(c["cluster_id"], {})
        if f.get("fixed_citation"):
            c["citation"] = f["fixed_citation"]
        if f.get("fixed_case_name"):
            c["case_name"] = f["fixed_case_name"]
    drops = {v["node"]: set(v.get("drop", [])) for v in verdict["node_verdicts"]}
    for k, v in brief["node_map"].items():
        brief["node_map"][k] = [i for i in v if i not in bad and i not in drops.get(k, set())]
    return normalize(brief)


def digest(brief):
    topics = json.load(open(TOPICS))
    cases = {c["cluster_id"]: c for c in brief["cases"]}
    out = [f"# {brief['state']} — {len(brief['cases'])} authorities, verified {brief['verified_date']}", ""]
    empty = []
    for node, ids in brief["node_map"].items():
        t = topics.get(node, {})
        out.append(f"## {node} · {t.get('trigger', '')}")
        if not ids:
            empty.append(node); out += ["   (no verified authority)", ""]; continue
        for i in ids:
            c = cases[i]; rel = c.get("relevance") or {}
            out += [f"- **{c['case_name']}**, {c['citation']}", f"  Holding: {c['holding']}",
                    f"  Why here: {rel.get(node) or rel.get('*') or ''}", f"  Quote: “{c['quote']}”", f"  {c['url']}"]
        out.append("")
    if brief.get("notes"):
        out += ["## Notes"] + [f"- {n}" for n in brief["notes"]]
    if empty:
        out += ["", "NODES WITHOUT AUTHORITY: " + ", ".join(empty)]
    return "\n".join(out) + "\n"


async def run_state(st, briefs_dir, apply):
    repo = ROOT
    research = prompts.research_federal(repo, TOPICS, COURTS) if st == "US" else prompts.research(st, repo, TOPICS, COURTS)
    b = normalize(await run_stage(st, "research", research, prompts.BRIEF_SCHEMA))
    v = await run_stage(st, "verify", prompts.verify(st, json.dumps(b, indent=1), TOPICS, COURTS), prompts.VERDICT_SCHEMA)
    b = apply_verdict(b, v)                      # reconcile is deterministic here; no model call needed
    missing = v.get("missing_authorities", [])
    b["notes"] = b.get("notes", []) + [f"Missing (for a later pass): {m}" for m in missing]
    verified_ids = [c["cluster_id"] for c in b["cases"]]
    b2 = normalize(await run_stage(st, "supplement", prompts.supplement(st, repo, json.dumps(b, indent=1), json.dumps(missing), TOPICS, COURTS), prompts.BRIEF_SCHEMA))
    # keep every previously verified case exactly as verified; only additions are new
    prev = {c["cluster_id"]: c for c in b["cases"]}
    b2["cases"] = [prev.get(c["cluster_id"], c) for c in b2["cases"]]
    v2 = await run_stage(st, "verify2", prompts.verify(st, json.dumps(b2, indent=1), TOPICS, COURTS, previously_verified=verified_ids), prompts.VERDICT_SCHEMA)
    final = apply_verdict(b2, v2)
    final["notes"] = final.get("notes", []) + [f"Missing (for a later pass): {m}" for m in v2.get("missing_authorities", [])]
    final["verified_date"] = datetime.date.today().isoformat()
    os.makedirs(briefs_dir, exist_ok=True)
    bp = os.path.join(briefs_dir, f"{st}.json")
    json.dump(final, open(bp, "w"), indent=1, ensure_ascii=False)
    open(os.path.join(briefs_dir, f"{st}.md"), "w").write(digest(final))
    per = [len(x) for x in final["node_map"].values()]
    log(st, f"brief saved — {len(final['cases'])} cases, per node min {min(per)} max {max(per)}, empty {[k for k, x in final['node_map'].items() if not x]}")
    if apply:
        cmd = [sys.executable, os.path.join(HERE, "apply_caselaw_brief.py"), bp, "--apply"] + (["--federal"] if st == "US" else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        log(st, r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            raise RuntimeError(f"{st}: apply failed")
    return final


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", required=True)
    ap.add_argument("--briefs", default=os.path.join(HERE, "briefs"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--parallel", type=int, default=3)
    a = ap.parse_args()
    if not os.environ.get("COURTLISTENER_TOKEN"):
        sys.exit("COURTLISTENER_TOKEN is not set")
    states = [s.strip().upper() for s in a.states.split(",") if s.strip()]
    sem = asyncio.Semaphore(a.parallel)
    failures = []

    async def one(st):
        async with sem:
            try:
                await run_state(st, a.briefs, a.apply)
            except Exception as e:
                failures.append(st); log(st, f"FAILED: {e}")

    await asyncio.gather(*(one(s) for s in states))
    print(f"\ndone: {len(states) - len(failures)}/{len(states)} jurisdictions" + (f" | FAILED: {failures}" if failures else ""))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
