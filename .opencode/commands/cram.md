---
description: Start or explain the cram-engine-mineru OpenCode-style TUI workflow
---

Use the local `cram-engine-mineru` TUI workflow.

If `$ARGUMENTS` contains a folder path, tell the user to open that folder and run:

```powershell
python D:\cram-engine\app\backend\cram.py
```

If `$ARGUMENTS` is empty, explain that the user should:

1. Put PDF/PPT/PPTX/images/notes into one course folder.
2. `cd` into that folder.
3. Run the TUI entrypoint above.
4. Use `/ingest`, `/plan`, `/notes`, `/mindmap`, `/quiz`, `/summary`, and `/lint`.

Do not use the upstream `/cram <course> start` flow. The current folder is the course workspace, `.cram/` stores long-term memory, and `cram-output/` stores reusable generated outputs.

