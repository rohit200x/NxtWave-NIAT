"""Evidence-constrained intake analysis. A real local scikit-learn NLP model is always used.
Optional OpenAI generation never invents facts and never overwrites source cards.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

HOME="https://www.niatindia.com/"
CAMPUS="https://www.niatindia.com/campus"
APPLICATION="https://apply.niatindia.com/login-upskill/?pi=upskill"
EVIDENCE={
 'degree': {'heading':'Who awards the degree?', 'fact':'NIAT is an upskilling initiative, not a university or degree-awarding body. A collaborating university independently controls admission and awards its degree.', 'caveat':'Ask the selected university for the precise program, accreditation, award conditions and written offer.', 'url':CAMPUS,'question':'Which legal institution issues my degree and transcript?'},
 'fees': {'heading':'What is the full cost?', 'fact':'NIAT says its upskilling fee depends on the collaborating institution; the published application information directs applicants to a counsellor for exact details.', 'caveat':'Request campus-specific tuition, upskilling charges, hostel, refund rules and instalment schedule in writing; do not infer a total.', 'url':APPLICATION,'question':'Can you send an itemised four-year cost and refund policy for my chosen campus?'},
 'placements': {'heading':'Can I rely on hiring claims?', 'fact':'The NIAT website explicitly says some displayed outcomes cover multiple NxtWave programs. Enrollment in NIAT does not assure a job or internship.', 'caveat':'Request cohort-, campus- and year-specific audited denominators and distinguish internships from final jobs.', 'url':HOME,'question':'Which placement figures apply specifically to my NIAT campus and graduating batch?'},
 'scholarship': {'heading':'What scholarship is actually guaranteed?', 'fact':'The NIAT application information describes conditional scholarships linked to assessment, profile and counselling performance.', 'caveat':'Treat amounts as potential, not assured; verify the eligibility letter, timing, renewal and what fee component is covered.', 'url':APPLICATION,'question':'Can you issue a written campus-specific scholarship determination and terms?'},
 'campus': {'heading':'Which campus will I attend?', 'fact':'NIAT lists its upskilling program at multiple collaborating institutions and regions across India.', 'caveat':'Institution, hostel, travel, facilities and admissions differ by campus; verify availability directly with that institution.', 'url':CAMPUS,'question':'What facilities, hostel charges and campus-specific policies apply to my preferred location?'},
 'curriculum': {'heading':'What exactly will I learn?', 'fact':'NIAT publicly describes project-based, industry-ready upskilling in AI, development, data and related technologies.', 'caveat':'Request the latest semester-by-semester syllabus and distinguish NIAT non-credit upskilling from university academic credit.', 'url':HOME,'question':'Which modules are NIAT upskilling versus university credit-bearing courses?'},
 'test': {'heading':'What is the next admissions step?', 'fact':'NIAT directs applicants to its NxtWave Assessment Test (NAT) and a counsellor-supported process.', 'caveat':'Check active dates, eligibility and fees on the live application portal rather than assuming an old deadline.', 'url':APPLICATION,'question':'What NAT slot, eligibility rules and current application terms apply to me?'},
 'other': {'heading':'I need a verifiable answer', 'fact':'NIAT provides official contact and counselling routes but not every campus-specific answer can be established from its public pages.', 'caveat':'The system will not guess. Request a documented answer from NIAT or the chosen university.', 'url':HOME,'question':'Can a counsellor provide an official source for this unresolved question?'},
}
SAMPLES={
 'degree':['is the btech recognised','who gives my degree','university ugc aicte affiliation recognition','valid diploma credits transcript','degree certificate official','degree not from niat','which college awards btech','university affiliation recognised degree','degree legitimacy university academic','degree kaun dega'],
 'fees':['how much total four year fees','expensive tuition hostel cost','emi education loan refund policy','money affordability budget','college fee breakup charges','hidden cost transport charges','paisa total kharcha','what is the full cost','fee structure fees'],
 'placements':['placement guarantee job promised','how many companies hire students','internship salary package CTC','placement data average salary','career outcome job guarantee','is 80 lpa for niat','batch wise audited placement','internship stipend genuine','job nahi mila'],
 'scholarship':['scholarships eligibility merit funding','scholarship amount can i get','financial aid waiver concession','nat score discount on fee','scholarship guaranteed or conditional','scholarship renewal criteria','scholarship kaise milegi'],
 'campus':['which campus nearest pune','hostel facilities safety mess','distance city travel accommodation','campus placement campus experience','where are colleges offered','college campus in maharashtra','hostel rules location'],
 'curriculum':['coding python ai ml syllabus','course projects teaching curriculum','what skills will they learn','semester wise modules subjects','credits industry training','training quality mentors','ai robotics cloud full stack'],
 'test':['nat entrance exam eligibility','application process deadline','when is next nat slot','assessment registration test','qualify for admission entrance','test pattern counselling stage'],
 'other':['i need more evidence','can someone explain','i have a different concern','not sure whether to decide','need a written answer','parents are confused']
}
@lru_cache(maxsize=1)
def classifier():
    texts=[]; labels=[]
    for cat, examples in SAMPLES.items():
        for ex in examples: texts.append(ex); labels.append(cat)
    model=Pipeline([('vector',TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),sublinear_tf=True)),('model',LogisticRegression(max_iter=1200,class_weight='balanced'))])
    model.fit(texts,labels)
    return model

def classify(text:str, priority:str=''):
    text=' '.join((text or '').split())[:800]
    model=classifier()
    scores=model.predict_proba([text+' '+priority.replace('_',' ')])[0]
    label=str(model.classes_[scores.argmax()])
    conf=round(float(max(scores)),3)
    if not text.strip() or conf<0.175: label=priority if priority in EVIDENCE and priority!='other' else 'other'
    return {'topic':label,'confidence':conf,'method':'local TF-IDF + logistic regression NLP model'}

def build_brief(student:dict, parent:dict):
    sc=classify(student.get('concern',''),student.get('priority',''))
    pc=classify(parent.get('concern',''),parent.get('priority',''))
    topics=list(dict.fromkeys([sc['topic'],pc['topic']]))
    if 'other' in topics and len(topics)>1: topics.remove('other')
    alignment='Shared concern' if sc['topic']==pc['topic'] else 'Different decision blockers'
    gap='Both parties independently raised '+sc['topic']+'.' if sc['topic']==pc['topic'] else 'Student prioritises '+sc['topic']+'; parent prioritises '+pc['topic']+'.'
    return {'student':sc,'parent':pc,'alignment':alignment,'gap':gap,'topics':topics,'cards':[{**EVIDENCE[t], 'topic':t} for t in topics], 'followups':[EVIDENCE[t]['question'] for t in topics], 'generation_mode':'Local trained NLP model + evidence-safe templates'}

def optional_llm_summary(student:dict,parent:dict,brief:dict):
    """Extra API call if owner configures OPENAI_API_KEY. Never pass names/phones (not collected)."""
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key: return None
    try:
        from openai import OpenAI
        evidence='\n'.join(f"- {c['heading']}: {c['fact']} Caveat: {c['caveat']}" for c in brief['cards'])
        client=OpenAI(api_key=key,timeout=12,max_retries=0)
        response=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),temperature=0.1,max_tokens=180,messages=[
           {'role':'system','content':'You draft a neutral parent/student decision-brief in max 85 words. Use ONLY provided verified evidence. Never claim a job, scholarship, approval or admission guarantee. Explicitly invite campus-specific written verification. Do not add facts. Do not address them by name.'},
           {'role':'user','content':f"Student concern: {student.get('concern','')[:500]}\nParent concern: {parent.get('concern','')[:500]}\nClassified gap: {brief['gap']}\nVerified evidence:\n{evidence}"}])
        return (response.choices[0].message.content or '').strip()[:1000] or None
    except Exception: return None
