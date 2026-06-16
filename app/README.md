# cram-engine-mineru desktop app

Codex-like desktop app for the 期末速成 engine.

- `frontend/`: React UI
- `backend/`: Python FastAPI backend
- `tauri/`: desktop shell

## 开发运行（dev）

桌面 App 默认连接 `http://127.0.0.1:8000` 的 FastAPI 后端。开发阶段可以手动启动后端；打包/桌面联调时可以先构建 sidecar，让 Tauri 自动拉起后端。

### 1. 启动后端

```powershell
cd app\backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 2. 配置大模型（OpenAI 兼容）

后端按 OpenAI 兼容协议调用 `POST {base_url}/chat/completions`，密钥只从环境变量读取，不会写进任何产物文件。

```powershell
setx CRAM_LLM_API_KEY "你的密钥"        # 必填
setx CRAM_LLM_BASE_URL "https://api.openai.com/v1"   # 可选，默认 OpenAI
setx CRAM_LLM_MODEL "gpt-4o-mini"        # 可选
```

`setx` 设置后需要重开终端。也可以在 `%APPDATA%\cram-engine-mineru\settings.json` 写入 `provider/base_url/model`（密钥仍走环境变量）。未配置密钥时，`/chat` 会返回 503 并提示缺少 `CRAM_LLM_API_KEY`。

### 3. 启动前端（浏览器调试）

前端默认访问 `http://127.0.0.1:8000`，如果要换后端地址，设置 `VITE_CRAM_BACKEND_URL`。

```powershell
cd app\frontend
npm install
npm run dev
```

打开 http://127.0.0.1:1420 。

打开 http://127.0.0.1:1420 。

### 4. 构建后端 sidecar（桌面壳使用）

```powershell
cd app\backend
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build-sidecar.ps1
```

生成位置：

```text
app\tauri\src-tauri\binaries\cram-backend-x86_64-pc-windows-msvc.exe
```

### 5. 启动桌面窗口

```powershell
cd app\tauri
npm install
npm run tauri dev
```

如果已经执行步骤 4，Tauri 会尝试自动启动 sidecar；如果没有构建 sidecar，就先按步骤 1 手动启动后端。
