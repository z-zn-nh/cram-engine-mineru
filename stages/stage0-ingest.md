# 阶段0：资料摄取

## 何时调用

用户输入 `/cram <课程名> start` 后，如果课程配置不存在，或配置中的 `materials.paths`
包含 PDF、PPT/PPTX、图片或资料文件夹，先执行本阶段。

## 目标

把用户的课程资料转换为适合 LLM 阅读的 Markdown/JSON，并生成
`~/.cram-engine/materials/<课程名>/materials-summary.md`，供阶段1拆解知识点树使用。

## 支持输入

- PDF：`.pdf`
- 演示文稿：`.ppt`、`.pptx`
- 图片：`.png`、`.jpg`、`.jpeg`、`.webp`
- 文本：`.txt`、`.md`
- 文件夹：递归扫描以上格式

## 处理策略

1. 主引擎使用 MinerU。
2. PPT/PPTX 优先交给 MinerU 原生解析。
3. 如果 PPT/PPTX 原生解析失败，再用 LibreOffice 转 PDF，然后把 PDF 交给 MinerU。
4. 图片优先交给 MinerU。公式密集、模型图或复杂截图识别不佳时，建议使用 Pix2Text；
   单独公式图可用 pix2tex 兜底。
5. 所有生成物保存到 `~/.cram-engine/materials/<课程名>/`，不要写入仓库。

## 推荐命令

```bash
python scripts/ingest_materials.py --course "<课程名>" "<资料路径1>" "<资料路径2>"
```

先检查环境：

```bash
python scripts/ingest_materials.py --course "<课程名>" --check-env
```

先看执行计划，不真正 OCR：

```bash
python scripts/ingest_materials.py --course "<课程名>" --dry-run "<资料路径>"
```

## 阶段0完成后

1. 确认 `materials-summary.md` 已生成。
2. 从 MinerU 输出的 Markdown/JSON 中提取以下信息，写入课程配置或阶段1输入：
   - 章节结构和标题层级
   - 反复出现的术语、公式、模型图名称
   - 老师 PPT 中加粗、标题、重复出现的重点
   - 可能对应名词解释、简答、论述、案例分析的考点
   - 文件名、页码或幻灯片来源
3. 如果用户同时提供手动知识点，以手动知识点为最高优先级；资料提取结果作为补充。

