# MindPulse Chat Security and Check-in Changes

Date: 2026-10-21

## Scope

This change set hardens the student chatbot, adds a confirmation-gated conversational daily check-in, and adds one configurable risk-engine data-coverage rule. Risk scoring, baseline calculation, consent logic, and escalation logic were otherwise left unchanged.

## Task 1: Guardrails

- Added `backend/app/chat/guardrails.py`.
- Normalizes incoming text using Unicode NFKC, control/zero-width removal, and whitespace collapse.
- Runs crisis detection before injection, intent routing, or hosted generation.
- Added English and Roman Urdu crisis phrases for native-speaker review.
- Added injection, prompt-extraction, role-play jailbreak, private-data, score, baseline, and consent-request blocking.
- Added hosted-output validation for canary disclosure, prompt disclosure, diagnosis, medication advice, unapproved URLs/phone numbers, and responses over 1200 characters.
- Added `backend/app/chat/crisis_resources.json` with explicit placeholders for verified local crisis resources.
- Crisis input stores the student message normally and returns deterministic `safety` mode without creating an escalation event.

## Task 2: LLM prompt and context

- Rewrote the system prompt with ROLE, ALLOWED SCOPE, OUT OF SCOPE, UNTRUSTED INPUT, SAFETY, STYLE, and OUTPUT FORMAT sections.
- Added a random startup canary token.
- Hosted responses must be JSON with `in_scope` and `reply`.
- Invalid JSON or out-of-scope responses use a fixed guided fallback.
- The context remains the fixed system prompt plus the current student's latest 10 session messages only.
- The LLM has no tools, database access, risk data, baseline data, consent data, profile data, or other-user data.

## Task 3: Input caps and rate limiting

- Retained the 2,000-character request limit.
- Added whitespace-only rejection.
- Added configurable in-memory per-user limits: 20 messages/minute and 300/day by default.
- Limits are keyed by authenticated JWT user ID. In-memory limiting is appropriate for the single-instance demo only.

## Task 4: Conversational check-in

- Added draft state on the chat session with collecting, awaiting_confirmation, cancelled, and saved states.
- Collects fields in this order: stress, workload, sleep hours, activity.
- Uses deterministic number extraction and the existing `CheckinRequest` ranges.
- Supports skip/cancel input and prioritizes crisis detection at every step.
- Added authenticated `POST /chat/checkin/confirm` with confirm, edit, and cancel actions.
- Only confirmation calls the existing `submit_checkin` service; collection never saves behavioral data.
- Updated the Flutter chat screen with Confirm, Edit, and Cancel controls.

## Task 5: Security tests

- Added `backend/tests/fixtures/chat_redteam.json` with more than 50 categorized cases.
- Added `backend/tests/test_chat_security.py` covering normalization, red-team classification, output filtering, context isolation, logging, and minimum signal coverage behavior.
- Existing hosted-chat fixtures were updated to the new JSON response contract.

Run the backend tests with:

```powershell
Set-Location .\backend
python -m unittest discover -s tests -v
```

## Task 6: Minimum signal coverage

- Added `min_signal_coverage` to the risk configuration with a default of `0.5`.
- Available signal weights are still renormalized, but if their total weight is below the configured coverage threshold, the result is `INSUFFICIENT_DATA` rather than LOW/MEDIUM/HIGH.
- Added the field to admin risk-policy validation and persistence.
- The setting is excluded from the signal-weight sum.

## Files changed

- `backend/app/chat/crisis_resources.json`
- `backend/app/chat/guardrails.py`
- `backend/app/chat/service.py`
- `backend/app/chat/routes.py`
- `backend/app/chat/schemas.py`
- `backend/ai/llm_client.py`
- `backend/app/core/config.py`
- `backend/app/risk_engine/config/risk_weights.json`
- `backend/app/risk_engine/scoring.py`
- `backend/app/risk_engine/service.py`
- `backend/app/dashboards/schemas.py`
- `backend/app/dashboards/admin_service.py`
- `backend/tests/fixtures/chat_redteam.json`
- `backend/tests/test_chat_security.py`
- `backend/tests/test_chat_fallback.py`
- `backend/tests/test_admin_controls.py`
- `mobile/lib/services/chat_service.dart`
- `mobile/lib/screens/chat/chat_screen.dart`

## Items requiring review

- Crisis-resource placeholders must be replaced with verified institution/local values before demonstration or deployment.
- Roman Urdu crisis phrases are intentionally small and require native-speaker review.
- The in-memory limiter is not suitable for multiple backend instances.
- The current Flutter confirmation card displays actions and status but does not yet provide field-level inline editing; choosing Edit restarts collection from stress.

## Follow-up revision: free personal conversation and demo readiness

The chatbot prompt was revised so students can speak freely about feelings,
ordinary life, relationships, family, money worries, studies, good news,
Roman Urdu, slang, emojis, vague messages, and gibberish. Only unrelated work
requests and clear assistant-directed attacks are refused. Refusals are short,
friendly, and non-shaming. The role-play injection patterns now require nearby
instruction/attack language, reducing false positives such as “I have to act as
the group leader tomorrow.” The session history window is eight messages.

The Trends authentication defect was fixed with
`mobile/lib/services/authenticated_client.dart`. Every Trends/status GET now
attaches the bearer token, refreshes once on `401`, retries, and clears tokens
with a login-required error if refresh fails. The root cause was inconsistent
refresh handling plus `getCurrentUser()` calling `_tryRefresh()` although the
implemented method was `tryRefresh()`. Backend CORS already allowed both
`localhost:8080` and `127.0.0.1:8080`, so it was not weakened or changed.

Added `backend/scripts/seed_demo_data.py` and the editable,
versioned `backend/scripts/demo_chats.json`. The seed is blocked unless
`ALLOW_DEMO_SEED=true`, supports `--reset`, marks all records synthetic, uses
the real bcrypt hashing, check-in, baseline, risk, and escalation services,
uses dates relative to today, creates the five story students plus parent,
counselor, admin, and the empty `live@mindpulse.com` account, and prints
the demo account/result table. Scripted histories use the requested exact daily
student-message counts and hard-coded sentiment values without running the
Hugging Face model.

Added demo seed contract coverage for message counts, crisis safety, sentiment
targets, synthetic account boundaries, and an explicit opt-in integration-test
gate for a MongoDB test database. The Flutter chat history now shows a Demo
data banner for synthetic messages and displays assistant response modes.

The integration seed assertions require a dedicated test database environment:
`MINDPULSE_TEST_DB=true`, `MONGO_DB_NAME=mindpulse_test`, and
`ALLOW_DEMO_SEED=true`. No real database is used automatically by the test.

The later free-conversation revision supersedes the earlier local blocking of
own risk/baseline/consent questions: those messages now reach the LLM so it can
truthfully explain that it has no access. Requests for another user’s data,
prompt extraction, and assistant-directed instruction attacks remain blocked;
diagnosis and medication requests are friendly out-of-scope refusals.

The guarded Mongo integration run measured Bilal's requested narrative as
`MEDIUM` observed / `MONITORING` at approximately `0.4713` with no alert under the unchanged formula;
the seed prints this mismatch and the test records it rather than changing
risk logic. The configured HIGH threshold is `0.65`, so reaching HIGH requires
adjusting Bilal's pre-decline persona baseline, not the engine.
