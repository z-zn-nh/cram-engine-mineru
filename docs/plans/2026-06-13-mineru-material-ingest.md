# MinerU Material Ingest Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local-first material ingestion layer so Cram Engine can use PDF, PPT/PPTX, and image resources, including formula-heavy screenshots.

**Architecture:** Add a Python CLI that normalizes course material paths, runs MinerU as the primary parser, and falls back to PPT-to-PDF conversion when native PPT parsing fails. The Skill flow gains a stage0 ingest step that stores extracted Markdown under `~/.cram-engine/materials/<course>/` and feeds summaries into stage1.

**Tech Stack:** Python standard library, pytest, MinerU CLI, optional LibreOffice, optional Pix2Text/pix2tex/PaddleOCR/Surya fallback tools.

---

### Task 1: Ingest CLI Skeleton

**Files:**
- Create: `scripts/ingest_materials.py`
- Create: `tests/test_ingest_materials.py`

**Steps:**
1. Write tests for file discovery, course output directory creation, and command planning.
2. Run `python -m pytest tests/test_ingest_materials.py` and verify the tests fail because the module is missing.
3. Implement a minimal CLI with pure functions for discovery and output paths.
4. Re-run tests and keep the implementation small.

### Task 2: MinerU Primary Strategy

**Files:**
- Modify: `scripts/ingest_materials.py`
- Modify: `tests/test_ingest_materials.py`

**Steps:**
1. Add failing tests that PDF, PPTX, and image files plan MinerU commands first.
2. Add support for configuring the MinerU executable name, defaulting to `mineru`.
3. Add dry-run mode so users can validate what would happen before running heavy OCR.
4. Re-run tests.

### Task 3: PPT Fallback Strategy

**Files:**
- Create: `scripts/convert-ppt-to-pdf.ps1`
- Modify: `scripts/ingest_materials.py`
- Modify: `tests/test_ingest_materials.py`

**Steps:**
1. Add failing tests that PPT/PPTX files get a LibreOffice PDF fallback plan.
2. Implement fallback command planning only; do not force conversion unless MinerU fails.
3. Document that PPT native parsing is preferred and PDF conversion is backup.
4. Re-run tests.

### Task 4: Skill Flow Update

**Files:**
- Create: `stages/stage0-ingest.md`
- Modify: `SKILL.md`
- Modify: `.trae/skills/cram-engine/SKILL.md`
- Modify: `.trae/rules/project_rules.md`

**Steps:**
1. Add stage0 instructions that collect material paths and call the ingest CLI.
2. Update configuration creation to accept PDF/PPT/PPTX/images/folders.
3. Update stage1 to read `materials-summary.md` together with manual knowledge points.
4. Keep all generated user data under `~/.cram-engine/`.

### Task 5: User Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `configs/example.yaml`
- Modify: `.gitignore`

**Steps:**
1. Document MinerU installation and optional open-source fallbacks.
2. Add example `materials` and `ingest` config blocks.
3. Add generated ingest artifacts to `.gitignore` if needed.
4. Run pytest and a dry-run CLI command against sample paths.
