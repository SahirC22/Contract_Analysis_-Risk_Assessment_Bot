"""
risk_rules.py

Rule-based risk scoring to complement LLM analysis.
Helps reduce over-reliance on opaque model decisions and
keeps risk assessment grounded and explainable.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import re


RISK_LEVELS = ["Low", "Medium", "High"]


@dataclass
class RuleMatch:
    rule_id: str
    description: str
    risk_level: str


# Simple keyword/regex-based rules.
# All rules ONLY inspect contractual content (liability, termination, etc.)
# and avoid anything related to personal or demographic attributes.
RULES: Dict[str, Dict] = {
    "unlimited_liability": {
        "pattern": re.compile(r"\bunlimited liability\b|\bwithout limit of liability\b|\bliable for all damages\b", re.IGNORECASE),
        "risk_level": "High",
        "description": "Unlimited or unbounded liability for one party.",
    },
    "one_sided_indemnity": {
        "pattern": re.compile(r"shall indemnify.+(and hold harmless|from and against all claims)", re.IGNORECASE),
        "risk_level": "High",
        "description": "Strong one-sided indemnity in favour of one party.",
    },
    "no_termination_clause": {
        # handled at contract summary level; here only for very explicit text
        "pattern": re.compile(r"may not terminate|no right to terminate", re.IGNORECASE),
        "risk_level": "High",
        "description": "Explicitly removes right to terminate the agreement.",
    },
    "automatic_renewal": {
        "pattern": re.compile(r"automatically renews|auto\-renew|shall be renewed automatically", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Automatic renewal without explicit opt-in.",
    },
    "broad_ip_assignment": {
        "pattern": re.compile(r"assigns all intellectual property|all rights, title and interest", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Very broad assignment of intellectual property rights.",
    },
    "vague_payment_terms": {
        "pattern": re.compile(r"payment.*(as mutually agreed|from time to time)", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Unclear or vague payment terms.",
    },
    "penalty_interest_high": {
        "pattern": re.compile(r"interest rate.*(3[0-9]|[4-9][0-9])\s?%", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Very high interest/penalty rates.",
    },
    "ambiguous_terms": {
        "pattern": re.compile(r"\breasonable efforts\b|\bcommercially reasonable\b|\bbest efforts\b|\bto the extent possible\b", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Ambiguous or subjective obligation wording, which may weaken enforceability or expectations.",
    },
    "unilateral_termination": {
        "pattern": re.compile(r"may terminate (this )?agreement at any time( without notice)?", re.IGNORECASE),
        "risk_level": "High",
        "description": "Termination rights granted to only one party, creating imbalance and business risk.",
    },
    "broad_confidentiality": {
        "pattern": re.compile(r"\bperpetual confidentiality\b|\bin perpetuity\b|\bwithout time limitation\b", re.IGNORECASE),
        "risk_level": "Medium",
        "description": "Overly broad confidentiality obligations that may restrict future business operations.",
    },
}


def evaluate_rules(clause_text: str) -> List[RuleMatch]:
    """
    Return list of rule matches for a given clause.
    """
    if not clause_text or not isinstance(clause_text, str):
        return []
    matches: List[RuleMatch] = []
    text = clause_text.strip()
    for rule_id, spec in RULES.items():
        if spec["pattern"].search(text):
            matches.append(
                RuleMatch(
                    rule_id=rule_id,
                    description=spec["description"],
                    risk_level=spec["risk_level"],
                )
            )
    return matches


def aggregate_risk_from_rules(matches: List[RuleMatch]) -> str:
    """
    Combine multiple rule matches into a single risk level.
    """
    if not matches:
        return "Low"

    if any(m.risk_level == "High" for m in matches):
        return "High"
    if any(m.risk_level == "Medium" for m in matches):
        return "Medium"
    return "Low"