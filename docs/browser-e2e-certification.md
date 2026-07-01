# CareerAgent Browser E2E Certification Foundation

v3.4 rework adds real browser E2E foundation through Playwright.

## Command

```bash
cd frontend
npm run test:e2e:browser
```

The command runs Chromium via `frontend/playwright.config.ts` and synthetic API route mocks. It is separate from the older Node mocked smoke gate:

```bash
npm run test:e2e
```

## Covered Scenarios

The browser spec covers:

- login and auth state;
- session list display;
- dashboard load;
- profile selector display;
- resume upload/select;
- JD create/select;
- match run;
- six-dimension report display through match detail;
- match compare;
- project rewrite review;
- interview question generation and answer feedback;
- study plan task status update;
- application detail/status update;
- Knowledge Base grounded answer with citation;
- Agent need_more_info resume and failed retry;
- Bad Case review list;
- Evaluation metrics viewer;
- raw private text hidden by default;
- 401 fallback to sign-in;
- empty resume state.

## Matrix

Current minimum matrix:

- Chromium: required and implemented.

Current limitation:

- Firefox/WebKit smoke is not yet required by this repository gate.
- Deployed frontend against a live backend is documented as re-audit hardening, not committed as a default local gate.

## Output Hygiene

Playwright output directories are ignored:

- `playwright-report/`
- `test-results/`

Do not commit screenshots, traces or browser reports.
