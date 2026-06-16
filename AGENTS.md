# cram-engine-mineru Agent Instructions

This repository is the user's local fork of `cram-engine`. It is not the upstream install flow.

不要使用原作者的安装方式或启动方式作为本 fork 的主流程。

## Primary Trigger

Use this workflow when the user uploads PDF, PPT/PPTX, image, txt, or md course materials and says:

```text
期末速成：<课程名>
```

The user may also provide exam types or teacher-emphasized topics in the same message.

## Required Behavior

1. Do not use the upstream `/cram <course> start` flow as the primary entry.
2. Do not use the upstream `npx skills add https://github.com/liuliu667/cram-engine` install command.
3. Prefer uploaded files first. If no files are available, ask once for a local folder path.
4. Run `scripts/ingest_materials.py` with MinerU before building the knowledge tree.
5. Store user data under `~/.cram-engine/`.
6. Read `stages/stage0-ingest.md` before material ingestion, then continue with stages 1-4.

## Desktop App Direction

桌面 App 是本 fork 的主体验：左侧学科文件夹对应不同课程，中间对话复习，右侧展示引用资料和产出结果。Agent 入口仍可用，但当 `app/` 桌面工程存在时，应优先把可复用输出写入当前学科文件夹，而不是只留在聊天文本里。产出结果包括速成计划、笔记、思维导图、题库、错题本、考前总结。

## Useful Commands

Check parsing environment:

```powershell
py -3.13 scripts\ingest_materials.py --course "测试课程" --check-env
```

Dry-run material ingestion:

```powershell
py -3.13 scripts\ingest_materials.py --course "课程名" --dry-run "D:\课程资料"
```

Install this fork as a local skill:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-skill.ps1
```
