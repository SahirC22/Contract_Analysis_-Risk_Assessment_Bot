"""
report.py

Typed dataclasses representing clause-level and contract-level analysis.
Provides JSON serialisation for UI / API.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
import json
from datetime import datetime


@dataclass
class ClauseAnalysis:
    clause_index: int
    original_text: str
    anonymised_text: str
    plain_english_explanation: str
    risk_level_llm: str
    risk_level_rules: str
    risk_level_final: str
    risk_reason_llm: str
    rule_hits: List[Dict[str, str]] = field(default_factory=list)
    suggested_alternative_clause: str = ""
    affected_party: str = "unclear"
    final_risk_score: float = 0.0
    negotiation_insight: str = ""

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractSummary:
    business_summary: str
    overall_risk_llm: str
    overall_risk_rules: str
    overall_risk_final: str
    top_risks: List[str]
    missing_critical_clauses: List[str]
    contract_completeness_score: int = 0
    conflicting_clauses: List[str] = field(default_factory=list)
    duplicate_or_ambiguous_terms: List[str] = field(default_factory=list)
    negotiation_insights: List[str] = field(default_factory=list)
    document_length_words: int = 0

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractReport:
    summary: ContractSummary
    clauses: List[ClauseAnalysis]
    anonymisation_map: Dict[str, str]
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    schema_version: str = "1.0"

    def to_json(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_json(),
            "clauses": [c.to_json() for c in self.clauses],
            "anonymisation_map": self.anonymisation_map,
            "analysis_timestamp": self.analysis_timestamp,
            "schema_version": self.schema_version,
        }

    def to_json_str(self, indent: int = 2) -> str:
        return json.dumps(self.to_json(), indent=indent, ensure_ascii=False)