# CareerAgent v3.3 Release Notes

v3.3 completes the Frontend Productization & End-to-End Experience foundation. It does not make CareerAgent production-ready.

## Added

- Centralized frontend object selectors in `frontend/src/components/EntitySelectors.tsx`.
- Selector-driven flows for Profile, Project Rewrite, Interview, Study Plan, Applications, Agent Runs, Knowledge Base and Bad Case source selection.
- Match Report Resume Version/JD run flow and same-JD Resume Version compare UI.
- Knowledge Base retrieval mode and answer mode controls.
- Dashboard business-summary deep links instead of primary internal ID copy.
- Frontend scripts: `lint`, `typecheck`, `test`, `test:e2e`.
- Node built-in source contract tests and mocked workflow E2E smoke.

## Boundaries

- The new `test:e2e` is mocked and not browser automation.
- No new frontend dependencies were installed.
- Project Rewrite still lacks a first-class rewrite list selector because no list endpoint exists.
- Frontend token storage still uses localStorage.
- v3.4 final read-only production readiness audit is still required before any production-ready candidate tag.
