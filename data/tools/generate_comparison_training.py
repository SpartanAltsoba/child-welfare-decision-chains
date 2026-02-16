#!/usr/bin/env python3
"""
State Comparison Training Data Generator
Generates training examples that compare CPS procedures between states.

Usage:
    python generate_comparison_training.py                    # Generate all pairs
    python generate_comparison_training.py --pairs 500        # Limit to 500 pairs
    python generate_comparison_training.py --states ME,IN,FL  # Specific states only
"""

import json
import os
import random
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from itertools import combinations

# Paths
ARIA_DIR = Path(".")
DATASET_DIR = ARIA_DIR / "dataset" / "child_welfare_data"
STATES_DIR = DATASET_DIR / "states_chains"
EVALUATIONS_DIR = DATASET_DIR / "evaluations"
TRAINING_OUTPUT = ARIA_DIR / "training" / "data"

# State name mapping
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

# Node type friendly names
NODE_NAMES = {
    "INP-01": "mandatory reporter intake",
    "INP-02": "voluntary/community report intake",
    "INP-03": "law enforcement referral",
    "INP-04": "court-ordered referral",
    "INP-05": "self-report/guardian request",
    "INP-06": "anonymous tip/hotline",
    "INP-07": "medical provider report",
    "INP-08": "educational system report",
    "INP-09": "systemic audit/oversight trigger",
    "INP-10": "screening to investigation escalation",
    "INP-11": "federal/tribal jurisdiction trigger",
    "INP-12": "emergency protective custody",
    "DEC-01": "screening decision",
    "DEC-02": "investigation disposition",
    "DEC-03": "service track assignment",
    "DEC-04": "removal decision",
    "DEC-05": "permanency decision",
    "DEC-06": "case closure decision",
    "ACT-01": "emergency removal action",
    "ACT-02": "home investigation",
    "ACT-03": "case plan development",
    "ACT-04": "service provision",
    "ACT-05": "forensic interview",
    "ACT-06": "placement action",
    "OUT-01": "family reunification",
    "OUT-02": "adoption/guardianship",
    "OUT-03": "aging out/emancipation",
    "OUT-04": "case dismissal",
    "OUT-05": "transfer to another jurisdiction",
    "OUT-06": "family preservation success",
}

# System prompt for training
SYSTEM_PROMPT = """You are ARIA (Artificial Research & Intelligence Assistant), the AI backbone of Project Milk Carton, a 501(c)(3) nonprofit dedicated to missing and exploited children.

You are a CONSTITUTIONAL LAW EXPERT and PARENT ADVOCATE with deep expertise in:
- The CPS Decision Chain methodology developed by Project Milk Carton
- Constitutional protections (4th, 5th, 14th Amendments) as applied to family law
- Federal child welfare requirements (CAPTA, ASFA, Title IV-E, ICWA, FFPSA)
- State-specific child welfare laws and procedures for all 50 states
- Structural power dynamics between government agencies and families
- Specific legal leverage points and advocacy strategies

Your purpose is to EMPOWER FAMILIES with knowledge that helps them:
- Understand their constitutional rights
- Navigate the child welfare system
- Protect themselves from government overreach
- Hold agencies accountable to legal requirements
- Access appropriate legal remedies when rights are violated

You provide EXPERT-LEVEL analysis with specific legal citations, case law references, and actionable strategies. You always advocate for family preservation and constitutional rights."""


def load_state_nodes(state_code: str) -> Dict[str, Dict]:
    """Load all nodes for a state, keyed by subnode ID."""
    nodes = {}
    state_dir = STATES_DIR / state_code

    if not state_dir.exists():
        return nodes

    for json_file in state_dir.glob("*.json"):
        if json_file.name == "statistics":
            continue
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            for node in data.get('nodes', []):
                subnode = node.get('subnode', '')
                nodes[subnode] = node
        except Exception as e:
            print(f"  Warning: Error loading {json_file}: {e}")

    return nodes


def load_state_evaluations(state_code: str) -> Dict[str, Dict]:
    """Load pre-computed evaluations for a state."""
    evals = {}
    eval_file = EVALUATIONS_DIR / f"{state_code}_evaluations.json"

    if not eval_file.exists():
        return evals

    try:
        with open(eval_file, 'r') as f:
            data = json.load(f)
        for ev in data.get('evaluations', []):
            # Extract base node ID (remove state prefix)
            node_id = ev.get('node_id', '')
            base_id = node_id.replace(f"{state_code}_", "")
            evals[base_id] = ev
    except Exception as e:
        print(f"  Warning: Error loading evaluations for {state_code}: {e}")

    return evals


def generate_comparison_question(state1: str, state2: str, node_type: str) -> str:
    """Generate a natural comparison question."""
    name1 = STATE_NAMES.get(state1, state1)
    name2 = STATE_NAMES.get(state2, state2)
    node_name = NODE_NAMES.get(node_type, node_type)

    templates = [
        f"How does {name1}'s {node_name} process compare to {name2}'s?",
        f"What are the differences between {name1} and {name2} in {node_name}?",
        f"Compare {name1} vs {name2} for {node_name} in child welfare cases.",
        f"How do {name1} and {name2} differ in their approach to {node_name}?",
        f"What should I know about {node_name} differences between {name1} and {name2}?",
    ]

    return random.choice(templates)


def format_reporting_obligation(obligation: Dict) -> str:
    """Format reporting obligation for output."""
    parts = []
    if obligation.get('when'):
        parts.append(f"When: {obligation['when']}")
    if obligation.get('to_whom'):
        parts.append(f"To Whom: {obligation['to_whom']}")
    if obligation.get('method'):
        parts.append(f"Method: {obligation['method']}")
    return "\n".join(parts)


def format_constitutional_analysis(const_data: Dict) -> str:
    """Format constitutional alignment data."""
    lines = [f"Overall Constitutional Alignment: {const_data.get('overall_alignment', 'unknown').upper()}"]

    constraints = const_data.get('constraints_triggered', [])
    if constraints:
        lines.append("\nConstitutional Protections Triggered:")
        for c in constraints:
            lines.append(f"\n{c.get('constraint_name', c.get('constraint_id', 'Unknown'))}:")
            lines.append(f"  Status: {c.get('alignment', 'unknown')}")
            if c.get('rationale'):
                lines.append(f"  Analysis: {c['rationale']}")
            if c.get('risk_factors'):
                lines.append("  Risk Factors:")
                for rf in c['risk_factors']:
                    lines.append(f"    - {rf}")

    return "\n".join(lines)


def format_federal_analysis(fed_data: Dict) -> str:
    """Format federal alignment data."""
    lines = [f"Overall Federal Alignment: {fed_data.get('overall_alignment', 'unknown').upper()}"]

    reqs = fed_data.get('requirements_applicable', [])
    if reqs:
        lines.append("\nApplicable Federal Requirements:")
        for r in reqs:
            lines.append(f"\n{r.get('requirement_name', r.get('requirement_id', 'Unknown'))}:")
            lines.append(f"  Compliance: {r.get('alignment', 'unknown')}")
            if r.get('rationale'):
                lines.append(f"  Analysis: {r['rationale']}")

    return "\n".join(lines)


def format_fairness_analysis(fairness: Dict) -> str:
    """Format fairness data."""
    lines = [f"Overall Fairness Score: {fairness.get('score', 0)}/1.0"]

    components = fairness.get('components', {})
    if components:
        lines.append("\nComponent Scores:")
        lines.append(f"  Notice Quality: {components.get('notice_quality', 'N/A')}")
        lines.append(f"  Hearing Adequacy: {components.get('hearing_adequacy', 'N/A')}")
        lines.append(f"  Time to Review: {components.get('time_to_review', 'N/A')}")
        lines.append(f"  Reversibility: {components.get('reversibility', 'N/A')}")
        lines.append(f"  Evidence Standard: {components.get('evidence_standard', 'N/A')}")
        lines.append(f"  Representation Access: {components.get('representation_access', 'N/A')}")

    if fairness.get('rationale'):
        lines.append(f"\nAssessment: {fairness['rationale']}")

    return "\n".join(lines)


def format_advocacy_hooks(hooks: List[Dict]) -> str:
    """Format advocacy strategies."""
    if not hooks:
        return "Standard advocacy strategies apply."

    lines = ["Based on the Decision Chain analysis, here are specific actions you can take:"]
    for i, hook in enumerate(hooks[:5], 1):  # Limit to 5 hooks
        lines.append(f"\n{i}. {hook.get('hook', 'Unknown')}")
        if hook.get('legal_basis'):
            lines.append(f"   Legal Basis: {hook['legal_basis']}")
        if hook.get('effectiveness'):
            lines.append(f"   Effectiveness: {hook['effectiveness']}")
        if hook.get('timing'):
            lines.append(f"   When to Use: {hook['timing']}")

    return "\n".join(lines)


def generate_comparison_response(
    state1: str, state2: str, node_type: str,
    node1: Dict, node2: Dict, eval1: Dict, eval2: Dict
) -> str:
    """Generate a comprehensive comparison response."""
    name1 = STATE_NAMES.get(state1, state1)
    name2 = STATE_NAMES.get(state2, state2)
    node_name = NODE_NAMES.get(node_type, node_type)

    lines = [
        f"Comparing {node_name} between {name1} and {name2}:\n",
        "=" * 60,
        f"\n{name1.upper()} ({state1})",
        "=" * 60,
        "\nOVERVIEW:",
        f"\n{node1.get('summary_html', 'No summary available.')}",
        "\n\nLEGAL AUTHORITY:",
        f"\n{node1.get('authority_html', 'See state statutes.')}",
        "\n\nREPORTING/ACTION REQUIREMENTS:",
        f"\n{format_reporting_obligation(node1.get('reporting_obligation', {}))}",
    ]

    # Add evaluation data if available
    if eval1:
        lines.extend([
            "\n\nCONSTITUTIONAL ANALYSIS:",
            f"\n{format_constitutional_analysis(eval1.get('constitutional_alignment', {}))}",
            "\n\nFEDERAL COMPLIANCE:",
            f"\n{format_federal_analysis(eval1.get('federal_alignment', {}))}",
            "\n\nFAIRNESS ANALYSIS:",
            f"\n{format_fairness_analysis(eval1.get('fairness', {}))}",
        ])

    lines.extend([
        "\n\n" + "=" * 60,
        f"\n{name2.upper()} ({state2})",
        "=" * 60,
        "\nOVERVIEW:",
        f"\n{node2.get('summary_html', 'No summary available.')}",
        "\n\nLEGAL AUTHORITY:",
        f"\n{node2.get('authority_html', 'See state statutes.')}",
        "\n\nREPORTING/ACTION REQUIREMENTS:",
        f"\n{format_reporting_obligation(node2.get('reporting_obligation', {}))}",
    ])

    if eval2:
        lines.extend([
            "\n\nCONSTITUTIONAL ANALYSIS:",
            f"\n{format_constitutional_analysis(eval2.get('constitutional_alignment', {}))}",
            "\n\nFEDERAL COMPLIANCE:",
            f"\n{format_federal_analysis(eval2.get('federal_alignment', {}))}",
            "\n\nFAIRNESS ANALYSIS:",
            f"\n{format_fairness_analysis(eval2.get('fairness', {}))}",
        ])

    # KEY DIFFERENCES section
    lines.extend([
        "\n\n" + "=" * 60,
        "\nKEY DIFFERENCES",
        "=" * 60,
    ])

    # Compare agencies
    agency1 = node1.get('reporting_obligation', {}).get('to_whom', '')
    agency2 = node2.get('reporting_obligation', {}).get('to_whom', '')
    if agency1 != agency2:
        lines.append(f"\nReporting Agency:")
        lines.append(f"  - {name1}: {agency1}")
        lines.append(f"  - {name2}: {agency2}")

    # Compare procedural weights
    pw1 = node1.get('procedural_weight', 0)
    pw2 = node2.get('procedural_weight', 0)
    if pw1 != pw2:
        lines.append(f"\nProcedural Weight (due process protections):")
        lines.append(f"  - {name1}: {pw1}")
        lines.append(f"  - {name2}: {pw2}")
        if pw1 > pw2:
            lines.append(f"  → {name1} provides stronger procedural protections")
        else:
            lines.append(f"  → {name2} provides stronger procedural protections")

    # Compare federal alignment
    fa1 = node1.get('federal_alignment_flag', '')
    fa2 = node2.get('federal_alignment_flag', '')
    if fa1 != fa2:
        lines.append(f"\nFederal Compliance:")
        lines.append(f"  - {name1}: {fa1}")
        lines.append(f"  - {name2}: {fa2}")

    # ADVOCACY section
    lines.extend([
        "\n\n" + "=" * 60,
        "\nADVOCACY STRATEGIES FOR BOTH STATES",
        "=" * 60,
        "\n" + format_advocacy_hooks(eval1.get('advocacy_hooks', []) if eval1 else []),
        "\n\nKEY CONSTITUTIONAL REMINDERS:",
        "\n- Fourth Amendment: You have the right to refuse warrantless entry to your home",
        "- Fifth Amendment: You have the right to remain silent and have an attorney present",
        "- Fourteenth Amendment: You have the right to notice of allegations and due process",
        "- Document everything: names, times, exact statements made",
        "- Be polite but firm in exercising your rights",
    ])

    return "\n".join(lines)


def generate_training_example(
    state1: str, state2: str, node_type: str,
    node1: Dict, node2: Dict, eval1: Dict, eval2: Dict
) -> Dict:
    """Generate a single training example in ChatML format."""
    question = generate_comparison_question(state1, state2, node_type)
    response = generate_comparison_response(state1, state2, node_type, node1, node2, eval1, eval2)

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": response}
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Generate state comparison training data")
    parser.add_argument("--pairs", type=int, default=0, help="Limit number of state pairs (0 = all)")
    parser.add_argument("--states", help="Comma-separated state codes to include")
    parser.add_argument("--nodes", help="Comma-separated node types to include (e.g., INP-01,DEC-01)")
    parser.add_argument("--output", default="aria_comparison_training.jsonl", help="Output filename")
    args = parser.parse_args()

    print("=" * 60)
    print("STATE COMPARISON TRAINING DATA GENERATOR")
    print("=" * 60)
    print()

    # Determine which states to process
    if args.states:
        states = [s.strip().upper() for s in args.states.split(",")]
    else:
        states = sorted([d.name for d in STATES_DIR.iterdir() if d.is_dir()])

    print(f"Processing {len(states)} states...")

    # Load all state data
    state_nodes = {}
    state_evals = {}

    for state in states:
        print(f"  Loading {state}...")
        state_nodes[state] = load_state_nodes(state)
        state_evals[state] = load_state_evaluations(state)

    print()

    # Determine which node types to compare
    if args.nodes:
        node_types = [n.strip().upper() for n in args.nodes.split(",")]
    else:
        # Get all common node types across states
        all_node_types = set()
        for nodes in state_nodes.values():
            all_node_types.update(nodes.keys())
        node_types = sorted(all_node_types)

    print(f"Comparing {len(node_types)} node types...")
    print()

    # Generate state pairs
    state_pairs = list(combinations(states, 2))
    random.shuffle(state_pairs)

    if args.pairs > 0:
        state_pairs = state_pairs[:args.pairs]

    print(f"Generating comparisons for {len(state_pairs)} state pairs...")
    print()

    # Generate training examples
    examples = []

    for i, (state1, state2) in enumerate(state_pairs):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(state_pairs)} pairs...")

        nodes1 = state_nodes.get(state1, {})
        nodes2 = state_nodes.get(state2, {})
        evals1 = state_evals.get(state1, {})
        evals2 = state_evals.get(state2, {})

        # Compare each node type that exists in both states
        for node_type in node_types:
            if node_type in nodes1 and node_type in nodes2:
                example = generate_training_example(
                    state1, state2, node_type,
                    nodes1[node_type], nodes2[node_type],
                    evals1.get(node_type, {}), evals2.get(node_type, {})
                )
                examples.append(example)

    print()
    print(f"Generated {len(examples)} training examples")

    # Write output
    output_file = TRAINING_OUTPUT / args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"Wrote training data to: {output_file}")
    print()

    # Show sample
    if examples:
        print("=" * 60)
        print("SAMPLE TRAINING EXAMPLE")
        print("=" * 60)
        sample = random.choice(examples)
        print(f"\nUSER: {sample['messages'][1]['content']}")
        print(f"\nASSISTANT (first 500 chars):")
        print(sample['messages'][2]['content'][:500] + "...")

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
