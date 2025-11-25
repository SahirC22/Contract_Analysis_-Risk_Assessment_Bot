# ⚖️ Legal Contract Analysis & Risk Assessment Bot

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

An AI-powered legal assistant designed specifically for **Indian SMEs** to analyze contracts, identify risks, and provide actionable negotiation insights — all without requiring legal expertise.

## 📋 Table of Contents

- [Features](#-features)
- [Demo](#-demo)
- [Project Requirements](#-project-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Technology Stack](#-technology-stack)
- [Configuration](#-configuration)
- [Limitations](#-limitations)
- [Contributing](#-contributing)
- [License](#-license)
- [Disclaimer](#-disclaimer)

## ✨ Features

### 🔍 **Comprehensive Contract Analysis**
- **Multi-format Support**: Upload PDF, DOCX, or TXT contracts
- **Smart Text Extraction**: Robust extraction from various document formats
- **Clause Segmentation**: Automatic identification and numbering of contract clauses
- **Bilingual Support**: Get explanations in **English** or **Hindi** or both side-by-side

### 🎯 **Hybrid Risk Assessment**
- **LLM-Based Analysis**: Uses GPT-4o/GPT-4o-mini for intelligent clause interpretation
- **Rule-Based Validation**: 10+ predefined risk patterns for common contract issues
- **Three-Level Risk Scoring**: Low, Medium, High risk classification
- **Conservative Approach**: Combines LLM and rule-based assessments for accuracy

### 📊 **Contract Health Metrics**
- **Completeness Score**: 0-100 rating based on critical clause presence
- **Conflict Detection**: Identifies contradictory clauses
- **Ambiguity Finder**: Flags vague or duplicate terms
- **Missing Clause Alert**: Highlights absent critical sections

### 💡 **Business Intelligence**
- **Plain English Explanations**: No legal jargon — business-friendly language
- **Affected Party Identification**: Know who bears obligations/risks
- **Alternative Clause Suggestions**: Get safer, fairer rewording options
- **Negotiation Insights**: Practical tips for improving terms

### 📥 **Export & Reporting**
- **JSON Export**: Structured data for integration
- **PDF Report**: Professional contract analysis report
- **CSV Export**: Clause-by-clause data for spreadsheet analysis
- **Risk Heatmap**: Visual risk distribution across clauses

### 🔒 **Privacy & Compliance**
- **Party Anonymization**: Replaces names with placeholders (PARTY_1, PARTY_2)
- **No Data Storage**: All processing happens in real-time
- **Bias Prevention**: Explicit instructions to avoid demographic discrimination
- **Indian Context**: Designed with Indian contract law considerations

## 🎬 Demo

```
# Upload a contract → Get instant analysis in under 2 minutes
✅ 26 clauses identified
✅ 3 High-risk clauses flagged
✅ 85/100 completeness score
✅ 5 negotiation recommendations provided
```

## 📋 Project Requirements

This project was built to meet the following constraints (as per HCL GenAI Level 1 Challenge):

### ✅ Technical Restrictions
- **LLM Models**: Claude 3 or GPT-4 for legal text analysis only
- **Programming**: Python with spaCy/NLTK for NLP preprocessing
- **UI Framework**: Streamlit or Gradio for interface development
- **File Formats**: PDF, DOC, and plain text uploads only
- **Processing Time**: Maximum 2 minutes per contract
- **No External APIs**: No integration with legal databases or case law systems
- **No Legal Databases**: Standalone analysis without external legal resources

### 🎯 Core Functionalities
- ✅ Contract type identification (employment, vendor, lease, partnership, service)
- ✅ Risk scoring (clause-by-clause + overall)
- ✅ Plain language explanations (English & Hindi)
- ✅ Identification of unfavorable terms
- ✅ Suggested alternative clauses
- ✅ Compliance checking with Indian laws
- ✅ Summary report generation
- ✅ Standardized contract templates
- ✅ Risk mitigation strategies
- ✅ Multilingual support (English + Hindi)
- ✅ Audit trails for legal consultation purposes
- ✅ Knowledge base of common contract issues in Indian SMEs

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- OpenAI API key
- 4GB RAM minimum
- Internet connection for API calls

### Step 1: Clone the Repository
```
git clone https://github.com/yourusername/contract-risk-analyzer.git
cd contract-risk-analyzer
```

### Step 2: Create Virtual Environment
```
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### Step 4: Set Up API Key
```
# Create .env file
echo "OPENAI_API_KEY=your-api-key-here" > .env

# Or set as environment variable (Windows)
set OPENAI_API_KEY=your-api-key-here

# Or set as environment variable (macOS/Linux)
export OPENAI_API_KEY=your-api-key-here
```

### Step 5: Run the Application
```
# Streamlit UI
streamlit run app.py

# Command-line interface
python main.py path/to/contract.pdf
```

## 📖 Usage

### Web Interface (Streamlit)

1. **Launch the app**:
   ```
   streamlit run app.py
   ```

2. **Configure settings** in the sidebar:
   - Select model (gpt-4o-mini recommended for cost/speed)
   - Choose output language (English/Hindi/Both)
   - Set processing timeout

3. **Upload contract**: 
   - Click "Upload Contract" button
   - Select PDF, DOCX, or TXT file (max 10MB)

4. **Analyze**:
   - Click "🚀 Analyze Contract"
   - Wait 30-120 seconds for processing

5. **Review results**:
   - Contract summary with risk assessment
   - Health indicators (completeness, conflicts, ambiguities)
   - Clause-by-clause breakdown with alternatives
   - Negotiation recommendations

6. **Export**:
   - Download JSON for integration
   - Download PDF for sharing
   - Download CSV for spreadsheet analysis

### Command-Line Interface

```
# Analyze a contract
python main.py contract.pdf

# Output saved to analysis_result.json
```

## 📁 Project Structure

```
contract-risk-analyzer/
├── analyzer/
│   ├── __init__.py              # Package initialization
│   ├── extractor.py             # PDF/DOCX/TXT text extraction
│   ├── preprocessor.py          # Text cleaning & clause segmentation
│   ├── llm_model.py            # OpenAI API integration & analysis
│   ├── risk_rules.py           # Rule-based risk detection
│   └── report.py               # Data structures for reports
├── app.py                       # Streamlit web interface
├── main.py                      # CLI entry point
├── requirements.txt             # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## 🔧 How It Works

### 1️⃣ **Text Extraction** (`extractor.py`)
- Uses `pdfplumber` for PDFs
- Uses `python-docx` for Word documents
- Handles encoding issues and preserves structure

### 2️⃣ **Preprocessing** (`preprocessor.py`)
- **Text Cleaning**: Normalizes whitespace, removes artifacts
- **Clause Segmentation**: Splits on numbered headings (1., 1.1, etc.)
- **Party Anonymization**: Replaces names with PARTY_1, PARTY_2 using spaCy NER
- **Sentence Chunking**: Splits long clauses for better analysis

### 3️⃣ **Hybrid Analysis** (`llm_model.py`)
- **Rule-Based Detection**: Scans for 10+ risk patterns:
  - Unlimited liability
  - One-sided indemnity
  - Automatic renewal
  - Broad IP assignment
  - Vague payment terms
  - Unilateral termination
  - Ambiguous obligations
  
- **LLM Analysis**: GPT-4o analyzes each clause for:
  - Plain English explanation
  - Risk level (Low/Medium/High)
  - Risk reasoning
  - Suggested alternative wording
  - Affected party identification
  - Negotiation insights

- **Risk Reconciliation**: Combines LLM + rules conservatively

### 4️⃣ **Summary Generation**
- Contract-wide risk assessment
- Top 3 business risks
- Completeness score (0-100)
- Conflicting clauses detection
- Ambiguous terms identification
- Negotiation recommendations

### 5️⃣ **Report Export** (`report.py`)
- Structured JSON with typed dataclasses
- PDF generation with ReportLab
- CSV export for data analysis

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.10+ | Core logic |
| **UI** | Streamlit | Web interface |
| **LLM** | OpenAI GPT-4o / GPT-4o-mini | Contract analysis |
| **NLP** | spaCy | Entity recognition & segmentation |
| **Text Extraction** | pdfplumber, python-docx | Document parsing |
| **PDF Generation** | ReportLab | Export reports |
| **Data Viz** | Altair | Risk heatmaps |

## ⚙️ Configuration

### Model Selection
```
# In app.py or via UI
model_name = "gpt-4o-mini"  # Faster, cheaper
model_name = "gpt-4o"       # More accurate
```

### Temperature Settings
```
# In llm_model.py
temperature = 0.15  # More deterministic (recommended)
temperature = 0.5   # More creative
```

### Processing Limits
```
# In preprocessor.py
max_clause_len = 900       # Max clause length in characters
min_clause_words = 15      # Min clause length in words
```

### Retry Logic
```
# In llm_model.py
max_retries = 3           # API retry attempts
retry_delay = 2.0         # Initial retry delay (seconds)
```

## ⚠️ Limitations

1. **Not Legal Advice**: This tool assists analysis but cannot replace professional legal counsel
2. **Processing Time**: Complex contracts may take up to 2 minutes
3. **API Costs**: Uses paid OpenAI API (approx ₹5-20 per contract depending on length)
4. **Language Support**: Primary focus on English contracts; Hindi translation available
5. **Jurisdiction**: Designed for Indian context; may miss region-specific laws
6. **No Database**: Cannot reference case law or legal precedents
7. **OCR Quality**: Scanned PDFs may have extraction errors

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup
```
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black analyzer/ app.py main.py

# Lint
flake8 analyzer/ app.py main.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Disclaimer

**THIS TOOL IS NOT A SUBSTITUTE FOR PROFESSIONAL LEGAL ADVICE.**

- The AI-generated analysis is for informational purposes only
- No attorney-client relationship is created by using this tool
- Always consult a qualified lawyer for:
  - Final contract review
  - Legal interpretation
  - Signing decisions
  - Dispute resolution
  - Compliance verification

The developers assume no liability for decisions made based on this tool's output.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/contract-risk-analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/contract-risk-analyzer/discussions)
- **Email**: support@yourproject.com

## 🙏 Acknowledgments

- Built for **HCL GenAI Level 1 Challenge**
- Designed to help Indian SMEs navigate complex contracts
- Inspired by the need for accessible legal technology

## 📊 Stats

- ⭐ Star this repo if you find it useful!
- 🐛 Report bugs via GitHub Issues
- 💡 Suggest features via Discussions

---

**Made with ❤️ for Indian Small & Medium Businesses**
```

This comprehensive README includes:[1][2][3][5]

1. **Professional badges** showing tech stack
2. **Complete feature list** matching your project capabilities
3. **Installation instructions** for all platforms
4. **Usage guide** for both web and CLI
5. **Technical architecture** explanation
6. **Project structure** overview
7. **Configuration options** for customization
8. **Limitations** to set proper expectations
9. **Legal disclaimer** to protect users
10. **Contributing guidelines** for open source collaboration
11. **All project requirements** from the challenge specifications

Replace `yourusername` and contact details with your actual information before publishing!

[1](https://github.com/ahmetkumass/contract-analyzer)
[2](https://github.com/benthecoder/SignSage)
[3](https://github.com/ramona1999/Contract-Risk-Assessment)
[4](https://github.com/LouisTsai-Csie/awesome-smart-contract-analysis-tools)
[5](https://github.com/deacs11/CrewAI_Contract_Clause_Risk_Assessment)
[6](https://github.com/relari-ai/agent-contracts)
[7](https://github.com/ifrahnz26/RiskLexis)
[8](https://github.com/hariscoder3/ContractIQ)
[9](https://github.com/OssamaLouati/Legal-AI_Project)
