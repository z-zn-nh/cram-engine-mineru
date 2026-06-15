from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from scripts.ingest_materials import IngestPlan, make_plan, run_plan

from .subjects import Subject


@dataclass(frozen=True)
class SubjectIngestResult:
    plan: IngestPlan
    manifest_path: Path
    summary_path: Path
    exit_code: int


def _copy_source(path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / path.name
    if path.resolve() != destination.resolve():
        shutil.copy2(path, destination)
    return destination


def ingest_subject_materials(
    subject: Subject,
    paths: list[Path],
    *,
    mineru_bin: str = "mineru",
    dry_run: bool = False,
) -> SubjectIngestResult:
    copied_sources = [_copy_source(Path(path).expanduser(), subject.path / "sources") for path in paths]
    parsed_root = subject.path / "parsed"
    plan = make_plan(subject.name, copied_sources, output_root=parsed_root, mineru_bin=mineru_bin)

    manifest = {
        "subject": subject.name,
        "subject_slug": subject.slug,
        "materials": [
            {
                "source": str(job.source),
                "output_dir": str(job.output_dir),
                "primary_engine": job.primary_engine,
                "fallback_strategy": job.fallback_strategy,
            }
            for job in plan.jobs
        ],
    }
    manifest_path = parsed_root / "ingest-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    exit_code = run_plan(plan, dry_run=dry_run)
    return SubjectIngestResult(
        plan=plan,
        manifest_path=manifest_path,
        summary_path=plan.summary_path,
        exit_code=exit_code,
    )

