# Local Upload Start Design

**Goal:** Make this fork deploy and start differently from the upstream `cram-engine` skill.

**Design:**
- Rename the skill identity to `cram-engine-mineru`.
- Install from the local fork with `scripts/install-skill.ps1`.
- Prefer CC desktop upload workflow: user uploads PDF/PPT/images and types `期末速成：课程名`.
- Treat slash commands as optional compatibility only, not the primary entry.
- On start, use attached files first, then ask for a folder path only if no attachments are available.

**Why:** The fork adds MinerU material ingestion and is intended for self-use. Using upstream's `npx skills add https://github.com/liuliu667/cram-engine` would install the wrong version and keep the old seven-question start flow.

