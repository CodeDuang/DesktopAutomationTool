# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件（文件夹模式 onedir）

使用方法:
    pyinstaller build.spec --clean --log-level=WARN

输出在 dist/桌面自动化工具/ 目录下，可直接拷贝整个文件夹使用。
"""

import os
import time
from pathlib import Path

def log_time(msg):
    t = time.strftime("%H:%M:%S", time.localtime())
    print(f"\n==== [{t}] {msg} ====\n")

ROOT = Path(os.path.dirname(os.path.abspath(SPEC)))

log_time("开始执行 Analysis（依赖扫描阶段）,非常花费时间")
a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('docs', 'docs'),
        ('version_info.txt', '.'),
    ],
    hiddenimports=[
    # --- pyautogui 截图必需模块 ---
    'pyscreeze', 'pyautogui',
    # --- Pillow（pyscreeze 的核心依赖）---
    'PIL', 'PIL.Image', 'PIL.ImageGrab', 'PIL.ImageStat',
    'PIL.ImageColor', 'PIL.PngImagePlugin', 'PIL.BmpImagePlugin',
    'PIL.JpegImagePlugin', 'PIL.GifImagePlugin', 'PIL.TiffImagePlugin',
    # --- PySide6 核心模块 ---
    'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
excludes=[
        'matplotlib', 'scipy', 'numpy.tests', 'pandas', 'tkinter',
        'setuptools', 'pkg_resources',
        # --- 排除 cv2 内部模块（已确认无需显式 import）---
        'cv2.config', 'cv2.utils', 'cv2.typing', 'cv2.misc', 'cv2.gapi',
        'cv2.mat_wrapper', 'cv2.data', 'cv2.load_config_py3',
        # --- 排除 win32com / pythoncom 全量扫描 ---
        'win32com', 'pythoncom', 'pywintypes',
        # --- 排除 pyautogui 的子包（减少符号解析）---
        'pyautogui.__main__', 'pyautogui._pyautogui_x11',
        # --- 排除 keyboard 的内部平台代码 ---
        'keyboard._darwinkeyboard', 'keyboard._cocoakeyboard', 'keyboard._nixkeyboard',
        # --- 排除不需要的 PySide6 子模块 ---
      'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
        'PySide6.QtBluetooth', 'PySide6.QtNfc',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtGraphs', 'PySide6.QtGraphsWidgets',
        'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtUiTools',
        'PySide6.QtLocation', 'PySide6.QtPositioning', 'PySide6.QtSensors',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtSpatialAudio',
        'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtQuick3D',
        'PySide6.QtQuickWidgets', 'PySide6.QtQuickControls2',
        'PySide6.QtQuickTest',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
        'PySide6.QtSerialBus', 'PySide6.QtSerialPort',
        'PySide6.QtSql', 'PySide6.QtStateMachine',
        'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
        'PySide6.QtTest', 'PySide6.QtTextToSpeech',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets', 'PySide6.QtWebView',
        'PySide6.QtXml',
        'PySide6.QtDBus', 'PySide6.QtConcurrent',
        'PySide6.QtPrintSupport', 'PySide6.QtNetworkAuth',
        'PySide6.QtHttpServer',
        'PySide6.QtAxContainer',
        'PySide6.QtLabsAnimation', 'PySide6.QtLabsFolderListModel',
        'PySide6.QtLabsPlatform', 'PySide6.QtLabsQmlModels',
        'PySide6.QtLabsSettings', 'PySide6.QtLabsSharedImage',
        'PySide6.QtLabsWavefrontMesh',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

log_time("Analysis 完成，开始构建 PYZ")
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

log_time("PYZ 构建完成，开始构建 EXE")
exe = EXE(
    pyz,
    a.scripts,
    [],                     # 不需要 icons 等额外资源
    exclude_binaries=True,  # 关键：DLL 等不打包进 exe，由 COLLECT 收集
    name='桌面自动化工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # 禁用 UPX 避免杀软误报
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

log_time("EXE 完成，开始 COLLECT（复制dll/资源）")
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='桌面自动化工具',   # 输出文件夹名
)

log_time("✅ 全部打包流程结束")