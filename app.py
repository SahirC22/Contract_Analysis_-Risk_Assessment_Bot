import streamlit as st
import json
import os
from openai import OpenAI
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Import analyzer modules
try:
    from analyzer.extractor import extract_text
    from analyzer.preprocessor import preprocess_contract
    from analyzer.llm_model import ContractAnalyzer, LLMConfig
except ImportError:
    # Fallback if not using package structure
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from extractor import extract_text
    from preprocessor import preprocess_contract
    from llm_model import ContractAnalyzer, LLMConfig

# ========== API KEY SETUP ==========
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("❌ Missing API key — Set OPENAI_API_KEY in environment variables or Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)


# ========== TRANSLATION HELPER ==========
def translate_to_hindi(text, model="gpt-4o-mini"):
    """Translate text to Hindi using GPT"""
    if not text or not text.strip():
        return text
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Translate into clear, simple business Hindi."},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.warning(f"Translation failed: {e}")
        return text


# ========== PDF REPORT GENERATOR ==========
def generate_pdf(summary, clauses):
    """Generate PDF report with summary and clause analysis"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Contract Analysis Report", styles['Title']))
    story.append(Spacer(1, 12))

    # Summary Section
    story.append(Paragraph("Contract Summary", styles['Heading1']))
    story.append(Paragraph(summary.get("business_summary", "No summary available"), styles['BodyText']))
    story.append(Spacer(1, 12))

    # Overall Risk
    overall_risk = summary.get("overall_risk_final", "Medium")
    story.append(Paragraph(f"<b>Overall Risk:</b> {overall_risk}", styles['BodyText']))
    story.append(Spacer(1, 12))

    # Top Risks
    top_risks = summary.get("top_risks", [])
    if top_risks:
        story.append(Paragraph("Top Business Risks:", styles['Heading2']))
        for i, risk in enumerate(top_risks, 1):
            story.append(Paragraph(f"{i}. {risk}", styles['BodyText']))
        story.append(Spacer(1, 12))

    # Contract Health Metrics
    story.append(Paragraph("Contract Health Metrics", styles['Heading2']))
    completeness = summary.get("contract_completeness_score", 0)
    story.append(Paragraph(f"<b>Completeness Score:</b> {completeness}/100", styles['BodyText']))
    
    conflicting = summary.get("conflicting_clauses", [])
    if conflicting:
        story.append(Paragraph(f"<b>Conflicting Clauses:</b> {len(conflicting)} found", styles['BodyText']))
    
    duplicates = summary.get("duplicate_or_ambiguous_terms", [])
    if duplicates:
        story.append(Paragraph(f"<b>Ambiguous Terms:</b> {len(duplicates)} found", styles['BodyText']))
    
    story.append(Spacer(1, 12))

    # Negotiation Insights
    insights = summary.get("negotiation_insights", [])
    if insights:
        story.append(Paragraph("Negotiation Recommendations:", styles['Heading2']))
        for i, insight in enumerate(insights, 1):
            story.append(Paragraph(f"{i}. {insight}", styles['BodyText']))
        story.append(Spacer(1, 12))

    # Clause-by-Clause Analysis Table
    story.append(Paragraph("Clause-by-Clause Analysis", styles['Heading1']))
    story.append(Spacer(1, 6))

    table_data = [["#", "Risk", "Explanation", "Alternative"]]
    for c in clauses:
        idx = str(c.get("clause_index", ""))
        risk = c.get("risk_level_final", "Medium")
        explanation = c.get("plain_english_explanation", "")[:200]
        alternative = c.get("suggested_alternative_clause", "None")[:150]
        table_data.append([idx, risk, explanation, alternative])

    t = Table(table_data, colWidths=[30, 60, 220, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer


# ========== STREAMLIT UI ==========
st.set_page_config(page_title="Legal Contract Analyzer", page_icon="⚖️", layout="wide")

st.title("⚖️ Legal Contract Analysis & Risk Assessment Bot")
st.markdown("""
**Built for Indian SMEs** — Upload your contract (PDF/DOCX/TXT) and get:
- Plain English/Hindi explanations
- Risk scoring with alternative clauses
- Compliance insights
- Negotiation recommendations
""")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    model_name = st.selectbox(
        "Model Selection",
        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        index=0,
        help="gpt-4o-mini is faster and cheaper. Use gpt-4o for complex contracts."
    )
    
    language = st.radio(
        "Output Language",
        ["English", "Hindi", "Both"],
        index=0
    )
    
    timeout = st.slider(
        "Processing Timeout (seconds)",
        min_value=60,
        max_value=300,
        value=120,
        step=30
    )
    
    st.markdown("---")
# File Upload
uploaded_file = st.file_uploader(
    "📎 Upload Contract (PDF, DOCX, or TXT)",
    type=["pdf", "docx", "txt"],
    help="Max file size: 10MB. Processing time: ~2 minutes per contract."
)

if uploaded_file:
    # File info
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📄 **{uploaded_file.name}** ({file_size_mb:.2f} MB)")
    
    if st.button("*Analyze Contract*", type="primary"):
        with st.spinner("⏳ Analyzing contract... This may take up to 2 minutes."):
            try:
                # Step 1: Extract text
                st.write("**Step 1/4:** Extracting text from document...")
                text = extract_text(uploaded_file, uploaded_file.name)
                
                if not text or len(text.strip()) < 100:
                    st.error("❌ Failed to extract meaningful text. Please check if the file is readable.")
                    st.stop()
                
                st.success(f"✅ Extracted {len(text.split())} words")
                
                # Step 2: Preprocess
                st.write("**Step 2/4:** Cleaning and segmenting clauses...")
                anonymised_text, original_clauses, anonymised_clauses, anon = preprocess_contract(text)
                st.success(f"✅ Identified {len(original_clauses)} clauses")
                
                # Step 3: Analyze with LLM
                st.write("**Step 3/4:** Running AI analysis (LLM + Rules)...")
                config = LLMConfig(
                    model_name=model_name,
                    temperature=0.1,
                    max_tokens=1500
                )
                analyzer = ContractAnalyzer(api_key=API_KEY, config=config)
                report = analyzer.analyze_contract(
                    original_clauses=original_clauses,
                    anonymised_clauses=anonymised_clauses,
                    full_text=text,
                    language=language if language != "Both" else "English"
                )
                
                result = report.to_json()
                st.success("✅ Analysis complete!")
                
                # ========== DISPLAY RESULTS ==========
                st.markdown("---")
                st.header("📊 Analysis Results")
                
                # ===== CONTRACT SUMMARY SECTION =====
                st.subheader("📌 Contract Summary")
                summary = result["summary"]
                summary_text = summary.get("business_summary", "")
                
                # Enhanced fallback with better error handling
                if not summary_text or not summary_text.strip() or len(summary_text) < 50:
                    summary_text = "This contract includes the following key business points:\n\n"
                    meaningful = [
                        c for c in result["clauses"]
                        if c.get("plain_english_explanation")
                        and len(c["plain_english_explanation"]) > 50
                        and "failed to process" not in c["plain_english_explanation"].lower()
                        and "could not interpret" not in c["plain_english_explanation"].lower()
                    ]
                    
                    if meaningful:
                        for c in meaningful[:10]:
                            summary_text += f"• **Clause {c['clause_index']}:** {c['plain_english_explanation']}\n\n"
                    else:
                        summary_text = "⚠️ The contract text may be unclear, scanned, or improperly formatted. Please upload a cleaner version or review manually."
                
                # Translation handling
                if language in ("Hindi", "Both"):
                    summary_hi = translate_to_hindi(summary_text, model=model_name)
                    if language == "Both":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**English:**")
                            st.write(summary_text)
                        with col2:
                            st.markdown("**हिंदी:**")
                            st.write(summary_hi)
                    else:
                        st.write(summary_hi)
                else:
                    st.write(summary_text)
                
                st.markdown("---")
                
                # ===== OVERALL RISK =====
                risk_colors = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
                overall_risk = summary.get("overall_risk_final", "Medium")
                st.markdown(f"### {risk_colors.get(overall_risk, '⚪')} Overall Risk: **{overall_risk}**")
                
                # Risk breakdown
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("LLM Assessment", summary.get("overall_risk_llm", "Medium"))
                with col2:
                    st.metric("Rule-Based Assessment", summary.get("overall_risk_rules", "Medium"))
                with col3:
                    st.metric("Final Risk", overall_risk)
                
                st.markdown("---")
                
                # ===== TOP RISKS =====
                top_risks = summary.get("top_risks", [])
                if top_risks:
                    st.subheader("🎯 Top Business Risks")
                    for i, risk in enumerate(top_risks, 1):
                        st.markdown(f"**{i}.** {risk}")
                    st.markdown("---")
                
                # ===== CONTRACT HEALTH METRICS =====
                st.subheader("🏥 Contract Health Indicators")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    completeness = summary.get("contract_completeness_score", 0)
                    st.metric("Completeness Score", f"{completeness}/100")
                    if completeness < 60:
                        st.warning("⚠️ Contract may be missing critical clauses")
                    elif completeness < 80:
                        st.info("ℹ️ Contract is fairly complete")
                    else:
                        st.success("✅ Contract is comprehensive")
                
                with col2:
                    conflicting = summary.get("conflicting_clauses", [])
                    st.metric("Conflicting Clauses", len(conflicting))
                    if conflicting:
                        with st.expander("View Conflicts"):
                            for conf in conflicting:
                                st.write(f"• {conf}")
                
                with col3:
                    duplicates = summary.get("duplicate_or_ambiguous_terms", [])
                    st.metric("Ambiguous Terms", len(duplicates))
                    if duplicates:
                        with st.expander("View Ambiguous Terms"):
                            for dup in duplicates:
                                st.write(f"• {dup}")
                
                st.markdown("---")
                
                # ===== NEGOTIATION INSIGHTS =====
                insights = summary.get("negotiation_insights", [])
                if insights:
                    st.subheader("💡 Negotiation Recommendations")
                    for i, insight in enumerate(insights, 1):
                        st.markdown(f"**{i}.** {insight}")
                    st.markdown("---")
                
                # ===== MISSING CLAUSES =====
                missing = summary.get("missing_critical_clauses", [])
                if missing:
                    st.subheader("⚠️ Missing Critical Clauses")
                    for clause in missing:
                        st.warning(f"• {clause}")
                    st.markdown("---")
                
                # ===== CLAUSE-BY-CLAUSE ANALYSIS =====
                st.subheader("📋 Clause-by-Clause Analysis")
                
                # Filter options
                risk_filter = st.multiselect(
                    "Filter by Risk Level",
                    ["Low", "Medium", "High"],
                    default=["Medium", "High"]
                )
                
                filtered_clauses = [
                    c for c in result["clauses"]
                    if c.get("risk_level_final", "Medium") in risk_filter
                ]
                
                st.write(f"Showing **{len(filtered_clauses)}** of **{len(result['clauses'])}** clauses")
                
                for clause in filtered_clauses:
                    risk_icon = risk_colors.get(clause.get("risk_level_final", "Medium"), "⚪")
                    
                    with st.expander(
                        f"{risk_icon} Clause {clause['clause_index']} — "
                        f"Risk: {clause.get('risk_level_final', 'Medium')}"
                    ):
                        # Original Text
                        st.markdown("**Original Text:**")
                        st.text(clause.get("original_text", "")[:500])
                        
                        # Plain English Explanation
                        explanation = clause.get("plain_english_explanation", "")
                        if explanation:
                            st.markdown("**Plain English Explanation:**")
                            if language == "Hindi":
                                explanation_hi = translate_to_hindi(explanation, model=model_name)
                                st.write(explanation_hi)
                            elif language == "Both":
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(explanation)
                                with col2:
                                    st.write(translate_to_hindi(explanation, model=model_name))
                            else:
                                st.write(explanation)
                        
                        # Risk Details
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**LLM Risk:** {clause.get('risk_level_llm', 'N/A')}")
                            st.markdown(f"**Rule-Based Risk:** {clause.get('risk_level_rules', 'N/A')}")
                        with col2:
                            st.markdown(f"**Affected Party:** {clause.get('affected_party', 'Unclear')}")
                            st.markdown(f"**Risk Score:** {clause.get('final_risk_score', 0):.2f}")
                        
                        # Risk Reason
                        risk_reason = clause.get("risk_reason_llm", "")
                        if risk_reason:
                            st.markdown("**Why is this risky?**")
                            st.info(risk_reason)
                        
                        # Rule Hits
                        rule_hits = clause.get("rule_hits", [])
                        if rule_hits:
                            st.markdown("**Rule-Based Findings:**")
                            for hit in rule_hits:
                                st.warning(f"⚠️ {hit.get('description', '')} (Risk: {hit.get('risk_level', '')})")
                        
                        # Suggested Alternative
                        alternative = clause.get("suggested_alternative_clause", "")
                        if alternative and alternative != "None provided":
                            st.markdown("**Suggested Alternative Clause:**")
                            st.success(alternative)
                        
                        # Negotiation Insight
                        negotiation = clause.get("negotiation_insight", "")
                        if negotiation:
                            st.markdown("**Negotiation Tip:**")
                            st.info(negotiation)
                
                st.markdown("---")
                
                # ===== EXPORT OPTIONS =====
                st.subheader("📥 Export Report")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # JSON Export
                    json_str = json.dumps(result, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📄 Download JSON Report",
                        data=json_str,
                        file_name=f"contract_analysis_{uploaded_file.name}.json",
                        mime="application/json"
                    )
                
                with col2:
                    # PDF Export
                    pdf_buffer = generate_pdf(summary, result["clauses"])
                    st.download_button(
                        label="📑 Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"contract_analysis_{uploaded_file.name}.pdf",
                        mime="application/pdf"
                    )
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.exception(e)

else:
    st.info("👆 Upload a contract file to begin analysis")
    
    # Sample features showcase
    with st.expander("✨ Features & Capabilities"):
        st.markdown("""
        ### What This Tool Does:
        
        - **Multi-Format Support**: PDF, DOCX, TXT  
        - **Bilingual**: English & Hindi explanations  
        - **Risk Scoring**: Hybrid LLM + Rule-based analysis  
        - **Clause-by-Clause**: Detailed breakdown with alternatives  
        - **Contract Health**: Completeness, conflicts, ambiguities  
        - **Negotiation Tips**: Actionable recommendations  
        - **Export Options**: JSON & PDF reports  
        - **Privacy**: No data stored, processed in real-time  
        
        ### Built For:
        - Small & Medium Business Owners
        - Freelancers & Consultants
        - Startups & Entrepreneurs
        - Anyone reviewing contracts without legal expertise
        """)
