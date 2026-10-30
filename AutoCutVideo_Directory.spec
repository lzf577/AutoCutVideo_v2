# -*- mode: python ; coding: utf-8 -*-
import os
import site
import glob
import faster_whisper
from PyInstaller.utils.hooks import copy_metadata

faster_whisper_path = os.path.dirname(faster_whisper.__file__)

datas = []
datas += copy_metadata('imageio')
datas += [(os.path.join(faster_whisper_path, 'assets', '*'), 'faster_whisper/assets')]

binaries = []
# Find CTranslate2 dlls if installed (CUDA environment provided by client)
for sp in site.getsitepackages():
    ct2_bin_pattern = os.path.join(sp, 'ctranslate2', '*.dll')
    for dll_path in glob.glob(ct2_bin_pattern):
        # 排除CUDA相关的dll，不带cuda环境
        lower_dll = dll_path.lower()
        if 'cublas' in lower_dll or 'cudnn' in lower_dll or 'cufft' in lower_dll or 'curand' in lower_dll or 'cusolver' in lower_dll or 'cusparse' in lower_dll or 'nvrtc' in lower_dll:
            continue
        binaries.append((dll_path, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['nvidia', 'torch', 'tensorrt', 'cupy', 'triton', 'matplotlib', 'pandas', 'scipy'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoCutVideo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoCutVideo',
)
