from __future__ import annotations

import sys
from pathlib import Path

from cram_app.commands import CommandRouter
from cram_app.tui import run_tui
from cram_app.workspace import CramWorkspace


def main() -> int:
    workspace = CramWorkspace.open(Path.cwd())
    if "--status" in sys.argv:
        print(CommandRouter(workspace).handle("/status").message)
        return 0

    run_tui(workspace.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
