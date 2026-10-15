"""Creates explicitly synthetic demo cases. Never confuse them with applicants."""
from app.main import db,now,log
from app.engine import build_brief
EXAMPLES=[
 ('I want to learn AI, but I am unsure whether university degree credits are separate.','I need to know exactly who awards the recognised B.Tech degree.','curriculum','degree','comparing','comparing','Pune'),
 ('I like coding but want to know if paid internships are guaranteed.','The published salary stats look impressive, are these for this NIAT batch?','placements','placements','ready','exploring','Hyderabad'),
 ('Is there a scholarship based on my NAT score?','Can someone give a written four-year tuition and hostel cost?','scholarship','fees','comparing','comparing','Chennai'),
 ('I want to explore machine learning electives in the first year.','Does this university have safe hostel facilities for first-year students?','curriculum','campus','exploring','ready','Kolhapur'),
 ('How should I prepare for the NAT examination and what is next?','Can we get the exact tuition and refund terms before paying anything?','test','fees','ready','exploring','Bengaluru'),
 ('I want actual projects with mentors, not just lectures.','Is it a real university degree from a UGC-recognised institution?','curriculum','degree','comparing','comparing','Delhi NCR')]
def seed():
    with db() as c:
        for i,(st,pa,sp,pp,sr,pr,place) in enumerate(EXAMPLES,1):
            code=f'DEMOCASE{i:02d}'
            if c.execute('SELECT 1 FROM sessions WHERE code=?',(code,)).fetchone():continue
            c.execute("INSERT INTO sessions(code,created_at,variant,is_demo) VALUES(?,?,?,1)",(code,now(),'A' if i%2 else 'B'))
            log(c,code,'session_created',{'synthetic':True})
            for role,concern,priority,readiness in [('student',st,sp,sr),('parent',pa,pp,pr)]:
                c.execute('INSERT INTO responses VALUES(?,?,?,?,?,?,?)',(code,role,concern,priority,readiness,place,now()));log(c,code,role+'_submitted',{'synthetic':True})
            brief=build_brief({'concern':st,'priority':sp},{'concern':pa,'priority':pp})
            for card in brief['cards']:
                c.execute('INSERT OR IGNORE INTO followups(code,topic,question,created_at) VALUES(?,?,?,?)',(code,card['topic'],card['question'],now()))
        print('Synthetic demo seeded: http://localhost:8000/s/DEMOCASE01/brief')
if __name__=='__main__':seed()
