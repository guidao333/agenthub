# AgentHub Client PyInstaller build spec.
#
# Build:
#   pyinstaller build.spec --clean --noconfirm

from pathlib import Path


ROOT = Path.cwd()


a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ("README.md", "."),
    ],
    hiddenimports=[
        "plugins.isp_broadband",
        "plugins.vision",
        "websockets",
        "httpx",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "numpy",
        "pandas",
        "matplotlib",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AgentHubClient",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
