# CareerAgent v3.4 Production Readiness Blocker Rework

This document records the v3.4 blocker rework. It is not the final production readiness certification.

## Scope

The rework addresses the audit finding:

`production foundation passed, production readiness blocked`

No production-ready tag may be created from this phase alone. The next required step is a fresh v3.4 final read-only audit.

## Blocker Rework Summary

| Blocker | Rework evidence | Current status |
| --- | --- | --- |
| P0 AI provider proof | `scripts/validate_ai_providers.py`, fake provider tests, provider proof schema, masked output | Provider path exists; real external proof must be generated outside Git |
| P0 real-style benchmark | `evals/datasets/anonymized_benchmark/` with 155 manually curated anonymized real-world-style cases | Stronger than synthetic foundation; still not private production data |
| P0 human review / LLM judge | Formal schema utilities, fixtures, agreement metrics, advisory judge metrics, docs | Protocol foundation; external reviewers still required for certification |
| P0 browser E2E | Playwright Chromium config and `npm run test:e2e:browser` | Browser foundation added; Firefox/WebKit and deployed-backend runs remain hardening |
| P1 ops proof | `scripts/validate_production_deployment.py`, `scripts/run_final_readiness_gates.sh`, proof templates | Local proof foundation; real cloud/managed DB/KMS/observability proof still external |
| P1 session controls | Auth session model, list/revoke endpoints, frontend session menu, audit log | Session list/revoke foundation; httpOnly refresh rotation/SSO/MFA remain future hardening |
| P1 backup purge | Legal deletion and backup purge templates added | Template only until managed backup purge evidence exists |

## Re-audit Gate

Run:

```bash
scripts/run_final_readiness_gates.sh
```

The script writes artifacts under `/tmp/careeragent-final-readiness-gates`. Do not commit those outputs.

## Tag Boundary

Do not create:

- `v3.4.0-production-ready-candidate`
- `v3.4.0-production-readiness-certified`
- any production-ready semantic tag

until v3.4 final read-only certification passes without P0/P1 blockers.
