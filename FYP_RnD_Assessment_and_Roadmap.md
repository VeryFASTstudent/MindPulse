# MindPulse FYP: R&D Assessment, RAG Decision, and Completion Roadmap

**Purpose:** Align the current implementation with the approved proposal, define a defensible R&D contribution, and prioritize work toward a strong FYP demonstration.

## Executive summary

MindPulse now has an end-to-end prototype for the main student workflow and role-specific counselor, parent, and university-admin screens. It includes check-ins, chatbot history with transparent hosted/guided modes, sentiment and longitudinal trends, recency-weighted personal baselines, smoothed explainable risk indicators, consent-gated escalation, support requests, an administrator-managed external-support directory, and audit records.

**Working estimate: approximately 75–80% of the proposal's implementation scope is present.** This is a qualitative feature-coverage estimate, not a measured project metric or a claim of research validation. Remaining work is concentrated in end-to-end scenario testing, sentiment/risk evaluation, usability evidence, live deployment/release verification, and final polishing. Do not describe this percentage as 75–80% scientifically validated or production-ready.

The strongest FYP framing is:

> **MindPulse investigates whether an explainable, consent-first system combining voluntary student check-ins, a separate sentiment model, and personalized longitudinal baselines can surface well-being patterns more responsibly than single-message or population-only approaches, while keeping support student-controlled.**

RAG is technically feasible, but it is **not stated as a core proposal objective** and should not replace or distract from the primary research contribution. If time permits after the core system is integrated and evaluated, add a small, curated retrieval layer for evidence-based well-being resources and university support information. Do not use RAG to classify risk, diagnose students, or decide escalation.

## What the proposal actually commits to

The proposal's objectives are broader than a mobile chatbot. The core commitments are:

1. Daily student check-ins and NLP-derived sentiment signals.
2. Longitudinal emotional, engagement, and lifestyle trend analysis.
3. Individual baselines that adapt gradually.
4. Explainable, weighted multi-signal risk categories.
5. Student-controlled consent and role-specific data access.
6. Escalation only when a risk threshold, persistence rule, and prior consent all hold.
7. Student, parent, and university-facing dashboards that minimize exposed data.
8. Evaluation of risk consistency, false alarms, trend sensitivity, user acceptance, and ethical compliance.
9. A structured support directory for university and optional external psychologists.

These are drawn from the project objectives and proposed approach in [FYPFast (4).md](./FYPFast%20(4).md), especially its objectives, Sections 5.1–5.10, and evaluation chapter. The implementation plan is detailed in [MindPulse_Implementation_Blueprint.md](./MindPulse_Implementation_Blueprint.md).

## Current implementation versus proposal

| Proposal area | Evidence in the workspace | Assessment |
|---|---|---|
| Student authentication and mobile shell | FastAPI auth routes and Flutter registration/login/profile | Implemented foundation |
| Daily lifestyle check-ins | Student-only check-in APIs and Flutter check-in form | Implemented |
| Chatbot | Local intent routing handles greetings, thanks, app help, common well-being topics, and safety language first; configured hosted LLM handles open-ended messages; Hugging Face emotion/sentiment analysis remains a separate background signal | Implemented; hosted generation requires valid provider quota; intent replies are deterministic and not a generative model |
| Sentiment/emotion processing | Separate sentiment component, background processing, daily sentiment endpoint, and chat-message trend | Implemented core; performance still needs measured validation |
| Consent and role privacy | Parent summaries require linked student and current consent; counselor workflows re-check consent; admin dashboard is aggregate-only with small-cohort suppression | Implemented in application logic; integration testing should continue |
| Personal baseline | Historical check-ins and available daily sentiment use a recency-weighted personal baseline; cold-start requires five prior completed check-ins | Implemented; decay and minimum sample size require evaluation |
| Explainable weighted risk | Configurable multi-signal weights/thresholds, missing-signal omission, three-score moving-average smoothing, and persistence requirement | Implemented; thresholds and predictive validity are unvalidated |
| Longitudinal trends | Student graphs for stress, workload, sleep, activity, sentiment, and message-count engagement with 7/30/90-day ranges | Implemented in the mobile UI; trend sensitivity still needs evidence |
| Consent-gated escalation | Sustained HIGH patterns create idempotent summary-only alerts after current-consent checks; counselor can acknowledge/close; parent view is consent-filtered | Implemented in-app; external notification delivery is deliberately not included |
| Counselor/support workflow | Student-confirmed counselor requests, counselor inbox/status changes, alert inbox, and consent withdrawal checks | Implemented; trusted operator provisions counselor profiles |
| External support directory | Admin can add verified provider/resource information and activate/deactivate entries; students browse active resources | Implemented; real provider entries must be verified and supplied by the institution |
| Parent/university dashboards | Parent view is linked-student and consent-gated; admin view is aggregate-only; admin can manage accounts, risk policy, audit log, and support resources | Implemented in the application; real role provisioning remains an operator task |
| Research evaluation | Unit tests cover scoring, smoothing, baseline, role boundaries, referrals, escalations, and admin controls | Early stage; no complete dataset-backed model evaluation, scenario study, or user-acceptance evaluation |
| Deployment | Flutter web release bundle builds successfully; local API and web bundle respond on the demo ports | Local demo verified; hosted deployment/release readiness not established |

Implementation evidence includes [backend/app/main.py](./backend/app/main.py), [backend/app/baseline/service.py](./backend/app/baseline/service.py), [backend/app/risk_engine/scoring.py](./backend/app/risk_engine/scoring.py), [backend/app/risk_engine/service.py](./backend/app/risk_engine/service.py), [backend/app/escalations/service.py](./backend/app/escalations/service.py), [backend/app/dashboards/routes.py](./backend/app/dashboards/routes.py), [backend/app/referral/routes.py](./backend/app/referral/routes.py), [backend/tests/test_risk_scoring.py](./backend/tests/test_risk_scoring.py), [backend/tests/test_escalation_workflow.py](./backend/tests/test_escalation_workflow.py), [mobile/lib/screens/home/trends_tab.dart](./mobile/lib/screens/home/trends_tab.dart), and [mobile/lib/screens/home/support_tab.dart](./mobile/lib/screens/home/support_tab.dart). Verification completed: **36/36 backend tests**, Flutter analysis with no issues, **4/4 Flutter tests**, backend compile/OpenAPI checks, and a successful Flutter web release build. The local API and built app also returned HTTP 200; protected support endpoints rejected unauthenticated requests. These checks do not establish model accuracy, clinical usefulness, or production readiness.

### Practical progress interpretation

- **Student core prototype:** substantially implemented; the main value now is integration, visual polish, and reliability.
- **Whole proposed system implementation:** around **75–80% by qualitative feature coverage**; primary screens and workflows are present, while end-to-end testing, release verification, and research evaluation remain.
- **Research validation:** early; passing unit tests is not evidence that the risk approach is accurate, fair, useful, or clinically valid.

The range is intentionally approximate. Do not convert it into a precise progress claim without an agreed feature-weighting rubric.

## Recommended R&D contribution

Treat this as a **design-and-evaluate research prototype**, not a clinical prediction product. The research value should come from implementing and testing a transparent method under controlled conditions.

### Suggested research question

> In simulated longitudinal student well-being scenarios, does combining personal-baseline deviations from voluntary check-ins and a separately computed sentiment signal with persistence gating produce more stable, explainable support prompts than single-day or population-baseline approaches?

This question is feasible without collecting real students' mental-health data or claiming clinical validation.

### Suggested testable claims

- A persistence gate suppresses alerts for isolated simulated spikes compared with a no-persistence variant.
- A personal-baseline method can distinguish the same absolute signal from different simulated starting profiles in a predictable, explainable way.
- Missing signals are surfaced as insufficient evidence or omitted with documented weight normalization, rather than silently treated as reassuring evidence.
- Consent-disabled cases never expose individual data to a stakeholder or create a referral notification.

These are software/research-prototype claims. They are not claims that MindPulse can detect, diagnose, or predict depression, anxiety, self-harm, or clinical burnout.

### Experimental design

1. **Define and document the signal schema.** Specify scale, direction, allowed missingness, confidence handling, collection frequency, and privacy purpose for every signal.
2. **Create deterministic synthetic longitudinal profiles** for at least stable, gradual decline, isolated spike, persistent elevated stress, sparse/missing data, and distinct baseline profiles. Keep scenarios and expected outcomes versioned.
3. **Compare baselines/ablations** using the same scenarios: personal versus population baseline; persistence gate on versus off; sentiment included versus excluded. This creates an R&D comparison rather than a feature checklist.
4. **Measure outcomes:** confusion matrix against synthetic scenario labels, false escalation count/rate, detection delay in cycles, sensitivity to a gradual change, stability under missing data, and consent-gate pass/fail counts.
5. **Evaluate the sentiment component separately** against a documented, manually reviewed, appropriately licensed test set. Report per-class precision/recall/F1 and macro-F1, not only accuracy. Do not tune thresholds on the final evaluation set.
6. **Run usability feedback only with appropriate approval and consent.** Use non-clinical usability questions; do not ask participants to disclose diagnoses or treat feedback as clinical validation.
7. **Publish limitations:** synthetic scenarios do not represent real student populations; sentiment labels are uncertain; thresholds, recency decay, and smoothing window are design assumptions; no clinical efficacy or diagnostic validity is established.

## RAG: feasibility and recommendation

### Is RAG possible here?

**Yes.** A retrieval-augmented generation (RAG) flow could retrieve reviewed passages from a small resource collection and provide them as grounded context to the conversational assistant:

1. A maintainer adds approved university support FAQs and vetted general well-being resources.
2. Documents are versioned, chunked, and indexed for lexical or embedding-based retrieval.
3. The backend retrieves relevant snippets for a student question.
4. The LLM answers only from those snippets where possible and identifies the source.
5. If no suitable source is found, the assistant says it does not have that information and offers a safe next step.

For an FYP MVP, a small local, curated corpus with straightforward semantic search is sufficient; do not add a complex vector infrastructure unless a measured need justifies it.

### Where RAG belongs—and does not belong

**Good fit:** grounded answers about MindPulse features, university counseling hours/contact methods, and carefully reviewed general self-help information.
**Not a fit:** numeric risk scoring, baseline calculation, medical triage, diagnosis, or deciding who receives a student's information. Those remain deterministic, consent-gated, and independently testable.

The proposal does not currently define RAG as an objective. Therefore:

- Complete and evaluate the core longitudinal risk and consent workflows first.
- Add RAG only as a clearly labeled **optional research extension** if the team has time and an approved, quality-controlled source corpus.
- Evaluate retrieval relevance, answer faithfulness to retrieved passages, citation/source correctness, and safe abstention. Do not claim RAG makes mental-health advice clinically safe.
- Never index private student chat or identifiable student data into a shared knowledge base.
- Do not present generated citations as real unless they link to the exact retrieved source.

If the project is close to its deadline, defer RAG. A reliable, evaluated personal-baseline and controlled-escalation study is a stronger and more proposal-aligned AI contribution than adding RAG superficially.

## Prioritized completion roadmap

### P0 — Make claims and system behavior defensible

- Update descriptions that imply continuous or passive monitoring: the implemented signals are primarily student-provided and voluntary.
- Use “well-being indicator/pattern” rather than “clinical risk,” “diagnosis,” or a confirmed burnout detector.
- Decide and document whether stakeholder notification is ever automatic. The proposal requires prior consent and persistence; the guided referral section also says referrals are student-requested and no outside party is automatically contacted. Recommended MVP: show a support option to the student; do not send a referral or disclose data until the student explicitly initiates and confirms it.
- Verify that absence of sentiment or engagement data cannot be interpreted as a low-risk signal without a documented rationale.
- Confirm that every user-facing score/status explains its inputs, limitations, and insufficient-data state.

### P1 — Verify the student demonstration path

- Verify the Trends screen against populated and empty histories, including date ranges, units, loading, error, and refresh states.
- Exercise chat in hosted and guided modes; retain the visible mode disclosure when provider quota/key is unavailable.
- Verify the complete mobile-to-backend path: register/login → consent → check-in → chat → sentiment result → risk status → trends.
- Add a demo mode using clearly labeled synthetic profiles if the database has too little longitudinal data for a meaningful live demo. Never present synthetic data as real users.

### P2 — Verify support and privacy-safe role workflows

- Run role-by-role scenarios for student requests, counselor follow-up, parent summaries, admin aggregate views, and verified support resources.
- Retain in-app-only escalation unless external notification delivery is explicitly consented to, designed, and tested.
- Expand integration tests to prove unauthorized roles, unlinked parents, small cohorts, and withdrawn consent cannot retrieve individual data.

### P3 — Turn the prototype into an R&D result

- Create deterministic scenario fixtures and expected outcomes.
- Add integration tests for check-in → baseline → risk → persistence → consent/referral gates.
- Add sentiment test-set evaluation with per-class metrics and confidence analysis.
- Run the ablation comparisons described above and save the actual input scenarios, outputs, and metrics.
- Report negative or mixed results honestly; a research project does not need to manufacture perfect accuracy.

### P4 — Polish and deliver

- Test the mobile release build and backend startup from documented clean setup instructions.
- Add a reproducible demo dataset, seed/reset instructions, environment-variable documentation, and a short demo script.
- If dashboards are out of time, present the working API design and a clearly labeled prototype/mockup rather than implying the dashboard is implemented.
- Add RAG only if P0–P3 are in good shape and the team can evaluate it.

## Evaluation scorecard to use in the report

| Dimension | Recommended measure | Evidence to retain |
|---|---|---|
| Sentiment model | Per-class precision, recall, F1; macro-F1; confidence calibration/low-confidence behavior | Dataset description, annotation protocol, split, predictions, metric script |
| Risk scenarios | Confusion matrix on labeled synthetic profiles; false escalation rate/count | Scenario definitions, expected labels, risk outputs |
| Trend behavior | Detection delay in cycles for gradual decline; false trend triggers for stable/noisy cases | Time series and trend output per scenario |
| Persistence gate | Alerts blocked for one-day spikes; allowed only after configured consecutive cycles | Automated test report for each boundary case |
| Baseline personalization | Same change tested against different starting profiles; baseline update sensitivity | Per-profile baseline and score traces |
| Missing data | Correct insufficient-data/omission behavior; no unsupported LOW outcome | Missing-signal test matrix and API/UI result |
| Consent/security | Zero unauthorized disclosures in role/link/consent test matrix | Integration test report and audit events |
| Usability | Task completion and short non-clinical feedback, subject to approval | Protocol, anonymized results, limitations |
| RAG (optional) | Retrieval relevance, source correctness, grounded answer rate, safe abstention | Curated corpus version, retrieval/answer test set |

Do not claim a model is “accurate” from a handful of handpicked examples. Report sample size and uncertainty, and distinguish simulated scenario performance from performance on real-world student data.

## Important proposal/report issue: verify all stated results

The proposal's Chapter 8 includes numerical results and statements such as a 120-example sentiment set with **86.7%** overall accuracy, three simulated 14-day profiles, and successful escalation cases. The workspace contains unit tests for risk/baseline behavior, but no corresponding sentiment evaluation set, complete scenario runner, stored evaluation report, or evidence that those Chapter 8 results were reproduced.

Before the panel or final report:

- Treat those Chapter 8 figures as **unverified** until the exact dataset, labels, scripts, and outputs are located and the experiment is rerun.
- If they are illustrative/planned values, remove or relabel them as planned evaluation; do not report them as achieved results.
- Replace unsupported claims with the actual measured results, including failed cases and limitations.

This is important for research integrity and is more valuable than adding an impressive-sounding model or feature.

## Panel-ready explanation

> “MindPulse is an R&D prototype for ethical, non-clinical student well-being awareness. The current implementation includes a Flutter student app, role-specific counselor/parent/admin screens, FastAPI services for consent, check-ins and chat, a separate sentiment component, and an explainable multi-signal risk engine with recency-weighted personal baselines and persistence logic. Support workflows are student-controlled, while stakeholder access is limited by role and consent. We are now focusing on end-to-end scenario testing and research evaluation; passing software tests is not evidence of clinical accuracy. RAG is feasible as an optional extension for reviewed support resources, but it is not in the proposal's core contribution and will not determine risk or escalation.”

## Recommendation

Protect the research contribution: **personalized longitudinal signals + explainable scoring + persistence + consent-first support**. The application layer for the primary workflows is present; prioritize integration verification and reproducible evaluation before investing in RAG. Keep claims modest, demonstrate the actual running screens, and use experiment artifacts to support every percentage or accuracy statement.
