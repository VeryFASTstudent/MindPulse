# MindPulse

MindPulse is a non-clinical student well-being R&D prototype. It combines
voluntary student check-ins, longitudinal trends, a separate sentiment model,
explainable risk indicators, consent-aware support workflows, and
role-restricted dashboards.

## What works in the application

- **Student:** account registration/login, daily check-ins, well-being status,
  private chatbot and chat history, 7/30/90-day stress/workload/sleep/activity/
  sentiment/engagement trends, counselor directory and student-confirmed
  support requests, external support directory, privacy/sharing controls, and
  logout.
- **Counselor:** consent-filtered support-request inbox, sustained-pattern alert
  inbox, and status updates.
- **Parent:** summaries only for linked students who enabled parent sharing.
- **University admin:** opt-in aggregates only; results are suppressed until at
  least five opted-in students have recent data. Admins can manage account
  activation, risk policy, audit history, and verified external-support entries.

Risk indicators use recency-weighted personal baselines, configurable signal
weights, and a short moving average to reduce single-day fluctuations. These
are experimental design choices, not clinically validated predictions.

Parents, counselors, and admins cannot view student chat transcripts. Risk and
sentiment indicators are exploratory signals, not diagnoses or clinical advice.

## Run the backend on Windows

From the project root:

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set the MongoDB connection and a private `JWT_SECRET` in `backend\.env`.
Chat first routes common intents (greetings, thanks, help, common well-being
topics, and safety language) to local, deterministic replies. Open-ended
messages are sent to the configured hosted model. For Gemini, set
`CHAT_PROVIDER=gemini` and `GEMINI_API_KEY` to a key created in Google AI
Studio. The default model is `gemini-2.5-flash`; change `GEMINI_CHAT_MODEL` to
another model available to your account if desired. The key belongs only in
`backend\.env`, never in Flutter or source control. For OpenAI, set
`CHAT_PROVIDER=openai` and `OPENAI_API_KEY`. If the hosted model is unavailable
or its quota is exceeded, the backend falls back to transparent local guided
mode; these local replies are not a generative LLM. Separately, the Hugging
Face emotion model processes messages in the background for sentiment trends;
it does not write the conversational reply. Restart the backend after changing
`.env`.

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` to inspect the API or
`http://127.0.0.1:8000/health` to check API and database connectivity. On first
startup, the sentiment model may download from Hugging Face in the background;
the chatbot remains available while it loads.

## Run the Flutter app

In another PowerShell window:

```powershell
Set-Location .\mobile
flutter pub get
flutter run -d web-server --web-port 8080
```

Open `http://127.0.0.1:8080`. The web app expects the API at
`http://127.0.0.1:8000`. For an Android emulator, the configured API address is
`http://10.0.2.2:8000`; for a physical device, change the address in
`mobile\lib\core\constants.dart` to the development computer's LAN IP.
To use a non-default API URL for a run, pass
`--dart-define=MINDPULSE_API_BASE_URL=http://127.0.0.1:8001` to `flutter run`.

On Windows installations where Flutter tooling fails because the workspace or
Flutter SDK path contains spaces (including the `objective_c` native-assets
hook), map both directories to drive letters. Replace these sample paths with
the locations on your computer:

```powershell
subst Z: "C:\Users\Hassan Musa\Downloads\mindpulse_phase1\mindpulse\mobile"
subst F: "C:\Users\Hassan Musa\Flutter"
Set-Location Z:\
F:\flutter\bin\flutter.bat pub get
F:\flutter\bin\flutter.bat run -d web-server --web-port 8080 --dart-define=MINDPULSE_API_BASE_URL=http://127.0.0.1:8001
```

These commands assume `F:` maps to `C:\Users\Hassan Musa\Flutter`, which
contains the `flutter` SDK folder. If the drive is already mapped, do not run
`subst` again; check the Flutter command path with
`Test-Path F:\flutter\bin\flutter.bat`.

## Stakeholder account provisioning

Public registration is intentionally student-only. An authorized operator can
create a parent, counselor, or admin account using the interactive provisioning
tool. It hashes the supplied password and does not store or print it:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
python -m scripts.provision_stakeholder
```

For a parent account, the tool requires an existing student email and links that
student. The student must separately enable parent sharing in Profile before
any summary appears. For a counselor account, the tool creates both the
counselor login and the directory profile. The student must enable referral
sharing and explicitly request support before the counselor can see a request.
An admin account can view only the privacy-protected aggregate dashboard.

Use synthetic accounts and data for demonstrations. Do not provision real
student mental-health data in a demo database.

## Validation

Backend unit tests:

```powershell
Set-Location .\backend
python -m unittest discover -s tests -v
python -m compileall -q app ai scripts
```

Flutter checks:

```powershell
Set-Location .\mobile
flutter analyze
flutter test
```

## Research scope and RAG

The proposal does not require a particular generative chatbot provider. It
specifies a conversational daily check-in chatbot and NLP-based sentiment
analysis. RAG is a possible future extension for retrieving reviewed
well-being and university-support resources; it is not required for the
current prototype and must not determine risk scores or escalation.

See [FYP_RnD_Assessment_and_Roadmap.md](./FYP_RnD_Assessment_and_Roadmap.md) for
the proposal alignment, evaluation design, and research limitations.

## Demo accounts (synthetic)

The repository includes a guarded synthetic dataset for demonstrations. It will
refuse to run unless `ALLOW_DEMO_SEED=true` is explicitly set. The seed uses
relative dates, real password hashing, the real risk engine, and the real
consent-checked escalation service. It never runs the Hugging Face model.

```powershell
Set-Location .\backend
$env:ALLOW_DEMO_SEED = "true"
python -m scripts.seed_demo_data --reset
```

All demo accounts use the password `Demo@12345`:

| Role | Email | Result/use |
|---|---|---|
| Student | `aisha@mindpulse.com` | Stable positive profile |
| Student | `bilal@mindpulse.com` | Sustained decline and consent-gated alert |
| Student | `hamza@mindpulse.com` | One-day spike without escalation |
| Student | `sana@mindpulse.com` | Sparse history and insufficient data |
| Student | `zainab@mindpulse.com` | High but stable personal baseline |
| Parent | `parent@mindpulse.com` | Linked to Bilal only |
| Counselor | `counselor@mindpulse.com` | Synthetic counselor inbox/profile |
| Admin | `admin@mindpulse.com` | Aggregate dashboard |
| Student | `live@mindpulse.com` | Empty account for live typing/check-in demo |

The unchanged risk formula currently evaluates the supplied Bilal narrative at
approximately `0.4713` (`MEDIUM` observed, `MONITORING` status, no alert) because
the configured HIGH threshold is `0.65` and the recency-weighted baseline adapts
during the decline.
The seed prints this mismatch instead of changing the engine. To demonstrate a
real HIGH alert, make Bilal's pre-decline baseline materially lower/higher in
the editable persona values while preserving the engine and then rerun the
seed; do not present the current MEDIUM result as a HIGH alert.

Use `--reset` to delete only records marked synthetic or belonging to these
demo addresses before recreating the dataset. Demo chat histories are stored
in `backend/scripts/demo_chats.json`; assistant messages are scripted guided
responses and are visibly marked as demo data in the Flutter chat screen.

## Chat security and Trends authentication

Personal, emotional, casual, positive, neutral, Roman Urdu, and short student
messages remain in scope. Local guardrails block only clear assistant-directed
instruction attacks, private-data/prompt extraction, crisis phrases, and
unrelated work requests. Hosted responses are JSON-validated and checked for
canary disclosure, diagnosis, medication advice, unapproved links/phone
numbers, and excessive length.

Trends/status requests use the shared authenticated client. It attaches the
JWT, refreshes once after a `401`, retries, and clears tokens with a clear
login-required error if refresh fails. The original cause of the Trends auth
error was inconsistent refresh handling: sentiment retried, behavior history
did not, and `getCurrentUser()` called a nonexistent `_tryRefresh()` method.
