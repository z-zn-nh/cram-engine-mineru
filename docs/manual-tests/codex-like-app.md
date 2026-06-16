# Codex-like 期末速成 App 手工验证

## 准备

- 安装后端依赖：`cd app\backend; pip install -r requirements.txt`
- 配置模型密钥：`$env:CRAM_LLM_API_KEY="你的密钥"`
- 可选配置：`$env:CRAM_LLM_BASE_URL="https://api.openai.com/v1"`、`$env:CRAM_LLM_MODEL="gpt-4o-mini"`
- 构建 sidecar：`powershell -ExecutionPolicy Bypass -File app\backend\build-sidecar.ps1`

## 桌面壳

- 运行：`cd app\tauri; npm run tauri dev`
- 确认窗口打开后是三栏结构：左侧学科文件夹，中间对话复习，右侧引用资料和产出结果。
- 确认左侧状态显示后端已连接。

## 学科和资料

- 新建学科 `通信原理`。
- 上传或导入一个小 PDF/PPT/PPTX/图片资料。
- 运行资料解析，确认原始资料进入当前学科的 `sources/`，解析结果进入 `parsed/`。

## 对话复习

- 输入：`生成期末速成路线`。
- 确认回答基于资料内容，右侧显示引用资料。
- 确认找不到依据时明确提示：`资料中未找到明确出处`。

## 产物

- 输入：`生成速成计划`。
- 确认右侧产出结果出现计划文件。
- 确认对应文件保存到当前学科文件夹的 `artifacts/速成计划/`。

## 思维导图

- 输入：`生成思维导图`。
- 确认右侧点击思维导图产物后显示树状结构，而不是只显示 JSON 原文。
- 确认 mindmap JSON 包含 `title`、`nodes[].label` 和必要引用。

## 回归

- 运行 `python -m unittest discover -s tests -v`。
- 运行 `cd app\frontend; npm run build`。
- 运行 `cd app\tauri; .\node_modules\.bin\tauri.cmd info`。
