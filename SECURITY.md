# Security Policy

## This is a legal dataset, not software

This repository contains structured legal data (JSON files with statute citations and legal analysis). It does not contain executable code that runs in production.

However, data integrity is critical. Incorrect legal information could harm families navigating the child welfare system.

## Reporting Data Integrity Issues

If you find incorrect legal citations, fabricated case law, or deliberately misleading information in this dataset:

1. **Open an issue** using the Data Correction template
2. **Email us** at chairman@projectmilkcarton.org with the subject "DATA INTEGRITY"

## What We Consider a Security Issue

- Fabricated statute citations (hallucinated law)
- Deliberately misleading legal analysis
- Injection of non-legal content into data files
- Modification of the schema to weaken validation

## Review Process

All contributions are reviewed by Project Milk Carton maintainers before merge. We verify:

1. Every citation references a real statute or court decision
2. Source URLs point to authoritative legal databases
3. JSON validates against our schema
4. No unauthorized modifications to schemas or federal baselines
