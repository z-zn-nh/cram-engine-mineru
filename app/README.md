# cram-engine-mineru app

当前主线是 OpenCode 风格 TUI，不是桌面 GUI。

- `backend/`: Python 后端、TUI、命令路由、长期记忆和输出管理
- `frontend/`: 早期浏览器 GUI 尝试，暂时保留但不是主入口
- `tauri/`: 早期桌面壳尝试，暂时保留但不是主入口

## TUI 运行方式

在课程资料文件夹里启动：

```powershell
cd D:\期末资料\通信原理
python D:\cram-engine\app\backend\cram.py
```

当前文件夹就是学科工作区。TUI 会自动创建：

```text
.cram/          # 长期记忆、会话、索引、缓存
cram-output/    # 速成计划、笔记、思维导图、题库、考前总结
```

## 工作流

1. 把 PDF、PPT/PPTX、图片、md/txt 笔记放进当前文件夹
2. 启动 OpenCode 风格 TUI
3. 输入 `/ingest` 扫描资料
4. 直接对话复习，或使用 `/plan`、`/notes`、`/mindmap`、`/quiz`、`/summary`
5. 使用 `/lint` 检查长期记忆、输出产物和引用之间的冲突

输出内容会写入 `cram-output/`，并在后续会话中作为低优先级引用。每次打开 Agent 都会读取 `.cram/` 中的长期记忆和上次会话。

## 模型配置

后端按 OpenAI-compatible 协议调用模型：

```powershell
setx CRAM_LLM_API_KEY "你的密钥"
setx CRAM_LLM_BASE_URL "https://api.openai.com/v1"
setx CRAM_LLM_MODEL "gpt-4o-mini"
```

`CRAM_LLM_API_KEY` 必填，`BASE_URL` 和 `MODEL` 可换成第三方兼容服务。

## 开发验证

```powershell
cd D:\cram-engine
pip install -r app\backend\requirements.txt
python -m unittest discover -s tests -v
```
