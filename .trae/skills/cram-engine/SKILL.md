---
name: cram-engine-mineru
description: 期末速成引擎 MinerU 自用版。当用户有本地课程文件夹，里面包含 PDF、PPT/PPTX、图片、笔记或生成产物，并希望用 OpenCode 风格 TUI Agent 进行考前速成复习时触发。
version: 2.0.0
compatibility: claude-4, DeepSeek, minimax
---

# 期末速成引擎 MinerU 自用版

这是一个自用的期末速成 Agent。当前主入口是 OpenCode 风格 TUI：用户在课程资料文件夹中运行 `cram`，当前文件夹就是学科工作区。

## 什么时候使用

当用户希望：

- 把 PDF、PPT/PPTX、图片、课堂笔记放进一个课程文件夹
- 在 cmd/PowerShell 中打开 TUI agent
- 让 agent 解析资料、整合知识、生成复习产物
- 持续对话扫清疑点、场景化学习、出题检查
- 每次打开都保留上一次记忆

## 工作区约定

当前文件夹是课程工作区，例如：

```text
通信原理/
├── 第1章.pptx
├── 老师重点.pdf
├── 公式截图.png
├── cram-output/
└── .cram/
```

`.cram/` 保存长期记忆、会话、索引、缓存、冲突记录。`cram-output/` 保存可打开和可编辑的输出文件。

## 重要原则

1. 不要把旧 GUI/Tauri app 当主线。
2. 不要把 AnythingLLM 当底座，除非用户明确重新要求。
3. 当前文件夹就是学科，不要再要求用户创建数据库里的学科。
4. 输出内容也会作为低优先级引用进入后续回答。
5. 原始资料优先级最高，生成产物优先级最低。
6. 找不到原始资料出处时，要明确说明“资料中未找到明确出处”或“该结论来自生成产物/长期记忆”。
7. 每次启动都读取 `.cram/memory/` 和 `.cram/sessions/`，不能像新会话一样失忆。
8. 需要检查长期记忆、输出产物和原始资料之间是否冲突。

## TUI 命令

```text
/help      查看命令
/status    查看资料、输出、引用、记忆状态
/ingest    扫描当前文件夹资料，md/txt 直接索引，PDF/图片/PPT 调用 MinerU 解析，PPT 失败时可用 LibreOffice 转 PDF 兜底
/plan      生成 cram-output/速成计划.md
/notes     生成 cram-output/知识点整合.md
/mindmap   生成 cram-output/思维导图.md
/quiz      生成 cram-output/题库.md
/summary   生成 cram-output/考前总结.md
/lint      检查原始资料、长期记忆和输出产物之间的矛盾
/config    重新配置 LLM
/model     切换对话模型
```

自然语言输入就是复习提问。回答应尽量引用 `.cram/index/chunks.jsonl` 中命中的资料片段。

## 资料处理

- md/txt 笔记直接切块索引。
- PDF、图片、PPT/PPTX 优先交给 MinerU。
- PPT/PPTX 如果 MinerU 原生解析失败，再用 LibreOffice/`soffice` 转 PDF 后交给 MinerU。
- 图片、扫描 PDF、公式截图优先由 MinerU 处理，必要时提示用户安装 Pix2Text 或 pix2tex 兜底。

## 输出与引用

引用优先级：

```text
原始课件 / PDF / 图片 / 老师重点
> 用户手写笔记
> .cram 长期记忆
> cram-output 生成产物
```

输出文件应保存在 `cram-output/`。输出文件可被后续索引为引用，但必须标记为生成产物，不能伪装成原始资料。

## 启动方式

```powershell
cd D:\期末资料\通信原理
cram
```

如果 `cram` 命令还没有安装，可在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-cram-command.ps1
```
