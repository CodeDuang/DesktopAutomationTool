"""鼠标坐标拾取器：半透明浮窗显示实时鼠标坐标"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QShortcut, QKeySequence
import pyautogui


class CoordinatePicker(QWidget):
    """鼠标坐标拾取器浮窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracking = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_coordinates)
        self._timer.setInterval(100)  # 100ms 更新频率

        self.setWindowTitle("坐标拾取器")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(320, 130)

        self._build_ui()
        self._setup_shortcuts()

    def _build_ui(self):
        self.setStyleSheet("""
            CoordinatePicker {
                background: rgba(30, 30, 30, 220);
                border: 2px solid #4CAF50;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-family: Consolas, monospace;
            }
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #66BB6A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # 标题栏
        title_layout = QHBoxLayout()
        title = QLabel("📍 鼠标坐标拾取器")
        title.setStyleSheet("font-size: 11px; color: #aaa;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.btn_toggle = QPushButton("▶ 开始")
        self.btn_toggle.clicked.connect(self._toggle_tracking)
        title_layout.addWidget(self.btn_toggle)
        layout.addLayout(title_layout)

        # 坐标显示
        self.lbl_coords = QLabel("X: ----  Y: ----")
        self.lbl_coords.setFont(QFont("Consolas", 13))
        self.lbl_coords.setAlignment(Qt.AlignCenter)
        self.lbl_coords.setStyleSheet("color: #4FC3F7; font-weight: bold;")
        layout.addWidget(self.lbl_coords)

        # 颜色显示
        self.lbl_color = QLabel("RGB: ---, ---, ---")
        self.lbl_color.setFont(QFont("Consolas", 10))
        self.lbl_color.setAlignment(Qt.AlignCenter)
        self.lbl_color.setStyleSheet("color: #aaa;")
        layout.addWidget(self.lbl_color)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("📋 复制坐标 (Ctrl+C)")
        self.btn_copy.clicked.connect(self._copy_coords)
        btn_layout.addWidget(self.btn_copy)

        self.btn_close = QPushButton("✕ (Esc)")
        self.btn_close.setFixedWidth(60)
        self.btn_close.clicked.connect(self.hide)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # 快捷键提示（需要鼠标焦点在窗口上）
        hint = QLabel("💡 快捷键(Ctrl+C/Esc)需鼠标焦点在此窗口上")
        hint.setFont(QFont("Microsoft YaHei", 8))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #888; padding-top: 2px;")
        layout.addWidget(hint)

    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._on_escape)
        QShortcut(QKeySequence(Qt.CTRL | Qt.Key_C), self, self._copy_coords)

    def _on_escape(self):
        """ESC 键：停止追踪并隐藏窗口"""
        self.stop_tracking()
        self.hide()

    def hideEvent(self, event):
        """窗口隐藏时自动停止 Timer，避免后台持续运行"""
        self.stop_tracking()
        super().hideEvent(event)

    def stop_tracking(self):
        """外部调用：停止追踪并隐藏"""
        if self._tracking:
            self._timer.stop()
            self._tracking = False
            self.btn_toggle.setText("▶ 开始")
            self.btn_toggle.setStyleSheet("background: #4CAF50; color: white; border: none; border-radius: 3px; padding: 4px 12px;")

    def _toggle_tracking(self):
        """开始/停止追踪"""
        if self._tracking:
            self._timer.stop()
            self._tracking = False
            self.btn_toggle.setText("▶ 开始")
            self.btn_toggle.setStyleSheet("background: #4CAF50; color: white; border: none; border-radius: 3px; padding: 4px 12px;")
        else:
            self._timer.start()
            self._tracking = True
            self.btn_toggle.setText("⏸ 停止")
            self.btn_toggle.setStyleSheet("background: #ff9800; color: white; border: none; border-radius: 3px; padding: 4px 12px;")
            self._update_coordinates()

    def _update_coordinates(self):
        """更新坐标显示"""
        try:
            x, y = pyautogui.position()
            self.lbl_coords.setText(f"X: {x:5d}    Y: {y:5d}")
            # 获取像素颜色
            try:
                r, g, b = pyautogui.pixel(x, y)
                self.lbl_color.setText(f"RGB: {r}, {g}, {b}")
            except Exception:
                self.lbl_color.setText("RGB: ---, ---, ---")
        except Exception:
            pass

    def _copy_coords(self):
        """复制坐标到剪贴板"""
        try:
            x, y = pyautogui.position()
            text = f"({x}, {y})"
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)
            self.lbl_coords.setStyleSheet("color: #4CAF50; font-weight: bold;")
            QTimer.singleShot(800, lambda: self.lbl_coords.setStyleSheet("color: #4FC3F7; font-weight: bold;"))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if not self._tracking:
            self._toggle_tracking()
