"""Material ingestion planner and runner for Cram Engine.

MinerU is the primary parser. PPT/PPTX fallback conversion is only used when
native MinerU parsing fails.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".txt",
    ".md",
}

PPT_EXTENSIONS = {".ppt", ".pptx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md"}


@dataclass(frozen=True)
class Material:
    path: Path
    kind: str


@dataclass(frozen=True)
class IngestJob:
    source: Path
    output_dir: Path
    primary_engine: str
    primary_command: tuple[str, ...]
    fallback_strategy: str | None
    fallback_command: tuple[str, ...] | None


@dataclass(frozen=True)
class IngestPlan:
    course: str
    course_slug: str
    output_dir: Path
    summary_path: Path
    jobs: tuple[IngestJob, ...]


def safe_course_slug(course: str) -> str:
    slug = course.strip()
    slug = slug.replace("\\", "-").replace("/", "-")
    slug = re.sub(r"[.]+", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError("course name cannot be empty")
    return slug


def material_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in PPT_EXTENSIONS:
        return "presentation"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix == ".pdf":
        return "pdf"
    raise ValueError(f"unsupported material type: {path}")


def discover_materials(paths: Iterable[Path | str]) -> list[Material]:
    found: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            for child in sorted(path.rglob("*"), key=lambda item: str(item).lower()):
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    found.append(child)
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(path)
        else:
            raise ValueError(f"unsupported material type: {path}")

    seen: set[Path] = set()
    unique: list[Path] = []
    for item in found:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(item)
    return [Material(path=item, kind=material_kind(item)) for item in unique]


def default_output_root() -> Path:
    return Path.home() / ".cram-engine" / "materials"


def mineru_command(mineru_bin: str, source: Path, output_dir: Path) -> tuple[str, ...]:
    # MinerU CLI names differ by version. The script defaults to the modern
    # executable name, while keeping the command isolated for easy adjustment.
    return (mineru_bin, "-p", str(source), "-o", str(output_dir))


def libreoffice_command(source: Path, output_dir: Path) -> tuple[str, ...]:
    return (
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(source),
    )


def make_plan(
    course: str,
    paths: Iterable[Path | str],
    *,
    output_root: Path | str | None = None,
    mineru_bin: str = "mineru",
) -> IngestPlan:
    slug = safe_course_slug(course)
    root = Path(output_root) if output_root else default_output_root()
    course_output = root.expanduser() / slug
    raw_output = course_output / "raw"
    materials = discover_materials(paths)
    jobs: list[IngestJob] = []

    for material in materials:
        source_output = raw_output / material.path.stem
        fallback_strategy: str | None = None
        fallback_command: tuple[str, ...] | None = None

        if material.kind == "presentation":
            fallback_strategy = "libreoffice_pdf_then_mineru"
            fallback_command = libreoffice_command(material.path, source_output / "fallback-pdf")
        elif material.kind == "image":
            fallback_strategy = "pix2text_then_pix2tex"

        jobs.append(
            IngestJob(
                source=material.path,
                output_dir=source_output,
                primary_engine="mineru",
                primary_command=mineru_command(mineru_bin, material.path, source_output),
                fallback_strategy=fallback_strategy,
                fallback_command=fallback_command,
            )
        )

    return IngestPlan(
        course=course,
        course_slug=slug,
        output_dir=course_output,
        summary_path=course_output / "materials-summary.md",
        jobs=tuple(jobs),
    )


def build_summary(plan: IngestPlan) -> str:
    lines = [
        f"# {plan.course} 资料摄取摘要",
        "",
        "## 处理策略",
        "",
        "- 主解析引擎：MinerU",
        "- PPT/PPTX：优先 MinerU 原生解析；失败后用 LibreOffice 转 PDF 再交给 MinerU",
        "- 图片：优先 MinerU；公式/复杂截图可用 Pix2Text 或 pix2tex 兜底",
        "- 输出目录：" + str(plan.output_dir),
        "",
        "## 资料清单",
        "",
    ]

    for index, job in enumerate(plan.jobs, start=1):
        fallback = job.fallback_strategy or "无"
        lines.extend(
            [
                f"### {index}. {job.source.name}",
                "",
                f"- 来源路径：`{job.source}`",
                f"- 主策略：MinerU",
                f"- 备用策略：{fallback}",
                f"- 输出目录：`{job.output_dir}`",
                "",
            ]
        )

    lines.extend(
        [
            "## 供阶段1使用的提示",
            "",
            "后续请读取本目录下 MinerU 生成的 Markdown/JSON，提取：",
            "",
            "- 章节结构、标题层级、反复出现的术语",
            "- 公式、模型图、流程图对应的概念关系",
            "- 适合名词解释、简答、论述、案例分析的潜在考点",
            "- 页码或文件来源，方便用户回看原资料",
            "",
        ]
    )
    return "\n".join(lines)


def write_summary(plan: IngestPlan) -> None:
    plan.output_dir.mkdir(parents=True, exist_ok=True)
    plan.summary_path.write_text(build_summary(plan), encoding="utf-8")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(command: tuple[str, ...], *, dry_run: bool) -> int:
    if dry_run:
        print("DRY RUN:", " ".join(command))
        return 0
    completed = subprocess.run(command, check=False)
    return completed.returncode


def run_plan(plan: IngestPlan, *, dry_run: bool) -> int:
    write_summary(plan)
    failures = 0

    for job in plan.jobs:
        job.output_dir.mkdir(parents=True, exist_ok=True)
        code = run_command(job.primary_command, dry_run=dry_run)
        if code == 0:
            continue

        if job.fallback_strategy == "libreoffice_pdf_then_mineru" and job.fallback_command:
            fallback_dir = Path(job.fallback_command[5])
            fallback_dir.mkdir(parents=True, exist_ok=True)
            convert_code = run_command(job.fallback_command, dry_run=dry_run)
            if convert_code != 0:
                failures += 1
                continue
            pdf_path = fallback_dir / f"{job.source.stem}.pdf"
            mineru_pdf = mineru_command(job.primary_command[0], pdf_path, job.output_dir)
            if run_command(mineru_pdf, dry_run=dry_run) != 0:
                failures += 1
        else:
            failures += 1

    return 1 if failures else 0


def check_environment(
    mineru_bin: str,
    *,
    exists=command_exists,
    python_version: tuple[int, int] | None = None,
    platform_name: str | None = None,
) -> str:
    version = python_version or sys.version_info[:2]
    platform = platform_name or sys.platform
    checks = [
        ("MinerU", mineru_bin),
        ("LibreOffice fallback", "soffice"),
        ("Pix2Text image fallback", "p2t"),
        ("pix2tex formula fallback", "pix2tex"),
    ]
    mineru_exists = exists(mineru_bin)
    lines = [
        "# Cram Engine 资料摄取环境检查",
        "",
        f"- Python: {version[0]}.{version[1]}",
    ]
    if (
        platform.startswith("win")
        and not mineru_exists
        and not ((3, 10) <= version <= (3, 12))
    ):
        lines.extend(
            [
                "  - 注意：Windows 建议使用 Python 3.10-3.12 安装 MinerU。",
                "  - 推荐命令：`py -3.12 -m pip install uv` 后运行 `py -3.12 -m uv pip install -U \"mineru[all]\"`。",
            ]
        )
    lines.append("")
    for label, command in checks:
        status = "OK" if (command == mineru_bin and mineru_exists) or exists(command) else "MISSING"
        lines.append(f"- {label}: {status} (`{command}`)")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Cram Engine course materials with MinerU.")
    parser.add_argument("--course", required=True, help="Course name.")
    parser.add_argument("--output-root", default=None, help="Defaults to ~/.cram-engine/materials.")
    parser.add_argument("--mineru-bin", default=os.environ.get("CRAM_MINERU_BIN", "mineru"))
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--check-env", action="store_true", help="Print parser environment status.")
    parser.add_argument("paths", nargs="*", help="Files or folders to ingest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check_env:
        print(check_environment(args.mineru_bin))
        return 0
    if not args.paths:
        raise SystemExit("at least one material path is required")

    plan = make_plan(
        args.course,
        args.paths,
        output_root=args.output_root,
        mineru_bin=args.mineru_bin,
    )
    return run_plan(plan, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
