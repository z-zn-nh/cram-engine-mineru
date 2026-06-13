---
name: cram-engine-mineru
description: 期末速成引擎 MinerU 自用版。当用户上传课程 PDF、PPT/PPTX、图片并输入“期末速成：课程名”，或提到期末复习、考试冲刺、考前突击、快速备考时触发。
version: 1.0.0
compatibility: claude-4, DeepSeek, minimax
---

# 期末速成引擎 (Cram Engine)

期末速成学习工具。基于学习科学原理，通过四阶段流水线将课程重点转化为个性化高效学习会话。

## 触发场景

当用户提到以下任一情况时自动激活：
- 上传课程 PDF、PPT/PPTX、图片后输入 `期末速成：<课程名>`
- 期末速成、期末复习、考试冲刺、考前突击
- 明确表示要在短时间内备考某门大学课程
- "帮我速成XX课""XX课怎么速成"

## 文件路径

- 阶段指令文件位于项目根目录的 `stages/` 下
- 资料摄取脚本位于项目根目录的 `scripts/ingest_materials.py`
- 配置模板位于项目根目录的 `configs/` 下
- 用户进度数据存储在 `~/.cram-engine/` 下（首次使用时自动创建）

## 工作流程

此 skill 执行资料摄取 + 四个学习阶段的流水线。**关键原则：每次只执行一个阶段，不要合并。每进入一个新阶段，必须先 Read 对应的 stage 文件获取完整系统指令。**

### 启动前检查

1. 从 `期末速成：<课程名>` 中解析课程名
2. 优先使用用户上传的文件作为课程资料
3. 如果没有上传文件，再询问资料文件夹路径
4. 检查用户是否已有 `~/.cram-engine/configs/<课程名>.yaml`
5. 如果配置存在 → 合并本次资料和题型信息；如果存在未摄取资料路径，先进入阶段0，否则进入阶段1
6. 如果配置不存在 → 执行下方「轻量配置创建流程」

#### 轻量配置创建流程

不要使用原作者七问流程。能从用户上传文件和启动指令推断的信息不要追问。

```
📋 已收到课程资料，先创建轻量配置。

① 课程名称：从 "期末速成：<课程名>" 中提取

② 资料来源：优先使用上传文件；没有上传文件才问资料文件夹路径

③ 题型：用户启动指令写了就记录；没写则阶段0后只问一次

④ 老师重点：用户写了就记录；没写则从资料标题、重复内容、总结页中提取

⑤ 知识点：阶段0从资料中自动提取，用户手动补充的信息优先级最高
```

默认 ingest：

```yaml
ingest:
  primary_engine: mineru
  ppt_strategy: mineru_native_then_pdf
  image_strategy: mineru_then_pix2text
  formula_ocr: true
  keep_page_refs: true
```

### 阶段0：资料摄取

1. **必须用 Read 工具读取** `stages/stage0-ingest.md` 获取资料处理策略
2. 对 `materials.paths` 中的文件或文件夹运行：
   `python scripts/ingest_materials.py --course "<课程名>" <资料路径...>`
3. MinerU 是主解析引擎。PPT/PPTX 原生解析失败时，再用 LibreOffice 转 PDF 兜底
4. 将 `~/.cram-engine/materials/<课程名>/materials-summary.md` 作为阶段1输入的一部分

所有问题回答完毕后，将信息整理为 YAML 配置写入 `~/.cram-engine/configs/<课程名>.yaml`。

默认 preferences：

```yaml
preferences:
  language: 中文
  tone: 先给一句话核心结论再展开，拒绝学术黑话
  teaching_methods: [concrete_first, chunking, elaboration, generation]
  memory_hooks: [acronym, contrast_table, absurd_example]
  exam_tactics: [keyword_mining, trap_awareness, framework_building]
  example_domains: [大学社团/学生会, 小组作业与合作冲突, 宿舍矛盾, 实习/兼职, 选课与绩点博弈]
  pacing:
    check_in_frequency: every_3_points
    reteach_trigger: "再讲一遍"
```

### 阶段1：拆解知识点树

1. **必须用 Read 工具读取** `stages/stage1-deconstruct.md` 获取完整的系统指令模板
2. 将课程配置中的 must_know、key_points 和阶段0生成的 materials-summary.md 填入系统指令
3. 执行拆解，输出知识点树
4. 将输出写入 `~/.cram-engine/progress/<课程名>-progress.md`
5. 展示知识点总数和分布，等待用户确认：
   - 回车 → 全部进入阶段2
   - "先攻 must_know" → 只学核心考点
   - 指定跳过编号（如"跳过 9, 10, 13"）
6. 确认后进入阶段2

### 阶段2：讲授（逐个知识点）

1. **必须用 Read 工具读取** `stages/stage2-teach.md` 获取完整系统指令
2. 读取进度文件，找到第一个未标记完成的知识点
3. 严格按4步认知策略执行：concrete first → chunking → elaboration → generation
4. 根据知识点的 hook 类型附加记忆强化（口诀/对比表/荒诞场景）
5. 讲完后更新进度文件中该知识点为已完成
6. **每讲完3个知识点暂停**：展示已学清单，问用户节奏
7. must_know 全部讲完后展示里程碑提示
8. 全部讲完或用户说"跳过"后进入阶段3

用户的节奏控制：
- "继续" → 正常节奏
- "加速" → 精简版（跳过 generation 步骤）
- "减速" → 每个点多配一个例子
- "再讲一遍" → 换场景换角度，不重复原话
- "跳过" → 停止讲授，直接进阶段3。跳过的点在阶段3仍会出题

### 阶段3：检题（按题型适配）

1. **必须用 Read 工具读取** `stages/stage3-test.md` 获取出题策略和四种子模式指令
2. 题型映射：
   - 选择/判断 → 子模式 A
   - 案例分析 → 子模式 B
   - 情景/应用 → 子模式 C
   - 其他题型 → 子模式 D
3. 出题策略（由你控制，不依赖模型）：
   - must_know 考点：每种题型全覆盖
   - key_points 考点：每点随机1-2种题型
4. 按子模式依次出题
5. 用户答完后逐题批改，标注对错和解析
6. 记录答错和不确定的知识点
7. 更新进度文件
8. 存在错题则进入阶段4，全对则跳过阶段4直接输出总结

### 阶段4：闭环补漏

1. **必须用 Read 工具读取** `stages/stage4-remediate.md` 获取完整系统指令
2. 只处理阶段3中出错或不确定的知识点
3. 每个错误知识点执行：诊断根因 → 换讲法 → 重测 → 顽固判定
4. must_know 答错的额外多出3道新题
5. 二次错误的标记为"顽固点"，建议隔天再攻
6. 输出总结：已纠正数、顽固点清单、must_know 掌握状态
7. 最终更新进度文件

## 交互风格

- 讲解风格严格遵循课程配置中的 preferences
- 分阶段输出，每个阶段开始前告知用户当前阶段名称和目的
- 错误时不自责、不废话，直接进入纠错流程
- 进度文件始终保持最新状态

## 设计原则

- 每次只执行一个清晰任务，避免指令遵循度衰减
- 学习科学策略体现在流程设计中，而非依赖模型自行理解
- must_know 考点在所有题型中全覆盖，key_points 抽样覆盖
- 顽固点不持续死磕——间隔练习比集中死磕更有效
