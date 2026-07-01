# v3.5 Monitoring And Security Checklist

- [ ] Metrics backend receives application, Agent, Eval and RAG run metrics.
- [ ] Log drain is centralized and redacts private fields.
- [ ] Tracing backend captures request and job spans without raw sensitive payloads.
- [ ] Error reporting groups failures without exposing tokens or user data.
- [ ] Alert rules cover readiness, provider failures, eval regressions and privacy/security events.
- [ ] Incident runbook has owner, severity and escalation fields.
- [ ] External security review covers API, auth, data encryption, privacy deletion, deployment and observability.
- [ ] Critical and high findings are closed or explicitly blocking release.

Completion boundary: local logs, template alerts or self-attestation alone do not certify monitoring/security readiness.
