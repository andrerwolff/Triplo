# Hosting Sbmtl (GitHub Pages or Vercel)

Sbmtl has a **React (Vite) frontend** and a **FastAPI backend**. You can host the frontend on **Vercel** or **GitHub Pages**; the backend must run on a service that supports Python (e.g. **Render** or **Railway**).

---

## Option A: Vercel (frontend) + Render/Railway (backend)

Best balance of simplicity and features.

### 1. Deploy the backend (e.g. Render)

1. Push your repo to GitHub (if not already).
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect the repo and set:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment** add:
   - `GEMINI_API_KEY` (for submittal evaluation)
   - `CORS_ORIGINS` = `https://your-app.vercel.app` (you’ll set this after deploying the frontend)
5. Deploy. Note the backend URL (e.g. `https://triplo-backend.onrender.com`).

**Railway:** Same idea: New Project → Deploy from GitHub → set root to `backend`, add the same env vars, and use `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### 2. Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import your GitHub repo.
2. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (auto-detected)
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. **Environment Variables:**
   - `VITE_API_URL` = your backend URL (e.g. `https://triplo-backend.onrender.com`)
4. Deploy.
5. Copy your Vercel URL (e.g. `https://triplo.vercel.app`), then in Render/Railway set **CORS_ORIGINS** to that URL and redeploy the backend.

Your app is live: frontend on Vercel, API on Render/Railway.

---

## Option B: GitHub Pages (frontend only) + backend elsewhere

GitHub Pages only serves **static files**. It cannot run the FastAPI backend.

### 1. Deploy the backend

Use **Render** or **Railway** as in Option A (step 1). Set `CORS_ORIGINS` to your GitHub Pages URL when you have it (e.g. `https://your-username.github.io/Triplo/`).

### 2. Deploy the frontend to GitHub Pages

1. In the repo, go to **Settings** → **Pages** → **Source**: GitHub Actions.
2. In the repo root, create `.github/workflows/deploy-pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install and build
        run: |
          cd frontend
          npm ci
          echo "VITE_API_URL=${{ secrets.VITE_API_URL }}" >> .env.production
          npm run build

      - name: Upload artifact
        uses: actions/upload-pages-artifact@3
        with:
          path: frontend/dist

  deploy:
    needs: build-and-deploy
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deploy
        uses: actions/deploy-pages@4
```

3. Add **Repository secret**: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**  
   - Name: `VITE_API_URL`  
   - Value: your backend URL (e.g. `https://triplo-backend.onrender.com`)

4. Push to `main`. After the workflow runs, the site will be at `https://<username>.github.io/<repo-name>/`.

5. **Important:** The app is served under a subpath (e.g. `/Triplo/`). Set the **base** in Vite so assets and routing work:

   In `frontend/vite.config.ts`, set `base: '/Triplo/'` (replace `Triplo` with your repo name):

   ```ts
   export default defineConfig({
     base: "/Triplo/",  // match your repo name for GitHub Pages
     plugins: [react(), tailwindcss()],
     // ... rest unchanged
   })
   ```

6. Set **CORS_ORIGINS** on the backend to `https://<username>.github.io` (or the full Pages URL).

---

## Summary

| Part      | GitHub Pages        | Vercel                    |
|----------|---------------------|---------------------------|
| Frontend | Yes (static only)   | Yes (recommended)         |
| Backend  | No                  | No (use Render/Railway)   |

- **Easiest:** Vercel for frontend + Render for backend (Option A).
- **No Vercel:** GitHub Pages for frontend (Option B) + Render/Railway for backend.

Always set **VITE_API_URL** (frontend) and **CORS_ORIGINS** (backend) to your deployed URLs so the browser can call your API.
