from __future__ import annotations
import csv, hashlib, io, json, os, secrets, sqlite3, time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .engine import EVIDENCE, build_brief, optional_llm_summary
ROOT=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv('NIAT_DB_PATH',str(ROOT.parent/'data.sqlite3')))
DEMO_MODE=os.getenv('DEMO_MODE','1')!='0'

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if DEMO_MODE:
        try:
            import seed_demo
            seed_demo.seed()
        except Exception as e:
            print(f'Notice: demo seeding skipped: {e}')
    yield

app=FastAPI(title='NIAT Decision Lab',description='Consent-first student/parent paired decision evidence flow',lifespan=lifespan)
app.mount('/static', StaticFiles(directory=str(ROOT/'static')),name='static')
templates=Jinja2Templates(directory=str(ROOT/'templates'))
security=HTTPBasic(auto_error=False)

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
        conn.commit()
    finally: conn.close()

def init_db():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS sessions (code TEXT PRIMARY KEY,created_at TEXT NOT NULL,variant TEXT NOT NULL,is_demo INTEGER DEFAULT 0, outcome TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS responses (session_code TEXT NOT NULL,role TEXT NOT NULL,concern TEXT NOT NULL, priority TEXT NOT NULL,readiness TEXT NOT NULL, location TEXT DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(session_code,role));
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,event TEXT NOT NULL,time TEXT NOT NULL,meta TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS followups (id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT NOT NULL,topic TEXT NOT NULL,question TEXT NOT NULL,status TEXT DEFAULT 'open',created_at TEXT NOT NULL,UNIQUE(code,topic));''')

def log(c,code,event,meta=None): c.execute('INSERT INTO events(code,event,time,meta) VALUES(?,?,?,?)',(code,event,now(),json.dumps(meta or {})))
def grab(c,code):
    s=c.execute('SELECT * FROM sessions WHERE code=?',(code,)).fetchone()
    if not s:raise HTTPException(404,'Session not found')
    return dict(s)
def responses(c,code): return {r['role']:dict(r) for r in c.execute('SELECT * FROM responses WHERE session_code=?',(code,)).fetchall()}
def page(req,name,**params):return templates.TemplateResponse(request=req,name=name,context={'title':'NIAT Decision Lab','evidence':EVIDENCE,'demo_mode':DEMO_MODE,**params})

@app.get('/health')
def health():return {'ok':True,'model':'local ML classifier','demo':DEMO_MODE}
@app.get('/',response_class=HTMLResponse)
def index(request:Request):return page(request,'home.html')
@app.post('/create')
def create(request:Request):
    code=secrets.token_urlsafe(10).replace('-','').replace('_','')[:13].upper()
    with db() as c:
        c.execute('INSERT INTO sessions(code,created_at,variant,is_demo) VALUES(?,?,?,0)',(code,now(),'A' if int(hashlib.sha256(code.encode()).hexdigest(),16)%2==0 else 'B'))
        log(c,code,'session_created')
    return RedirectResponse('/s/'+code,303)
@app.get('/s/{code}',response_class=HTMLResponse)
def session(request:Request,code:str):
    with db() as c: s=grab(c,code); answers=responses(c,code)
    return page(request,'session.html',session=s,answers=answers)
@app.get('/s/{code}/brief',response_class=HTMLResponse)
def brief(request:Request,code:str):
    with db() as c:
        s=grab(c,code); answers=responses(c,code)
        if len(answers)<2:return page(request,'waiting.html',session=s,answers=answers)
        b=build_brief(answers['student'],answers['parent'])
        for card in b['cards']:
            c.execute('INSERT OR IGNORE INTO followups(code,topic,question,created_at) VALUES(?,?,?,?)',(code,card['topic'],card['question'],now()))
        log(c,code,'brief_viewed',{'topics':b['topics']})
        tickets=[dict(x) for x in c.execute('SELECT * FROM followups WHERE code=?',(code,))]
    summary=optional_llm_summary(answers['student'],answers['parent'],b)
    if summary:b['generation_mode']='Local NLP model + OpenAI API evidence-based synthesis'
    return page(request,'brief.html',session=s,answers=answers,brief=b,summary=summary,tickets=tickets)

@app.get('/s/{code}/{role}',response_class=HTMLResponse)
def intake(request:Request,code:str,role:Literal['student','parent']):
    with db() as c: s=grab(c,code); answer=responses(c,code).get(role,{})
    return page(request,'intake.html',session=s,role=role,answer=answer)
@app.post('/s/{code}/request-review')
def review(code:str):
    with db() as c:grab(c,code);log(c,code,'counsellor_review_requested')
    return RedirectResponse('/s/'+code+'/brief?review=1',303)

@app.post('/s/{code}/{role}')
def save_intake(code:str,role:Literal['student','parent'],concern:str=Form(...),priority:str=Form(...),readiness:str=Form(...),location:str=Form(''),consent:str=Form('')):
    concern=concern.strip(); location=location.strip()
    if consent!='yes':raise HTTPException(400,'Consent required to store the anonymous response')
    if len(concern)<8 or len(concern)>800:raise HTTPException(400,'Concern must be 8–800 characters')
    if priority not in EVIDENCE or len(location)>80 or readiness not in ('exploring','comparing','ready'):raise HTTPException(400,'Invalid input')
    with db() as c:
        grab(c,code)
        c.execute('''INSERT INTO responses (session_code,role,concern,priority,readiness,location,updated_at) VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(session_code,role) DO UPDATE SET concern=excluded.concern,priority=excluded.priority,readiness=excluded.readiness,location=excluded.location,updated_at=excluded.updated_at''',(code,role,concern,priority,readiness,location,now()))
        log(c,code,role+'_submitted')
    return RedirectResponse('/s/'+code+'/brief',303)
@app.get('/evidence',response_class=HTMLResponse)
def sources(request:Request):return page(request,'evidence.html')

# Public dashboard contains only aggregate, anonymous event counts. Counsellor queue has HTTP Basic access.
def counts(c):
    rows=c.execute('''SELECT is_demo,COUNT(*) sessions, SUM(CASE WHEN (SELECT COUNT(*) FROM responses r WHERE r.session_code=s.code)>=1 THEN 1 ELSE 0 END) partial,
       SUM(CASE WHEN (SELECT COUNT(*) FROM responses r WHERE r.session_code=s.code)=2 THEN 1 ELSE 0 END) paired, SUM(CASE WHEN outcome='enrolled' THEN 1 ELSE 0 END) enrolled FROM sessions s GROUP BY is_demo''').fetchall()
    return [dict(x) for x in rows]
@app.get('/dashboard',response_class=HTMLResponse)
def dashboard(request:Request):
    with db() as c:
        stats=counts(c)
        by_topic=[dict(x) for x in c.execute('SELECT topic,COUNT(*) n FROM followups GROUP BY topic ORDER BY n DESC')]
        requests=c.execute("SELECT COUNT(DISTINCT code) FROM events WHERE event='counsellor_review_requested'").fetchone()[0]
    return page(request,'dashboard.html',stats=stats,by_topic=by_topic,requests=requests)

def admin_auth(credentials:HTTPBasicCredentials|None=Depends(security)):
    expected=os.getenv('ADMIN_PASSWORD','')
    if not expected:raise HTTPException(503,'Admin disabled until ADMIN_PASSWORD is configured')
    ok=credentials and secrets.compare_digest(credentials.username,'counsellor') and secrets.compare_digest(credentials.password,expected)
    if not ok:raise HTTPException(401,'Counsellor access only',headers={'WWW-Authenticate':'Basic'})
@app.get('/admin',response_class=HTMLResponse,dependencies=[Depends(admin_auth)])
def admin(request:Request):
    with db() as c:
        queue=[dict(x) for x in c.execute('''SELECT f.id,f.code,f.topic,f.question,f.status,s.is_demo FROM followups f JOIN sessions s ON f.code=s.code ORDER BY CASE WHEN f.status='open' THEN 0 ELSE 1 END,f.id DESC LIMIT 100''')]
    return page(request,'admin.html',queue=queue)
@app.post('/admin/followups/{fid}/complete',dependencies=[Depends(admin_auth)])
def close_ticket(fid:int):
    with db() as c:
        f=c.execute('SELECT code FROM followups WHERE id=?',(fid,)).fetchone()
        if not f:raise HTTPException(404,'Not found')
        c.execute("UPDATE followups SET status='answered' WHERE id=?",(fid,)); log(c,f['code'],'evidence_answered',{'id':fid})
    return RedirectResponse('/admin',303)
@app.post('/admin/outcomes/{code}',dependencies=[Depends(admin_auth)])
def update_outcome(code:str,outcome:str=Form(...)):
    if outcome not in ('pending','not_proceeding','enrolled'):raise HTTPException(400,'Invalid outcome')
    with db() as c:grab(c,code);c.execute('UPDATE sessions SET outcome=? WHERE code=?',(outcome,code));log(c,code,'decision_recorded',{'outcome':outcome})
    return RedirectResponse('/admin',303)
@app.get('/admin/export.csv',dependencies=[Depends(admin_auth)])
def export_csv():
    with db() as c: rows=c.execute('SELECT f.code,f.topic,f.question,f.status,s.is_demo,s.outcome FROM followups f JOIN sessions s ON f.code=s.code').fetchall()
    buf=io.StringIO();w=csv.writer(buf);w.writerow(['case_code','topic','evidence_request','status','is_demo','outcome']); w.writerows([list(x) for x in rows])
    return StreamingResponse(iter([buf.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=niat_review_queue.csv'})
