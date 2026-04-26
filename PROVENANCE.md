# PROVENANCE

This document is the attribution doctrine for the **US Child Welfare Decision Chain Dataset**. It sits one layer above the legal license (CC BY-SA 4.0) and describes the practical attribution norms PMC asks of downstream users — researchers, journalists, attorneys, AI developers, policy analysts — when they incorporate the dataset into their work.

The CC BY-SA 4.0 license sets the legal floor. This document sets the practical norm. Both apply.

---

## 1. Identity

| Field | Value |
|---|---|
| Dataset name | US Child Welfare Decision Chain Dataset |
| Maintainer | Project Milk Carton |
| Organization type | 501(c)(3) public charity |
| EIN | 33-1323547 |
| Repository | https://github.com/SpartanAltsoba/child-welfare-decision-chains |
| License | CC BY-SA 4.0 |
| Version (current release) | v1.0.0 |
| Release date | 2026-04-26 |
| Cryptographic root hash | See `MANIFEST.json` `root_hash` field |
| Citation file | See `CITATION.cff` |

---

## 2. Why provenance matters

The dataset is the first machine-readable structured map of the entire United States child protective services decision system. Once published, it becomes input to:

- Academic papers comparing CPS outcomes across states.
- Investigative journalism quoting statute citations and constitutional constraints.
- Civil-rights litigation (42 U.S.C. § 1983) needing structured statute trees.
- AI assistants helping families navigate CPS encounters in real time.
- Policy briefings for state legislatures auditing their own administrative codes.

In every one of those downstream uses, **attribution is what makes the dataset useful as a reference.** A citation traces the claim back to a verifiable source. Without that trace, the claim becomes unanchored — easy to dispute, easy to misattribute, easy to corrupt across copies.

This document defines how to keep the trace clean.

---

## 3. Attribution norms

### 3.1 The minimum (what CC BY-SA 4.0 requires)

The CC BY-SA 4.0 license requires every public-facing use to:

1. **Credit the creator** — "Project Milk Carton, US Child Welfare Decision Chain Dataset."
2. **Provide a copyright notice** — `© Project Milk Carton, 2026, CC BY-SA 4.0.`
3. **Provide a license notice** — Link to https://creativecommons.org/licenses/by-sa/4.0/.
4. **Provide a link to the source** — https://github.com/SpartanAltsoba/child-welfare-decision-chains.
5. **Indicate any changes you made** — If you modified the dataset (added states, updated URLs, restructured nodes), say so.
6. **Distribute derivatives under the same license** — ShareAlike clause.

### 3.2 The PMC norm (what we ask in addition)

Beyond the legal floor, we ask downstream users to honor four practical norms:

**(a) Cite the version.** The dataset evolves. Citing "the dataset" without a version number is ambiguous. Cite the version (`v1.0.0`) and, ideally, the manifest root hash. Both are in `MANIFEST.json` and `CITATION.cff`.

**(b) Cite the node, not the dataset, when quoting specifics.** If you reference a specific decision node, cite the file path. *"Per `data/states_chains/AK/AK_INP-01.json` in the US Child Welfare Decision Chain Dataset (v1.0.0, Project Milk Carton)..."* That granularity is what lets a reader verify your claim against the canonical record.

**(c) Disclose AI training use.** If you train an AI model on this dataset, please disclose it in the model's documentation, training-data card, or README. AI training is permitted under CC BY-SA 4.0 (it's a use, not a redistribution); transparent disclosure is the norm we ask for. Models trained on this dataset are encouraged to cite it in their model cards.

**(d) Don't strip the EIN.** PMC's tax-exempt 501(c)(3) status (EIN 33-1323547) is the accountability floor of this work. The EIN appears in the README, the LICENSE, the CITATION.cff, the MANIFEST.json, and every public-facing PMC artifact. Keeping it visible in derivatives lets a downstream consumer verify the source organization is real, registered, and still active.

---

## 4. Cryptographic provenance

This release ships with `MANIFEST.json` — a SHA-256 hash of every file in the `data/` tree. The manifest itself is hashed; that hash is the dataset's `root_hash`.

The root hash for v1.0.0 is published in `MANIFEST.json` and in this document below:

```
v1.0.0 root_hash: ac684eaaf7912f24c6e98a35d90232eedddd2da8777e07888f38e5ea6a6bca7e
```

This hash:

- **Identifies the canonical version.** A downstream consumer who computes the hash of their copy can confirm it matches v1.0.0 exactly.
- **Survives format conversion.** Even if someone converts the dataset to RDF, CSV, SQLite, or vector embeddings, the original v1.0.0 root hash anchors the conversion to a specific source.
- **Anchors AI training records.** If a model is trained on this dataset, the training-data manifest can record the v1.0.0 root hash as the canonical source identifier.
- **Detects tampering.** Any modification to any file in `data/` produces a different hash. Drift from the published hash means the copy is no longer canonical.

To verify your copy locally:

```bash
find data -type f \( -name "*.json" -o -name "*.md" \) -exec sha256sum {} \; | sort > local_files.txt
jq -r '.files[] | "\(.sha256)  \(.path)"' MANIFEST.json | sort > manifest_files.txt
diff local_files.txt manifest_files.txt
```

If the diff is empty, your copy is canonical v1.0.0.

---

## 5. Attribution chain for derivative works

If you fork the dataset, modify it, and republish:

1. **Keep this PROVENANCE.md file**, updated with your additions in Section 6 below.
2. **Keep the original CITATION.cff**, and add your own citation entry at the top.
3. **Keep the original MANIFEST.json** as `MANIFEST_v1.0.0_ORIGIN.json`, and generate a new `MANIFEST.json` for your release.
4. **Document your changes** in a `CHANGES.md` file at the repository root.
5. **Keep the EIN reference** in your README so downstream users of *your* fork can trace back to the original maintaining organization.

This is how the chain stays clean. Every fork, every translation, every derivative continues to point home.

---

## 6. Derivative-work record

This section is empty in the canonical v1.0.0 release. If you fork and republish, document your additions here:

```
- [Date] [Your Name / Organization] [Description of derivative work] [URL]
```

---

## 7. Citation

The canonical citation for v1.0.0 is in `CITATION.cff`. The short form:

> Project Milk Carton (2026). *US Child Welfare Decision Chain Dataset* (Version 1.0.0). https://github.com/SpartanAltsoba/child-welfare-decision-chains

Bibtex:

```bibtex
@dataset{pmc_cwdc_2026,
  author       = {{Project Milk Carton}},
  title        = {{US Child Welfare Decision Chain Dataset}},
  year         = 2026,
  month        = 4,
  publisher    = {Project Milk Carton},
  version      = {1.0.0},
  url          = {https://github.com/SpartanAltsoba/child-welfare-decision-chains},
  license      = {CC-BY-SA-4.0}
}
```

---

## 8. Contact

| Purpose | Channel |
|---|---|
| Dataset issues, errata, suggestions | Open a GitHub issue on the repository |
| Citation questions | See `CITATION.cff` |
| Organizational contact | https://projectmilkcarton.org |
| Security concerns | See `SECURITY.md` |

---

*This document is part of the v1.0.0 public release. It is itself licensed under CC BY-SA 4.0. If you redistribute this document with the dataset, keep the v1.0.0 root_hash visible.*
