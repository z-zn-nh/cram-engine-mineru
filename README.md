# 期末速成引擎 MinerU 自用版

> 基于 [liuliu667/cram-engine](https://github.com/liuliu667/cram-engine) 改造的本地资料版。  
> 面向 PDF、PPT/PPTX、图片、公式截图等课程资料，先用 MinerU 解析，再进入“拆解 → 讲授 → 检题 → 补漏”的期末速成流程。

仓库地址：[z-zn-nh/cram-engine-mineru](https://github.com/z-zn-nh/cram-engine-mineru)

## 桌面 App 方向

本 fork 的核心定位仍然是期末速成引擎。后续桌面 App 会采用类似 Codex 的三栏工作区：左侧是学科文件夹，中间是对话式复习，右侧是引用资料来源与产出结果。现有 Skill / Agent 入口会保留，但桌面 App 会成为主要体验。

## 这是什么

这是一个给 AI Agent 用的期末复习 Skill / 项目规则包，不是普通 Web 应用。

它适合你把课件、PDF、图片资料上传给 CC / Codex / OpenCode 后，直接输入：

```text
期末速成：课程名
```

然后让 Agent 自动完成：

1. 用 MinerU 摄取 PDF、PPT/PPTX、图片资料
2. 提取章节、术语、公式、模型图和潜在考点
3. 拆成知识点树
4. 逐个讲解
5. 按题型出题检查
6. 针对错题补漏

## 和原版有什么区别

原版更偏 slash command 和手动配置；这个 fork 更偏自用资料流。

主要改动：

- Skill 名称改为 `cram-engine-mineru`
- 启动方式改为“上传文件 + `期末速成：课程名`”
- 新增 MinerU 资料摄取阶段 `stage0-ingest`
- 支持 PDF、PPT/PPTX、图片、txt、md 和文件夹
- PPT/PPTX 优先 MinerU 原生解析，失败后再转 PDF 兜底
- 图片和公式截图优先 MinerU，必要时可接 Pix2Text / pix2tex 兜底
- 新增 Codex / OpenCode 支持：`AGENTS.md`、`.opencode/skills`、`.opencode/commands`

不要使用原作者 README 里的 `npx skills add ... liuliu667/cram-engine ...` 安装方式。那会安装回原版，不包含本 fork 的 MinerU 流程。

## 安装

先克隆本仓库：

```powershell
git clone https://github.com/z-zn-nh/cram-engine-mineru.git D:\cram-engine-mineru
cd D:\cram-engine-mineru
```

安装到本地 skills 目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-skill.ps1
```

默认安装到：

```text
%USERPROFILE%\.agents\skills\cram-engine-mineru
```

如果你的客户端读取 Claude 官方 skills 目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-skill.ps1 -TargetRoot "$env:USERPROFILE\.claude\skills"
```

## 资料解析环境

主引擎是 MinerU。你已经能在 Python 3.13 下跑通也可以继续用。

检查环境：

```powershell
py -3.13 scripts\ingest_materials.py --course "测试课程" --check-env
```

推荐安装完整 MinerU：

```powershell
pip install --upgrade pip
pip install uv
uv pip install -U "mineru[all]"
```

可选备用工具：

```powershell
# PPT 转 PDF 兜底：安装 LibreOffice，并确保 soffice 在 PATH 中

# 公式/复杂图片兜底
pip install pix2text pix2tex
```

## 使用方式

### CC 桌面端

上传 PDF、PPT/PPTX 或图片后输入：

```text
期末速成：通信原理
```

也可以附加题型和老师重点：

```text
期末速成：通信原理
题型：选择、简答、计算题
老师重点：采样定理、傅里叶变换、调制解调
```

### Codex

Codex 会读取仓库根目录的 `AGENTS.md`。

打开仓库目录，上传课程资料，然后输入：

```text
期末速成：课程名
```

### OpenCode

OpenCode 可读取：

- `AGENTS.md`
- `.opencode/skills/cram-engine-mineru/SKILL.md`
- `.opencode/commands/cram.md`

上传资料后输入：

```text
期末速成：课程名
```

或者使用命令：

```text
/cram 课程名
```

这个 `/cram` 是本 fork 的 OpenCode 命令，不是原作者的 `/cram <课程名> start`。

## 手动摄取资料

如果你只想先把资料转成 Markdown/JSON：

```powershell
py -3.13 scripts\ingest_materials.py --course "课程名" "D:\你的课程资料文件夹"
```

先 dry-run：

```powershell
py -3.13 scripts\ingest_materials.py --course "课程名" --dry-run "D:\你的课程资料文件夹"
```

输出位置：

```text
%USERPROFILE%\.cram-engine\materials\课程名\
```

## 常用指令

| 指令 | 作用 |
|---|---|
| `期末速成：<课程名>` | 上传资料后从头开始 |
| `继续速成：<课程名>` | 从断点继续 |
| `查看速成状态：<课程名>` | 查看当前阶段和错题情况 |
| `重练知识点：<课程名> / <知识点>` | 单独重讲、重测、补漏 |
| `生成考前总结：<课程名>` | 输出考前复习建议 |

## 文件结构

```text
cram-engine-mineru/
├── AGENTS.md
├── SKILL.md
├── .opencode/
├── .trae/
├── configs/
├── docs/
├── scripts/
│   ├── ingest_materials.py
│   ├── convert-ppt-to-pdf.ps1
│   └── install-skill.ps1
├── stages/
│   ├── stage0-ingest.md
│   ├── stage1-deconstruct.md
│   ├── stage2-teach.md
│   ├── stage3-test.md
│   └── stage4-remediate.md
└── tests/
```

## 适合什么课

更适合：

- 文史哲、法学、教育学、经管类等概念密集课程
- 以名词解释、简答、论述、案例分析为主的考试
- 医学、计算机、通信、工科里的概念部分
- 有 PPT、PDF、课堂截图、老师重点的课程

不太适合：

- 高数、线代、概率论等纯计算课
- 主要靠刷题熟练度的推导/计算课
- 以代码作业或设计作品为主要考核的课程

## 许可

MIT License
