# Contributing to the Child Welfare Decision Chain Dataset

Thank you for your interest in improving child welfare transparency in the United States. This dataset exists because every family deserves to know their rights when they interact with the child protective services system.

## How to Contribute

### Priority: 49 State Constitutional Planes (NEEDED)

The single biggest gap in this dataset is **state constitutional provisions**. Only Texas and California are completed. We need 49 more states.

Each state file lives at `data/legal_planes/state_constitutional/{STATE}_constitution.json` and needs:

- State constitutional search & seizure provisions
- Due process provisions
- Any provisions that **exceed** the federal floor
- State supreme court cases interpreting these provisions
- Whether the state provides greater protection than the 4th/14th Amendments

Use `data/legal_planes/state_constitutional/_TEMPLATE.json` as your starting template.
Use `data/legal_planes/state_constitutional/TX_constitution.json` as a completed example.

**Pick a state, fill it in, submit a PR.** Even one state helps.

### Other Ways to Help

1. **Update statute URLs** - Laws change. URLs break. If you find a dead link in any state chain file, fix it.
2. **Add case law** - Find relevant state supreme court decisions on child welfare and add them to the appropriate state chain nodes.
3. **Verify citations** - Cross-check statute citations against current law.
4. **Fill administrative rules** - Add state administrative code citations to chain nodes.
5. **Improve CCDF data** - Update Child Care Development Fund chains with current funding data.

### Quality Standards

**Every contribution must follow these rules:**

1. **REAL CITATIONS ONLY.** Every statute, case, and regulation must be real and verifiable. Include source URLs.
2. **No hallucinated law.** If you're unsure, leave it blank rather than guess. A gap is better than misinformation.
3. **Use .gov or recognized legal databases.** Source URLs must point to official government sites, Cornell LII, CourtListener, Google Scholar, or equivalent.
4. **Follow the schema.** All JSON files must validate against `data/schemas/extended_decision_chain.schema.json`.
5. **One state per PR.** Makes review manageable.

### Data Sources We Trust

| Source | URL | What It Has |
|--------|-----|-------------|
| Child Welfare Information Gateway | childwelfare.gov | Federal and state statutory compilations |
| Cornell Legal Information Institute | law.cornell.edu | Federal statutes, USC |
| CourtListener | courtlistener.com | Court opinions, free API |
| State legislature websites | varies | Primary statutory text |
| Google Scholar | scholar.google.com | Court opinions |
| National Conference of State Legislatures | ncsl.org | Policy comparisons |

### How to Submit

1. Fork this repository
2. Create a branch: `git checkout -b add-{STATE}-constitution` (e.g., `add-NV-constitution`)
3. Make your changes
4. Validate against the schema
5. Submit a pull request with:
   - Which state(s) you updated
   - Sources you used
   - Any notes on ambiguous areas

### Code of Conduct

This is a child welfare dataset. Contributions must be:
- Factually accurate
- Non-partisan
- Focused on legal rights and due process
- Respectful of all families

---

*Project Milk Carton is a 501(c)(3) nonprofit dedicated to raising awareness about missing children and child welfare transparency.*
*https://projectmilkcarton.org*
