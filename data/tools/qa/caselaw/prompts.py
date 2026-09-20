"""Prompts and structured-output schemas for the v1.1.0 case-law rebuild. Single source of truth for the pipeline
(run locally on a Claude plan, or in GitHub Actions on an API key — same prompts either way)."""

API_RULES = """
COURTLISTENER API RULES (a shared budget; other agents may be running at the same time):
- The token is in the environment variable COURTLISTENER_TOKEN. Use it with curl as: -H "Authorization: Token $COURTLISTENER_TOKEN". NEVER print the token or include it in your output.
- Base https://www.courtlistener.com/api/rest/v4/ . Search: /search/?type=o&q=<query>&court=<court_id>[&court=<id2>]&order_by=score%20desc . Cluster: /clusters/<cluster_id>/ (citations, case_name, date_filed, docket). Opinion text: /opinions/<opinion_id>/ (plain_text, else html_with_citations or html; strip tags). Search hits already carry caseName, citation[], court, dateFiled, cluster_id, opinions[].id and a snippet — use them before spending calls on clusters.
- Pace: at most one request every 2 seconds and at most 150 requests for your whole task. On HTTP 429 wait the Retry-After seconds. Never loop on failures.
- State court ids are in {courts_file} (e.g. tex = Texas Supreme Court, texapp = Court of Appeals of Texas). Federal: scotus, and the circuit for the state (ca9, ca5, ca2 ...).
- Justia (law.justia.com) is bot-walled to scripts; do not fetch it. CourtListener is the source for everything.
"""

LAW_RULES = """
LAW-FIRM STANDARD (this dataset is read by lawyers and by families; both must be able to trust every entry):
- NO LAW FROM MEMORY. You may use your knowledge to decide what to SEARCH for, but every case you return must have been retrieved from CourtListener in this session and its opinion text read.
- QUOTE: the court's OWN statement of the rule or holding, from the MAJORITY opinion — never the syllabus, headnotes, a dissent or concurrence, the court's description of a prior case, a party's argument, or the statement of facts. A complete sentence or complete clause carrying the rule WITH its qualifications; never truncate so that a condition or exception drops out. At most 30 words, an exact substring of the opinion text (whitespace and quote marks normalized), no ellipses.
- HOLDING: one sentence stating what the court decided on the point that matters here; it must not invert, broaden or narrow the quote. Re-read the opinion's disposition before writing it.
- Prefer, in order: the jurisdiction's highest court published opinions; published intermediate appellate opinions; the U.S. Supreme Court where the node turns on a federal constitutional or statutory standard; the jurisdiction's federal circuit for § 1983 / removal cases. Avoid unpublished memorandum decisions unless nothing published exists on the point, and say so in notes.
- Leading precedent beats recency. A 1994 state supreme court case that sets the standard outranks a 2025 memorandum that applies it.
- Citation: the official reporter citation(s) from the cluster in Bluebook form WITHOUT the case name — "118 Nev. 737, 58 P.3d 181 (2002)", "455 U.S. 745 (1982)", "577 S.W.3d 230 (Tex. 2019)" (court designator only when the reporter does not identify the court). If the cluster has no reporter citation, slip form: "No. <docket> (<Court abbrev> <Mon. D, YYYY>)". The case name goes in case_name only, as the court styles it (e.g. "In re N.G.").
- Each case entry: cluster_id, case_name, citation, court (full name), court_id, date_decided (YYYY-MM-DD), year, url (the CourtListener opinion page https://www.courtlistener.com/opinion/<opinion_id>/<slug>/ or the cluster page), holding, quote, relevance: an object mapping each node id this case serves to ONE sentence saying why it matters at that decision point (or "*" for a sentence that fits every mapped node).
- Coverage: every one of the 42 nodes gets 2 to 6 cases. A case may serve several nodes. Aim for 20 to 40 distinct cases per jurisdiction. Do not pad: if a node genuinely has no on-point authority beyond the federal standard, give it the federal standard and say so in notes.
- The existing key_cases in the files are keyword-matched noise (recent listings with synthetic citations). Treat their titles only as candidate names to look up; keep one only if you retrieved it and it is on point.
"""

NODES = "INP-01..12, DEC-01..06, ACT-01..06, OUT-01..06, FAIL-01..06, PMC-01..06"


def research(st, repo, topics_file, courts_file):
    return f"""You are building the case-law layer for jurisdiction {st} in the public dataset github.com/SpartanAltsoba/child-welfare-decision-chains (v1.1.0). Local clone: {repo}. Do NOT edit any file in the repo; return a structured brief only.

WHAT THE 42 DECISION POINTS ARE: read {topics_file} (node id → family, trigger name, one-line summary). Read three or four of the jurisdiction's own node files ({repo}/data/states_chains/{st}/{st}_INP-01.json, {st}_DEC-03.json, {st}_ACT-03.json, {st}_OUT-04.json, {st}_FAIL-02.json) for the statutes and definitions the nodes rest on, and skim the existing layers.case_law.key_cases titles across the {st} files (candidate names only).

RESEARCH PLAN: for each family, run targeted CourtListener searches in the jurisdiction's highest court first, then its intermediate appellate court, for the doctrines that decide each node: reporting duty and reporter immunity; investigation, interviews and consent; Fourth Amendment entry and caseworker searches; emergency removal / exigency; substantiated findings, central registry and due-process hearing rights; adjudication standard and burden; reasonable efforts and case plans; foster placement, kinship preference, sibling placement; ICWA / state ICWA (active efforts, qualified expert witness, placement preferences, transfer); reunification and permanency hearings; termination of parental rights (grounds, clear and convincing, best interests, incarcerated parents, appointed counsel); guardianship and adoption; extended foster care / jurisdiction past 18; appeals, timeliness and ineffective assistance; § 1983 liability for wrongful removal in this jurisdiction's circuit; records confidentiality and disclosure; missing children from care; oversight. Retrieve and read each candidate opinion. Select 2–6 per node.
{LAW_RULES}
{API_RULES.format(courts_file=courts_file)}
Return ONLY the structured brief: state="{st}", verified_date=today's date (YYYY-MM-DD), cases[], node_map (all 42 node ids: {NODES}, each a list of cluster_ids present in cases), notes (what you could not find, any unpublished decisions used and why, anything a lawyer should know)."""


def research_federal(repo, topics_file, courts_file):
    return f"""You are building the case-law layer for the FEDERAL BASELINE (jurisdiction "US") in the public dataset github.com/SpartanAltsoba/child-welfare-decision-chains (v1.1.0). Local clone: {repo}. Do NOT edit any file; return a structured brief only.

The federal baseline has the same 42 decision points as every state (read {topics_file}); its nodes are in {repo}/data/chains/cps/federal_baseline/*_federal_*_nodes.json (id key "subnode"). Read two or three of them for the federal statutes each node rests on (CAPTA, Title IV-E, ASFA, Fostering Connections, ICWA, Family First, the Fourth and Fourteenth Amendments).

RESEARCH PLAN: U.S. Supreme Court first (court=scotus): Santosky v. Kramer; Stanley v. Illinois; Lassiter v. Department of Social Services; Troxel v. Granville; M.L.B. v. S.L.J.; Quilloin v. Walcott; Smith v. Organization of Foster Families; DeShaney v. Winnebago County; Suter v. Artist M.; Mississippi Band of Choctaw Indians v. Holyfield; Adoptive Couple v. Baby Girl; Haaland v. Brackeen; Parham v. J.R.; Prince v. Massachusetts; Meyer v. Nebraska; Pierce v. Society of Sisters; Camreta v. Greene; Maryland v. Craig; Ferguson v. City of Charleston; Gonzaga University v. Doe; Armstrong v. Exceptional Child Center, as they apply. Then the circuit decisions that define caseworker Fourth Amendment and § 1983 liability nationally (retrieve and read them; e.g. Calabretta v. Floyd, Wallis v. Spencer, Mabe v. San Bernardino, Rogers v. County of San Joaquin (9th Cir.); Tenenbaum v. Williams, Southerland v. City of New York (2d Cir.); Croft v. Westmoreland County (3d Cir.); Doe v. Heck (7th Cir.); Gates v. Texas DFPS, Wernecke v. Garcia (5th Cir.); Roska v. Peterson, Hollingsworth v. Hill (10th Cir.); Andrews v. Hickman County (6th Cir.)) — include only those you retrieved and read. Select 2–6 per node; the same Supreme Court case may serve many nodes with node-specific relevance sentences. For purely programmatic nodes (CFSR monitoring, IV-E funding, data systems), cite the cases that define private-enforcement and federalism limits where on point, and say in notes where no case law governs.
{LAW_RULES}
{API_RULES.format(courts_file=courts_file)}
Return ONLY the structured brief: state="US", verified_date=today (YYYY-MM-DD), cases[], node_map (all 42 node ids: {NODES}), notes."""


def verify(st, brief_json, topics_file, courts_file, previously_verified=None):
    prev = ""
    if previously_verified:
        prev = f"\nOnly cases whose cluster_id is NOT in this already-verified list need full checking: {previously_verified}. For already-verified cases return ok=true with why=\"previously verified\".\n"
    return f"""You are the adversarial verifier for the case-law brief for jurisdiction {st}. The brief:

{brief_json}
{prev}
Read {topics_file} for what each node is about. Then REFUTE, case by case, using CourtListener only:
1. GET /clusters/<cluster_id>/ and confirm case_name (the court's styling), citation (official; the string must match a citation the cluster carries, in Bluebook form WITHOUT the case name, or a correct slip form if the cluster has none), court, date_decided, year. If the citation or name is wrong but the case is right, set ok=true and supply fixed_citation / fixed_case_name.
2. GET the opinion text and confirm the quote is an exact substring of the MAJORITY opinion (normalize whitespace and quote marks) and is the court's own statement of the rule with its qualifications — not the syllabus, a dissent, a party's argument, the facts, or the court's description of a prior case — and that the holding is what the court actually held on that point, not inverted, broadened or narrowed.
3. For every node in node_map: are the mapped cases genuinely on point for that decision point? A reporting-duty case mapped to a termination node is not. List cluster_ids to drop per node under node_verdicts[].drop. Flag nodes left with fewer than 2 cases.
4. Under missing_authorities, name the leading {st} authorities a practitioner would expect and that are absent (only ones you are confident exist; each as "Case name, citation — why").
Default to ok=false when uncertain. A wrong citation or an inverted holding in a law firm's brief is a firing offense; treat it that way.
{API_RULES.format(courts_file=courts_file)}
Return ONLY the structured object: state, case_verdicts (one per case), node_verdicts (one per node), missing_authorities."""


def reconcile(st, brief_json, verdict_json):
    return f"""You are the reconciler for the case-law brief for jurisdiction {st}. Brief: {brief_json}. Verdicts: {verdict_json}.

Produce the FINAL brief: remove every case with ok=false (from cases and from every node_map list); apply fixed_citation / fixed_case_name where supplied; remove each node's dropped cluster_ids; keep the relevance sentences for surviving mappings; normalize every citation to Bluebook form WITHOUT the case name. Do not research, do not add cases, do not rewrite holdings. If a node ends with 0 cases, leave it empty and add a note naming the node. Append the verifier's missing_authorities to notes under the prefix "Missing (for a later pass): ". Keep verified_date. No file edits.

Return ONLY the structured brief (same shape as the input brief)."""


def supplement(st, repo, brief_json, missing, topics_file, courts_file):
    return f"""You are closing coverage gaps in the verified case-law brief for jurisdiction {st} (dataset github.com/SpartanAltsoba/child-welfare-decision-chains v1.1.0; local clone {repo}; do not edit repo files). The reconciled brief:

{brief_json}

The verifier named these leading authorities as missing: {missing}. Read {topics_file} for what each node is about.

Do exactly three things, all from CourtListener opinion text retrieved in this session: (1) for each named missing authority, search for it (name + citation; court = the jurisdiction's courts or scotus), retrieve cluster and opinion, read it, and if it is real and on point produce a full case entry with node-specific relevance sentences; (2) for every node with fewer than 2 cases, search for the leading published authority on that decision point (highest court first) and add it if retrieved and on point — if nothing exists beyond the federal standard, map the applicable U.S. Supreme Court case (retrieve it) and say so in notes; (3) return the COMPLETE updated brief: existing cases unchanged, plus additions, node_map extended, notes = existing notes + one line per addition ("Added <case> for <nodes>: <why>") and one line per authority you could not verify.
{LAW_RULES}
{API_RULES.format(courts_file=courts_file)}
Return ONLY the structured brief."""


CASE_SCHEMA = {"type": "object", "properties": {
    "cluster_id": {"type": "integer"}, "case_name": {"type": "string"}, "citation": {"type": "string"},
    "court": {"type": "string"}, "court_id": {"type": "string"}, "date_decided": {"type": "string"}, "year": {"type": "integer"},
    "url": {"type": "string"}, "holding": {"type": "string"}, "quote": {"type": "string"},
    "relevance": {"type": "object", "additionalProperties": {"type": "string"}}},
    "required": ["cluster_id", "case_name", "citation", "court", "court_id", "date_decided", "year", "url", "holding", "quote", "relevance"]}

BRIEF_SCHEMA = {"type": "object", "properties": {
    "state": {"type": "string"}, "verified_date": {"type": "string"},
    "cases": {"type": "array", "items": CASE_SCHEMA},
    "node_map": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "integer"}}},
    "notes": {"type": "array", "items": {"type": "string"}}},
    "required": ["state", "verified_date", "cases", "node_map", "notes"]}

VERDICT_SCHEMA = {"type": "object", "properties": {
    "state": {"type": "string"},
    "case_verdicts": {"type": "array", "items": {"type": "object", "properties": {
        "cluster_id": {"type": "integer"}, "ok": {"type": "boolean"}, "why": {"type": "string"},
        "fixed_citation": {"type": "string"}, "fixed_case_name": {"type": "string"}}, "required": ["cluster_id", "ok", "why"]}},
    "node_verdicts": {"type": "array", "items": {"type": "object", "properties": {
        "node": {"type": "string"}, "ok": {"type": "boolean"}, "why": {"type": "string"},
        "drop": {"type": "array", "items": {"type": "integer"}}}, "required": ["node", "ok", "why", "drop"]}},
    "missing_authorities": {"type": "array", "items": {"type": "string"}}},
    "required": ["state", "case_verdicts", "node_verdicts", "missing_authorities"]}
