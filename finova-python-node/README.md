# Finova AI Market Intelligence Dashboard (Python + Node.js Split)

This repository contains the split-architecture version of the Finova AI Market Intelligence Dashboard:
* **Frontend (`/frontend`)**: Built on Node.js using React 19, Vite, TypeScript 5, and Tailwind CSS 4.
* **Backend (`/backend`)**: Built on Python 3.10+ using FastAPI and Uvicorn.

This setup decouples the frontend client code from the data orchestration, API caching, rate limit key-rotation, and Gemini AI streaming.

---

## Folder Structure

```text
finova-python-node/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── providers/        # Finnhub, Alpha Vantage, Roic AI providers
│   │   ├── symbols/          # Local stock search database
│   │   ├── cache.py          # L1 & L2 (file-based) caching logic
│   │   ├── copilot.py        # Gemini copilot & system context builders
│   │   ├── main.py           # FastAPI routes and middleware
│   │   └── config.py         # Backend environment parameters
│   ├── run.py                # Server startup script
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Backend environment template
│
└── frontend/                 # Node.js React/Vite Frontend
    ├── src/                  # Application source code (pages, components, hooks)
    ├── index.html            # Main HTML entry point
    ├── package.json          # Node dependencies
    └── vite.config.ts        # Vite configuration with proxy rules
```

---

## Installation & Setup

### 1. Backend Setup (Python)

Navigate to the `backend` folder and follow these steps:

1. **Create and Activate a Virtual Environment** (Optional but recommended):
   ```bash
   cd backend
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   copy .env.example .env
   ```
   Provide your:
   * `FINNHUB_API_KEY` (and `FINNHUB_API_KEY_2` for rotation)
   * `ALPHA_VANTAGE_API_KEY` (up to 4 keys)
   * `GEMINI_API_KEY`

4. **Run the Backend**:
   ```bash
   python run.py
   ```
   The backend will start on **`http://127.0.0.1:8000`**. You can view the API documentation (Swagger UI) at **`http://127.0.0.1:8000/docs`**.

---

### 2. Frontend Setup (Node.js)

Navigate to the `frontend` folder and follow these steps:

1. **Install Node Modules**:
   ```bash
   cd ../frontend
   npm install
   ```

2. **Configure Port & Environment**:
   Vite by default runs on port `3000`. The `vite.config.ts` includes a proxy rewrite rule that redirects all `/api/*` calls from port `3000` to port `8000` automatically.
   *(Note: You do NOT need to configure API keys on the frontend anymore; they are securely loaded by the Python backend).*

3. **Run the Dev Server**:
   ```bash
   npm run dev
   ```
   Open **`http://localhost:3000`** in your browser.

---

## Features Migrated

1. **CORS & Proxying**: Frontend calls `/api/market/quote` relative paths. Next.js proxies these to the FastAPI backend at port `8000`, resolving cross-origin requests seamlessly.
2. **Key Rotation & Orchestration**: Finnhub (2 keys) and Alpha Vantage (4 keys) rotate automatically in Python when 429 or rate limits are reached. Gaps in metrics are filled using `roic_ai.py` scraper.
3. **Double Caching**: 
   * **L1**: Fast in-memory caching in Python.
   * **L2**: Disk-persistent daily candles (24h TTL) stored in `backend/data/candles/{SYM}.json`.
4. **SSE AI Streaming**: Gemini streaming answers for both the `Copilot` and `Support Chat` stream via server-sent events (`text/event-stream`), matching the exact payload expectations of the React frontend.
5. **Technical Indicators & Sector performance**: Re-implemented indicators (RSI, SMA, BBands) and sectors (SPDR ETF performance) in Python.
