---
name: cram-engine-mineru
description: 期末速成引擎 MinerU 自用版。Use when the user uploads PDF, PPT/PPTX, or image course materials and says 期末速成, 考前突击, 考试冲刺, or wants short-term university course review.
---

# 期末速成引擎 MinerU 自用版 (Cram Engine MinerU)

期末速成学习工具。基于学习科学原理（认知负荷理论、精细加工、生成效应、检索练习），通过四阶段流水线将课程重点转化为个性化高效学习会话。

## 桌面 App 优先

桌面 App 是本 fork 的主体验：左侧学科文件夹管理不同课程，中间用于对话复习，右侧展示引用资料和产出结果。Skill/Agent 入口用于辅助解析、检索和生成，但可复用产出必须写入当前学科文件夹，不能只藏在聊天回复里。产出结果包括速成计划、笔记、思维导图、题库、错题本、考前总结。

## 触发条件

当用户提到以下任一情况时使用此 skill：
- 上传 PDF、PPT/PPTX、图片等课程资料后输入：`期末速成：<课程名>`
- 期末速成、期末复习、考试冲刺、考前突击、快速备考
- 明确表示要在短时间内备考某门大学课程
- 提到"帮我速成XX课"

## 启动方式

主要入口是 CC 桌面端上传文件 + 自然语言指令，不依赖 slash command。

```text
期末速成：<课程名>
```

可附加考试信息：

```text
期末速成：通信原理
题型：选择、简答、计算题
老师重点：采样定理、傅里叶变换、调制解调
```

继续或查看状态：

```text
继续速成：<课程名>
查看速成状态：<课程名>
重练知识点：<课程名> / <知识点>
生成考前总结：<课程名>
```

## 文件路径约定

引擎文件（阶段指令、配置模板）位于本 SKILL.md 所在目录：
- 阶段指令：`<skill_dir>/stages/`
- 配置模板：`<skill_dir>/configs/`
- 资料摄取脚本：`<skill_dir>/scripts/ingest_materials.py`

用户数据（个人课程配置、学习进度）存储在用户主目录下：
- 课程配置：`~/.cram-engine/configs/<课程名>.yaml`
- 进度文件：`~/.cram-engine/progress/<课程名>-progress.md`
- 资料解析结果：`~/.cram-engine/materials/<课程名>/`
- 首次使用时自动创建 `~/.cram-engine/` 目录结构

> `<skill_dir>` 指 `~/.agents/skills/cram-engine-mineru/`（本 fork 的本地安装路径）。

## 工作流程

此 skill 执行“资料摄取 + 四个学习阶段”的流水线。**关键原则：每次只让模型执行一个清晰任务，不要合并阶段。**

### 启动前检查

1. 确定引擎文件路径（`<skill_dir>/stages/`）
2. 从用户指令中解析课程名。格式优先识别 `期末速成：<课程名>`
3. 优先使用用户上传的文件作为 `materials.paths`
4. 如果没有上传文件，再询问资料文件夹路径；如果用户没有资料，允许只用手动考点继续
5. 检查用户是否已有 `~/.cram-engine/configs/<课程名>.yaml`
6. 如果配置存在 → 合并本次上传资料、题型、老师重点，不覆盖旧进度
7. 如果配置不存在 → 执行下方「轻量配置创建流程」
8. 确保 `~/.cram-engine/progress/` 和 `~/.cram-engine/materials/` 目录存在

#### 轻量配置创建流程

不要再使用原作者的七问流程。上传文件场景下，能从用户指令和附件推断的信息不要追问。

```
📋 已收到课程资料，先创建轻量配置。

① 课程名称：从 "期末速成：<课程名>" 中提取

② 资料来源：优先使用用户上传的 PDF/PPT/PPTX/图片

③ 题型：如果用户启动指令里写了就直接记录；没写则在阶段0后根据资料推断，
   并只问一次"题型老师有没有说过？"

④ 老师重点：如果用户写了就记录；没写则从标题、重复内容、加粗、总结页中提取候选重点

⑤ 知识点：阶段0从资料中自动提取，用户手动补充的信息优先级最高
```

所有问题回答完毕后，将收集的信息整理为课程配置 YAML，写入 `~/.cram-engine/configs/<课程名>.yaml`。

课程配置的 `preferences` 使用以下默认值（用户无需手动填写）：

```yaml
preferences:
  language: 中文
  tone: 先给一句话核心结论再展开，拒绝学术黑话
  teaching_methods:
    - concrete_first
    - chunking
    - elaboration
    - generation
  memory_hooks:
    - acronym
    - contrast_table
    - absurd_example
  exam_tactics:
    - keyword_mining
    - trap_awareness
    - framework_building
  example_domains:
    - 大学社团/学生会
    - 小组作业与合作冲突
    - 宿舍矛盾
    - 实习/兼职
    - 选课与绩点博弈
  pacing:
    check_in_frequency: every_3_points
    reteach_trigger: "再讲一遍"
```

课程配置的 `ingest` 使用以下默认值（用户无需手动填写）：

```yaml
ingest:
  primary_engine: mineru
  ppt_strategy: mineru_native_then_pdf
  image_strategy: mineru_then_pix2text
  formula_ocr: true
  keep_page_refs: true
```

### 阶段0：资料摄取

1. 读取 `<skill_dir>/stages/stage0-ingest.md` 获取资料处理策略
2. 如果 `materials.paths` 非空，运行：
   `python <skill_dir>/scripts/ingest_materials.py --course "<课程名>" <资料路径...>`
3. MinerU 是主引擎。PPT/PPTX 先交给 MinerU 原生解析；失败后再用 LibreOffice 转 PDF 兜底
4. 图片优先 MinerU；公式密集图片可提示用户安装 Pix2Text / pix2tex 兜底
5. 将 `~/.cram-engine/materials/<课程名>/materials-summary.md` 作为阶段1输入的一部分

### 阶段1：拆解知识点树

1. 读取 `<skill_dir>/stages/stage1-deconstruct.md` 获取系统指令模板
2. 将课程配置中的 `must_know`、`key_points` 和阶段0生成的 `materials-summary.md` 填入系统指令
3. 调用模型，执行拆解
4. 将输出写入进度文件 `~/.cram-engine/progress/<课程名>-progress.md`
5. 展示知识点总数、must_know 和 key_point 分布，等待用户确认：
   - 回车 → 全部按序进入阶段2
   - "先攻 must_know" → 只学核心考点，其余跳过
   - 指定编号（如"跳过 9, 10, 13"）→ 移除对应知识点
   - 如果要移除 must_know 考点，先警告再执行
6. 确认后进入阶段2

### 阶段2：讲授（逐个知识点）

1. 读取 `<skill_dir>/stages/stage2-teach.md` 获取完整系统指令
2. 读取进度文件，找到第一个未标记完成的知识点
3. 以该系统指令 + 当前知识点内容调用模型
4. 严格按4步认知策略执行：concrete first → chunking → elaboration → generation
5. 根据知识点的 hook 类型附加记忆强化（口诀/对比表/荒诞场景）
6. 讲完后更新进度文件中该知识点为已完成
7. 继续下一个知识点
8. **每讲完3个知识点**：暂停，展示已学清单，问用户节奏（继续/加速/减速/跳过）
9. **must_know 全部讲完后**：展示里程碑提示（"核心考点全部讲完，还剩 N 个扩展知识点"），用户可说"跳过"直接进阶段3
10. 全部讲完后进入阶段3

用户的 pacing 偏好来自课程配置：
- 用户说"再讲一遍"→ 换场景/换例子/换角度重讲（不重复原话）
- 用户说"继续"→ 正常节奏
- 用户说"加速"→ 精简版（跳过 generation 步骤）
- 用户说"减速"→ 每个点多配一个例子
- 用户说"跳过"→ 停止阶段2，直接进入阶段3。跳过的知识点在阶段3仍按分级策略出题

### 阶段3：检题（按题型适配）

1. 读取 `<skill_dir>/stages/stage3-test.md` 获取出题策略和四种子模式的系统指令
2. **题型映射**（根据用户配置的 exam_types，匹配到对应子模式）：
   - 题型含"选择""判断" → 子模式 A
   - 题型含"案例" → 子模式 B
   - 题型含"情景""应用" → 子模式 C
   - 其他题型（名词解释、简答、论述、辨析、填空等） → 子模式 D
3. **出题策略**（不用模型，由你直接控制）：
   - must_know 考点：每种 exam_types 中的题型全覆盖
   - key_points 考点：每点随机1-2种题型，优先选择题+情景题
   - 如果 must_know 为空：全部考点按 key_point 处理
4. 按子模式依次调用模型出题
5. 用户答完后逐题批改：
   - 正常题：标注对错 + 1句话解析
   - 陷阱题：额外揭晓陷阱逻辑
6. 记录：答错的知识点、答对但用户追问了"为什么"的知识点
7. 更新进度文件
8. 判断是否进入阶段4

### 阶段4：闭环补漏

1. 读取 `<skill_dir>/stages/stage4-remediate.md` 获取系统指令
2. 只处理阶段3中出错或不确定的知识点
3. 每个错误知识点执行：诊断根因 → 换讲法 → 重测 → 顽固判定
4. must_know 答错的考点：额外多出3道新题
5. 二次错误的标记为"顽固点"，建议明天再攻（不继续死磕）
6. 全部处理后输出总结：已纠正数、顽固点清单、must_know 考点掌握状态
7. 最终更新进度文件

### 交互风格

- 讲解风格和例子坐标系严格遵循课程配置中的 `preferences`
- 分阶段输出，每个阶段开始前告知用户当前阶段名称和目的
- 错误时不自责、不废话，直接进入纠错流程
- 进度文件始终保持最新状态

## 设计原则

- 每次只让模型执行一个清晰任务，避免巨型 System Prompt 导致的指令遵循度衰减
- 学习科学策略体现在流程设计中（阶段顺序、暂停检查、检索练习），而非依赖模型自行理解
- must_know 考点在所有题型中全覆盖，key_points 抽样覆盖以节省时间
- 顽固点不持续死磕——认知科学表明间隔练习比集中死磕更有效
