# Mutual Fund FAQ Assistant (HDFC Mutual Fund Facts-Only RAG Chatbot)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Embeddings](https://img.shields.io/badge/Embeddings-BAAI%2Fbge--small--en--v1.5-orange.svg)](https://huggingface.co/BAAI/bge-small-en-v1.5)
[![LLM](https://img.shields.io/badge/LLM-Groq%20Llama3-purple.svg)](https://console.groq.com)
[![SEBI Compliance](https://img.shields.io/badge/SEBI-Facts--Only%20%7C%20Zero%20Advisory-green.svg)](https://www.sebi.gov.in/)

> A lightweight, **facts-only** Retrieval-Augmented Generation (RAG) chatbot designed to deliver verified, source-backed financial information for **10 HDFC Mutual Fund schemes** sourced directly from official public documents.

---

## 🎯 Project Overview & Core Principles

Retail investors and customer support teams frequently need quick, factual answers about mutual fund schemes—such as expense ratios, exit loads, Net Asset Value (NAV), SIP minimums, and lock-in periods. 

This project implements a precision-tuned RAG pipeline adhering strictly to the principle of **"Accuracy over intelligence."** The system is built with zero tolerance for speculative, subjective, or advisory responses, ensuring 100% compliance with SEBI guidelines for financial factual disclosure.

### 🌟 Key Highlights
- **🚫 Zero Advisory Bias (SEBI Guardrails):** Built-in intent classifiers and refusal handlers (`src/generation/refusal_handler.py`) automatically intercept and reject requests for investment advice, stock recommendations, or fund comparisons.
- **⚡ Enriched Semantic Retrieval:** Standardized on `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors) with prepended Contextual Headers (`[Scheme: ... | Category: ...]`) stored in a local ChromaDB vector store.
- **⏰ Automated Ingestion Scheduler:** Includes a background scheduler component (`src/ingestion/scheduler.py`) with thread-safe mutex locking that periodically refreshes scheme factsheets and NAV data to guarantee real-time data freshness without manual intervention.
- **🔗 Verifiable Transparency:** Every generated answer is bounded by a strict 3-sentence summary rule and includes explicit clickable source links and "Last Updated" metadata.

---

## 🏛️ Architecture & Data Flow

```mermaid
flowchart LR
    subgraph Ingestion["Data Ingestion & Scheduler (GitHub Actions)"]
        A["Groww Scheme URLs<br/>(10 HDFC Funds)"] --> B["Scraper & Chunker"]
        B --> C["Embedder<br/>(bge-small-en-v1.5)"]
        S["GitHub Actions Cron<br/>(scheduled_ingestion.yml)"] -.->|Periodic Trigger / Webhook| B
    end

    subgraph Storage["Vector Database"]
        C --> D["ChromaDB Index<br/>(vectorstore/)"]
    end

    subgraph RAG["Query Processing & Guardrails"]
        E["User Query"] --> F{"Intent Classifier"}
        F -->|Advisory / Opinion| G["Refusal Handler<br/>+ Educational Link"]
        F -->|Factual Query| H["Metadata-Aware<br/>Retriever"]
        D <-->|Top-k Chunks| H
        H --> I["Groq Llama3 LLM<br/>(Temperature = 0.0)"]
        I --> J["Citation Formatter<br/>+ Source URL"]
    end

    style S fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style D fill:#E8913A,stroke:#B5702D,color:#fff
    style G fill:#D9534F,stroke:#B52B27,color:#fff
```

---

## 📚 Selected Corpus (HDFC Mutual Fund Schemes)

The RAG corpus is powered by 10 carefully curated HDFC Mutual Fund scheme pages sourced from Groww:

| # | Scheme Name | Category | Groww Source URL |
| :---: | :--- | :--- | :--- |
| 1 | **HDFC Nifty 50 Index Fund** | Equity Index | [View Page](https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth) |
| 2 | **HDFC BSE Sensex Index Fund** | Equity Index | [View Page](https://groww.in/mutual-funds/hdfc-bse-sensex-index-fund-direct-growth) |
| 3 | **HDFC Children's Fund** | Goal-Based | [View Page](https://groww.in/mutual-funds/hdfc-children's-fund-direct-plan) |
| 4 | **HDFC Banking & Financial Services Fund** | Sectoral | [View Page](https://groww.in/mutual-funds/hdfc-banking-financial-services-fund-direct-growth) |
| 5 | **HDFC Corporate Debt Opportunities Fund** | Debt | [View Page](https://groww.in/mutual-funds/hdfc-corporate-debt-opportunities-fund-direct-growth) |
| 6 | **HDFC Gold ETF Fund of Fund** | Commodity | [View Page](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth) |
| 7 | **HDFC Nifty Next 50 Index Fund** | Equity Index | [View Page](https://groww.in/mutual-funds/hdfc-nifty-next-50-index-fund-direct-growth) |
| 8 | **HDFC Nifty500 Multicap 50:25:25 Index Fund** | Multicap Index | [View Page](https://groww.in/mutual-funds/hdfc-nifty500-multicap-50:25:25-index-fund-direct-growth) |
| 9 | **HDFC Diversified Equity All Cap Active FoF** | Fund of Funds | [View Page](https://groww.in/mutual-funds/hdfc-diversified-equity-all-cap-active-fof-direct-growth) |
| 10 | **HDFC Nifty India Digital Index Fund** | Thematic Index | [View Page](https://groww.in/mutual-funds/hdfc-nifty-india-digital-index-fund-direct-growth) |

---

## 🛠️ Project Structure

```text
├── .github/                  # GitHub Actions CI/CD workflows
│   └── workflows/
│       └── scheduled_ingestion.yml # Automated cron scheduler & webhook bridge
├── config/                   # Prompts, environment settings, and logging configuration
├── data/                     # Ingestion storage
│   ├── urls.json             # Curated scheme URLs
│   ├── raw/                  # Raw scraped HTML/text artifacts
│   └── processed/            # Cleaned semantic JSON chunks with prepended headers
├── docs/                     # Full architectural specifications, eval frameworks, and plans
├── src/                      # Core application package
│   ├── ingestion/            # Scraper, chunker, embedder, and automated scheduler
│   ├── retrieval/            # Vector similarity search against ChromaDB
│   ├── generation/           # Intent classifier, refusal handler, LLM generator, and citations
│   ├── api/                  # FastAPI REST routes, schemas, and CORS entrypoint
│   └── ui/                   # Vanilla HTML5/CSS/JS frontend interface
├── stitch_hdfc_fund_facts_ui/ # UI design mockups and frontend brand assets
├── vectorstore/              # Persistent SQLite ChromaDB vector index
├── Dockerfile                # Container deployment configuration
├── pytest.ini                # Test suite settings
├── requirements.txt          # Python project dependencies
└── run.py                    # One-click server startup script
```

---

## 🚀 Setup & Installation Guide

### Prerequisites
- **Python 3.10+** installed on your system.
- A free **Groq API Key** from [Groq Cloud Console](https://console.groq.com) for high-speed Llama3 inference.

### 1. Clone & Setup Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Open `.env` and set your `GROQ_API_KEY`:
```ini
GROQ_API_KEY="gsk_your_actual_api_key_here"
LLM_MODEL="llama3-8b-8192"
EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
INGESTION_CRON="0 5 * * *"  # 05:00 UTC = 10:30 AM IST
```

---

## 🏃 Running the Application

### Option A: Quick Start (Using `run.py`)
Launch the backend API server with a single command:
```bash
python run.py
```

### Option B: Using Uvicorn Directly
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Opening the Frontend UI
Once the backend server is running on `http://localhost:8000`, open the web interface directly in your browser:
- Navigate to `src/ui/index.html` or double-click `index.html` in your file explorer.
- The UI communicates automatically with the local API endpoint (`http://localhost:8000/api/query`).

---

## 🔌 REST API Reference

The backend exposes interactive OpenAPI Swagger documentation at:
👉 **http://localhost:8000/docs**

| Method | Endpoint | Description | Access |
| :---: | :--- | :--- | :---: |
| `POST` | `/api/query` | Submit a chat query; returns factual answer with citations or polite refusal | Public |
| `GET` | `/api/schemes` | Retrieve list of all 10 indexed mutual fund schemes | Public |
| `GET` | `/api/health` | Check system status, vector DB connectivity, and model readiness | Public |
| `POST` | `/api/ingest` | Trigger manual re-ingestion of the document corpus | Admin |
| `GET` | `/api/ingest/status` | Check status of the Automated Ingestion Scheduler | Public |

### Example Query Payload (`POST /api/query`)
```json
{
  "query": "What is the exit load and expense ratio of HDFC Nifty 50 Index Fund?"
}
```

---

## 🧪 Testing & Evaluation

Run the automated test suite to verify ingestion pipelines, chunking logic, and refusal compliance:
```bash
# Run all tests
pytest

# Run API integration tests only
pytest test_api.py -v
```

---

## ⚠️ Known Constraints & Limitations

1. **Single AMC Focus:** The corpus is scoped exclusively to **HDFC Mutual Fund** schemes. Queries regarding other asset management companies (e.g., SBI, ICICI, Nippon) will return no results.
2. **Scheduled Real-Time Refresh:** While the system does not stream per-second stock market ticker prices, the built-in automated background scheduler periodically scrapes and re-indexes official scheme factsheets so answers reflect the latest published figures.
3. **No Live Web Search:** The chatbot operates strictly within its indexed vector database and will never hallucinate or scrape external news blogs or aggregator forums (e.g., Moneycontrol, Value Research).
4. **3-Sentence Summary Limit:** To maintain conciseness and readability for retail investors, all generative answers are capped at 3 sentences and append an official source link for deep-dive reading.

---

## 📄 License & Compliance

This project is developed for educational and professional demonstration of advanced Retrieval-Augmented Generation architectures. 
**Disclaimer:** *Facts-only. No investment advice is provided by this software. Always refer to official Scheme Information Documents (SID) and Key Information Memorandums (KIM) before investing.*
