# NIAT Decision Lab — runnable growth system

**Independent assignment prototype, not affiliated with NIAT.** Track B — a genuinely different bottom-of-funnel mechanic: two independent perspectives → machine-learned blocker identification → official, caveated proof cards → consent-first counsellor action queue → instrumented conversion dashboard.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000 — use **Create a two-seat decision lab** or the synthetic preloaded path http://localhost:8000/s/DEMOCASE01/brief. View the public anonymised funnel at `/dashboard` and the linked primary-source evidence at `/evidence`.

## What is genuinely connected?

1. **FastAPI + HTML form workflow:** independent student/parent seats, shared random invitation code, consent gate.
2. **Real local AI model:** scikit-learn `TfidfVectorizer` + `LogisticRegression`, trained on concern language. Calls `predict_proba` for each response, uses top labels to route evidence and tickets. Works out-of-the-box **without any API key**.
3. **Evidence-locked proof library:** maintains verified public NIAT citations, limitations, and precise written requests. Does not infer fee, scholarship, degree credit or job outcomes.
4. **SQLite + growth events:** durable response, event and follow-up tables, cohort/concern dashboard. Six synthetic records are explicitly labelled and segregated.
5. **Protected counsellor actions + CSV:** counsellor views and closes requested evidence tickets, manually records outcomes; CSV export for CRM handoff. No automatic messages to third parties.
6. **Optional genuine LLM synthesis:** Set `OPENAI_API_KEY` to enable a server-side OpenAI API call for an evidence-limited two-sided summary. Without a key, the app *truthfully* displays local-model-only operation.

## Admin walkthrough

Set environment variable `ADMIN_PASSWORD` to a strong secret, then open `/admin`; username `counsellor`, password the value set. Admin is **disabled** if unset, and HTTP Basic is best used behind HTTPS. This is MVP authentication, not production SSO.

## Reviewer end-to-end demo

1. Open `/`, create a case and copy its invitation URL.
2. Submit student concern “I want AI projects but is this a recognised degree?”
3. Submit parent concern “Can I see all four years of fees and hostel costs in writing?”
4. Read the detected disagreement and separately sourced degree/fee cards at `/brief`.
5. Click **Request prototype review**, which adds an event but does **not** contact NIAT.
6. Inspect `/dashboard` for real pipeline counts; sign into `/admin` to see ticket status / export CSV / record outcome.

## Deploy (the current chat cannot claim a hosted link)

- **Replit:** Import/upload this ZIP, select Python, install `requirements.txt`, set Run command `uvicorn app.main:app --host 0.0.0.0 --port 8000`, set `ADMIN_PASSWORD`, optionally `OPENAI_API_KEY`; use Replit Deploy to obtain a public URL.
- **Render:** Create a Web Service from the repository/ZIP, or use included `render.yaml`. For persistence, mount a disk and set `NIAT_DB_PATH` to the disk path. **Free ephemeral storage is only for a demo and can reset.**
- **Other platforms:** Any Python 3.11+ host with persistent writable SQLite storage and HTTPS.

Public deployment URL and Loom URL must be populated in `submission/SUBMIT_ME.md` **after actually publishing**. Do not invent URLs.

## Ethics / release checklist

- This demo is **not operated by NIAT** and does not scrape private user data.
- Do not claim production AI performance; the classifier is trained on small curated example phrases. Manually review misclassifications and protect false positives.
- Unverified institution-specific prices, acceptance dates, scholarships, outcomes, and degree credit are deliberately not generated.
- Students may be under 18. No names, phone, emails or auto-message collection. Optional external OpenAI processing is disclosed on the intake consent form and should stay disabled until an organisation has approved the processing arrangement. Obtain appropriate parental and institutional approval before real experimentation.
- Shared invite URLs act as access secrets; do not post publicly. Admin access must be over HTTPS. Rotate passwords, apply retention limits, abuse protection and comply with local privacy law before testing with real households.
- Only NIAT staff could validate whether a similar internal initiative exists. Our novelty claim is **not visibly present in the audited public funnel**, not proof of internal nonexistence.
- A real A/B test requires holdout/random assignment, counsellor signoff and tracking of *verified* next steps, not button clicks or synthetic demo accounts.

## Walkthrough video

`demo/NIAT_Decision_Lab_Browser_Walkthrough.mp4` is a 78-second silent video assembled from real browser-rendered screens while the full workflow was exercised through the FastAPI test client. It is **not** a Loom-hosted recording and is **not** evidence of a publicly hosted app. The accompanying `demo/LOOM_NARRATION.txt` is a ready-to-read spoken script.

## Tests

```bash
pip install pytest
python -m pytest -q
```

## Public evidence (checked 15 October 2026)

- NIAT home and disclaimers: https://www.niatindia.com/
- NIAT institutions list: https://www.niatindia.com/campus
- NIAT application details: https://apply.niatindia.com/login-upskill/?pi=upskill
- Scaler undergraduate program: https://www.scaler.com/school-of-technology/
- Newton School of Technology: https://www.newtonschool.co/newton-school-of-technology-nst/home

Code authored as an independent demonstration for this challenge. All demo cases are synthetic; no NIAT dataset was accessed.
