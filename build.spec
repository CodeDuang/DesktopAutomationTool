# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件

使用方法:
    pyinstaller build.spec

输出在 dist/ 目录下。
"""

import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('docs', 'docs'),
    ],
    hiddenimports=[
        # 跨模块/C扩展依赖（PyInstaller 无法自动推导）
        'pyautogui',
        'cv2',
        'PIL',
        'pyperclip',
        'keyboard',
        'pytesseract',
        'win32gui',
        'win32api',
        'win32con',
        # 新增模块（确保不被 tree-shaking 移除）
        'views.widgets.hotkey_recorder',
        # Qt 底层模块
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.tests',
        'pandas',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='桌面自动化工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可设置为图标文件路径
)
