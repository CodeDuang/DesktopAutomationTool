"""桌面自动化工具 - 入口文件

使用方法:
    python main.py              # 启动 GUI
    python main.py --help       # 查看帮助
"""

from __future__ import annotations

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from views.main_window import MainWindow, SettingsDialog
from views.widgets.coordinate_picker import CoordinatePicker
from views.widgets.screenshot_tool import ScreenshotTool
from utils.config import AppConfig


def check_dependencies() -> list[str]:
    """检查必要依赖，返回缺失的依赖列表"""
    missing = []
    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui")

    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")

    try:
        import PIL
        PIL._avif = None
    except ImportError:
        missing.append("Pillow")

    try:
        import pyperclip
    except ImportError:
        missing.append("pyperclip")

    try:
        import keyboard
    except ImportError:
        missing.append("keyboard")

    # pytesseract 是可选的
    try:
        import pytesseract
    except ImportError:
        pass  # OCR 功能不可用，但不阻止启动

    # pywin32
    try:
        import win32gui
    except ImportError:
        pass  # Windows 窗口管理功能不可用，但不阻止启动

    return missing


def main():
    """应用入口"""
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print("警告: 以下依赖未安装，部分功能可能不可用:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("请运行: pip install -r requirements.txt")
        print()

    # 创建 Qt 应用
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)

    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 加载样式
    style_path = os.path.join(os.path.dirname(__file__), "resources", "styles", "default.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # 创建主窗口
    main_window = MainWindow()

    # 创建全局工具窗口（初始隐藏，设定父对象确保关闭主窗口时自动清理）
    coord_picker = CoordinatePicker(main_window)
    coord_picker.move(100, 100)

    screenshot_tool = ScreenshotTool(main_window)
    screenshot_tool.move(450, 100)

    # 将工具窗口关联到主窗口
    main_window.coord_picker = coord_picker
    main_window.screenshot_tool = screenshot_tool

    # 在主窗口添加工具菜单
    from PySide6.QtWidgets import QMenuBar, QMenu
    from PySide6.QtGui import QAction

    menubar = main_window.menuBar()

    # 工具菜单
    tools_menu = menubar.addMenu("🔧 工具")
    action_coord = QAction("📍 坐标拾取器", main_window)
    action_coord.triggered.connect(lambda: coord_picker.show())
    tools_menu.addAction(action_coord)

    action_screenshot = QAction("📷 截图工具", main_window)
    action_screenshot.triggered.connect(lambda: screenshot_tool.show())
    tools_menu.addAction(action_screenshot)

    tools_menu.addSeparator()

    action_settings = QAction("⚙ 设置", main_window)
    action_settings.triggered.connect(lambda: SettingsDialog(main_window).exec())
    tools_menu.addAction(action_settings)

    # 帮助菜单
    help_menu = menubar.addMenu("❓ 帮助")
    action_about = QAction("关于", main_window)
    action_about.triggered.connect(
        lambda: QMessageBox.about(
            main_window,
            f"关于 {AppConfig.APP_NAME}",
            f"<h3>{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}</h3>"
            f"<p>桌面 GUI 自动化测试工具</p>"
            f"<p>用于机械性测试工作：识别按钮点击、Excel 列名定位输入等。</p>"
            f"<hr>"
            f"<p><b>功能特性:</b></p>"
            f"<ul>"
            f"<li>键盘快捷键模拟</li>"
            f"<li>图像匹配定位点击</li>"
            f"<li>OCR 文字识别点击</li>"
            f"<li>循环执行 + 条件判断</li>"
            f"<li>失败截图 + 日志追踪</li>"
            f"<li>项目导入/导出</li>"
            f"</ul>"
            f"<p>基于 Python 3.10 + PySide6 + PyAutoGUI</p>",
        )
    )
    help_menu.addAction(action_about)

    action_guide = QAction("📖 用户手册", main_window)
    action_guide.triggered.connect(lambda: _open_guide())
    help_menu.addAction(action_guide)

    # 显示主窗口
    main_window.show()

    sys.exit(app.exec())


def _open_guide():
    """打开用户手册"""
    import subprocess

    guide_path = os.path.join(os.path.dirname(__file__), "docs", "USER_GUIDE.md")
    if os.path.exists(guide_path):
        os.startfile(guide_path)
    else:
        QMessageBox.information(None, "提示", "用户手册文件不存在，请查看 docs/USER_GUIDE.md")


if __name__ == "__main__":
    main()
