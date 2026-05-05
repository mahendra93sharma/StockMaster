# StockMaster

## What This Project Does

StockMaster is a three-tier Indian-market stock-insights platform that provides real-time market data, LLM-powered analysis, and actionable stock recommendations.

**Key Features:**

- **Automated Data Ingestion** — Scrapes NSE/BSE price ticks, bulk/block deals, corporate actions, and market news on a configurable schedule (APScheduler).
- **LLM-Powered Analysis** — Runs AI analysis on scraped data to generate stock recommendations and insights.
- **REST API** — FastAPI backend serving authenticated endpoints for stocks, recommendations, shark-deals, and home feed.
- **Android App** — Kotlin/Jetpack Compose mobile app with MVVM + Clean Architecture for the consumer-facing experience.
- **Web Admin Dashboard** — HTMX-powered operator dashboard for scheduler control, data QA, and monitoring.
- **Authentication** — Google Sign-In via Firebase with JWT-based session management.

**Tech Stack:**

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, PostgreSQL 15, APScheduler, Anthropic LLM |
| Android | Kotlin 2, Jetpack Compose, MVVM + Clean Architecture |
| Web Admin | FastAPI + Jinja2 + HTMX |
| Auth | Firebase Admin SDK + JWT |

---

## How to Deploy

### Backend — Deploy on Render

1. **Create a PostgreSQL database** on Render (or use an external managed Postgres instance).

2. **Create a new Web Service** on [Render](https://render.com):
   - Connect your GitHub/GitLab repository.
   - Set the **Root Directory** to `backend`.
   - Set **Runtime** to Docker (the project includes a `Dockerfile`).
   - Set the **Start Command** (if not using Docker CMD):
     ```
     gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
     ```

3. **Configure Environment Variables** on Render:
   ```
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<db>
   ENV=production
   SECRET_KEY=<your-secret-key>
   FIREBASE_PROJECT_ID=<your-firebase-project-id>
   GOOGLE_APPLICATION_CREDENTIALS=<path-or-json>
   ANTHROPIC_API_KEY=<your-anthropic-key>
   ```

4. **Run database migrations** (use Render's shell or a pre-deploy command):
   ```bash
   alembic upgrade head
   ```

5. Render will automatically build and deploy on every push to your main branch.

---

### Frontend (Web App) — Deploy on Vercel

1. **Create a new project** on [Vercel](https://vercel.com):
   - Import your repository.
   - Set the **Root Directory** to the frontend/web app folder.
   - Vercel auto-detects the framework (Next.js, React, etc.) and configures the build.

2. **Configure Environment Variables** on Vercel:
   ```
   NEXT_PUBLIC_API_URL=https://<your-render-backend>.onrender.com
   ```

3. **Deploy** — Vercel builds and deploys automatically on every push.

---

### Android App

The Android app is built with Gradle and supports three build flavors: `qa`, `uat`, and `production`. Distribute via Google Play Console or Firebase App Distribution.

```bash
cd android
./gradlew assembleProductionRelease
```
