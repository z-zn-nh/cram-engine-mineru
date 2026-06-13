---
description: 当用户上传课程资料并输入“期末速成：课程名”，或提到期末速成、期末复习、考试冲刺、考前突击、快速备考时，激活期末速成引擎 MinerU 自用版
alwaysApply: false
---

# 期末速成引擎规则

## 触发后行为

当检测到用户需要期末速成时，自动激活 `cram-engine-mineru` skill。

如果 skill 未自动激活，手动引导用户：
"检测到你需要期末速成。请上传 PDF、PPT/PPTX 或图片资料，然后输入：期末速成：课程名。"

## 适用课程类型

- ✅ 所有文科：文史哲、法学、教育学、新闻传播、社会学、政治学、经管类
- ✅ 考试以理解和论述为主的课程
- ❌ 纯定量课不适用：高等数学、概率论、计量经济学

## 引擎文件位置

- 阶段指令：`stages/stage1-deconstruct.md` → `stage2-teach.md` → `stage3-test.md` → `stage4-remediate.md`
- 配置模板：`configs/example.yaml`
- 资料摄取：`scripts/ingest_materials.py`，默认使用 MinerU
- 资料存储：`~/.cram-engine/materials/<课程名>/`
- 进度存储：`~/.cram-engine/`

## 资料处理规则

- 支持 PDF、PPT/PPTX、图片、txt、md 和资料文件夹
- PPT/PPTX 优先由 MinerU 原生解析，失败后才用 LibreOffice 转 PDF
- 图片、扫描 PDF、公式截图优先由 MinerU 处理，必要时提示用户安装 Pix2Text 或 pix2tex 兜底
