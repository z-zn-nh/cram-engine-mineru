---
name: cram-engine-mineru
description: Use when the user uploads course PDF, PPT/PPTX, images, or notes and asks for 期末速成, 考前突击, 考试冲刺, or short-term university course review.
---

# Cram Engine MinerU

This is the OpenCode skill wrapper for the local `cram-engine-mineru` fork.

## Trigger

Use when the user uploads course files and types:

```text
期末速成：<课程名>
```

## Required Flow

1. Prefer uploaded files. If no files are available, ask for a local folder path.
2. Read `AGENTS.md` and root `SKILL.md` for the full workflow.
3. Read `stages/stage0-ingest.md`.
4. Run `scripts/ingest_materials.py` with MinerU.
5. Use the generated `~/.cram-engine/materials/<课程名>/materials-summary.md` as stage1 input.
6. Continue with `stages/stage1-deconstruct.md`, `stage2-teach.md`, `stage3-test.md`, and `stage4-remediate.md`.

Do not use the upstream `/cram <课程名> start` flow as the primary entry.

