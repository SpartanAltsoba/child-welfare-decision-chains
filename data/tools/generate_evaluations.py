#!/usr/bin/env python3
"""
Evaluation Capsule Generator
Analyzes CPS decision chain nodes against constitutional and federal planes.
Generates evaluation capsules for training data.

Usage:
    python generate_evaluations.py              # Generate for all states
    python generate_evaluations.py --state CA   # Generate for single state
    python generate_evaluations.py --validate   # Validate existing evaluations
"""

import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Paths
ARIA_DIR = Path(".")
DATASET_DIR = ARIA_DIR / "dataset" / "child_welfare_data"
LEGAL_PLANES_DIR = DATASET_DIR / "legal_planes"
STATES_DIR = DATASET_DIR / "states_chains"
OUTPUT_DIR = DATASET_DIR / "evaluations"

# Load reference planes
def load_constitutional_plane() -> Dict:
    with open(LEGAL_PLANES_DIR / "constitutional_plane.json", 'r') as f:
        return json.load(f)

def load_federal_plane() -> Dict:
    with open(LEGAL_PLANES_DIR / "federal_plane.json", 'r') as f:
        return json.load(f)

# Constitutional constraint mapping by node family
CONSTITUTIONAL_TRIGGERS = {
    "INP-01": ["CONST_4A_SEARCH", "CONST_5A_SELF_INCRIMINATION"],
    "INP-02": ["CONST_4A_SEARCH"],
    "INP-03": ["CONST_4A_SEARCH", "CONST_6A_COUNSEL"],
    "INP-04": ["CONST_14A_PROCEDURAL_DP"],
    "INP-05": ["CONST_14A_SUBSTANTIVE_DP"],
    "INP-06": ["CONST_14A_PROCEDURAL_DP"],
    "INP-07": ["CONST_4A_SEARCH", "CONST_5A_SELF_INCRIMINATION"],
    "INP-08": ["CONST_4A_SEARCH"],
    "INP-09": ["CONST_14A_PROCEDURAL_DP"],
    "INP-10": ["CONST_14A_PROCEDURAL_DP"],
    "INP-11": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_EQUAL_PROTECTION"],
    "INP-12": ["CONST_4A_SEIZURE", "CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
    "DEC-01": ["CONST_14A_PROCEDURAL_DP"],
    "DEC-02": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_EQUAL_PROTECTION"],
    "DEC-03": ["CONST_14A_PROCEDURAL_DP"],
    "DEC-04": ["CONST_4A_SEIZURE", "CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
    "DEC-05": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
    "ACT-01": ["CONST_4A_SEIZURE", "CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
    "ACT-02": ["CONST_4A_SEARCH", "CONST_5A_SELF_INCRIMINATION"],
    "ACT-03": ["CONST_14A_PROCEDURAL_DP"],
    "ACT-04": ["CONST_14A_PROCEDURAL_DP"],
    "ACT-05": ["CONST_6A_COUNSEL", "CONST_5A_SELF_INCRIMINATION"],
    "OUT-01": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
    "OUT-02": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP", "CONST_14A_EQUAL_PROTECTION"],
    "OUT-03": ["CONST_14A_PROCEDURAL_DP", "CONST_14A_SUBSTANTIVE_DP"],
}

# Federal requirement mapping by node
FEDERAL_TRIGGERS = {
    "INP-01": ["FED_CAPTA"],
    "INP-02": ["FED_CAPTA"],
    "INP-03": ["FED_VICAA", "FED_ASFA"],
    "INP-04": ["FED_ASFA", "FED_IV_E"],
    "INP-05": ["FED_FFPSA"],
    "INP-06": ["FED_CAPTA"],
    "INP-07": ["FED_CAPTA", "FED_VICAA"],
    "INP-08": ["FED_CAPTA"],
    "INP-09": ["FED_CFSR"],
    "INP-10": ["FED_CAPTA", "FED_CFSR"],
    "INP-11": ["FED_ICWA", "FED_VICAA"],
    "INP-12": ["FED_ASFA", "FED_IV_E", "FED_CFSR"],
    "DEC-01": ["FED_CAPTA", "FED_CFSR"],
    "DEC-02": ["FED_CFSR"],
    "DEC-03": ["FED_FFPSA", "FED_CFSR"],
    "DEC-04": ["FED_ASFA", "FED_IV_E", "FED_ICWA"],
    "DEC-05": ["FED_ASFA", "FED_IV_E", "FED_MEPA", "FED_ICWA"],
    "ACT-01": ["FED_ASFA", "FED_IV_E"],
    "ACT-02": ["FED_CFSR"],
    "ACT-03": ["FED_ASFA", "FED_CFSR"],
    "ACT-04": ["FED_FFPSA", "FED_CFSR"],
    "ACT-05": ["FED_VICAA"],
    "OUT-01": ["FED_ASFA", "FED_FFPSA", "FED_CFSR"],
    "OUT-02": ["FED_ASFA", "FED_IV_E", "FED_MEPA"],
    "OUT-03": ["FED_ASFA", "FED_IV_E"],
}


def calculate_fairness_score(node: Dict, procedural_weight: float) -> Dict:
    """Calculate fairness evaluation for a node."""
    # Base fairness from procedural weight
    base_fairness = procedural_weight

    # Adjust based on node characteristics
    notice_quality = 0.5  # Default
    hearing_adequacy = 0.5
    reversibility = 0.5
    representation = 0.5

    # Nodes with higher procedural weight have better due process
    if procedural_weight >= 0.5:
        notice_quality = min(1.0, procedural_weight + 0.2)
        hearing_adequacy = min(1.0, procedural_weight + 0.1)
        representation = min(1.0, procedural_weight + 0.1)

    # Emergency nodes have lower reversibility
    node_id = node.get('subnode', '')
    if 'INP-12' in node_id or 'DEC-04' in node_id or 'ACT-01' in node_id:
        reversibility = 0.3
        notice_quality = max(0.2, notice_quality - 0.3)

    # Calculate overall score
    score = (notice_quality + hearing_adequacy + reversibility + representation) / 4

    return {
        "score": round(score, 2),
        "components": {
            "notice_quality": round(notice_quality, 2),
            "hearing_adequacy": round(hearing_adequacy, 2),
            "time_to_review": "72 hours" if procedural_weight < 0.4 else "30 days",
            "reversibility": round(reversibility, 2),
            "evidence_standard": "preponderance" if procedural_weight < 0.6 else "clear_and_convincing",
            "representation_access": round(representation, 2)
        },
        "rationale": generate_fairness_rationale(node, score)
    }


def generate_fairness_rationale(node: Dict, score: float) -> str:
    """Generate human-readable fairness rationale."""
    node_id = node.get('subnode', '')
    trigger_name = node.get('trigger_name', node.get('decision_name', node.get('action_name', '')))

    if score >= 0.7:
        return f"{trigger_name} provides adequate procedural protections with meaningful notice and opportunity to be heard."
    elif score >= 0.5:
        return f"{trigger_name} has moderate procedural protections but may have gaps in notice or hearing adequacy."
    elif score >= 0.3:
        return f"{trigger_name} has limited procedural protections; action may occur before meaningful review."
    else:
        return f"{trigger_name} has minimal procedural protections; constitutional due process concerns exist."


def calculate_structural_advantage(node: Dict, procedural_weight: float) -> Dict:
    """Determine which actor the decision structure advantages."""
    node_id = node.get('subnode', '')

    # Default to agency advantage (most common in CPS)
    beneficiary = "agency"
    confidence = 0.7
    lock_in_risk = False
    drivers = []

    # Emergency/removal nodes heavily favor agency
    if any(x in node_id for x in ['INP-12', 'DEC-04', 'ACT-01']):
        beneficiary = "agency"
        confidence = 0.9
        lock_in_risk = True
        drivers = [
            "Action occurs before judicial review",
            "Burden shifts to parent to regain custody",
            "Time asymmetry favors agency (child placed before hearing)",
            "Information asymmetry (agency has case file, parent does not)"
        ]

    # Court-ordered nodes are more neutral
    elif 'INP-04' in node_id or procedural_weight >= 0.55:
        beneficiary = "neutral"
        confidence = 0.6
        drivers = ["Judicial oversight present", "Both parties can present evidence"]

    # Prevention/voluntary nodes may favor family
    elif 'INP-05' in node_id:
        beneficiary = "parent"
        confidence = 0.6
        drivers = ["Voluntary participation", "Family-directed services", "No removal"]

    return {
        "beneficiary": beneficiary,
        "confidence": round(confidence, 2),
        "drivers": drivers,
        "lock_in_risk": lock_in_risk,
        "asymmetries": {
            "information": "Agency has access to full case file; parent has limited access" if beneficiary == "agency" else "Information relatively balanced",
            "resources": "Agency has institutional resources and legal support" if beneficiary == "agency" else "Resources vary",
            "timing": "Agency can act before hearing; parent must wait for review" if lock_in_risk else "Timing relatively balanced"
        }
    }


def calculate_constitutional_alignment(node: Dict, const_plane: Dict) -> Dict:
    """Evaluate node against constitutional plane."""
    node_id = node.get('subnode', '')
    base_node = node_id.split('_')[-1] if '_' in node_id else node_id
    procedural_weight = node.get('procedural_weight', 0.5)

    triggered = CONSTITUTIONAL_TRIGGERS.get(base_node, ["CONST_14A_PROCEDURAL_DP"])
    constraints = {c['constraint_id']: c for c in const_plane.get('constraints', [])}

    evaluations = []
    for constraint_id in triggered:
        constraint = constraints.get(constraint_id, {})

        # Determine alignment based on procedural weight and constraint type
        if 'SEIZURE' in constraint_id or 'SUBSTANTIVE' in constraint_id:
            if procedural_weight < 0.4:
                alignment = "tension"
                risk_factors = ["Action may occur without warrant", "Limited pre-deprivation hearing"]
            else:
                alignment = "conditional"
                risk_factors = ["Requires proper exigency finding"]
        else:
            alignment = "conditional" if procedural_weight < 0.5 else "aligned"
            risk_factors = [] if alignment == "aligned" else ["Procedural adequacy depends on execution"]

        evaluations.append({
            "constraint_id": constraint_id,
            "constraint_name": constraint.get('name', constraint_id),
            "alignment": alignment,
            "rationale": f"Procedural weight {procedural_weight} indicates {'adequate' if procedural_weight >= 0.5 else 'limited'} due process.",
            "risk_factors": risk_factors
        })

    # Overall alignment is the worst of individual alignments
    alignment_order = ["aligned", "conditional", "tension", "violation"]
    overall = "aligned"
    for e in evaluations:
        if alignment_order.index(e['alignment']) > alignment_order.index(overall):
            overall = e['alignment']

    return {
        "overall_alignment": overall,
        "constraints_triggered": evaluations,
        "procedural_weight": procedural_weight,
        "due_process_score": round(min(1.0, procedural_weight + 0.2), 2)
    }


def calculate_federal_alignment(node: Dict, fed_plane: Dict) -> Dict:
    """Evaluate node against federal plane."""
    node_id = node.get('subnode', '')
    base_node = node_id.split('_')[-1] if '_' in node_id else node_id
    fed_flag = node.get('federal_alignment_flag', 'meets')

    triggered = FEDERAL_TRIGGERS.get(base_node, ["FED_CFSR"])
    requirements = {r['requirement_id']: r for r in fed_plane.get('requirements', [])}

    evaluations = []
    for req_id in triggered:
        req = requirements.get(req_id, {})

        # Use the node's federal_alignment_flag
        alignment = fed_flag if fed_flag in ['baseline', 'meets', 'exceeds', 'below'] else 'meets'
        funding_risk = alignment == 'below'

        evaluations.append({
            "requirement_id": req_id,
            "requirement_name": req.get('name', req_id),
            "alignment": alignment,
            "rationale": f"State implementation {'meets' if alignment != 'below' else 'falls below'} federal floor.",
            "funding_risk": funding_risk
        })

    return {
        "overall_alignment": fed_flag,
        "requirements_applicable": evaluations
    }


def generate_obligations(node: Dict) -> Dict:
    """Generate actor obligations for this node."""
    node_id = node.get('subnode', '')
    trigger_name = node.get('trigger_name', node.get('decision_name', ''))

    # Base obligations that apply to most nodes
    agency_obligations = [
        "Act within statutory authority",
        "Document actions and basis",
        "Provide notice to affected parties"
    ]

    parent_obligations = [
        "Respond to agency contact",
        "Participate in required proceedings"
    ]

    parent_rights = [
        "Due process before deprivation",
        "Notice of allegations",
        "Right to hearing"
    ]

    court_obligations = [
        "Ensure due process",
        "Make required findings"
    ]

    # Customize based on node type
    if 'INP-12' in node_id or 'DEC-04' in node_id:
        agency_obligations.extend([
            "Document exigent circumstances",
            "Seek judicial review within statutory timeframe",
            "Make reasonable efforts finding"
        ])
        parent_rights.extend([
            "Shelter hearing within 24-72 hours",
            "Right to counsel",
            "Right to confront evidence"
        ])
        court_obligations.extend([
            "Conduct timely shelter hearing",
            "Make reasonable efforts determination"
        ])

    return {
        "agency": {
            "obligations": agency_obligations,
            "satisfaction_checkable": True,
            "accountability_mechanism": "CFSR review; court oversight; complaint mechanisms"
        },
        "parent": {
            "obligations": parent_obligations,
            "rights_at_stake": parent_rights
        },
        "court": {
            "obligations": court_obligations,
            "findings_required": ["Reasonable efforts", "Continued necessity"] if 'DEC' in node_id or 'ACT' in node_id else []
        },
        "reporter": {
            "obligations": ["Report in good faith"] if 'INP' in node_id else [],
            "protections": ["Immunity for good-faith reports", "Confidentiality"] if 'INP' in node_id else []
        }
    }


def generate_oversight(node: Dict) -> Dict:
    """Generate oversight analysis for this node."""
    node_id = node.get('subnode', '')
    procedural_weight = node.get('procedural_weight', 0.5)

    triggers = ["Court review", "Supervisory review"]
    activation = 0.7
    suppression_risk = False
    suppression_factors = []

    if procedural_weight < 0.4:
        triggers.extend(["Emergency judicial review", "CFSR monitoring"])
        activation = 0.5
        suppression_risk = True
        suppression_factors = [
            "Time pressure may bypass review",
            "Rubber-stamp judicial approval",
            "Resource constraints limit oversight"
        ]

    return {
        "expected_triggers": triggers,
        "activation_likelihood": round(activation, 2),
        "suppression_risk": suppression_risk,
        "suppression_factors": suppression_factors
    }


def generate_advocacy_hooks(node: Dict) -> List[Dict]:
    """Generate parent advocacy leverage points."""
    node_id = node.get('subnode', '')
    hooks = []

    # Universal hooks
    hooks.append({
        "hook": "Request all documentation",
        "legal_basis": "State public records laws; due process",
        "effectiveness": "high",
        "timing": "Immediately upon contact"
    })

    hooks.append({
        "hook": "Document all interactions",
        "legal_basis": "Evidence preservation for potential § 1983 action",
        "effectiveness": "high",
        "timing": "Ongoing"
    })

    # Node-specific hooks
    if 'INP-12' in node_id or 'DEC-04' in node_id:
        hooks.extend([
            {
                "hook": "Demand shelter hearing within statutory timeframe",
                "legal_basis": "State statute; 14th Amendment due process",
                "effectiveness": "high",
                "timing": "Immediately upon removal"
            },
            {
                "hook": "Challenge exigent circumstances finding",
                "legal_basis": "4th Amendment; state statute",
                "effectiveness": "medium",
                "timing": "At shelter hearing"
            },
            {
                "hook": "Request reasonable efforts documentation",
                "legal_basis": "ASFA; 42 U.S.C. § 671",
                "effectiveness": "high",
                "timing": "At every hearing"
            }
        ])

    if 'INP' in node_id:
        hooks.append({
            "hook": "Exercise right to refuse warrantless entry",
            "legal_basis": "4th Amendment",
            "effectiveness": "high",
            "timing": "At initial contact"
        })

    return hooks


def generate_evaluation_capsule(node: Dict, state: str, const_plane: Dict, fed_plane: Dict) -> Dict:
    """Generate complete evaluation capsule for a node."""
    node_id = node.get('subnode', '')
    procedural_weight = node.get('procedural_weight', 0.5)

    # Determine node family
    family = "INP"
    for f in ["INP", "DEC", "ACT", "OUT", "FAIL", "PMC"]:
        if f in node_id:
            family = f
            break

    return {
        "node_id": f"{state}_{node_id}",
        "state": state,
        "node_family": family,
        "evaluation_timestamp": datetime.now().isoformat(),
        "constitutional_alignment": calculate_constitutional_alignment(node, const_plane),
        "federal_alignment": calculate_federal_alignment(node, fed_plane),
        "fairness": calculate_fairness_score(node, procedural_weight),
        "structural_advantage": calculate_structural_advantage(node, procedural_weight),
        "obligations": generate_obligations(node),
        "oversight": generate_oversight(node),
        "advocacy_hooks": generate_advocacy_hooks(node)
    }


def process_state(state_code: str, const_plane: Dict, fed_plane: Dict) -> List[Dict]:
    """Process all nodes for a single state."""
    state_dir = STATES_DIR / state_code
    if not state_dir.exists():
        print(f"  Warning: State directory not found: {state_dir}")
        return []

    evaluations = []

    # Process each node file
    file_patterns = [
        (f'1_{state_code}_inp_nodes.json', 'nodes'),
        (f'2_{state_code}_dec_nodes.json', 'nodes'),
        (f'3_{state_code}_act_nodes.json', 'nodes'),
        (f'4_{state_code}_out_nodes.json', 'nodes'),
        (f'5_{state_code}_fail_nodes.json', 'nodes'),
        (f'6_{state_code}_pmc_nodes.json', 'nodes'),
    ]

    for filename, nodes_key in file_patterns:
        filepath = state_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                nodes = data.get(nodes_key, [])
                for node in nodes:
                    capsule = generate_evaluation_capsule(node, state_code, const_plane, fed_plane)
                    evaluations.append(capsule)
            except Exception as e:
                print(f"    Error processing {filename}: {e}")

    return evaluations


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation capsules for CPS decision chains")
    parser.add_argument("--state", help="Process single state (e.g., CA, TX)")
    parser.add_argument("--validate", action="store_true", help="Validate existing evaluations")
    args = parser.parse_args()

    print("=" * 60)
    print("EVALUATION CAPSULE GENERATOR")
    print("=" * 60)
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load reference planes
    print("Loading reference planes...")
    const_plane = load_constitutional_plane()
    fed_plane = load_federal_plane()
    print(f"  Constitutional constraints: {len(const_plane.get('constraints', []))}")
    print(f"  Federal requirements: {len(fed_plane.get('requirements', []))}")
    print()

    # Determine states to process
    if args.state:
        states = [args.state.upper()]
    else:
        states = sorted([d.name for d in STATES_DIR.iterdir() if d.is_dir()])

    print(f"Processing {len(states)} states...")
    print()

    all_evaluations = []

    for state in states:
        print(f"  Processing {state}...")
        evaluations = process_state(state, const_plane, fed_plane)

        if evaluations:
            # Save state-specific file
            output_file = OUTPUT_DIR / f"{state}_evaluations.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "state": state,
                    "generated": datetime.now().isoformat(),
                    "evaluation_count": len(evaluations),
                    "evaluations": evaluations
                }, f, indent=2)

            all_evaluations.extend(evaluations)
            print(f"    Generated {len(evaluations)} evaluation capsules")

    # Save combined file
    combined_file = OUTPUT_DIR / "all_evaluations.json"
    with open(combined_file, 'w') as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "total_evaluations": len(all_evaluations),
            "states_processed": len(states),
            "evaluations": all_evaluations
        }, f, indent=2)

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total evaluations: {len(all_evaluations)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()


if __name__ == "__main__":
    main()
