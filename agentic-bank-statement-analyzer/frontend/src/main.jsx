import React,{useState} from 'react';import{createRoot}from'react-dom/client';import axios from'axios';import{Upload,BrainCircuit,TrendingUp,WalletCards,MessageSquare,FileText,ArrowUpRight,ArrowDownRight}from'lucide-react';import{BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer}from'recharts';import'./styles.css';
const API='https://agentic-bank-statement-analyzer.onrender.com';
function App(){
  const[file,setFile]=useState(null);
  const[data,setData]=useState(null);
  const[busy,setBusy]=useState(false);
  const[q,setQ]=useState('');
  const[answer,setAnswer]=useState('');

  const analyze=async()=>{
    if(!file)return;
    setBusy(true);
    try{
      const fd=new FormData();
      fd.append('file',file);
      const r=await axios.post(API+'/api/statements/analyze',fd);
      setData(r.data);
      setAnswer('');
    }catch(e){
      alert(e.response?.data?.detail||'Analysis failed');
    }finally{
      setBusy(false);
    }
  };

  const ask=async()=>{
    if(!q||!data)return;
    try{
      const r=await axios.post(API+'/api/agent/chat',{statement_id:data.statement_id,question:q});
      setAnswer(r.data.answer);
    }catch(e){
      alert(e.response?.data?.detail||'Agent error');
    }
  };

  const a=data?.analytics;
  const chart=a?Object.entries(a.by_category).map(([name,value])=>({name,value})):[];

  return <div className="app">
    <nav>
      <div className="brand"><BrainCircuit size={24}/> ABS Analyzer</div>
      <div className="navright"><span>Financial Intelligence</span></div>
    </nav>
    <main>
      <section className="hero">
        <div>
          <div className="eyebrow">AGENTIC FINANCIAL ANALYTICS</div>
          <h1>Turn bank statements into <span>actionable intelligence.</span></h1>
          <p>Upload a PDF statement and let an agentic workflow extract transactions, categorize spending, analyze cash flow, detect unusual activity, and answer questions about your finances.</p>
        </div>
      </section>

      <section className="upload">
        <div className="drop">
          <Upload size={32}/>
          <h2>Analyze a bank statement</h2>
          <p>PDF only · up to 15 MB</p>
          <input type="file" accept="application/pdf" onChange={e=>setFile(e.target.files[0])}/>
          {file&&<div className="file"><FileText size={17}/>{file.name}</div>}
          <button className="primary" disabled={!file||busy} onClick={analyze}>{busy?'Analyzing…':'Run Agentic Analysis'}</button>
        </div>
        <div className="workflow">
          <h3>Agent workflow</h3>
          <div>01 <b>Extract</b><span>Read transactions from the PDF</span></div>
          <div>02 <b>Understand</b><span>Categorize and normalize data</span></div>
          <div>03 <b>Analyze</b><span>Cash flow, trends, anomalies and savings</span></div>
          <div>04 <b>Explain</b><span>RAG/LLM-assisted conversational insights</span></div>
        </div>
      </section>

      {a&&<>
        <section className="metrics">
          <Metric title="Income" value={a.income} icon={<ArrowUpRight/>}/>
          <Metric title="Expenses" value={a.expenses} icon={<ArrowDownRight/>}/>
          <Metric title="Net Cash Flow" value={a.net_cash_flow} icon={<WalletCards/>}/>
          <Metric title="Savings Rate" value={`${a.savings_rate}%`} icon={<TrendingUp/>}/>
        </section>
        <section className="grid">
          <div className="panel">
            <div className="panelhead"><div><h2>Spending intelligence</h2><p>{a.transaction_count} transactions analyzed</p></div></div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chart}><XAxis dataKey="name" tick={{fontSize:11}}/><YAxis/><Tooltip/><Bar dataKey="value" radius={[8,8,0,0]}/></BarChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h2>Agentic analyst</h2>
            <p>Ask questions about the analyzed statement.</p>
            <div className="suggestions">
              <button onClick={()=>setQ('What was my highest expense?')}>Highest expense?</button>
              <button onClick={()=>setQ('How much did I spend on food?')}>Food spending?</button>
              <button onClick={()=>setQ('How much money came in versus went out?')}>Income vs expenses?</button>
              <button onClick={()=>setQ('Where can I reduce my spending?')}>Where can I save?</button>
            </div>
            <div className="chat">
              <textarea value={q} onChange={e=>setQ(e.target.value)} placeholder="Ask the financial agent…"/>
              <button className="primary" onClick={ask}><MessageSquare size={16}/> Ask Agent</button>
              {answer&&<div className="answer"><b>Agent insight</b><p>{answer}</p></div>}
            </div>
          </div>
        </section>
        <section className="panel">
          <h2>Largest detected expenses</h2>
          <div className="table">
            {a.top_expenses.map((r,i)=><div className="row" key={i}><span>{r.date}</span><strong>{r.description}</strong><span>{r.category}</span><b>{Math.abs(r.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</b></div>)}
          </div>
        </section>
      </>}
    </main>
    <footer>Agentic Bank Statement Analyzer · Built for intelligent financial document analysis</footer>
  </div>;
}

function Metric({title,value,icon}){
  return <div className="metric"><div className="icon">{icon}</div><small>{title}</small><strong>{typeof value==='number'?value.toLocaleString(undefined,{minimumFractionDigits:2}):value}</strong></div>;
}

createRoot(document.getElementById('root')).render(<App/>);
