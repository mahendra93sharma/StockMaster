# StockMaster — System Architecture (Milestone 1)

> **Status:** Draft — awaiting human acknowledgement before Milestone 2 begins.

---

## 1. What we are building

StockMaster is a three-tier Indian-market stock-insights platform:

| Tier | Technology | Responsibility |
|---|---|---|
| **Backend** | Python 3.11, FastAPI, PostgreSQL 15, APScheduler | Ingest NSE/BSE data, run LLM analysis, serve REST API |
| **Android app** | Kotlin 2, Jetpack Compose, MVVM + Clean Architecture | Consumer-facing mobile experience |
| **Web admin** | FastAPI + Jinja2 + HTMX | Operator dashboard (scheduler control, data QA, cost monitoring) |

---

## 2. Component diagram

```
 ┌────────────────────────────────────────────────────────────────────┐
 │  Backend  (FastAPI, port 8000)                                      │
 │                                                                      │
 │  ┌──────────────┐   JWT verify   ┌─────────────────────────────┐   │
 │  │ /auth/google  │◄──────────────│  Firebase Admin SDK          │   │
 │  └──────┬───────┘                └─────────────────────────────┘   │
 │         │ issue backend JWT                                          │
 │  ┌──────▼───────────────────────────────────────────────────────┐  │
 │  │  /api/v1/*  (JWT-protected)                                   │  │
 │  │   stocks · recommendations · shark-deals · home/feed · admin  │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                                                                      │
 │  ┌──────────────────────────────────────────────────────────────┐  │
 │  │  APScheduler (in-process)                                     │  │
 │  │   • Market hours (09:00–15:30 IST, Mon–Fri) every 30 min:    │  │
 │  │       NSE/BSE price ticks, gainers/losers, bulk/block deals   │  │
 │  │   • Outside market hours, hourly: news + corporate actions    │  │
 │  │   • End-of-day (16:00 IST): official archive CSV feeds       │  │
 │  │   • After every successful scrape: LLM analysis pipeline      │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                       │                                              │
 │                       ▼                                              │
 │  ┌──────────────────────────────────────────────────────────────┐  │
 │  │  PostgreSQL 15                                                │  │
 │  │   users · instruments · price_ticks · bulk_deals             │  │
 │  │   block_deals · notable_investors · news · corporate_actions │  │
 │  │   recommendations · closed_trades · scheduler_runs           │  │
 │  │   raw_payloads · sessions · auth_providers                   │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────┘
          ▲  REST / JSON                     ▲  REST / JSON
          │                                  │
 ┌────────┴───────────┐           ┌──────────┴─────────┐
 │  Android app        │           │  Web admin          │
 │  qa / uat / prod    │           │  /admin (HTMX)      │
 └─────────────────────┘           └────────────────────┘
```

---

## 3. Authentication flow

```
Android                    Backend                    Firebase
  │                           │                           │
  │── Google sign-in ─────────────────────────────────►  │
  │◄─ Firebase ID token ──────────────────────────────── │
  │                           │                           │
  │── POST /auth/google ─────►│                           │
  │   { id_token }            │── verify token ──────────►│
  │                           │◄─ user claims ─────────── │
  │                           │  upsert user in DB        │
  │◄── { access_token,        │  issue 15-min JWT         │
  │     refresh_token }       │  store refresh_hash in DB │
  │                           │                           │
  │── API calls               │                           │
  │   Authorization: Bearer   │                           │
  │   <access_token>          │                           │
```

- Firebase ID tokens are **never stored** — verified once and discarded.
- Backend issues its own short-lived JWT (15 min) + rotating refresh token.
- Refresh tokens are stored as HMAC-SHA256 hashes; raw values never persisted.

---

## 4. Data ingestion pipeline

```
APScheduler trigger
      │
      ├─ 1. Fetch from NSE/BSE official feed (CSV/API)
      │       └─ fallback: httpx + BeautifulSoup HTML scraping
      │
      ├─ 2. Persist raw payload to raw_payloads (sha256 + timestamp)
      │
      ├─ 3. Parse + validate → SQLAlchemy models
      │
      ├─ 4. Upsert to target tables (instruments, price_ticks, bulk_deals …)
      │
      ├─ 5. Write scheduler_runs row (status, duration, items_ingested)
      │
      └─ 6. For each updated instrument → LLM analysis pipeline
               │
               ├─ 6a. Aggregate: 30-day OHLCV + news + corp actions
               ├─ 6b. SHA-256 input bundle → skip if matches last call
               ├─ 6c. Call Claude (tool-use, structured JSON output)
               ├─ 6d. Validate output against Pydantic schema
               ├─ 6e. Persist to recommendations, mark old ones superseded
               └─ 6f. Log tokens used + cost; enforce daily spend cap
```

---

## 5. Android architecture

Each feature module follows three strict layers:

```
feature-stock/
  ├── data/
  │    ├── remote/     (Retrofit DTOs, StockApiService)
  │    ├── local/      (Room DAOs, entities, caching)
  │    ├── mapper/     (DTO → domain model)
  │    └── repository/ (StockRepositoryImpl)
  ├── domain/
  │    ├── model/      (pure Kotlin, zero Android imports)
  │    ├── repository/ (StockRepository interface)
  │    └── usecase/    (GetRecommendationsUseCase, etc.)
  └── presentation/
       ├── screen/     (Composables — stateless)
       └── viewmodel/  (StateFlow<UiState<T>>)
```

Network layer injects a single `OkHttpClient` with:
1. `AuthInterceptor` — attaches `Authorization: Bearer <access_token>` to every request.
2. `TokenRefreshAuthenticator` — on 401, calls `POST /auth/refresh`, replaces tokens in DataStore, retries original request (exactly once).

---

## 6. Three-environment strategy

| Aspect | qa | uat | production |
|---|---|---|---|
| Application ID suffix | `.qa` | `.uat` | _(none)_ |
| API base URL | `https://qa.api.stockmaster.app/` | `https://uat.api.stockmaster.app/` | `https://api.stockmaster.app/` |
| Firebase project | stockmaster-qa | stockmaster-uat | stockmaster-prod |
| LLM daily spend cap | $5 | $20 | configurable via env |
| OpenAPI `/docs` | enabled | enabled | disabled (ADMIN_DOCS=true to enable) |
| CORS | `*` allowed | allowlist | strict allowlist |
| Log level | DEBUG | INFO | INFO (JSON structured) |
| App-icon overlay | green badge | orange badge | _(none)_ |

---

## 7. Repository layout

```
StockMaster/
├── ARCHITECTURE.md          ← this file
├── backend/
│   ├── app/
│   │   ├── api/v1/          (auth, stocks, home, admin routers)
│   │   ├── core/            (config, security, logging, exceptions)
│   │   ├── db/              (models, async session, declarative base)
│   │   ├── schemas/         (Pydantic request/response models)
│   │   ├── services/        (scraping, llm, scheduler, analytics)
│   │   ├── crud/            (repository layer — no business logic)
│   │   └── main.py
│   ├── admin/               (FastAPI + Jinja2 + HTMX dashboard)
│   ├── alembic/
│   ├── tests/               (unit + integration + e2e smoke)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml
└── android/
    ├── app/
    │   └── src/
    │       ├── main/
    │       ├── qa/          (google-services.json, icon overlay)
    │       ├── uat/
    │       └── production/
    ├── core/                (network, di, ui-kit shared modules)
    ├── data/                (repository impls, retrofit, room)
    ├── domain/              (use-cases, models — pure Kotlin)
    ├── feature-auth/
    ├── feature-home/
    ├── feature-stock/
    └── feature-profile/
```

---

## 8. Key assumptions I am making

| # | Assumption | Rationale |
|---|---|---|
| A1 | NSE/BSE official archive CSVs (nse-csv, bseindia.com download center) are used as primary feed; HTTPS HTML scraping is used only as a fallback | Per §2 rule 4 and §7.1 |
| A2 | APScheduler runs in-process (no Celery) for the initial build | Per §4 stack note; can be extracted later |
| A3 | `claude-sonnet-4-5` (latest available at time of writing) is used; model name is configurable via env | Ties to §4 LLM spec |
| A4 | Each environment has its own Firebase project; all three `google-services.json` files are provided by the human out-of-band and never committed | Per §9 security |
| A5 | The seed script populates ≥10 instruments and ≥1 synthetic recommendation per horizon so the Android app is demoable without waiting for a real scrape | Per §11 local dev requirement |
| A6 | Alembic auto-generates revisions from the SQLAlchemy models (not hand-written SQL) | Consistency with ORM models |
| A7 | Admin dashboard uses HTMX (not React SPA) | Per §7.4 primary option |
| A8 | Bruno collection is used instead of Postman (open-source, git-friendly) | Per §12 "Postman / Bruno" option |

---

## 9. What I need from you before starting Milestone 2

Nothing that blocks Milestone 2. All questions above are resolved by assumptions A1–A8.

**Optional confirmations** (I will proceed with the assumption if you say nothing):
- Confirm you are okay with `claude-sonnet-4-5` as the default model name (A3), or supply a different model string.
- Confirm you will provide the three `google-services.json` files yourself when wiring Firebase (A4).

---

**Ready for Milestone 2 (database schema + Alembic migrations) on your go-ahead.**
