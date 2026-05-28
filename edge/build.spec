# AgentHub Edge PyInstaller 打包配置（one-folder 模式）
# 模型文件不打入，放在 dist/AgentHubEdge/models/ 目录
# 用法: pyinstaller build.spec --clean

# -*- mode: python ; coding: utf-8 -*-
import os

HERE = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['entry.py'],
    pathex=[HERE],
    binaries=[],
    datas=[],
    hiddenimports=[
        'ultralytics',
        'cv2',
        'numpy',
        'requests',
        'psutil',
        'torch',
        'torchvision',
        'PIL',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'IPython',
        'pytest',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AgentHubEdge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AgentHubEdge',
)

# 打包完成后，复制 models 目录到 dist/AgentHubEdge/models/
import shutil
dist_dir = os.path.join(HERE, 'dist', 'AgentHubEdge')
models_src = os.path.join(HERE, 'models')
models_dst = os.path.join(dist_dir, 'models')
if os.path.exists(models_dst):
    shutil.rmtree(models_dst)
if os.path.exists(models_src):
    shutil.copytree(models_src, models_dst)
    print(f'[OK] models/ copied to dist/AgentHubEdge/models/')
