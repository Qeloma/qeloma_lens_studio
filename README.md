# QelomaLens

![QelomaLens — The lens that sees beyond the page](assets/cover.svg)

[![License: MIT](https://img.shields.io/badge/license-MIT-C0532E.svg)](./LICENSE) ![Node >= 20](<https://img.shields.io/badge/node-%3E%3D20-1A1A1A.svg>) ![TypeScript](https://img.shields.io/badge/TypeScript-5.8-1A1A1A.svg) ![Built with Supabase](https://img.shields.io/badge/backend-Supabase-3ECF8E.svg) ![Deployed on Vercel](https://img.shields.io/badge/frontend-Vercel-000000.svg)

QelomaLens is a standalone, language-agnostic, capability-driven AI
understanding service. It ingests any input (PDF, DOCX, PNG, JPG, plain text,
or raw bytes), normalizes it into a canonical **Input Envelope**, and runs
self-describing **capabilities** on demand — powered by Google Gemini with
deterministic rule-based fallbacks that mean it never hard-fails.

**Live demo:** [qelomalens.vercel.app](https://qelomalens.vercel.app) —
running with real Gemini AI and Supabase-backed auth + persistence. See
[DEPLOYMENT.md](./DEPLOYMENT.md) to deploy your own instance.

For the current local build-agent documentation, including the Python
FastAPI agent setup and local run instructions, see
[BUILD_AGENT_GUIDE.md](./BUILD_AGENT_GUIDE.md).

---

## Features

- **Multi-format ingestion** — PDF, DOCX, PNG/JPG, and raw text/pasted
  clauses, normalized into one canonical shape (`src/ingestion/`).
- **Capability pipeline** — `SUMMARIZE`, `EXTRACT_FACTS`, `VERDICT`,
  `COMPARE`, `BREAKDOWN`, `NEXT_ACTIONS`, `GENERATE`, each a self-describing
  plugin with its own Gemini prompt *and* deterministic fallback.
- **Grounded chat** — follow-up Q&A scoped strictly to the ingested
  document's content.
- **Real authentication** — email/password and magic-link sign-in via
  Supabase Auth (`src/hooks/useAuth.tsx`, `src/components/AuthModal.tsx`).
  Analyses are saved to your account when signed in; anonymous try-it-out
  still works.
- **Three reference UI shells** — Full-Page workspace, Docked side panel,
  and a Floating widget, driven by the same CSS-custom-property design
  tokens (`src/index.css`) — a demo of embedding the same client in
  different host contexts.
- **Never hard-fails** — every external dependency (Gemini, Supabase) has a
  deterministic fallback. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the
  two-layer fallback design.

## Tech stack

| Layer     | Choice                                                       |
| --------- | ------------------------------------------------------------ |
| Frontend  | React 19 + Vite 6 + Tailwind CSS 4                           |
| Backend   | Express 4 (Node), deployed as a Vercel serverless function   |
| AI        | Google Gemini (`@google/genai`), with rule-based fallbacks   |
| Auth + DB | Supabase (Postgres + Auth), free tier                        |
| Hosting   | Vercel (Hobby, free tier)                                    |

## Project layout

```markdown
/
├── api/index.ts              # Vercel serverless entrypoint (reuses src/app.ts)
├── server.ts                 # Local dev server (Vite middleware + same app)
├── vercel.json                # Build config + /v1, /health rewrites
├── supabase/
│   ├── config.toml
│   └── migrations/            # profiles, input_envelopes, RLS policies
└── src/
    ├── app.ts                 # Shared Express app factory
    ├── main.tsx, App.tsx       # React entry + top-level state machine
    ├── hooks/useAuth.tsx       # Supabase auth context (sign up/in, magic link)
    ├── lib/                    # Browser + server Supabase clients
    ├── api/client.ts           # Fetch wrapper, attaches API key + auth token
    ├── ai/                     # Gemini provider + rule-based fallback provider
    ├── capabilities/           # One folder per capability plugin
    ├── config/                 # Env-driven config, single source of truth
    ├── gateway/v1.router.ts    # REST contract (/v1/*)
    ├── ingestion/              # File normalizers + envelope persistence
    ├── orchestrator/           # Runs a capability, gates on confidence
    ├── tenancy/                # X-API-Key → tenant resolution
    └── components/             # Reference UI (Header, LandingHero, AuthModal, …)
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for how these pieces talk to each
other and why.

## Getting started

```bash
npm install          # or: bun install
cp .env.example .env # fill in GEMINI_API_KEY at minimum — see below
npm run dev
```

Open `http://localhost:3000`. Without any Supabase env vars set, sign-in
shows a "not configured" notice and document analysis still works anonymously
against an in-memory store — nothing to configure to try the app locally.

### Environment variables

Full reference lives in [`.env.example`](./.env.example) — copy it to `.env`
and fill in. Nothing is required to run the app locally except
`GEMINI_API_KEY` (and even that is optional: without it, every capability
runs its rule-based fallback instead of calling Gemini).

| Variable | Required | Purpose |
| ------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY` | optional | Enables the real AI path; falls back to rule-based logic without it |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | optional | Server-side persistence for uploaded documents — **required** for a serverless deployment to work correctly across requests |
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | optional | Enables real sign-in/sign-up in the browser |
| `MAX_FILE_SIZE_MB` | optional | Upload size limit — see the Vercel-specific note in [DEPLOYMENT.md](./DEPLOYMENT.md) |
| `SINGLE_TENANT_MODE`, `AI_ENABLED`, `DEFAULT_TENANT_ID`, `DEFAULT_TENANT_KEY` | optional | Tenancy/demo defaults, see `src/config/index.ts` |

## Deploying your own copy

Zero-cost path: **Supabase (Auth + Postgres)** for the backend, **Vercel**
for the frontend and API. Full walkthrough in
[DEPLOYMENT.md](./DEPLOYMENT.md).

```bash
# 1. Supabase: create a project, then push the schema
supabase link --project-ref <your-project-ref>
supabase db push

# 2. Vercel: import this repo at vercel.com/new, add the env vars listed
#    in DEPLOYMENT.md, deploy.
```

## API smoke tests

```bash
# Health check
curl -s http://localhost:3000/health

# Discover capabilities
curl -s http://localhost:3000/v1/capabilities

# Ingest a document
curl -s -X POST http://localhost:3000/v1/inputs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_qelomalens_default" \
  -d '{"text": "Monthly Payslip: Basic Salary $5,000, Tax Deduction $440, Allowance $200. Net Pay $4,760.", "name": "july_payslip.txt"}'

# Run capabilities (SUMMARIZE & EXTRACT_FACTS)
curl -s -X POST http://localhost:3000/v1/inputs/<INPUT_ID>/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_qelomalens_default" \
  -d '{"capabilities": ["SUMMARIZE", "EXTRACT_FACTS"]}'

# Grounded chat query
curl -s -X POST http://localhost:3000/v1/inputs/<INPUT_ID>/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_qelomalens_default" \
  -d '{"message": "What is my net pay after all deductions?"}'
```

Swap `localhost:3000` for `https://qelomalens.vercel.app` to run these against the live deployment instead.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE)
