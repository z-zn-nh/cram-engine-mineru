# cram Agent Core 设计方案

> 2026-06-20 · 状态：已对齐，按 P0→P3 实施
> 目标读者：接手开发的 agent / 维护者

## 背景

cram 当前是"无状态空壳"：每轮 `CommandRouter._agent_messages()` 只拼 `固定 system + 本轮关键词检索的片段 + 当前这句话`。会话日志写进 `.cram/sessions/*.jsonl` 但**从不读回**，长期记忆 `memory.md` 不进 prompt，模型每轮失忆，且把"每轮都变的检索片段塞进 system 前缀"——对 DeepSeek 的自动前缀缓存是最差实践（命中率≈0）。

本方案把它改造成有真正上下文的 **Agent Core**。定位：单机单用户、DeepSeek、中文学习场景。

## 决策（已确认）

1. **RAG**：接受引入**本地嵌入模型**（fastembed + bge，离线、零额外 key）。
2. **可观测**：日志文件 + 状态栏简显即可。
3. **compaction**：窗口用量 **80%** 触发，保留**近 10 轮**原文。

后置（本期不做）：教学 agent（建在核心之上）、子代理协作、权限/高危审批等重护栏。

## 模块拆分

- **ContextAssembler**：每轮按「稳定→易变」+ token 预算组装消息。
- **MemoryStore**：短期（会话历史）+ 长期（`memory.md`）+ 摘要，读写闭环。
- **Retriever**：统一检索接口；关键词 →（P3）本地向量 + rerank。
- **AgentLoop**：工具循环 + compaction + 轻量 reflect。
- **Observability**：token / 缓存命中 / 耗时 / 工具序列打点。

## 上下文窗口分层（核心 + 吃满 DeepSeek 缓存）

```
稳定前缀（逐字节不变 → 命中 ds 自动前缀缓存）：
  1 系统身份/原则（精简）
  2 工具定义（固定，随 API tools 传）
  3 长期记忆 memory.md（变化很慢）
  4 工作区地图（文件/产物/已索引清单；文件变才变）
  ── 会话历史（append-only，近 10 轮，前缀稳定）──
易变尾部（每轮变，不进缓存）：
  5 本轮 RAG 检索片段 + 当前用户消息（合并为最后一条 user）
```

要点：
- 检索片段从 system **挪到最后一条 user 消息**里；system 保持逐字节稳定。
- 会话历史 append-only，天然缓存友好；compaction 会重写前缀→短暂 miss（可接受）。
- ds 自动缓存，无需 `cache_control`；靠响应 `prompt_cache_hit_tokens` 验证。

## 记忆系统

- **短期**：`load_recent_session_events()` 读回近 10 轮，作为 user/assistant 消息注入历史区。
- **长期** `memory.md`：课程要点 / 用户偏好 / 易错点 / 已掌握·顽固点。写：`update_memory` 工具显式记 + 会话收尾自动抽取；读：每轮进稳定前缀。
- **compaction（对标 Codex）**：窗口用量 ≥80% → 摘要替换较早消息（保留 初始上下文 + 近 10 轮原文 + 摘要 + 当前请求），压缩后重注工作区地图 + 长期记忆 re-ground。

## RAG（DeepSeek 无 embedding → 本地）

- 嵌入：`fastembed`(ONNX/CPU) + `bge-m3`/`bge-small-zh`；向量库先 numpy 余弦，量大再 `sqlite-vec`。
- 检索 = 关键词(已有) + 向量 融合 → `bge-reranker` 重排。
- 统一 `Retriever` 接口，P0 先包现有关键词检索 + budget，P3 再接向量/rerank（不阻塞核心）。

## 轻量控制环

行动循环之上加"工具结果回灌后自评要不要继续 / 无进展即收尾"（已有 MAX_AGENT_STEPS 兜底）。不做多 agent。

## 可观测

每轮记录：输入 token、`prompt_cache_hit_tokens`/miss、输出 token、耗时、工具序列、按 ds 价估算成本 → 写 `.cram/logs/` + 状态栏简显（如 `1.2k tok · 缓存 82% · 0.4s`）。

## 输出校验（轻护栏）

回答里的 `[来源:x]` 必须落在"本轮注入的检索片段标签集合"内，否则降级标注"无明确出处"。重护栏后置。

## 落地顺序

| 期 | 内容 | 验收 |
|---|---|---|
| **P0** | ContextAssembler：稳定/易变分层、会话历史读回、工作区地图、检索移到尾部 | agent 记得上文；system 前缀稳定（不含检索片段） |
| **P1** | 长期记忆闭环：`memory.md` 读 + `update_memory` 工具 + 收尾自动抽取 | 跨会话积累 |
| **P2** | compaction（80%/10 轮）+ 最小可观测 | 长对话不爆；token/命中率/耗时可见 |
| **P3** | RAG：Retriever 接口 → 本地向量 + rerank | 答得准、引用实 |
| 之后 | 教学 agent 重构到核心上 → 子代理/护栏 | |

每期独立可冒烟 + 测试。
