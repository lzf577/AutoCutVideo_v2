# -*- mode: python ; coding: utf-8 -*-
import os
import faster_whisper
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

faster_whisper_path = os.path.dirname(faster_whisper.__file__)

datas = []
datas += collect_data_files('faster_whisper')
datas += copy_metadata('imageio')
datas += [('logo.ico', '.')]
datas += [('readme.md', '.')]
datas += [(os.path.join(faster_whisper_path, 'assets', '*'), 'faster_whisper/assets')]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PIL._tkinter_finder', 'PIL._imaging', 'PIL._imagingtk', 'PIL._imagingmath', 'PIL._imagingmorph'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='AutoCutVideo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
