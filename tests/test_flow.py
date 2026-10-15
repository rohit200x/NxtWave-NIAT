import os,tempfile
from pathlib import Path
os.environ['NIAT_DB_PATH']=str(Path(tempfile.mkdtemp())/'db.sqlite3')
os.environ['ADMIN_PASSWORD']='test-passcode'
from fastapi.testclient import TestClient
from app.main import app
from app.engine import classify,build_brief

def test_real_local_ml_and_evidence():
    r=classify('Who awards my BTech degree and is the university UGC recognised?', 'degree')
    assert r['topic']=='degree'
    assert r['method'].startswith('local')
    b=build_brief({'concern':'I want to learn python and machine learning','priority':'curriculum'},{'concern':'I need university degree recognition','priority':'degree'})
    assert b['alignment']=='Different decision blockers'
    assert len(b['cards'])==2
    assert all(c['url'].startswith('https://') for c in b['cards'])

def test_complete_flow():
    with TestClient(app) as client:
        r=client.post('/create',follow_redirects=False)
        assert r.status_code==303
        code=r.headers['location'].split('/')[-1]
        for role,concern,priority in [('student','I need to learn machine learning and coding projects','curriculum'),('parent','Will my daughter receive a genuine UGC university degree?','degree')]:
            r=client.post(f'/s/{code}/{role}',data={'concern':concern,'priority':priority,'readiness':'comparing','location':'Pune','consent':'yes'},follow_redirects=False)
            assert r.status_code==303
        r=client.get(f'/s/{code}/brief')
        assert r.status_code==200 and b'Different decision blockers' in r.content
        assert b'Open original source' in r.content
        r=client.post(f'/s/{code}/request-review',follow_redirects=False)
        assert r.status_code==303
        r=client.get('/dashboard')
        assert b'NON-DEMO PROTOTYPE SESSIONS' in r.content
        assert client.get('/admin').status_code==401
        r=client.get('/admin',auth=('counsellor','test-passcode'))
        assert r.status_code==200
        assert b'Evidence requested' in r.content
        assert client.get('/admin/export.csv',auth=('counsellor','test-passcode')).status_code==200

def test_reject_no_consent():
    with TestClient(app) as client:
        r=client.post('/create',follow_redirects=False)
        code=r.headers['location'].split('/')[-1]
        r=client.post(f'/s/{code}/student',data={'concern':'This is a real question about tuition','priority':'fees','readiness':'exploring'})
        assert r.status_code==400
