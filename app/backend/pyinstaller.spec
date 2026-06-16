# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path.cwd()
DIST = ROOT.parent / "tauri" / "src-tauri" / "binaries"


a = Analysis(
    ["sidecar_main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=["uvicorn.logging", "uvicorn.loops", "uvicorn.protocols.http"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cram-backend-x86_64-pc-windows-msvc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    distpath=str(DIST),
)
