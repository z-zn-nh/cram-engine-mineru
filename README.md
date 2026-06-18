# 期末速成引擎 MinerU 自用版

> 基于 [liuliu667/cram-engine](https://github.com/liuliu667/cram-engine) 改造。当前主线不是 GUI，也不是 AnythingLLM，而是一个在课程资料文件夹里启动的 OpenCode 风格 TUI 期末速成 Agent。

仓库地址：[z-zn-nh/cram-engine-mineru](https://github.com/z-zn-nh/cram-engine-mineru)

## 核心形态

当前文件夹就是学科工作区。你把 PDF、PPT/PPTX、图片、课堂笔记等资料放进一个文件夹，然后在该文件夹里启动：

```powershell
cd D:\期末资料\通信原理
cram
```

TUI 会打开一个类似 OpenCode 的全屏对话界面：

- 顶部状态栏显示课程名、资料数量、输出数量和记忆状态
- 中间是 Agent 对话流
- 底部是输入框
- 引用、写入文件、下一步动作直接出现在对话流里

## 文件夹约定

第一次打开时会自动创建：

```text
通信原理/
├── 第1章.pptx
├── 老师重点.pdf
├── 公式截图.png
├── cram-output/
│   ├── 速成计划.md
│   ├── 知识点整合.md
│   ├── 思维导图.md
│   ├── 题库.md
│   └── 考前总结.md
└── .cram/
    ├── memory/
    │   ├── memory.md
    │   └── conflicts.jsonl
    ├── sessions/
    │   └── current.jsonl
    ├── parsed/
    ├── index/
    └── cache/
```

`.cram/` 是长期记忆和索引区，`cram-output/` 是给你打开、编辑、保存的复习产物区。

## 记忆与引用

Agent 每次打开都会读取 `.cram/` 里的长期记忆和上次会话。输出内容也会作为低优先级引用重新进入资料目录：

```text
原始课件 / PDF / 图片 / 老师重点
> 用户手写笔记
> .cram 里的长期记忆
> cram-output 里的生成产物
```

如果只在生成产物里找到结论，而原始资料里没有明确出处，Agent 必须提示这一点，避免自己引用自己后越滚越偏。

## 常用命令

在 TUI 输入框里使用：

| 命令 | 作用 |
|---|---|
| `/help` | 查看命令 |
| `/status` | 查看当前资料、输出、引用和记忆状态 |
| `/ingest` | 扫描当前文件夹资料，后续接入 MinerU 解析 |
| `/plan` | 写入 `cram-output/速成计划.md` |
| `/notes` | 写入 `cram-output/知识点整合.md` |
| `/mindmap` | 写入 `cram-output/思维导图.md` |
| `/quiz` | 写入 `cram-output/题库.md` |
| `/summary` | 写入 `cram-output/考前总结.md` |
| `/lint` | 检查长期记忆、输出产物和引用之间的冲突 |

直接输入自然语言就是复习提问，例如：

```text
帮我用考试题角度讲采样定理
```

## 环境配置

安装后端依赖：

```powershell
cd D:\cram-engine
pip install -r app\backend\requirements.txt
```

安装 `cram` 命令：

```powershell
cd D:\cram-engine
powershell -ExecutionPolicy Bypass -File scripts\install-cram-command.ps1
```

安装器会同时写入 `C:\Users\<你>\.cram-engine-mineru\bin\cram.cmd` 和 `C:\Users\<你>\AppData\Local\Microsoft\WindowsApps\cram.cmd`。后者通常已经在 Windows 的 PATH 里，可以避免新装命令后当前终端仍然找不到 `cram`。

第一次安装后需要重开终端。之后可以在任意课程资料文件夹里运行：

```powershell
cd D:\期末资料\通信原理
cram
```

如果只想确认命令是否安装成功，不进入全屏 TUI，可以运行：

```powershell
cram --status
```

配置 OpenAI-compatible 模型：

```powershell
setx CRAM_LLM_API_KEY "你的密钥"
setx CRAM_LLM_BASE_URL "https://api.openai.com/v1"
setx CRAM_LLM_MODEL "gpt-4o-mini"
```

`setx` 后需要重新打开终端。

## MinerU

主解析引擎仍然是 MinerU。第一版 TUI 已经建立文件夹、记忆、输出和命令体系；后续 `/ingest` 会继续接入 MinerU 解析 PDF/PPT/图片并建立可引用索引。

检查环境：

```powershell
py -3.13 scripts\ingest_materials.py --course "测试课程" --check-env
```

安装 MinerU：

```powershell
pip install --upgrade pip
pip install uv
uv pip install -U "mineru[all]"
```

## 旧入口说明

`app/frontend` 和 `app/tauri` 是之前的 GUI 尝试，暂时不是主线。当前主线是 OpenCode 风格 TUI，用来先验证 Agent 是否真的能理解资料、整合知识、引用来源、发现矛盾并生成有用复习产物。

## 许可

MIT License
