"""
main.py
Backend execution pipeline — no UI.
Run: python main.py path/to/contract.pdf
"""

from analyzer.extractor import extract_text
from analyzer.preprocessor import preprocess_contract
from analyzer.llm_model import ContractAnalyzer, LLMConfig
import sys
import json
import os

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise EnvironmentError("❌ Missing API key — set OPENAI_API_KEY in environment variables.")


def run_analysis(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    print("📄 Extracting contract text...")
    with open(file_path, "rb") as f:
        text = extract_text(f, None)

    print("🧹 Cleaning, anonymising & segmenting clauses...")
    anonymised_text, original_clauses, anonymised_clauses, anon = preprocess_contract(text)

    print(f"✂️ {len(original_clauses)} clauses detected.")

    print("🤖 Running ContractAnalyzer (LLM + Rules)...")
    analyzer = ContractAnalyzer(api_key=API_KEY, config=LLMConfig(model_name="gpt-4o"))
    report = analyzer.analyse_full_contract(
        original_text=text,
        anonymised_text=anonymised_text,
        clauses=original_clauses,
        anonymised_clause_texts=anonymised_clauses,
        anonymisation_map=anon.entity_map,
        output_language="English",
    )

    print("✅ Analysis complete.")
    return report.to_json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("python main.py <contract_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    result = run_analysis(file_path)

    with open("analysis_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("📂 Saved output → analysis_result.json")