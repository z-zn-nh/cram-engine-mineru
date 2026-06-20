---
name: cram-engine-mineru
description: Use when the user has a local course folder and wants an OpenCode-style TUI exam-cram agent with MinerU parsing, long-term memory, citations, and generated study outputs.
---

# Cram Engine MinerU

This is the OpenCode-facing skill wrapper for `cram-engine-mineru`.

## Primary Workflow

The primary workflow is now an OpenCode 风格 TUI launched inside a course folder:

```powershell
cd D:\期末资料\通信原理
python D:\cram-engine\app\backend\cram.py
```

当前文件夹就是学科工作区。Do not treat the old GUI/Tauri app or AnythingLLM as the primary path.

## Folder Contract

The agent creates and uses:

```text
.cram/          # 长期记忆, sessions, parsed data, indexes, cache, conflicts
cram-output/    # generated study artifacts
```

Generated outputs are indexed as low-priority references. Raw course materials and user notes remain higher priority.

## Commands

```text
/help
/status
/ingest
/plan
/notes
/mindmap
/quiz
/summary
/lint
/config
/model
```

Free-form text is a study question.

## Required Behavior

1. Preserve memory between openings by reading `.cram/memory/` and `.cram/sessions/`.
2. Save reusable outputs to `cram-output/`.
3. Mark generated outputs as generated references, not raw course material.
4. Use `/lint` to check conflicts between raw sources, long-term memory, and generated outputs.
5. Keep MinerU as the preferred parser for PDF/PPT/images when ingestion is implemented.

