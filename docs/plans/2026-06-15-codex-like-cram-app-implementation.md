# Codex-like Cram App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Codex-like desktop app for the existing 期末速成 engine, with subject folders, document ingestion, LLM-powered review chat, citations, and saved artifacts.

**Architecture:** Keep the product focused on exam cramming. Use a Tauri + React shell for the desktop app, a Python/FastAPI backend for MinerU, storage, retrieval, and LLM orchestration, and a subject-folder file system as the durable source of truth for generated outputs.

**Tech Stack:** Tauri, React, TypeScript, assistant-ui, Python, FastAPI, SQLite, MinerU, OpenAI-compatible LLM APIs, optional Markmap/Mermaid for mind maps.

---

## Task 1: Record Baseline and Protect Existing Skill

**Files:**
- Read: `D:/cram-engine/SKILL.md`
- Read: `D:/cram-engine/AGENTS.md`
- Read: `D:/cram-engine/scripts/ingest_materials.py`
- Read: `D:/cram-engine/tests/`
- Modify: `D:/cram-engine/README.md`

**Step 1: Run existing tests**

Run:

```powershell
cd D:\cram-engine
python -m unittest discover -s tests -v
```

Expected: all existing tests pass before any app work begins.

**Step 2: Add a README section for the app direction**

Add a short section explaining that the existing skill remains supported, but the new primary direction is a desktop app:

```markdown
## 桌面 App 方向

本 fork 的核心定位仍然是期末速成引擎。后续桌面 App 会采用类似 Codex 的三栏工作区：
左侧学科文件夹，中间对话式复习，右侧引用来源与产出结果。
```

**Step 3: Run docs contract tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add README.md
git commit -m "docs: describe desktop app direction"
```

---

## Task 2: Scaffold the App Workspace

**Files:**
- Create: `D:/cram-engine/app/`
- Create: `D:/cram-engine/app/frontend/`
- Create: `D:/cram-engine/app/backend/`
- Create: `D:/cram-engine/app/tauri/`
- Create: `D:/cram-engine/app/README.md`

**Step 1: Create minimal app folders**

Create the app folders without moving the existing skill files.

**Step 2: Add app README**

Create:

```markdown
# cram-engine-mineru desktop app

Codex-like desktop app for the 期末速成 engine.

- `frontend/`: React UI
- `backend/`: Python FastAPI backend
- `tauri/`: desktop shell
```

**Step 3: Add a smoke test for app folder presence**

Create `tests/test_app_structure.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_workspace_exists():
    assert (ROOT / "app").is_dir()
    assert (ROOT / "app" / "frontend").is_dir()
    assert (ROOT / "app" / "backend").is_dir()
    assert (ROOT / "app" / "tauri").is_dir()
```

**Step 4: Run tests**

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app tests/test_app_structure.py
git commit -m "feat: scaffold desktop app workspace"
```

---

## Task 3: Implement Subject Folder Storage

**Files:**
- Create: `D:/cram-engine/app/backend/cram_app/__init__.py`
- Create: `D:/cram-engine/app/backend/cram_app/paths.py`
- Create: `D:/cram-engine/app/backend/cram_app/subjects.py`
- Create: `D:/cram-engine/tests/test_subject_storage.py`

**Step 1: Write tests**

Create tests for subject slugging and required directories:

```python
import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.subjects import create_subject, subject_slug


class SubjectStorageTests(unittest.TestCase):
    def test_subject_slug_keeps_chinese_and_removes_path_chars(self):
        self.assertEqual(subject_slug("通信原理/期末"), "通信原理-期末")

    def test_create_subject_creates_required_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", root=Path(tmp))
            for name in ["sources", "parsed", "chunks", "index", "chats", "artifacts", "citations"]:
                self.assertTrue((subject.path / name).is_dir())
            self.assertTrue((subject.path / "subject.sqlite").exists())
```

**Step 2: Run test and verify it fails**

```powershell
python -m unittest tests.test_subject_storage -v
```

Expected: import failure.

**Step 3: Implement minimal storage**

Implement:

```python
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


REQUIRED_DIRS = ("sources", "parsed", "chunks", "index", "chats", "artifacts", "citations")


@dataclass(frozen=True)
class Subject:
    name: str
    slug: str
    path: Path


def subject_slug(name: str) -> str:
    slug = name.strip().replace("\\", "-").replace("/", "-")
    slug = re.sub(r"[.]+", "", slug)
    slug = re.sub(r"\s+", "-", slug).strip("-")
    if not slug:
        raise ValueError("subject name cannot be empty")
    return slug


def create_subject(name: str, root: Path) -> Subject:
    slug = subject_slug(name)
    path = root / slug
    path.mkdir(parents=True, exist_ok=True)
    for child in REQUIRED_DIRS:
        (path / child).mkdir(exist_ok=True)
    db = path / "subject.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("create table if not exists metadata (key text primary key, value text not null)")
        conn.execute("insert or replace into metadata(key, value) values ('subject_name', ?)", (name,))
    return Subject(name=name, slug=slug, path=path)
```

**Step 4: Run tests**

```powershell
python -m unittest tests.test_subject_storage -v
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/backend/cram_app tests/test_subject_storage.py
git commit -m "feat: add subject folder storage"
```

---

## Task 4: Define Artifact Protocol and Persistence

**Files:**
- Create: `D:/cram-engine/app/backend/cram_app/artifacts.py`
- Create: `D:/cram-engine/tests/test_artifacts.py`

**Step 1: Write tests**

Test that artifact types map to fixed folders and cannot write outside the subject:

```python
import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.artifacts import save_artifact
from app.backend.cram_app.subjects import create_subject


class ArtifactTests(unittest.TestCase):
    def test_save_mindmap_artifact_under_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            artifact = save_artifact(
                subject,
                artifact_type="mindmap",
                title="通信原理总图",
                content='{"root":"通信原理"}',
                citations=["教材.pdf:p45"],
                fmt="json",
            )
            self.assertTrue(artifact.path.exists())
            self.assertIn("artifacts", artifact.path.parts)
            self.assertEqual(artifact.relative_path.as_posix(), "artifacts/思维导图/通信原理总图.json")
```

**Step 2: Implement artifact mapping**

Use fixed Chinese folders:

```python
ARTIFACT_DIRS = {
    "cram_plan": "速成计划",
    "notes": "笔记",
    "mindmap": "思维导图",
    "qbank": "题库",
    "mistakes": "错题本",
    "summary": "考前总结",
}
```

The save function must sanitize filenames, write content with UTF-8, and write a sidecar citation file:

```text
artifacts/思维导图/通信原理总图.json
artifacts/思维导图/通信原理总图.citations.json
```

**Step 3: Run tests**

```powershell
python -m unittest tests.test_artifacts -v
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add app/backend/cram_app/artifacts.py tests/test_artifacts.py
git commit -m "feat: persist subject artifacts"
```

---

## Task 5: Wrap MinerU Ingestion for App Subjects

**Files:**
- Modify: `D:/cram-engine/scripts/ingest_materials.py`
- Create: `D:/cram-engine/app/backend/cram_app/ingest.py`
- Create: `D:/cram-engine/tests/test_app_ingest.py`

**Step 1: Write tests**

Test that app ingestion copies input files into `sources/` and plans MinerU output under `parsed/`.

**Step 2: Refactor without breaking CLI**

Keep `scripts/ingest_materials.py` working. Add reusable functions only if needed:

```python
def plan_material_ingestion(course, paths, output_root=None, mineru_bin="mineru"):
    return make_plan(course, paths, output_root=output_root, mineru_bin=mineru_bin)
```

**Step 3: Implement app wrapper**

`app/backend/cram_app/ingest.py` should:

- accept a subject object and uploaded paths;
- copy original files to `sources/`;
- call existing MinerU plan with output root set to `subject.path / "parsed"`;
- write a manifest under `parsed/ingest-manifest.json`;
- return job status.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_app_ingest -v
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts/ingest_materials.py app/backend/cram_app/ingest.py tests/test_app_ingest.py
git commit -m "feat: add app subject ingestion"
```

---

## Task 6: Add Chunk and Citation Index

**Files:**
- Create: `D:/cram-engine/app/backend/cram_app/chunks.py`
- Create: `D:/cram-engine/app/backend/cram_app/citations.py`
- Create: `D:/cram-engine/tests/test_chunks.py`

**Step 1: Write tests**

Test chunk records include:

- chunk id;
- source file;
- page or slide;
- text;
- citation label.

**Step 2: Implement chunk JSONL**

First version can use JSONL files before adding vector DB:

```text
chunks/chunks.jsonl
citations/citations.json
```

**Step 3: Implement simple search**

Create a keyword scorer that returns top chunks for a query. This is intentionally simple for V1 and will be replaced or supplemented by vector search later.

**Step 4: Run tests and commit**

```powershell
python -m unittest tests.test_chunks -v
python -m unittest discover -s tests -v
git add app/backend/cram_app/chunks.py app/backend/cram_app/citations.py tests/test_chunks.py
git commit -m "feat: add chunk and citation index"
```

---

## Task 7: Add LLM Provider Settings

**Files:**
- Create: `D:/cram-engine/app/backend/cram_app/settings.py`
- Create: `D:/cram-engine/app/backend/cram_app/llm.py`
- Create: `D:/cram-engine/tests/test_llm_settings.py`

**Step 1: Write tests**

Test:

- OpenAI-compatible base URL can be saved.
- API key is not written into artifact files.
- missing API key returns a clear configuration error.

**Step 2: Implement settings**

Store provider config in app-level SQLite or JSON:

```json
{
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4.1-mini"
}
```

API keys should use OS keychain later. For V1, use environment variable or local settings with a warning in docs.

**Step 3: Implement LLM client interface**

Define an interface:

```python
class LLMClient:
    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        ...
```

**Step 4: Run tests and commit**

```powershell
python -m unittest tests.test_llm_settings -v
python -m unittest discover -s tests -v
git add app/backend/cram_app/settings.py app/backend/cram_app/llm.py tests/test_llm_settings.py
git commit -m "feat: add llm provider settings"
```

---

## Task 8: Implement Retrieval-Augmented Cram Chat

**Files:**
- Create: `D:/cram-engine/app/backend/cram_app/chat.py`
- Create: `D:/cram-engine/app/backend/cram_app/prompts.py`
- Create: `D:/cram-engine/tests/test_cram_chat.py`

**Step 1: Write tests with a fake LLM**

Use a fake LLM client and fake chunks. Verify:

- chat retrieves relevant chunks;
- prompt includes citation instructions;
- answer returns citations separately from generated content;
- no relevant chunk produces "资料中未找到明确出处".

**Step 2: Implement prompt rules**

Core rules:

```text
资料优先，来源优先，整合优先。
思维导图结构优先。
场景解释只在帮助理解时出现。
找不到资料依据时必须说明。
```

**Step 3: Implement chat orchestration**

Input:

```json
{
  "subject": "通信原理",
  "message": "先讲调制解调，然后出题",
  "mode": "review"
}
```

Output:

```json
{
  "message": "...",
  "citations": [...],
  "artifacts": [...]
}
```

**Step 4: Run tests and commit**

```powershell
python -m unittest tests.test_cram_chat -v
python -m unittest discover -s tests -v
git add app/backend/cram_app/chat.py app/backend/cram_app/prompts.py tests/test_cram_chat.py
git commit -m "feat: add retrieval augmented cram chat"
```

---

## Task 9: Add FastAPI Backend

**Files:**
- Create: `D:/cram-engine/app/backend/main.py`
- Create: `D:/cram-engine/app/backend/cram_app/api.py`
- Create: `D:/cram-engine/tests/test_api_contract.py`

**Step 1: Define API contract tests**

Endpoints:

```text
GET    /health
GET    /subjects
POST   /subjects
POST   /subjects/{subject}/sources
POST   /subjects/{subject}/chat
GET    /subjects/{subject}/artifacts
GET    /subjects/{subject}/citations
```

**Step 2: Implement FastAPI app**

Keep endpoints thin. Business logic stays in `cram_app/*`.

**Step 3: Run backend tests**

```powershell
python -m unittest tests.test_api_contract -v
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add app/backend tests/test_api_contract.py
git commit -m "feat: expose cram app api"
```

---

## Task 10: Scaffold React Frontend

**Files:**
- Create: `D:/cram-engine/app/frontend/package.json`
- Create: `D:/cram-engine/app/frontend/src/App.tsx`
- Create: `D:/cram-engine/app/frontend/src/main.tsx`
- Create: `D:/cram-engine/app/frontend/src/styles.css`
- Create: `D:/cram-engine/app/frontend/src/api/client.ts`

**Step 1: Initialize React app**

Use Vite React TypeScript.

**Step 2: Add dependencies**

Install:

```powershell
npm install @assistant-ui/react lucide-react
```

Add UI dependencies only as needed. Keep first UI lean.

**Step 3: Implement static three-column layout**

The first screen should show:

- left subject tree placeholder;
- middle chat placeholder;
- right citations/artifacts placeholder.

**Step 4: Run frontend checks**

```powershell
npm run build
```

Expected: build succeeds.

**Step 5: Commit**

```powershell
git add app/frontend
git commit -m "feat: scaffold react desktop frontend"
```

---

## Task 11: Implement Subject Folder UI

**Files:**
- Create: `D:/cram-engine/app/frontend/src/components/SubjectSidebar.tsx`
- Modify: `D:/cram-engine/app/frontend/src/App.tsx`
- Modify: `D:/cram-engine/app/frontend/src/api/client.ts`

**Step 1: Add API client methods**

Add:

```ts
export async function listSubjects() {}
export async function createSubject(name: string) {}
```

**Step 2: Implement sidebar**

Sidebar must show:

- subject list;
- selected subject;
- fixed child groups: 资料、速成计划、笔记、思维导图、题库、错题本、考前总结;
- new subject button.

**Step 3: Build**

```powershell
npm run build
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add app/frontend/src
git commit -m "feat: add subject folder sidebar"
```

---

## Task 12: Implement Chat Review UI

**Files:**
- Create: `D:/cram-engine/app/frontend/src/components/ReviewChat.tsx`
- Modify: `D:/cram-engine/app/frontend/src/App.tsx`
- Modify: `D:/cram-engine/app/frontend/src/api/client.ts`

**Step 1: Use assistant-ui for message thread**

Wire a basic chat thread to `POST /subjects/{subject}/chat`.

**Step 2: Add upload and model controls**

The composer row should have:

- text input;
- upload button;
- selected model indicator;
- send button.

**Step 3: Build**

```powershell
npm run build
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add app/frontend/src
git commit -m "feat: add review chat interface"
```

---

## Task 13: Implement Right Citations and Artifacts Panel

**Files:**
- Create: `D:/cram-engine/app/frontend/src/components/RightPanel.tsx`
- Create: `D:/cram-engine/app/frontend/src/components/ArtifactPreview.tsx`
- Modify: `D:/cram-engine/app/frontend/src/App.tsx`

**Step 1: Render citations**

Show source name, page or slide, and short excerpt.

**Step 2: Render artifacts**

Show artifact groups:

- 速成计划
- 笔记
- 思维导图
- 题库
- 错题本
- 考前总结

Clicking an artifact previews it in the right panel.

**Step 3: Build**

```powershell
npm run build
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add app/frontend/src
git commit -m "feat: add citations and artifacts panel"
```

---

## Task 14: Add Mind Map Artifact Rendering

**Files:**
- Modify: `D:/cram-engine/app/backend/cram_app/artifacts.py`
- Create: `D:/cram-engine/app/frontend/src/components/MindMapPreview.tsx`
- Modify: `D:/cram-engine/app/frontend/src/components/ArtifactPreview.tsx`
- Create: `D:/cram-engine/tests/test_mindmap_artifact.py`

**Step 1: Define mindmap JSON schema**

Use:

```json
{
  "title": "通信原理",
  "nodes": [
    {
      "id": "modulation",
      "label": "调制解调",
      "children": [],
      "citations": ["第3讲.pptx:s8"]
    }
  ]
}
```

**Step 2: Test schema validation**

Reject mind maps without root title or node labels.

**Step 3: Implement renderer**

Use a simple nested tree first. Add Markmap or React Flow later if needed.

**Step 4: Run tests/build and commit**

```powershell
python -m unittest tests.test_mindmap_artifact -v
npm run build
git add app tests/test_mindmap_artifact.py
git commit -m "feat: render mind map artifacts"
```

---

## Task 15: Add Tauri Shell

**Files:**
- Create: `D:/cram-engine/app/tauri/src-tauri/`
- Create: `D:/cram-engine/app/tauri/src-tauri/tauri.conf.json`
- Create: `D:/cram-engine/app/tauri/src-tauri/Cargo.toml`
- Create: `D:/cram-engine/app/tauri/src-tauri/src/main.rs`

**Step 1: Initialize Tauri**

Configure Tauri to load the React frontend.

**Step 2: Add backend sidecar placeholder**

Do not package FastAPI yet. First make Tauri open the frontend reliably.

**Step 3: Run desktop dev build**

```powershell
npm run tauri dev
```

Expected: desktop window opens and shows three-column UI.

**Step 4: Commit**

```powershell
git add app/tauri
git commit -m "feat: add tauri desktop shell"
```

---

## Task 16: Connect Tauri to FastAPI Sidecar

**Files:**
- Modify: `D:/cram-engine/app/tauri/src-tauri/tauri.conf.json`
- Create: `D:/cram-engine/app/backend/pyinstaller.spec`
- Modify: `D:/cram-engine/app/frontend/src/api/client.ts`

**Step 1: Package backend as a sidecar**

Use PyInstaller for the FastAPI backend.

**Step 2: Start backend from Tauri**

Configure Tauri sidecar startup and make frontend call local backend.

**Step 3: Add health check**

Frontend should wait for `/health` before enabling the app.

**Step 4: Verify**

```powershell
npm run tauri dev
```

Expected: desktop window opens, backend health is OK, subject list loads.

**Step 5: Commit**

```powershell
git add app
git commit -m "feat: connect desktop shell to backend sidecar"
```

---

## Task 17: Update Documentation and Skill Adapters

**Files:**
- Modify: `D:/cram-engine/README.md`
- Modify: `D:/cram-engine/AGENTS.md`
- Modify: `D:/cram-engine/SKILL.md`
- Modify: `D:/cram-engine/.opencode/skills/cram-engine-mineru/SKILL.md`

**Step 1: Document app usage**

Add:

```text
桌面 App 是主体验：左侧学科文件夹，中间对话复习，右侧引用和产物。
Skill/Agent 入口保留，用于辅助调用本地引擎。
```

**Step 2: Adjust agent instructions**

Agents should prefer app project folders when present and avoid treating chat text as the final storage location.

**Step 3: Run tests**

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add README.md AGENTS.md SKILL.md .opencode/skills/cram-engine-mineru/SKILL.md
git commit -m "docs: align agents with desktop app workflow"
```

---

## Task 18: End-to-End Manual Verification

**Files:**
- Create: `D:/cram-engine/docs/manual-tests/codex-like-app.md`

**Step 1: Write manual test checklist**

Checklist:

- Create subject `通信原理`.
- Upload a small PDF or PPT.
- Run ingestion.
- Ask: `生成期末速成路线`.
- Verify response has citations.
- Verify right panel shows citations.
- Verify `artifacts/速成计划/` contains a saved Markdown file.
- Ask: `生成思维导图`.
- Verify mind map displays in the app and exists under `artifacts/思维导图/`.

**Step 2: Run full tests and builds**

```powershell
python -m unittest discover -s tests -v
cd app\frontend
npm run build
```

Expected: PASS.

**Step 3: Commit**

```powershell
git add docs/manual-tests/codex-like-app.md
git commit -m "docs: add desktop app manual verification"
```

---

## Implementation Notes

- Keep the old skill usable until the app path is stable.
- Do not make the app a generic knowledge-base product.
- Every reusable output must become an artifact under the current subject folder.
- Every important generated claim should try to carry a citation.
- Mind maps should be structure-first; examples and scenes are conditional, not decorative.
- Prefer small commits after every passing vertical slice.

