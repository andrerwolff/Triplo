# Sbmtl

Sbmtl is a construction project management web app. Use it to manage multiple projects, store reference documents (PDF, Word, text), track submittals (under review and completed), and log RFIs.

**Hosting:** See [DEPLOYMENT.md](DEPLOYMENT.md) for deploying the frontend on **Vercel** or **GitHub Pages** and the backend on Render or Railway.

## Run the app (FastAPI + React)

The recommended stack is **FastAPI** (backend) + **React** (frontend with ShadCN UI).

### 1. Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

(If `pip` or `uvicorn` is not found, use `python3 -m pip` and `python3 -m uvicorn` as above.)

**If you see "Address already in use" (port 8000):** Another backend is still running. Free the port and try again:
```bash
lsof -i :8000   # list processes on port 8000
kill <PID>      # replace <PID> with the number from the second column
```

Data is stored in `backend/triplo_data.json`.

**Submittal evaluation (LLM):** To use the Technical Submittal Auditor (evaluate submittals against reference specs), set `GEMINI_API_KEY` in the environment before starting the backend:

```bash
# backend/.env (create from backend/.env.example; do not commit .env)
export GEMINI_API_KEY=your-api-key
# Optional: use a different model (default is gemini-2.5-flash)
# export GEMINI_AUDIT_MODEL=gemini-2.5-pro
```

If `GEMINI_API_KEY` is not set, the "Evaluate" button will remain available but the request will fail with a clear error.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The app talks to the API at `http://localhost:8000` by default. To use another API URL, set:

```bash
# frontend/.env or frontend/.env.local
VITE_API_URL=http://localhost:8000
```

---

## Features

- **Dashboard:** Create, open, and delete projects.
- **Project Dashboard:** Overview of reference doc count, submittals, and RFIs.
- **Reference Docs:** Upload `.txt`, `.docx`, or `.pdf` files. Extracted text is shown and saved to the project. Optionally tag documents with a CSI division.
- **Submittals:** Upload submittals, move them from "Under Review" to "Completed," and optionally assign a CSI division. Use **Evaluate** to run the Technical Submittal Auditor: the app compares each submittal to the project's reference docs (specs) via an LLM and produces a scannable report (executive summary table, compliance narrative, missing information, critical deviations, suggested action: Approve / Approve as Noted / Revise and Resubmit).
- **RFIs:** Add and view RFIs with title, description, status, and date.
- **Persistence:** Projects and their data are saved to `triplo_data.json` (backend directory when using FastAPI).

## Optional: Gemini API

Set `GEMINI_API_KEY` in the environment when running the backend (see Backend section above). Copy `backend/.env.example` to `backend/.env` and add your key. Do not commit `.env`.
