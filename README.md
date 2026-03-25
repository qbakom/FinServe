# FinServe AI Credit Memo Generator

A proof-of-concept application that automates credit memo preparation for financial services companies. Built for the 10Clouds FI assessment task.

## What It Does

Takes structured loan application data (client profile, financials, facility request) and produces a complete credit memo with:

- **Deterministic risk scoring** — financial ratios (D/E, DSCR, LTV, leverage, current ratio) and a composite risk rating (AAA→CCC) computed by code, not AI
- **AI-generated narrative** — executive summary, financial analysis, risk assessment, collateral analysis, recommendation, and conditions written by Gemini
- **PDF export** — professional A4 credit memo ready for committee review

## Architecture

```
User Input (Web UI) → FastAPI → Risk Engine (deterministic) → Gemini API (narrative) → PDF Export
```

Key design decision: **AI writes the narrative; code computes the numbers.** This separation is critical in financial services — risk metrics must be reproducible and auditable.

## Requirements

- **Python 3.12+**
- System libraries for PDF generation (Ubuntu/Debian): `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0`, `libcairo2`
- Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

## Quick Start

```bash
# Python 3.12+ required
python3 --version

# Install dependencies
pip install -r requirements.txt

# System deps for PDF generation (Ubuntu/Debian)
apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2

# Set API key
export GEMINI_API_KEY=your_key_here

# Run
python3 -m uvicorn src.app:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## Project Structure

```
├── src/                    # Application source code
│   ├── app.py              # FastAPI application (routes, orchestration)
│   ├── models.py           # Pydantic data models
│   ├── risk_engine.py      # Deterministic risk scoring engine
│   ├── memo_generator.py   # AI narrative generation (Gemini API)
│   └── pdf_export.py       # WeasyPrint PDF rendering
├── templates/
│   └── index.html          # Web UI (single-page form + memo preview)
├── sample_data/            # 3 realistic sample applications
│   ├── 01_techflow_solutions.json    (strong SME — AA rating)
│   ├── 02_green_harvest_farms.json   (moderate — BBB rating)
│   └── 03_urban_style_retail.json    (high-risk — BB/B rating)
├── docs/                   # Assessment presentation & task description
├── Dockerfile              # Docker build (Python 3.12 + WeasyPrint deps)
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/api/samples` | List sample applications |
| GET | `/api/samples/{filename}` | Get sample data |
| POST | `/api/generate` | Generate credit memo (JSON) |
| POST | `/api/generate/pdf` | Generate credit memo (PDF download) |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic
- **AI:** Google Gemini 2.5 Flash (via google-genai SDK)
- **PDF:** WeasyPrint
- **Frontend:** Vanilla HTML/CSS/JS (no framework needed for a PoC)
