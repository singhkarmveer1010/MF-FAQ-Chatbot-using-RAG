# 🚀 Production Deployment Plan: Mutual Fund FAQ Assistant

> **Project:** HDFC Mutual Fund Facts-Only RAG Chatbot  
> **Backend Target:** [Railway](https://railway.app) (Docker + Persistent Volume + FastAPI + ChromaDB)  
> **Frontend Target:** [Vercel](https://vercel.com) (Next.js 16 App Router + TypeScript + Obsidian Dark Theme)  
> **AI Engine:** Groq Cloud API (`llama-3.3-70b-versatile`) + BAAI/bge-small-en-v1.5  

---

## 🏛️ Executive Summary & Architecture Topology

This document provides an end-to-step, production-ready guide for deploying the **Mutual Fund FAQ Assistant** in a decoupled cloud architecture. The backend API is hosted on **Railway** inside a Docker container with an attached persistent volume for the ChromaDB vector store. The high-performance web interface is built with **Next.js (App Router & TypeScript)** in the `frontend/` directory, styling exclusively with Vanilla CSS in an ultra-premium dark obsidian theme. It is deployed to **Vercel's Global Edge Network**, utilizing API rewrites to communicate seamlessly with the backend without Cross-Origin Resource Sharing (CORS) complications or exposing internal endpoints.

```mermaid
flowchart TB
    subgraph Users["👤 End Users & Retail Investors"]
        Browser["Web Browser / Mobile Device"]
    end

    subgraph Vercel["⚡ Vercel Global Edge CDN (Next.js Frontend)"]
        UI["Next.js App Router Engine<br/>(frontend/: page.tsx, globals.css, Sidebar, ChatArea)"]
        Rewrite["Next.js & Vercel API Proxy Rewrite<br/>(/api/* ➔ Railway Domain)"]
    end

    subgraph Railway["🚂 Railway Cloud Platform (Backend API)"]
        Container["Docker Container<br/>(FastAPI Uvicorn Server - Port 8000)"]
        Volume[("Persistent Railway Volume<br/>(/app/vectorstore - ChromaDB)")]
        Scheduler["Background Ingestion Daemon<br/>(APScheduler / Threading)"]
    end

    subgraph External["🌐 External APIs & Data Sources"]
        Groq["Groq Cloud API<br/>(Llama 3.3 70B Versatile)"]
        Groww["Groww Official Scheme Pages<br/>(10 HDFC Mutual Funds)"]
        GitHub["GitHub Actions CI/CD<br/>(scheduled_ingestion.yml)"]
    end

    Browser <-->|HTTPS / UI Interaction| UI
    UI <-->|Fetch /api/query, /api/schemes| Rewrite
    Rewrite <-->|Secure Proxy HTTPS| Container
    Container <-->|Read / Write Vectors| Volume
    Container <-->|High-Speed LLM Inference| Groq
    Scheduler -->|Periodic Scraping| Groww
    Scheduler -->|Update Index| Volume
    GitHub -.->|Daily Cron Webhook Trigger| Container
```

---

## 📋 Pre-Deployment Requirements & Checklist

Before starting the deployment process, ensure you have the following credentials and accounts ready:

| Requirement | Description | Link / Action |
| :--- | :--- | :--- |
| **GitHub Account** | Repository containing the codebase pushed to GitHub | [github.com](https://github.com) |
| **Railway Account** | For hosting the Python backend container and persistent storage | [railway.app](https://railway.app) |
| **Vercel Account** | For hosting the high-speed Next.js frontend interface | [vercel.com](https://vercel.com) |
| **Groq API Key** | High-speed LLM inference key (`gsk_...`) | [console.groq.com](https://console.groq.com) |
| **Admin Secret Token** | A secure random string for triggering manual ingestion webhooks | Generate via `openssl rand -hex 32` or pick a secure password |

---

## 🚂 Phase 1: Backend Deployment on Railway

Railway will automatically detect the root `Dockerfile`, build the Python 3.10 image, install dependencies from `requirements.txt`, and expose the FastAPI server.

### Step 1.1: Create New Railway Project
1. Log into your [Railway Dashboard](https://railway.app/dashboard).
2. Click **+ New Project** ➔ Select **Deploy from GitHub repo**.
3. Select your `RAG Chatbot` repository.
4. Railway will initialize the service and begin an initial build. *Note: Do not worry if the first request returns an empty scheme list; we need to configure environment variables and volume storage first.*

### Step 1.2: Configure Environment Variables
Navigate to your Railway service ➔ Click on the **Variables** tab ➔ Click **Raw Editor** (or add one by one) and input the following configuration:

```ini
# --- LLM Provider & Models ---
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# --- Vector Database & Paths ---
VECTOR_STORE_TYPE=chromadb
VECTOR_STORE_PATH=/app/vectorstore

# --- RAG Retrieval & Guardrails ---
RETRIEVAL_TOP_K=5
SIMILARITY_THRESHOLD=0.7
MAX_RESPONSE_SENTENCES=3
LLM_TEMPERATURE=0.0

# --- Server Binding ---
API_HOST=0.0.0.0
API_PORT=8000

# --- Automated Ingestion Security & Cron ---
INGESTION_CRON=0 5 * * *
INGESTION_INTERVAL_HOURS=24
INGEST_ADMIN_TOKEN=your_secure_admin_token_here
```

> [!IMPORTANT]
> Ensure `VECTOR_STORE_PATH` is set explicitly to `/app/vectorstore`. This matches the directory created in the Dockerfile (`RUN mkdir -p vectorstore`) and is where we will mount the persistent volume.

### Step 1.3: Attach a Persistent Volume (CRITICAL STEP)
By default, Docker containers on cloud platforms are **stateless**. Because `.gitignore` excludes `vectorstore/*.sqlite3` from Git, your database will wipe on every redeployment unless a persistent volume is attached.

1. In Railway, click on your service card ➔ Go to the **Volumes** tab (or press Cmd/Ctrl + K and search "Add Volume").
2. Click **+ Create Volume**.
3. Set the **Mount Path** to exactly:
   ```text
   /app/vectorstore
   ```
4. Click **Add Volume**. Railway will automatically restart the container with the persistent storage attached.

### Step 1.4: Generate a Public Domain
1. Go to the **Settings** tab of your Railway service.
2. Scroll down to the **Networking** section.
3. Click **Generate Domain** under **Public Networking** (or attach a custom domain).
4. You will receive a URL like: `https://rag-chatbot-production.up.railway.app`.
5. **Test Backend Liveness:** Open `https://rag-chatbot-production.up.railway.app/api/health` in your browser. You should receive a JSON response:
   ```json
   {
     "status": "healthy",
     "engine": "llama-3.3-70b",
     "vectorstore": "connected"
   }
   ```

### Step 1.5: Bootstrap the Vector Database (Initial Ingestion)
Since the persistent volume starts empty, we must trigger an initial scrape of the 10 HDFC Mutual Fund scheme pages to populate ChromaDB.

Open your terminal or command prompt and run the following `curl` command (replace `<YOUR-RAILWAY-URL>` and `<YOUR-ADMIN-TOKEN>` with your actual values):

```bash
curl -X POST "https://rag-chatbot-production.up.railway.app/api/ingest?background=true" \
  -H "Authorization: Bearer your_secure_admin_token_here" \
  -H "Content-Type: application/json"
```

> [!TIP]
> **Verification:** Wait 30–60 seconds for the scraper to finish processing, then visit `https://rag-chatbot-production.up.railway.app/api/schemes`. You should see the complete list of 10 HDFC Mutual Fund schemes returned in the JSON array!

---

## ⚡ Phase 2: Frontend Deployment on Vercel

The frontend is a standalone, modern **Next.js TypeScript application** located inside the `frontend/` directory. We will host it on Vercel and configure a proxy rewrite so the browser communicates seamlessly with your Railway backend.

### Step 2.1: Import Repository in Vercel
1. Log into your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** ➔ **Project**.
3. Import your `RAG Chatbot` repository from GitHub.
4. In the **Configure Project** screen:
   - **Framework Preset:** Leave as `Next.js` (Vercel will auto-detect it when the root directory is set).
   - **Root Directory:** Click **Edit** and select `frontend` (or type `frontend`).
5. Do **not** click Deploy yet! Proceed to Step 2.2 first.

### Step 2.2: Configure Vercel API Rewrites (`vercel.json` & `next.config.ts`)
To prevent CORS errors and avoid hardcoding production backend URLs inside frontend components, the Next.js app utilizes proxy rewrites. When the frontend calls `/api/query` or `/api/schemes`, Vercel's edge network securely forwards the request to your Railway backend.

A configuration file named `vercel.json` has been prepared in `frontend/vercel.json`. Verify that its content matches:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://rag-chatbot-production.up.railway.app/api/:path*"
    }
  ]
}
```

> [!NOTE]
> **Before deploying to Vercel:** Open `frontend/vercel.json` in your code editor and replace `rag-chatbot-production.up.railway.app` with the actual domain generated by Railway in Step 1.4. Commit and push this change to GitHub! *(Alternatively, you can set the environment variable `NEXT_PUBLIC_API_URL` to your Railway URL in Vercel's Environment Variables tab).*

### Step 2.3: Deploy to Production
1. In the Vercel project configuration screen, click **Deploy**.
2. Vercel will build and deploy the Next.js site in seconds.
3. Once complete, click **Visit Domain** (e.g., `https://rag-chatbot-frontend.vercel.app`).
4. Your Groww-inspired dark obsidian mutual fund assistant is now live on Vercel!

---

## 🔄 Phase 3: Automated CI/CD & Scheduled Ingestion

To ensure your chatbot always provides the latest NAVs, expense ratios, and scheme figures without manual intervention, configure the automated GitHub Actions scheduler.

### Step 3.1: Configure GitHub Repository Secrets
Navigate to your GitHub Repository ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ Click **New repository secret**, and add the following two secrets:

| Secret Name | Exact Value Example | Purpose |
| :--- | :--- | :--- |
| `API_BASE_URL` | `https://rag-chatbot-production.up.railway.app` | Tells GitHub Actions where your live backend API is hosted |
| `INGEST_ADMIN_TOKEN` | `your_secure_admin_token_here` | Authorizes the automated cron workflow to trigger re-ingestion |

### Step 3.2: How Automated Scheduling Works
The project includes a pre-configured GitHub Actions workflow at `.github/workflows/scheduled_ingestion.yml`:
1. **Daily Cron Schedule:** Every day at `05:00 UTC` (10:30 AM IST—shortly after mutual fund NAVs and factsheets update), GitHub Actions wakes up.
2. **Secure Webhook Bridge:** It sends an authenticated POST request to your live Railway API (`/api/ingest?background=true`).
3. **Mutex-Protected Scraping:** The Railway container acquires a thread-safe lock (`vector_store_lock` in `scheduler.py`), scrapes official Groww documents, updates chunks in ChromaDB, and releases the lock without dropping ongoing user chat queries.
4. **Manual On-Demand Trigger:** You can also trigger this workflow anytime by going to the **Actions** tab in GitHub ➔ **Automated Ingestion Scheduler** ➔ **Run workflow**.

---

## 🧪 Phase 4: Production Verification & SEBI Compliance Checklist

After completing the deployment, execute the following test suite against your live Vercel frontend URL:

### 1. Catalog & Health Verification
- [ ] **Liveness Indicator:** Verify the green health dot and badge in the top left sidebar of the UI display `SEBI Verified Active` and `llama-3.3-70b`.
- [ ] **Scheme Catalog Loading:** Verify the sidebar enumerates all **10 HDFC Mutual Fund schemes** with custom icons, search filtering, and exact scheme names.

### 2. Factual Retrieval & Citation Accuracy
- [ ] **Fact-Only Query:** Click the example chip *"What is the exit load and expense ratio of HDFC Nifty 50 Index Fund?"*
- [ ] **Response Bounding:** Confirm the AI response is concise and does not exceed **3 sentences** (SEBI readability guardrail).
- [ ] **Attribution Footer:** Verify the response card displays a clickable Groww source button (`View Official Scheme Page ➔`) and a live timestamp.

### 3. SEBI Advisory Refusal Guardrail Test
- [ ] **Advisory Prompt Submission:** Input: *"Which mutual fund should I invest in for maximum returns? Is HDFC Nifty 50 better than SBI Bluechip?"*
- [ ] **Refusal Interception:** Verify the system immediately rejects the request with a **Red/Amber Advisory Refusal Card** stating it can only provide factual disclosures and cannot offer investment advice or comparisons.

### 4. Security & PII Blocking Test
- [ ] **PII Injection Attempt:** Input: *"My PAN number is ABCDE1234F and my phone is 9876543210. Can you check my portfolio?"*
- [ ] **Security Interception:** Confirm the regular expression guardrail blocks the request immediately with a **Purple/Red PII Security Shield Card**, protecting retail investor privacy.

---

## 🛠️ Troubleshooting & Known Solutions

| Symptom / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Sidebar shows "No schemes found" or count is 0** | The persistent volume is empty and initial data ingestion has not run yet. | Execute Step 1.5 (`curl -X POST /api/ingest`) using your admin token to scrape and index the corpus. |
| **Frontend chat requests fail with 404 or CORS Error** | `frontend/vercel.json` is missing or contains the wrong Railway destination URL. | Update `frontend/vercel.json` with your exact Railway HTTPS URL (without trailing slash) and redeploy Vercel. |
| **Railway container crashes during ingestion (Out of Memory)** | BAAI/bge-small-en-v1.5 embedding model loading exceeds available RAM on Micro tier. | In Railway settings, upgrade container resources to at least **1 GB RAM** (Standard tier or higher). |
| **504 Gateway Timeout during manual ingestion** | Scraping 10 pages synchronously takes longer than the standard HTTP request timeout. | Ensure you append `?background=true` to the `/api/ingest` URL so the task runs asynchronously in the background daemon. |

---
*Generated by Antigravity Advanced Agentic Coding for Mutual Fund FAQ Assistant (Phase 8 Next.js Deployment).*
