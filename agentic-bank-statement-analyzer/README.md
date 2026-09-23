# Agentic Bank Statement Analyzer

A full-stack financial document intelligence application inspired by the visual hierarchy and project presentation style of the supplied portfolio reference, but implemented as an original application.

## Stack
- Frontend: React + Vite, Recharts, Lucide
- Backend: FastAPI
- Database: MongoDB
- Document extraction: pdfplumber + pypdf
- Agent layer: deterministic financial analysis tools with optional Hugging Face LLM augmentation
- Authentication: JWT + bcrypt
- Deployment target: Vercel/Netlify frontend + Render/Railway backend + MongoDB Atlas

## Features
- Register/login/logout
- PDF-only bank statement upload
- Transaction extraction and normalization
- Automatic categories
- Income, expenses, net cash flow, savings rate
- Spending categories and trends visualization
- Largest expenses
- Unusual/high-value transaction visibility
- Cash-flow analysis
- Savings analysis
- Agentic question answering
- Optional Hugging Face LLM for context-aware explanations
- MongoDB persistence per authenticated user

## Run locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
uvicorn app.main:app --reload --port 8000
```

MongoDB must be running locally or replace `MONGO_URI` with a MongoDB Atlas URI.

For LLM-enhanced answers, add `HF_API_TOKEN` in `.env`. Without it, the built-in analytics agent still answers supported financial questions.

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open the Vite URL, normally http://localhost:5173.

## Important production notes
- Replace `JWT_SECRET` with a strong random secret.
- Restrict CORS to your deployed frontend URL.
- Add encrypted secrets through the hosting provider, never commit `.env`.
- Financial data is sensitive. Add encryption at rest, retention/deletion controls, audit logging, rate limiting, and a clear privacy policy before using real customer statements.
- PDF parsing supports text-based statements. Scanned/image-only statements need an OCR service before production use.
- The system is an analysis tool, not a regulated financial advisor; avoid presenting outputs as professional financial advice.
