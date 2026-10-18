# MindPulse — Complete Implementation Blueprint
### An AI-Driven Student Well-Being Support System with Ethical Risk Detection

---

## 1. Final Technology Stack

| Layer | Technology | Why This? | Alternatives Considered | Why Not Alternatives |
|---|---|---|---|---|
| Mobile App | **Flutter** | Single codebase for Android/iOS, fast to build screens for an FYP, huge widget ecosystem, good for dashboards/charts (fl_chart) | React Native | RN needs more native tooling overhead (CocoaPods/Gradle quirks), Flutter's hot reload and single-language (Dart) model is faster for a small student team; you already have FastAPI/Python experience so Dart-only frontend keeps mental context switches to two languages, not three (JS+Python) |
| Backend API | **FastAPI (Python)** | Async, auto-generated OpenAPI docs, native Pydantic validation, easiest to pair with HuggingFace/ML libraries since everything stays in Python | Django REST / Node+Express | Django is heavier (ORM built for SQL, you're using MongoDB), Node/Express would fragment your stack since AI/NLP work is Python-native |
| Database | **MongoDB** | Flexible schema fits evolving behavioral signals and chat logs; document model matches nested structures like baselines and risk score breakdowns | PostgreSQL | Relational would work but adds migration overhead for an evolving FYP schema; Mongo's document model is a closer fit to chat/session data (required per your spec) |
| Conversational AI | **OpenAI API (GPT-4o-mini or GPT-4o)** via a thin wrapper service | Reliable, fast to integrate, strong instruction-following for a "supportive, non-clinical" persona, no GPU/infra needed | Self-hosted LLM (Llama, Mistral) | Self-hosting adds GPU cost/infra complexity with no FYP benefit; a hosted API lets you focus engineering time on the risk engine, which is the actual novel contribution |
| Sentiment/Emotion Analysis | **HuggingFace `distilroberta`/`bert`-based sentiment+emotion models** (e.g., `j-hartmann/emotion-english-distilroberta-base`) run locally via `transformers` | Free, runs on CPU for small volumes, gives explainable per-message scores independent of the LLM (important — see Section 5) | Ask the LLM itself to output a sentiment score | Mixing "the chatbot" and "the judge of the chatbot" in one model is an evaluator-conflict risk and is not separately auditable; a dedicated lightweight model keeps sentiment analysis explainable and swappable |
| Authentication | **JWT (access + refresh tokens)** with `passlib[bcrypt]` for hashing | Stateless, standard for mobile+multiple dashboard clients, RBAC claims embed directly in the token | Session cookies | Cookies are awkward for a mobile app talking to a separate API host; JWT is the FastAPI-idiomatic choice |
| Parent/Admin/Counselor Dashboards | **React + a charting lib (Recharts)**, served as a separate web app hitting the same FastAPI backend | Fast to build data-table/chart-heavy views separately from the mobile UI | Building dashboards in Flutter Web | Flutter Web is heavier for a mostly-forms-and-charts UI; React is faster to iterate on and is what most FYP evaluators expect from a "web dashboard" | 
| Hosting (MVP) | **Render/Railway (backend) + MongoDB Atlas (DB) + Expo/APK build (mobile)** | Free/low-cost tiers sufficient for FYP demo load | AWS full stack | AWS is more "production," but its setup cost (VPC, IAM, etc.) is disproportionate to FYP timeline; note this as a "future work" migration path |

---

## 2. Complete Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                        │
│  Student Mobile App (Flutter)                                 │
│  Parent Dashboard (React)   Admin Dashboard (React)            │
│  Counselor Interface (React)                                  │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 API GATEWAY / FASTAPI BACKEND                 │
│  Auth & RBAC Middleware  |  Rate Limiting  |  Input Validation │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        CORE SERVICES                          │
│  Chat Service        Consent Service      Behavioral Analysis │
│  Sentiment Analysis  Trend Analysis       Risk Scoring Engine  │
│  Referral Service    Notification Service Audit Logging       │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 AI & RISK PROCESSING LAYER                    │
│  External LLM (OpenAI API) — conversational only              │
│  Local Sentiment/Emotion Model (HuggingFace, CPU)              │
│  Deterministic Risk Scoring Logic (rule-based, NOT the LLM)    │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                              │
│                         MongoDB Atlas                          │
└─────────────────────────────────────────────────────────────┘
```

**Key architectural principle:** the LLM is a *leaf node* used only for generating chatbot replies. It never writes to `risk_scores` or `baselines` directly. All numeric/behavioral data flows through the deterministic Risk Scoring Engine, keeping the risk decision explainable and auditable — a point your FYP evaluators will likely probe.

---

## 3. Complete Module Breakdown

**Backend (`app/`)**
- `auth/` — registration, login, JWT issuance/refresh, RBAC dependency injection
- `consent/` — consent CRUD, consent-check middleware used by every data-exposing endpoint
- `chat/` — chat session management, message routing to LLM, signal extraction hook
- `behavior/` — check-in ingestion (stress, workload, sleep, activity)
- `sentiment/` — wraps the local HuggingFace model, called async after each chat message
- `baseline/` — baseline creation + rolling update logic
- `risk_engine/` — normalization, weighting, scoring, classification, persistence checks
- `referral/` — counselor directory, appointment/request flow, external therapist directory
- `notifications/` — in-app notification generation (risk change, referral status, etc.)
- `dashboards/` — aggregation queries for parent/admin/counselor views
- `audit/` — write-only audit log service, called by every sensitive-data access
- `db/` — Motor (async MongoDB driver) client, index setup
- `core/` — settings, security utils, exception handlers

**AI Modules (`ai/`)**
- `llm_client.py` — OpenAI wrapper, prompt templates, safety instructions
- `sentiment_model.py` — HuggingFace pipeline loader + inference
- `signal_extractor.py` — turns raw chat/sentiment output into structured behavioral signals (never stores raw text alongside signals used by non-student roles)

**Mobile (`lib/`)** — see Section 11 for structure
**Dashboards (`dashboard-web/`)** — separate React app, role-gated routes

---

## 4. Complete Database Design (MongoDB)

### Collections

**`users`**
```json
{
  "_id": ObjectId,
  "role": "student | parent | counselor | admin",
  "email": "string",
  "password_hash": "string",
  "full_name": "string",
  "linked_student_ids": ["ObjectId"],   // for parent role
  "created_at": ISODate,
  "is_active": true
}
```

**`student_profiles`**
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "university_id": "string",
  "program": "string",
  "semester": 5,
  "created_at": ISODate
}
```

**`consents`**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "share_summary_with_parent": true,
  "share_with_university_support": false,
  "allow_referral_data_share": true,
  "updated_at": ISODate
}
```

**`chat_sessions`**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "started_at": ISODate,
  "last_message_at": ISODate,
  "status": "active | closed"
}
```

**`messages`**
```json
{
  "_id": ObjectId,
  "session_id": ObjectId,
  "student_id": ObjectId,
  "sender": "student | assistant",
  "text": "string",
  "created_at": ISODate
}
```
*Access rule: only the student and system processes can read `text`. Parents/admins never query this collection.*

**`behavioral_signals`**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "date": ISODate,
  "self_rated_stress": 7,
  "workload": 8,
  "sleep_hours": 5.5,
  "activity_score": 3,
  "checkin_completed": true,
  "chat_messages_count": 4,
  "avg_response_delay_sec": 45
}
```

**`sentiment_results`**
```json
{
  "_id": ObjectId,
  "message_id": ObjectId,
  "student_id": ObjectId,
  "sentiment_score": -0.42,      // -1 to 1
  "dominant_emotion": "sadness",
  "confidence": 0.81,
  "created_at": ISODate
}
```

**`baselines`**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "typical_stress": 4.2,
  "typical_workload": 5.0,
  "typical_sleep": 6.8,
  "typical_engagement": 0.7,
  "typical_sentiment": 0.1,
  "sample_size": 21,
  "last_updated": ISODate
}
```

**`risk_scores`**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "date": ISODate,
  "raw_components": {
    "sentiment_deviation": 0.6,
    "stress_deviation": 0.7,
    "workload_deviation": 0.3,
    "sleep_deviation": 0.5,
    "engagement_deviation": 0.2
  },
  "weighted_score": 0.52,
  "risk_level": "MEDIUM",
  "consecutive_days_at_level": 3,
  "explanation": "Elevated for 3 consecutive days, driven mainly by stress and sentiment deviation"
}
```

**`notifications`**, **`counselors`**, **`appointments`**, **`external_therapists`**, **`audit_logs`** — straightforward CRUD collections; documents omitted for brevity but follow the same explicit, minimal-field pattern above.

### Relationships
- `student_profiles.user_id → users._id`
- `behavioral_signals.student_id`, `sentiment_results.student_id`, `baselines.student_id`, `risk_scores.student_id` all reference `users._id` (student role) — one-to-many, queried by date range
- `appointments` references both `counselors._id` and `users._id` (student)
- `consents.student_id` is checked before *every* cross-role read (parent/admin/counselor endpoints)

### Indexing Strategy
- `users`: unique index on `email`
- `behavioral_signals`, `sentiment_results`, `risk_scores`: compound index on `{student_id: 1, date: -1}` — all trend queries are "latest N days for this student"
- `messages`: compound index on `{session_id: 1, created_at: 1}`
- `appointments`: index on `{student_id: 1, status: 1}` and `{counselor_id: 1, status: 1}`

---

## 5. AI Processing Pipeline

Chatbot message flow (as requested):

```
Student → Mobile App → REST API (/chat/message) → Backend
   → LLM Service (OpenAI, system prompt: supportive, non-clinical, no diagnosis)
   → Response saved + returned → Mobile App

  (in parallel, async background task)
Backend → Sentiment Model (local HF model) → sentiment_results
        → Signal Extractor → behavioral_signals (chat_messages_count, avg_response_delay, sentiment aggregate)
```

**Privacy boundary:** the signal extractor outputs *only numeric/categorical signals* (sentiment score, message count, delay). The raw message `text` never leaves the `messages` collection and is never joined into any parent/admin dashboard query.

**Why separate conversational AI from risk decision-making (Section 5 requirement):**
- A. Conversational AI (OpenAI) — generates replies only
- B. Sentiment/emotion analysis (local HF model) — produces a numeric signal per message
- C. Behavioral analysis — aggregates check-in + chat signals per day
- D. Trend analysis — compares recent window (e.g., 7-day rolling avg) vs. baseline
- E. Risk scoring — deterministic weighted formula (Section 6), **not** an LLM call

This separation is the direct answer to "do not use an LLM alone to determine risk level" — the LLM has no code path into `risk_scores`.

---

## 6. Risk Scoring Algorithm

**Inputs (per day, per student):**
- `sentiment_deviation` = (baseline.typical_sentiment − today's avg sentiment) normalized to [0,1]
- `stress_deviation` = (today's self_rated_stress − baseline.typical_stress) / scale, clipped to [0,1]
- `workload_deviation` = similarly normalized
- `sleep_deviation` = (baseline.typical_sleep − today's sleep_hours) / scale, clipped to [0,1] (less sleep = higher deviation)
- `engagement_deviation` = drop in check-in consistency or chat frequency vs. baseline

**Normalization:** each raw deviation is min-max clipped into [0,1] so no single signal can dominate purely due to scale.

**Weighting (configurable via `config/risk_weights.json`, not hard-coded):**
```json
{
  "sentiment_deviation": 0.30,
  "stress_deviation": 0.25,
  "workload_deviation": 0.15,
  "sleep_deviation": 0.15,
  "engagement_deviation": 0.15
}
```

**Score calculation:**
```
weighted_score = Σ (weight_i × deviation_i)
```

**Threshold classification (also configurable, not medically hard-coded):**
- `weighted_score < 0.35` → LOW
- `0.35 ≤ weighted_score < 0.65` → MEDIUM
- `weighted_score ≥ 0.65` → HIGH

**Persistence/trend requirement (false-positive prevention):** a single high-scoring day does **not** trigger escalation. The risk level shown/escalated is based on the **3-day rolling classification** — a student must score in a given band for ≥3 consecutive days (configurable `min_consecutive_days`) before that level is surfaced to counselors or triggers referral prompts. This directly satisfies "do not let one abnormal day change the baseline/trigger escalation."

**Baseline update rule:** the baseline is a rolling average over the trailing 21 days, recalculated nightly, but each day's contribution is capped (e.g., no single day can shift the baseline by more than 1/`sample_size` of its current value) — preventing one outlier day from swinging the reference point.

**What happens per level:**
- LOW → dashboard shows "steady," no action
- MEDIUM → in-app supportive message + self-help suggestions surfaced; internal flag for "increased monitoring" (visible only to the student, plus counselor if consent given)
- HIGH (sustained ≥3 days) → triggers the referral flow (Section 7)

---

## 7. Referral Algorithm / Flow

```
Sustained HIGH risk detected
        ↓
In-app supportive message shown to student
        ↓
University Counselor recommended (PRIMARY — always shown first)
        ↓
Student views counselor profile + availability
        ↓
Student sends a "request/contact" (MVP: request-based, not live calendar booking)
        ↓
Counselor sees the request in their interface, accepts/reschedules
        ↓
[Optional, student-initiated] Student opens External Therapist Directory
        ↓
Student browses verified external therapists (location/online, contact info)
        ↓
Student chooses to contact one directly — the app does NOT auto-send any data
```

**MVP scope decision:** implement referral as a **request/contact mechanism**, not a full calendar-booking system. A real booking system (slot locking, calendar sync, reminders) is disproportionate engineering effort for an FYP and is explicitly listed as future work (Section 21). The request model (student requests → counselor accepts/declines → status updates) is realistic, demoable, and satisfies the evaluators' requirement for a "referral mechanism."

**Referral document (`appointments`)**
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "counselor_id": ObjectId,
  "requested_at": ISODate,
  "status": "requested | accepted | declined | completed",
  "trigger_risk_score_id": ObjectId,
  "student_consent_confirmed": true
}
```

**Consent gate:** before a referral is even created, the system checks `consents.allow_referral_data_share`. If false, the student still sees the recommendation but the counselor is not notified — the student must first opt in.

---

## 8. Authentication and RBAC Design

- JWT access token (short-lived, ~30 min) + refresh token (7 days), issued at `/auth/login`
- Token payload: `{ "sub": user_id, "role": "student|parent|counselor|admin", "exp": ... }`
- FastAPI dependency `require_role(["student"])` used per-route
- Parent access is additionally scoped: a parent's token only unlocks data for `linked_student_ids`, checked on every query — not just role, but relationship
- Passwords hashed with bcrypt (`passlib`)
- All cross-role reads additionally re-check the relevant `consents` document at query time (RBAC says "can this role type see this endpoint," consent says "can this role see *this specific student's* data")

---

## 9. Consent Mechanism

- Consent is a **separate collection**, editable anytime by the student, with granular toggles:
  - `share_summary_with_parent`
  - `share_with_university_support`
  - `allow_referral_data_share`
- Every dashboard/aggregation endpoint calls a shared `check_consent(student_id, field)` utility before returning data — default is **deny** (fail-closed), not allow.
- Withdrawing consent takes effect immediately on the next query — no caching of consent state beyond a single request.
- University admin dashboards only ever see aggregated queries (e.g., `count of HIGH risk this week`) — these are not gated per-student since no individual is identifiable, but the aggregation query itself excludes students who opted out entirely of `share_with_university_support`.

---

## 10. Mobile Application Screen List

1. Splash / onboarding
2. Registration
3. Login
4. Consent setup (first-run) + editable later in Settings
5. Home / dashboard (well-being snapshot, streak, quick check-in CTA)
6. Daily check-in (stress slider, workload slider, sleep hours, activity)
7. Chatbot screen
8. Well-being trends (charts: stress, sentiment, sleep over time)
9. Risk/well-being status card (LOW/MEDIUM/HIGH, plain-language explanation)
10. Referral/support screen (counselor info, request button, external directory)
11. Notifications
12. Profile
13. Settings (consent toggles, logout, account)

---

## 11. Dashboard Screen List

**Parent Dashboard:** Login → Linked student selector → Well-being summary card → Trend chart (only if consented) → Alerts (only if consented) → No chat access ever.

**University Admin Dashboard:** Login → Aggregate overview (risk distribution pie/bar) → Trends by academic period → No individual student view.

**Counselor Interface:** Login → Referred students queue → Referral request detail (risk band + consented context only, never raw chat) → Accept/decline/reschedule → Status history.

---

## 12. Counselor Workflow

1. Counselor logs in, sees a queue of `appointments` with `status = requested`
2. Opens a request — sees student name (already an internal university relationship, not "external" data sharing), the *risk band* (not raw score internals unless configured), and consented summary signals
3. Accepts → status becomes `accepted`, student is notified
4. After meeting, counselor marks `completed`
5. Counselor never sees raw chatbot conversation text — only what the consent settings expose (summary-level)

---

## 13. External Therapist Workflow

1. Student opens "External Support" from the Referral screen (self-initiated, not auto-triggered)
2. Browses `external_therapists` directory: name, specialization, location/online, contact info
3. Student taps "Contact" → app simply surfaces the therapist's contact details (phone/email/booking link) — **no student data is transmitted by the system**
4. Optionally logs "I contacted this therapist" for the student's own referral history (visible only to the student)

---

## 14. Complete Folder Structure

```
mindpulse/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # settings, security, exceptions
│   │   ├── db/               # mongo client, index setup
│   │   ├── auth/              # routes, schemas, services
│   │   ├── consent/
│   │   ├── chat/
│   │   ├── behavior/
│   │   ├── sentiment/
│   │   ├── baseline/
│   │   ├── risk_engine/
│   │   │   └── config/risk_weights.json
│   │   ├── referral/
│   │   ├── notifications/
│   │   ├── dashboards/
│   │   └── audit/
│   ├── ai/
│   │   ├── llm_client.py
│   │   ├── sentiment_model.py
│   │   └── signal_extractor.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── mobile/
│   └── lib/
│       ├── core/
│       ├── models/
│       ├── services/
│       ├── screens/
│       ├── widgets/
│       ├── providers/
│       ├── utils/
│       └── main.dart
├── dashboard-web/
│   └── src/
│       ├── pages/parent/
│       ├── pages/admin/
│       ├── pages/counselor/
│       ├── components/
│       └── services/api.js
└── docs/
    ├── architecture.md
    ├── api-spec.md
    └── testing-strategy.md
```

---

## 15. Data Flow (End-to-End)

```
Registration → Login → Consent setup → Initial baseline (built from first
7–14 days of check-ins, seeded with population defaults until enough data
exists) → Daily check-in → Chatbot interaction → Backend receives message
→ LLM reply generated → Sentiment model scores message → Signal extractor
writes behavioral_signals + sentiment_results → Nightly job: trend analysis
compares rolling window to baseline → Risk engine computes weighted_score
→ Classifies LOW/MEDIUM/HIGH → Checks 3-day persistence rule →
If sustained HIGH: creates referral prompt (subject to consent) →
Student sees counselor recommendation → Optional external therapist step →
Follow-up: counselor marks appointment completed → risk monitoring continues
```

---

## 16. Sequence Flow — Chat Message (example)

```
Student → POST /chat/message → Backend validates JWT + consent
Backend → OpenAI API (system prompt enforces non-clinical tone)
OpenAI → reply text → Backend stores message, returns reply → Student
(async) Backend → HF sentiment model → sentiment_results
(async) Backend → signal_extractor → behavioral_signals
```

## 16b. Sequence Flow — Nightly Risk Job
```
Scheduler (cron/APScheduler) → for each active student:
  fetch last 7 days behavioral_signals + sentiment_results
  fetch current baseline
  compute deviations → weighted_score → risk_level
  check last 3 risk_scores for persistence
  write risk_scores document
  if sustained HIGH and consent allows referral → create referral prompt + notification
```

---

## 17. Testing Strategy

- **Unit tests:** risk scoring math (weights sum correctly, clipping works, threshold boundaries), baseline update capping
- **Integration tests:** check-in → signal → risk pipeline end-to-end against a test MongoDB
- **API tests:** every endpoint with valid/invalid JWT, valid/invalid role
- **Auth/RBAC tests:** parent cannot access unlinked student, student cannot access admin routes
- **Consent tests:** toggling `share_with_university_support` off immediately blocks a repeat query
- **Risk scoring scenarios:**
  - Low-risk student (stable signals) → stays LOW
  - Medium-risk student (moderate deviation, 2 days) → stays MEDIUM, no referral (persistence not met)
  - Persistent high-risk student (HIGH for 3+ days) → referral triggered
  - Temporary stress spike (1 day HIGH, then normal) → does NOT trigger referral
  - Missing data (student skips check-ins) → engine should degrade gracefully, not crash, and flag "insufficient data" rather than guessing
  - Student withdraws consent mid-flow → parent/admin queries immediately reflect the change
  - Unauthorized parent access to a non-linked student → 403
  - Unauthorized admin access to individual student data → blocked at query level, only aggregates ever exposed
  - Counselor unavailable → appointment stays `requested`, student notified of delay
  - Student chooses external therapist → logged only in student's own referral history
  - Student refuses referral → no escalation, monitoring continues, re-offered later if still sustained HIGH

---

## 18. Deployment Architecture (MVP)

```
MongoDB Atlas (managed, free tier for FYP)
        ↑
FastAPI backend on Render/Railway (env vars for OPENAI_API_KEY, JWT_SECRET, MONGO_URI)
        ↑
React dashboards deployed as static sites (Vercel/Netlify) calling the backend API
        ↑
Flutter app built as APK for demo (or Expo-equivalent internal distribution)
```
No API keys are ever bundled in the Flutter app or React bundle — all AI calls happen server-side.

---

## 19. Implementation Roadmap

- **Phase 1** — Project setup: repo structure, FastAPI skeleton, MongoDB connection, `.env` config
- **Phase 2** — Database + authentication: `users`, `student_profiles`, JWT auth, RBAC dependency
- **Phase 3** — Student mobile app shell: navigation, auth screens, home dashboard (static)
- **Phase 4** — Chatbot: `/chat` routes, OpenAI wrapper, message persistence
- **Phase 5** — Behavioral data collection: check-in endpoints + mobile check-in screen
- **Phase 6** — Sentiment analysis: HuggingFace pipeline integration, async scoring job
- **Phase 7** — Baseline: initial baseline builder, rolling update job
- **Phase 8** — Risk engine: normalization, weighting config, scoring, classification, persistence rule
- **Phase 9** — Referral system: counselor directory, appointment requests, external therapist directory
- **Phase 10** — Parent dashboard (React)
- **Phase 11** — University admin dashboard (React, aggregated views)
- **Phase 12** — Counselor interface (React)
- **Phase 13** — Integration: connect mobile trend/risk screens to real data, notification wiring
- **Phase 14** — Testing: unit + integration + scenario tests from Section 17
- **Phase 15** — Deployment: Atlas + Render/Railway + static dashboard hosting + APK build

---

## 20. MVP vs. Future Work

**In MVP:**
- Chat + sentiment + risk scoring pipeline (full)
- Request-based referral (not live calendar booking)
- Consent toggles (student-controlled)
- Aggregated admin dashboard
- Basic parent dashboard (summary + trend only)

**Future work (explicitly out of MVP scope):**
- Real-time calendar/appointment booking with slot locking
- Push notifications via FCM (MVP can use in-app notification polling)
- Multi-language chatbot support
- Wearable/device integration for sleep/activity (MVP uses self-reported input)
- Advanced anomaly detection beyond the rule-based engine (e.g., a supervised model trained on longitudinal data once enough is collected)

---

## 21. Major Technical Risks and Solutions

| Risk | Solution |
|---|---|
| OpenAI API downtime/rate limits | Retry with backoff; fallback canned supportive message; never block check-in/risk features on chat availability |
| Cold-start baseline (new student, no history) | Seed baseline with conservative population-average defaults for the first 14 days, clearly flagged as "provisional" |
| Sparse data → false LOW/HIGH classification | "Insufficient data" state shown instead of a risk label until a minimum number of check-ins exist (e.g., 5 days) |
| Local sentiment model too slow on free-tier hosting | Run inference async/background, not blocking the chat reply |
| Consent bugs leaking data | Fail-closed default (deny unless explicitly enabled) + audit log every dashboard read |
| Scope creep into "diagnosis" language | All chatbot prompts and UI copy reviewed against a fixed non-clinical phrasing checklist |

---

**Next step:** tell me which phase to implement (e.g., "IMPLEMENT PHASE 1") and I'll generate the exact files, code, commands, and verification steps for that phase, building on the decisions above without changing them unnecessarily.
