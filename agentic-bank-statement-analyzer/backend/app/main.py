import os, re, uuid, io, json
from datetime import datetime

import pdfplumber
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv('HF_API_TOKEN', '')
HF_MODEL = os.getenv('HF_MODEL', 'google/gemma-3-4b-it')

app = FastAPI(title='Agentic Bank Statement Analyzer', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

DB_PATH = "abs_analyzer.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


conn = get_db()
conn.execute("""
CREATE TABLE IF NOT EXISTS statements (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
conn.commit()
conn.close()

# ---------- extraction / analytics ----------
CATEGORIES = {
    'Food & Dining': ['restaurant', 'food', 'cafe', 'supermarket', 'grocery', 'hotel', 'uber eats', 'glovo'],
    'Transport': ['uber', 'bolt', 'fuel', 'shell', 'petrol', 'transport', 'matatu', 'airline', 'bus'],
    'Bills & Utilities': ['electricity', 'water', 'internet', 'airtel', 'safaricom', 'utility', 'rent'],
    'Shopping': ['amazon', 'jumia', 'shop', 'mall', 'store', 'clothing'],
    'Healthcare': ['hospital', 'pharmacy', 'clinic', 'medical', 'health'],
    'Entertainment': ['netflix', 'spotify', 'cinema', 'game', 'entertainment'],
    'Transfers': ['transfer', 'mpesa', 'bank transfer', 'send money', 'received'],
    'Salary & Income': ['salary', 'payroll', 'wage', 'income', 'credit'],
}


def parse_amount(s):
    try:
        return float(str(s).replace(',', '').replace('KES', '').replace('KSh', '').strip())
    except Exception:
        return 0.0


def categorize(desc, amount):
    d = desc.lower()
    for cat, words in CATEGORIES.items():
        if any(w in d for w in words):
            return cat
    return 'Other Income' if amount > 0 else 'Other Expense'


def extract_transactions(text):
    lines = [re.sub(r'\s+', ' ', x).strip() for x in text.splitlines() if x.strip()]
    rows = []
    date_re = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b')
    money_re = re.compile(r'(?<!\w)(?:KES\s*)?[-(]?\d[\d,]*(?:\.\d{1,2})?\)?')
    for line in lines:
        dm = date_re.search(line)
        if not dm:
            continue
        amounts = money_re.findall(line[dm.end():])
        if not amounts:
            continue
        nums = [parse_amount(x.replace('(', '-').replace(')', '')) for x in amounts]
        amount = nums[-1]
        desc = line[dm.end():]
        desc = re.sub(r'(?:KES\s*)?[-(]?\d[\d,]*(?:\.\d{1,2})?\)?', ' ', desc)
        desc = re.sub(r'\s+', ' ', desc).strip(' -|')
        if amount > 0 and any(k in desc.lower() for k in ['payment', 'purchase', 'withdraw', 'debit', 'fee', 'charge', 'airtime', 'rent', 'bill']):
            amount = -amount
        rows.append({'date': dm.group(1), 'description': desc or 'Transaction', 'amount': round(amount, 2), 'category': categorize(desc, amount)})
    return rows


def analytics(rows):
    income = sum(r['amount'] for r in rows if r['amount'] > 0)
    expenses = abs(sum(r['amount'] for r in rows if r['amount'] < 0))
    net = income - expenses
    bycat = {}
    for r in rows:
        if r['amount'] < 0:
            bycat[r['category']] = round(bycat.get(r['category'], 0) + abs(r['amount']), 2)
    high = sorted([r for r in rows if r['amount'] < 0], key=lambda x: abs(x['amount']), reverse=True)[:5]
    return {
        'income': round(income, 2),
        'expenses': round(expenses, 2),
        'net_cash_flow': round(net, 2),
        'savings_rate': round((net / income * 100) if income else 0, 2),
        'transaction_count': len(rows),
        'by_category': dict(sorted(bycat.items(), key=lambda x: x[1], reverse=True)),
        'top_expenses': high,
    }


@app.post('/api/statements/analyze')
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, 'PDF files only')
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, 'Maximum PDF size is 15 MB')
    text = ''
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    except Exception:
        raise HTTPException(400, 'Could not read this PDF')
    rows = extract_transactions(text)
    if not rows:
        raise HTTPException(422, 'No transactions could be detected. Try a text-based bank statement PDF.')
    result = {
        'statement_id': str(uuid.uuid4()),
        'filename': file.filename,
        'transactions': rows,
        'analytics': analytics(rows),
        'created_at': datetime.utcnow().isoformat(),
    }

    conn = get_db()
    conn.execute(
        "INSERT INTO statements (id, filename, data, created_at) VALUES (?, ?, ?, ?)",
        (result['statement_id'], file.filename, json.dumps(result), result['created_at']),
    )
    conn.commit()
    conn.close()

    return result


@app.get('/api/statements')
def statements():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, filename, created_at FROM statements ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- agent ----------
class ChatIn(BaseModel):
    statement_id: str
    question: str


def tool_answer(rows, q):
    a = analytics(rows)
    ql = q.lower()
    if 'highest' in ql or 'largest' in ql:
        r = a['top_expenses'][0] if a['top_expenses'] else None
        return f"Your highest detected expense was {abs(r['amount']):,.2f} for {r['description']} ({r['category']}) on {r['date']}." if r else 'I could not identify an expense.'
    if 'food' in ql or 'dining' in ql:
        return f"Detected Food & Dining spending is {a['by_category'].get('Food & Dining', 0):,.2f}."
    if 'income' in ql or 'came in' in ql:
        return f"Total detected income is {a['income']:,.2f}. Total expenses are {a['expenses']:,.2f}, leaving net cash flow of {a['net_cash_flow']:,.2f}."
    if 'reduce' in ql or 'save' in ql:
        top = next(iter(a['by_category']), None)
        return f"Your largest detected spending category is {top} at {a['by_category'].get(top, 0):,.2f}. Reviewing recurring spending in that category is a practical starting point for reducing expenses." if top else 'There is not enough categorized spending data to suggest a reduction area.'
    return f"I found {a['transaction_count']} transactions, {a['income']:,.2f} income, {a['expenses']:,.2f} expenses, and {a['net_cash_flow']:,.2f} net cash flow. Your detected savings rate is {a['savings_rate']:.2f}%."


async def llm_answer(context, q):
    if not HF_TOKEN:
        return None
    prompt = f"You are a financial statement analysis assistant. Use only the supplied data. Do not invent transactions. Give concise, practical answers. DATA: {context}\nQUESTION: {q}"
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post(
                f'https://api-inference.huggingface.co/models/{HF_MODEL}',
                headers={'Authorization': f'Bearer {HF_TOKEN}'},
                json={'inputs': prompt, 'parameters': {'max_new_tokens': 350, 'temperature': 0.2}},
            )
            if r.status_code == 200:
                j = r.json()
                return j[0].get('generated_text', '').replace(prompt, '').strip() if isinstance(j, list) else None
    except Exception:
        return None
    return None


@app.post('/api/agent/chat')
async def chat(data: ChatIn):
    conn = get_db()
    row = conn.execute("SELECT data FROM statements WHERE id = ?", (data.statement_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, 'Statement not found')

    doc = json.loads(row['data'])
    a = doc['analytics']
    context = {'summary': a, 'transactions': doc['transactions'][:100]}
    answer = await llm_answer(str(context), data.question)
    used = 'Hugging Face LLM' if answer else 'Analytics tools'
    if not answer:
        answer = tool_answer(doc['transactions'], data.question)
    return {'answer': answer, 'agent': used}


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'Agentic Bank Statement Analyzer'}
