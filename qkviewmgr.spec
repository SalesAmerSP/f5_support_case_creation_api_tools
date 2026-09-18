# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for qkviewmgr standalone single-file binary."""

import os
import certifi

block_cipher = None

a = Analysis(
    ['src/qkviewmgr/qkviewmgr.py'],
    pathex=['src', 'src/qkviewmgr'],
    binaries=[],
    datas=[
        (certifi.where(), 'certifi'),
    ],
    hiddenimports=[
        'qkviewmgr',
        'qkviewmgr.f5functions',
        'qkviewmgr.wizard',
        'qkviewmgr.gui',
        'f5functions',
        'wizard',
        'gui',
        'certifi',
        'urllib3',
        'requests',
        'tqdm',
        'configparser',
        'getpass',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='qkviewmgr',
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
)
