# CareerAgent v3.5 External Production Evidence Package

This directory stores public schemas, templates and checklists for external production evidence. It must not contain real provider keys, real review exports, cloud secrets, screenshots with private data, certificates, database URLs or generated proof outputs.

Allowed in Git:

- `schemas/`
- `templates/`
- `checklists/`
- `private_outputs/.gitkeep`

Not allowed in Git:

- generated proof JSON files;
- real `.env` files;
- real API keys, tokens, cloud credentials, DB URLs or TLS material;
- raw resume/JD/interview/review private data.

Generated evidence belongs under `evidence/private_outputs/` or `/tmp`; the directory is ignored by Git except for `.gitkeep`.
