# Project Context: Mutual Fund FAQ Assistant

> This document captures the **complete context** derived from the [Problem Statement](file:///c:/Users/DELL/Pictures/Milestone%201/RAG%20Chatbot/docs/problemstatement.md). It serves as the single source of truth for understanding the project's purpose, boundaries, technical approach, and acceptance criteria.

---

## 1. Project Identity

| Field | Value |
| :--- | :--- |
| **Project Name** | Mutual Fund FAQ Assistant |
| **Project Type** | Facts-Only Q&A Chatbot |
| **Core Architecture** | Retrieval-Augmented Generation (RAG) |
| **Selected AMC** | **HDFC Mutual Fund** (HDFC Asset Management Company Limited) |
| **Reference Product** | Groww (Indian mutual fund investment platform) |
| **Domain** | Financial Services — Mutual Funds (India) |
| **Scheme Count** | 10 HDFC mutual fund schemes |
| **Core Principle** | *Accuracy over intelligence* — the system must deliver only verified, source-backed financial information with zero advisory bias or speculation. |

---

## 2. Problem Being Solved

Retail investors and customer support teams frequently need quick, factual answers about mutual fund schemes — expense ratios, exit loads, NAV, SIP minimums, lock-in periods, and more. Currently, finding this information requires navigating across multiple AMC websites, SEBI portals, and AMFI resources.

This project creates a **lightweight RAG-based chatbot** that:
- Ingests and automatically schedules periodic real-time refresh of a curated corpus of official public documents.
- Retrieves and presents only factual, verifiable answers.
- Strictly refuses any advisory, subjective, or opinion-based queries.
- Cites every answer with an official source link and a "last updated" timestamp.

---

## 3. Target Audience

| Persona | Need |
| :--- | :--- |
| **Retail Investors** | Comparing mutual fund schemes; seeking factual details like NAV, expense ratio, exit loads, and lock-in periods. |
| **Customer Support & Content Teams** | Handling repetitive mutual fund queries; requiring quick, verified, and source-linked answers to improve efficiency. |

---

## 4. Technical Architecture Context

### 4.1. System Type
- **Retrieval-Augmented Generation (RAG)** pipeline.
- Lightweight implementation — not a full-scale enterprise search engine.

### 4.2. Data Ingestion — Corpus Definition
The RAG system is powered by a **strictly curated document corpus**:

| Parameter | Specification |
| :--- | :--- |
| **Selected AMC** | **HDFC Mutual Fund** (HDFC Asset Management Company Limited) |
| **Scheme Count** | 10 mutual fund schemes |
| **Category Diversity** | Equity Index, Sectoral, Debt, Commodity, Goal-Based, Fund of Funds, Multicap Index, Thematic Index |
| **URL Count** | 15–25 official public URLs |
| **Real-Time Data Freshness** | Automated GitHub Actions cron scheduler (`scheduled_ingestion.yml`) triggers periodic re-ingestion to fetch latest scheme figures (NAV, AUM, expense ratios) |

#### Selected Schemes (HDFC Mutual Fund)

| # | Scheme Name | Category | Groww URL |
| :--- | :--- | :--- | :--- |
| 1 | HDFC Nifty 50 Index Fund | Equity Index | [Link](https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth) |
| 2 | HDFC BSE Sensex Index Fund | Equity Index | [Link](https://groww.in/mutual-funds/hdfc-bse-sensex-index-fund-direct-growth) |
| 3 | HDFC Children's Fund | Goal-Based | [Link](https://groww.in/mutual-funds/hdfc-children's-fund-direct-plan) |
| 4 | HDFC Banking & Financial Services Fund | Sectoral | [Link](https://groww.in/mutual-funds/hdfc-banking-financial-services-fund-direct-growth) |
| 5 | HDFC Corporate Debt Opportunities Fund | Debt | [Link](https://groww.in/mutual-funds/hdfc-corporate-debt-opportunities-fund-direct-growth) |
| 6 | HDFC Gold ETF Fund of Fund | Commodity | [Link](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth) |
| 7 | HDFC Nifty Next 50 Index Fund | Equity Index | [Link](https://groww.in/mutual-funds/hdfc-nifty-next-50-index-fund-direct-growth) |
| 8 | HDFC Nifty500 Multicap 50:25:25 Index Fund | Multicap Index | [Link](https://groww.in/mutual-funds/hdfc-nifty500-multicap-50:25:25-index-fund-direct-growth) |
| 9 | HDFC Diversified Equity All Cap Active FoF | Fund of Funds | [Link](https://groww.in/mutual-funds/hdfc-diversified-equity-all-cap-active-fof-direct-growth) |
| 10 | HDFC Nifty India Digital Index Fund | Thematic Index | [Link](https://groww.in/mutual-funds/hdfc-nifty-india-digital-index-fund-direct-growth) |

#### Source Document Types
| Document Type | Description |
| :--- | :--- |
| Scheme Factsheets | Monthly/quarterly performance and holdings data |
| KIM (Key Information Memorandum) | Investor-facing scheme summary |
| SID (Scheme Information Document) | Detailed legal and operational scheme document |
| AMC FAQ / Help Pages | Official Q&A and user guides from the AMC website |
| AMFI / SEBI Guidance Pages | Regulatory and investor education resources |
| Statement & Tax Download Guides | Instructions for downloading CAS, capital gains reports, etc. |

### 4.3. Query Handling Pipeline
```
User Query → Intent Classification → Retrieval from Corpus → Response Generation → Citation Attachment → Output
                    ↓ (if advisory/subjective)
              Refusal Response + Educational Link
```

---

## 5. Supported Query Categories

The assistant must be able to answer the following **facts-only** query types:

| Category | Example Queries |
| :--- | :--- |
| **Basic Scheme Details** | Expense ratio, exit load details, minimum SIP amount, ELSS lock-in period |
| **Risk & Classification** | Riskometer classification, benchmark index, risk profile (Conservative / Moderate / Aggressive) |
| **Performance & Valuation** | Net Asset Value (NAV), last 3 years returns |
| **Portfolio & Management** | Scheme asset split (Equity vs. Debt vs. Hybrid), fund manager details, top holding details |
| **Tools & Processes** | SIP/Lumpsum Calculator *(educational purposes only)*, process to download account statements or capital gains reports |

---

## 6. Response Formatting Rules

Every successful (non-refusal) response **must** follow this exact structure:

| Rule | Requirement |
| :--- | :--- |
| **Length** | Maximum of **3 sentences** |
| **Citation** | Exactly **one** citation link to the official source document |
| **Footer** | Must end with: `Last updated from sources: <date>` |

### Example Response Format
```
The expense ratio of [Scheme Name] Direct Growth plan is 0.35% per annum.
This is an annual charge deducted from the fund's NAV daily.
Source: [AMC Factsheet URL]

Last updated from sources: 2026-07-01
```

---

## 7. Refusal Handling Context

### 7.1. What Must Be Refused
Any query that is **non-factual, subjective, comparative, or advisory** in nature.

#### Examples of Refusable Queries
- *"Should I invest in HDFC Nifty 50 Index Fund?"*
- *"Which fund is better — HDFC Nifty 50 or HDFC Nifty Next 50?"*
- *"Is this a good time to start an SIP in HDFC Banking & Financial Services Fund?"*
- *"Will HDFC Gold ETF Fund of Fund give good returns?"*
- *"Is HDFC Corporate Debt Opportunities Fund safe for long-term investment?"*

### 7.2. Refusal Response Requirements
| Aspect | Requirement |
| :--- | :--- |
| **Tone** | Polite, professional, clearly worded |
| **Boundary Reinforcement** | Must state it is a facts-only assistant |
| **Educational Redirect** | Provide a relevant AMFI or SEBI investor education link |

### Example Refusal Response
```
I'm a facts-only assistant and cannot provide investment advice or fund comparisons.
For investment guidance, please consult a SEBI-registered financial advisor.
You may find helpful educational resources here: https://www.amfiindia.com/investor-corner

Last updated from sources: 2026-07-01
```

---

## 8. User Interface Context

The UI must be **clean, minimal, and intuitive** with these mandatory elements:

| Element | Details |
| :--- | :--- |
| **Welcome Message** | Explains the assistant's purpose and capabilities |
| **Example Questions** | Three (3) clickable or visible sample queries to guide first-time users |
| **Disclaimer** | Prominently displayed: **"Facts-only. No investment advice."** |

---

## 9. Compliance & Constraint Matrix

### 9.1. Data & Source Constraints
- ✅ **Allowed:** Official HDFC Mutual Fund website (`hdfcfund.com`), Groww scheme pages, AMFI portal, SEBI portal.
- ❌ **Prohibited:** Third-party blogs, financial news portals, aggregator websites (e.g., Moneycontrol, ET Money, Value Research).

### 9.2. Privacy & Security Constraints
The system must implement **zero data collection**. The following PII fields are strictly **prohibited** from being collected, stored, or processed:

| Prohibited Data | Reason |
| :--- | :--- |
| PAN Numbers | Personally identifiable tax ID |
| Aadhaar Numbers | Government-issued identity |
| Bank Account Numbers | Financial account information |
| OTPs | Authentication credentials |
| Email Addresses | Contact PII |
| Phone Numbers | Contact PII |

### 9.3. Content Restrictions
| Restriction | Details |
| :--- | :--- |
| **No Advisory Content** | Zero tolerance for investment advice, buy/sell/hold recommendations, or opinionated commentary |
| **No Custom Comparisons** | Do not perform fund-vs-fund comparisons or future return projections |
| **Performance Queries** | For any performance-related query, respond with factual data AND provide a direct link to the official scheme factsheet |

### 9.4. Transparency Requirements
- Every answer must be **short, factual, and independently verifiable**.
- Every answer must include its **source link** and **last-updated timestamp**.

---

## 10. Deliverables Checklist

| # | Deliverable | Contents |
| :--- | :--- | :--- |
| 1 | **README Document** | Setup instructions, selected AMC & schemes, RAG architecture overview, known limitations |
| 2 | **Disclaimer Snippet** | `"Facts-only. No investment advice."` integrated across UI and outputs |
| 3 | **Automated Scheduler** | GitHub Actions scheduled cron workflow (`scheduled_ingestion.yml`), secure API webhook (`INGEST_ADMIN_TOKEN`), and mutex read/write locking to ensure real-time data freshness without manual re-ingestion |

---

## 11. Success Criteria (Acceptance Gates)

| # | Criterion | Description |
| :--- | :--- | :--- |
| 1 | **Accurate Retrieval** | Highly accurate extraction of factual mutual fund information from the curated corpus |
| 2 | **Strict Adherence** | Zero deviation from the facts-only mandate; complete absence of speculative or advisory language |
| 3 | **Consistent Citations** | 100% compliance — every substantive answer includes exactly one valid source link and the "Last updated" footer |
| 4 | **Robust Refusal** | Reliable detection and polite refusal of investment advice requests and subjective comparisons |
| 5 | **User Experience** | Clean, minimal, lightweight interface with clear disclaimers and helpful sample queries |

---

## 12. Key Domain Terminology

| Term | Full Form / Meaning |
| :--- | :--- |
| **AMC** | Asset Management Company — the entity that manages mutual fund schemes |
| **AMFI** | Association of Mutual Funds in India — the industry body |
| **SEBI** | Securities and Exchange Board of India — the financial regulator |
| **NAV** | Net Asset Value — the per-unit market value of a mutual fund scheme |
| **SIP** | Systematic Investment Plan — periodic fixed-amount investment |
| **ELSS** | Equity Linked Savings Scheme — a tax-saving mutual fund category with a 3-year lock-in |
| **KIM** | Key Information Memorandum — a concise scheme summary for investors |
| **SID** | Scheme Information Document — the detailed legal document governing a scheme |
| **RAG** | Retrieval-Augmented Generation — an AI architecture that retrieves relevant documents before generating a response |
| **CAS** | Consolidated Account Statement — a single statement of all mutual fund holdings |
| **Riskometer** | A SEBI-mandated risk classification gauge (Low → Very High) |
| **Expense Ratio** | The annual fee charged by the fund, expressed as a percentage of AUM |
| **Exit Load** | A fee charged when an investor redeems units before a specified period |
| **AUM** | Assets Under Management — total market value of investments managed by the fund |

---

> [!NOTE]
> This context document is derived entirely from the [Problem Statement](file:///c:/Users/DELL/Pictures/Milestone%201/RAG%20Chatbot/docs/problemstatement.md). It should be updated if the problem statement is revised.
