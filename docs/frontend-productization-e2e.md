# CareerAgent v3.3 Frontend Productization & End-to-End Experience

v3.3 turns the existing React workbench from a local foundation UI into a more usable frontend productization foundation. It is still not production-ready and does not certify the full product.

## What Changed

- Added centralized object selectors in `frontend/src/components/EntitySelectors.tsx`.
- Main workflow pages now use selectors for Profile, Resume, Resume Version, JD, Match Report, Project, Application, Agent Run, Knowledge Document, RAG Answer Run, Interview Answer and Agent Workflow refs.
- Match Report now runs primarily with `resume_version_id + jd_id` and exposes same-JD Resume Version compare via `/api/matches/compare`.
- Project Rewrite, Interview, Study Plan, Application, Agent and Bad Case workflows no longer require users to copy/paste primary internal IDs.
- Knowledge Base exposes retrieval mode and answer mode controls while still rendering only preview/snippet/citation content.
- Dashboard copy now uses business summaries and deep-link metric cards instead of internal IDs as primary information.
- Frontend scripts now include `lint`, `typecheck`, `test` and `test:e2e`; v3.4 adds `test:e2e:browser`.

## Privacy Display Boundary

- Resume/JD/RAG/Interview displays remain preview-first.
- Agent payloads are rendered through `sanitizeForDisplay` and `privacy_safe_payload`.
- Bad Case creation uses source selectors for known object types and summary-only text fields.
- Raw JD/document/resume text inputs remain available where the user intentionally creates a JD or RAG document; saved/displayed views use previews and citations.
- Frontend auth still stores the access token in localStorage through the existing client. v3.4 adds session list/revoke UI, but httpOnly refresh-token rotation remains a hardening item, not production-ready session security.

## Test Boundary

No new frontend dependencies were installed in v3.3. The added gates use Node built-ins:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run test:e2e:browser
```

- `lint` is a static contract check for direct fetch, raw backend URLs, exposed hand-filled ID copy and selector exports.
- `test` uses `node:test` contract checks over the source tree.
- `test:e2e` is a mocked workflow smoke test.
- `test:e2e:browser` is Playwright Chromium browser automation with synthetic API mocks. It is not a substitute for deployed-backend E2E.

## Still Not Production-Ready

- Browser-level E2E with real UI rendering now exists for Chromium with synthetic API mocks.
- Deployed-backend E2E, visual regression, accessibility audit gate, cross-browser matrix and device farm are still required for stricter certification.
- Token storage remains localStorage-based, though v3.4 adds session list/revoke controls.
- Project Rewrite refs still lack a first-class list selector because there is no rewrite list API.
- The product still relies on deterministic/local AI foundations unless real providers and real datasets are explicitly configured and audited.

v3.3 is a frontend productization foundation candidate. v3.4 blocker rework adds browser E2E foundation, but final read-only production readiness audit must still pass before any production-ready candidate tag is considered.
