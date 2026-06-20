# cram-engine-mineru Agent Instructions

This repository is the user's local fork of `cram-engine`. The primary product direction is now an OpenCode 风格 TUI that runs inside a course folder.

## Primary Product Shape

- 当前文件夹就是学科工作区，不再把学科抽象成远端数据库或 GUI 左栏。
- `.cram/` stores 长期记忆, session logs, parsed data, indexes, cache, and conflict records.
- `cram-output/` stores user-facing reusable artifacts.
- 输出内容也会作为低优先级引用，原始资料永远优先于生成产物。
- 每次打开 Agent must preserve previous memory by reading `.cram/memory/` and `.cram/sessions/`.
- The first interface should feel like an OpenCode-style full-screen terminal agent: status bar, conversation stream, bottom input, slash commands.

## Required Behavior

1. Do not present the old GUI/Tauri app as the primary workflow.
2. Do not use AnythingLLM as the base unless the user explicitly reopens that direction.
3. Do not use upstream `/cram <course> start` as the main flow.
4. Prefer the current working directory as the course folder.
5. Write reusable outputs to `cram-output/`.
6. Keep machine state under `.cram/`.
7. Treat output files as references, but lower priority than raw PDF/PPT/images/user notes.
8. When evidence is missing from raw material, say that the source is generated memory/output rather than raw course material.
9. Use `/lint` or equivalent checks to identify conflicts between raw sources, memory, and generated outputs.

## TUI Commands

The expected first-pass TUI commands are:

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

Free-form text is a study question and should be answered with source-grounded citations whenever possible.

## Development Notes

Install backend dependencies:

```powershell
pip install -r app\backend\requirements.txt
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Run TUI from a course folder:

```powershell
cd D:\期末资料\通信原理
python D:\cram-engine\app\backend\cram.py
```
