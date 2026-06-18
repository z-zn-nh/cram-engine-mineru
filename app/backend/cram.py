from __future__ import annotations

from pathlib import Path

from cram_app.tui import run_tui


def main() -> int:
    run_tui(Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
