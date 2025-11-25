"""
llm_model.py

Wrapper around GPT-4/Claude-style models + integration
with risk_rules and report dataclasses.

Focus on:
- Clear prompts
- Explicit fairness / anti-bias instructions
- Hybrid LLM + rule-based risk assessment
- Robust error handling and retry logic
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import logging
import time
from openai import OpenAI, APIError, RateLimitError, APIConnectionError

try:
    from .risk_rules import evaluate_rules, aggregate_risk_from_rules
    from .report import ClauseAnalysis, ContractSummary, ContractReport
except ImportError:
    from risk_rules import evaluate_rules, aggregate_risk_from_rules
    from report import ClauseAnalysis, ContractSummary, ContractReport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BIAS_SAFETY_INSTRUCTIONS = """
You MUST avoid any form of discrimination or bias.
Base your assessment ONLY on the contractual content:
- obligations
- rights
- liabilities
- payment terms
- termination conditions
- intellectual property
- dispute resolution

NEVER allow parties' names, nationalities, genders, ethnicities,
or other demographic hints to influence the risk assessment.
If such attributes appear, treat them as neutral placeholders.
"""

@dataclass
class LLMConfig:
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.15
    max_tokens: int = 2000
    max_retries: int = 3
    retry_delay: float = 2.0


class ContractAnalyzer:
    def __init__(self, api_key: str, config: LLMConfig | None = None):
        self.client = OpenAI(api_key=api_key)
        self.config = config or LLMConfig()

    # ------------- LLM HELPERS WITH RETRY LOGIC -------------
    def _chat(self, system: str, user: str, max_retries: Optional[int] = None) -> str:
        """
        Make LLM API call with retry logic and better error handling.
        """
        retries = max_retries if max_retries is not None else self.config.max_retries
        last_error = None
        
        for attempt in range(retries):
            try:
                logger.info(f"API call attempt {attempt + 1}/{retries}")
                
                resp = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=60.0,  # 60 second timeout
                )
                
                content = resp.choices[0].message.content
                
                if not content or not content.strip():
                    raise ValueError("Empty response from API")
                
                logger.info(f"API call successful on attempt {attempt + 1}")
                return content.strip()
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
            except APIConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < retries - 1:
                    time.sleep(self.config.retry_delay)
                    
            except APIError as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < retries - 1:
                    time.sleep(self.config.retry_delay)
                    
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < retries - 1:
                    time.sleep(self.config.retry_delay)
        
        # All retries failed
        logger.error(f"All {retries} attempts failed. Last error: {last_error}")
        raise Exception(f"LLM API call failed after {retries} attempts: {last_error}")

    def _parse_json_response(self, raw_response: str, fallback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely parse JSON response with fallback.
        """
        if not raw_response or not raw_response.strip():
            logger.warning("Empty response received, using fallback")
            return fallback_data
        
        # Normalize response and remove markdown code fences if present
        cleaned = raw_response.strip()
        
        # Remove common markdown code fences like `````` or ``````
        if cleaned.startswith("```"):
            cleaned = cleaned[len("```json"):].strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        
        # Also remove single backtick code snippets if they wrap JSON
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1].strip()
        
        try:
            parsed = json.loads(cleaned)
            logger.info("Successfully parsed JSON response")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            logger.warning(f"Raw response: {raw_response[:500]}")
            
            # Try to find JSON object substring in the cleaned text
            try:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = cleaned[start:end]
                    parsed = json.loads(json_str)
                    logger.info("Extracted JSON from response")
                    return parsed
            except Exception:
                pass
            
            logger.warning("Using fallback data")
            return fallback_data

    # ------------- CLAUSE ANALYSIS -------------
    def analyze_clause(
        self, clause_text: str, clause_index: int, anonymised_text: str, language: str = "English"
    ) -> ClauseAnalysis:
        """
        Run hybrid (LLM + rules) analysis for a single clause.
        """
        # Skip empty or very short clauses
        if not clause_text or len(clause_text.strip()) < 10:
            logger.warning(f"Clause {clause_index} is too short or empty")
            return self._create_fallback_clause_analysis(clause_index, clause_text, anonymised_text)
        
        # Run rule-based analysis first
        rule_matches = evaluate_rules(clause_text)
        rules_risk = aggregate_risk_from_rules(rule_matches)

        lang_instruction = (
            "Explanations and suggestions must be in English."
            if language == "English"
            else "Explanations and suggestions must be in Hindi. Keep risk labels in English."
        )

        system_msg = (
            "You are an expert contract lawyer helping small and medium "
            "businesses in India understand contracts. "
            "Always respond with VALID JSON only, no other text. "
        ) + BIAS_SAFETY_INSTRUCTIONS + "\n" + lang_instruction

        user_prompt = f"""
Analyze this contract clause:

\"\"\"{clause_text}\"\"\"

Return ONLY valid JSON (no markdown, no extra text):
{{
  "plain_english_explanation": "Clear explanation of what this clause means in simple business terms",
  "risk_level": "Low | Medium | High",
  "risk_reason": "Specific reason for the risk rating based on obligations, penalties, liability, or ambiguity",
  "suggested_alternative_clause": "A safer, fairer version of this clause",
  "affected_party": "Buyer | Seller | Vendor | Service Provider | Client | Both Parties | Unclear",
  "negotiation_insight": "Practical advice on negotiating this clause"
}}

Focus on: obligations, liabilities, payment terms, termination, IP rights, warranties, indemnity.
"""

        # ✅ DEFINE FALLBACK BEFORE TRY BLOCK
        fallback = {
            "plain_english_explanation": f"This clause outlines terms related to the agreement. It should be reviewed carefully for any obligations, deadlines, or potential liabilities it may create.",
            "risk_level": "Medium",
            "risk_reason": "Standard contractual clause requiring careful review of obligations and terms.",
            "suggested_alternative_clause": "Ensure all terms are clearly defined with specific timelines and responsibilities for each party.",
            "affected_party": "Both Parties",
            "negotiation_insight": "Review this clause carefully and ensure all terms are acceptable before signing.",
        }

        try:
            raw = self._chat(system_msg, user_prompt)
            parsed = self._parse_json_response(raw, fallback)
            
        except Exception as e:
            logger.error(f"Failed to analyze clause {clause_index}: {e}")
            return self._create_fallback_clause_analysis(clause_index, clause_text, anonymised_text)

        llm_risk = parsed.get("risk_level", "Medium").title()
        final_risk = self._combine_risks(llm_risk, rules_risk)

        return ClauseAnalysis(
            clause_index=clause_index,
            original_text=clause_text,
            anonymised_text=anonymised_text,
            plain_english_explanation=parsed.get("plain_english_explanation", ""),
            risk_level_llm=llm_risk,
            risk_level_rules=rules_risk,
            risk_level_final=final_risk,
            risk_reason_llm=parsed.get("risk_reason", ""),
            suggested_alternative_clause=parsed.get("suggested_alternative_clause", ""),
            affected_party=parsed.get("affected_party", "Unclear"),
            rule_hits=[{"rule_id": rm.rule_id, "description": rm.description, "risk_level": rm.risk_level} for rm in rule_matches],
        )

    def _create_fallback_clause_analysis(
        self, clause_index: int, clause_text: str, anonymised_text: str
    ) -> ClauseAnalysis:
        """
        Create a basic clause analysis when LLM fails.
        """
        rule_matches = evaluate_rules(clause_text)
        rules_risk = aggregate_risk_from_rules(rule_matches)
        
        return ClauseAnalysis(
            clause_index=clause_index,
            original_text=clause_text,
            anonymised_text=anonymised_text,
            plain_english_explanation="This clause requires manual review. Please consult with a legal professional for detailed analysis.",
            risk_level_llm="Medium",
            risk_level_rules=rules_risk,
            risk_level_final=rules_risk if rules_risk != "Low" else "Medium",
            risk_reason_llm="Automated analysis unavailable for this clause.",
            suggested_alternative_clause="Seek legal advice for alternative wording.",
            affected_party="Unclear",
            rule_hits=[{"rule_id": rm.rule_id, "description": rm.description, "risk_level": rm.risk_level} for rm in rule_matches],
        )

    @staticmethod
    def _combine_risks(llm_risk: str, rules_risk: str) -> str:
        """
        Conservative combination of LLM and rule-based risk assessments.
        """
        order = {"Low": 0, "Medium": 1, "High": 2}
        llm_score = order.get(llm_risk.title(), 1)
        rules_score = order.get(rules_risk.title(), 1)

        # Take the higher risk (more conservative)
        final_score = max(llm_score, rules_score)

        for k, v in order.items():
            if v == final_score:
                return k
        return "Medium"

    # ------------- CONTRACT SUMMARY -------------
    def summarize_contract(self, full_text: str, overall_rules_risk: str, language: str = "English") -> ContractSummary:
        """
        Generate comprehensive contract summary with all metrics.
        """
        lang_instruction = (
            "Write the summary in clear English."
            if language == "English"
            else "Write the summary in Hindi. Keep risk labels in English."
        )

        system_msg = f"""
You are a senior contract analyst. Produce a concise business summary.
Respond ONLY with VALID JSON, no markdown, no extra text.
{lang_instruction}
"""

        # Limit text length for API
        text_sample = full_text[:8000] if len(full_text) > 8000 else full_text
        word_count = len(full_text.split())

        user_prompt = f"""
Analyze this contract:

\"\"\"{text_sample}\"\"\"

Return ONLY valid JSON:
{{
  "business_summary": "150-250 word summary covering purpose, parties, obligations, payment, duration, liability, IP, termination, disputes",
  "overall_risk": "Low | Medium | High",
  "top_3_business_risks": ["risk 1", "risk 2", "risk 3"],
  "negotiation_recommendations": ["tip 1", "tip 2", "tip 3"],
  "contract_completeness_score": 75,
  "conflicting_clauses": ["conflict description or empty"],
  "duplicate_or_ambiguous_terms": ["term or empty"],
  "document_length_words": {word_count}
}}

Rate completeness 0-100 based on: parties, obligations, payment, duration, termination, liability, IP, disputes.
"""

        # ✅ DEFINE FALLBACK BEFORE TRY BLOCK
        fallback = {
            "business_summary": "This is a business contract that outlines terms between parties. Key areas include obligations, payment terms, duration, and termination conditions. Please review all clauses carefully with legal counsel.",
            "overall_risk": overall_rules_risk,
            "top_3_business_risks": ["Potential liability exposure", "Unclear termination conditions", "Payment terms should be reviewed"],
            "negotiation_recommendations": ["Clarify all obligations and timelines", "Review liability limitations", "Ensure termination rights are balanced"],
            "contract_completeness_score": 60,
            "conflicting_clauses": [],
            "duplicate_or_ambiguous_terms": [],
            "document_length_words": word_count
        }

        try:
            raw = self._chat(system_msg, user_prompt)
            parsed = self._parse_json_response(raw, fallback)
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            parsed = fallback

        llm_overall = parsed.get("overall_risk", "Medium").title()
        final_overall = self._combine_risks(llm_overall, overall_rules_risk)

        return ContractSummary(
            business_summary=parsed.get("business_summary", ""),
            overall_risk_llm=llm_overall,
            overall_risk_rules=overall_rules_risk.title(),
            overall_risk_final=final_overall,
            top_risks=parsed.get("top_3_business_risks", []),
            missing_critical_clauses=[],
            contract_completeness_score=parsed.get("contract_completeness_score", 60),
            conflicting_clauses=parsed.get("conflicting_clauses", []),
            duplicate_or_ambiguous_terms=parsed.get("duplicate_or_ambiguous_terms", []),
            negotiation_insights=parsed.get("negotiation_recommendations", []),
            document_length_words=parsed.get("document_length_words", word_count)
        )

    # ------------- TOP-LEVEL PIPELINE -------------
    def analyze_contract(
        self,
        original_clauses: List[str],
        anonymised_clauses: List[str],
        full_text: str,
        language: str = "English",
    ) -> ContractReport:
        """
        Main entry point: Analyze all clauses and generate report.
        """
        logger.info(f"Starting analysis of {len(original_clauses)} clauses")
        clause_results: List[ClauseAnalysis] = []

        # Analyze each clause
        for idx, (orig, anon) in enumerate(zip(original_clauses, anonymised_clauses), start=1):
            try:
                logger.info(f"Analyzing clause {idx}/{len(original_clauses)}")
                clause_result = self.analyze_clause(
                    clause_text=orig,
                    clause_index=idx,
                    anonymised_text=anon,
                    language=language
                )
                clause_results.append(clause_result)
                
                # Small delay to avoid rate limiting
                if idx % 5 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error analyzing clause {idx}: {e}")
                # Add fallback for failed clause
                clause_results.append(
                    self._create_fallback_clause_analysis(idx, orig, anon)
                )

        # Aggregate rule-based risk
        all_rule_matches = []
        for c in original_clauses:
            all_rule_matches.extend(evaluate_rules(c) or [])
        overall_rules_risk = aggregate_risk_from_rules(all_rule_matches)

        # Generate summary
        logger.info("Generating contract summary")
        summary = self.summarize_contract(full_text, overall_rules_risk, language=language)

        # Build report
        report = ContractReport(
            summary=summary,
            clauses=clause_results,
            anonymisation_map={},
        )

        logger.info("Analysis complete")
        return report
