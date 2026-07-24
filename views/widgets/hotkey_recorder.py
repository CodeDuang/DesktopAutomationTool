"""快捷键录制器：支持手动输入和鼠标点击录制两种模式"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QKeyEvent, QWheelEvent

# 修饰键排序权重
_MODIFIER_ORDER = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}


class HotkeyRecorder(QWidget):
    """快捷键录制器

    支持两种输入方式：
    1. 手动在文本框输入快捷键（如 ctrl+c）
    2. 点击"录制"按钮，按下键盘组合键，点击鼠标结束录制
       录制期间支持捕获键盘按键和鼠标滚轮（上/下滑）
    """

    textChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording = False
        self._pressed_keys: set[str] = set()  # 当前按下的键
        self._recorded_combo: str = ""  # 当前录制的组合键字符串
        self._popup_label = None  # 录制提示悬浮标签

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("例如: ctrl+c, alt+tab, win+r")
        self.edit.setToolTip(
            "多个键用 + 连接。\n" "支持键盘按键和鼠标滚轮（wheel_up / wheel_down）\n" "点击「录制」按钮可通过实际按键自动录入"
        )
        layout.addWidget(self.edit)

        self.btn_record = QPushButton("🎙 录制")
        self.btn_record.setCheckable(True)
        self.btn_record.setToolTip("点击开始录制快捷键，再按一次或点击鼠标结束录制")
        self.btn_record.toggled.connect(self._on_toggle_record)
        layout.addWidget(self.btn_record)

        self.edit.textChanged.connect(lambda t: self.textChanged.emit(t))

    def text(self) -> str:
        return self.edit.text()

    def setText(self, text: str):
        self.edit.setText(text)

    def _on_toggle_record(self, checked: bool):
        if checked:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self._recording = True
        self._pressed_keys.clear()
        self._recorded_combo = ""

        self.btn_record.setText("⏹ 录制中... (点击鼠标结束)")
        self.btn_record.setStyleSheet("background: #f44336; color: white; font-weight: bold;")
        self.edit.setPlaceholderText("🎙 正在录制，请按下快捷键组合...")
        self.edit.setText("")
        self.edit.setStyleSheet("background: #fff3e0;")

        # 在顶层窗口安装事件过滤器
        window = self.window()
        if window:
            window.installEventFilter(self)

    def _stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        self._pressed_keys.clear()

        self.btn_record.setText("🎙 录制")
        self.btn_record.setStyleSheet("")
        self.edit.setPlaceholderText("例如: ctrl+c, alt+tab, win+r")
        self.edit.setStyleSheet("")

        # 移除事件过滤器
        window = self.window()
        if window:
            window.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if not self._recording:
            return super().eventFilter(obj, event)

        etype = event.type()

        # 键盘按下
        if etype == QEvent.KeyPress:
            key_name = self._qt_key_to_name(event)
            if key_name:
                self._pressed_keys.add(key_name)
                self._update_live_display()
            return True

        # 键盘释放 — 当非修饰键释放时，记录组合键
        if etype == QEvent.KeyRelease:
            key_name = self._qt_key_to_name(event)
            if key_name:
                is_modifier = key_name in ("ctrl", "alt", "shift", "win")
                if not is_modifier and self._pressed_keys:
                    # 将当前按下的所有键组成组合键
                    self._recorded_combo = self._build_combo()
                self._pressed_keys.discard(key_name)
                self._update_live_display()
            return True

        # 鼠标滚轮
        if etype == QEvent.Wheel:
            delta = event.angleDelta().y()
            wheel_key = "wheel_up" if delta > 0 else "wheel_down"
            self._pressed_keys.add(wheel_key)
            self._recorded_combo = self._build_combo()
            self._pressed_keys.discard(wheel_key)
            self._update_live_display()
            return True

        # 鼠标点击 → 结束录制
        if etype in (QEvent.MouseButtonPress,):
            self.btn_record.setChecked(False)
            return True

        return super().eventFilter(obj, event)

    def _build_combo(self) -> str:
        """将当前按下的键构建为快捷键字符串"""
        keys = list(self._pressed_keys)
        # 修饰键优先排序，wheel_ 放最后
        keys.sort(key=lambda k: (_MODIFIER_ORDER.get(k, 99) if not k.startswith("wheel_") else 100))
        return "+".join(keys)

    def _update_live_display(self):
        """更新实时显示"""
        if self._recorded_combo:
            self.edit.setText(self._recorded_combo)
        elif self._pressed_keys:
            self.edit.setText("+".join(sorted(self._pressed_keys, key=lambda k: _MODIFIER_ORDER.get(k, 99))))
        else:
            self.edit.setText("")

    # ---- Qt 键码 → 键名字符串 ----

    @staticmethod
    def _qt_key_to_name(event) -> str | None:
        """将 Qt 按键事件转换为 pyautogui 风格的键名"""
        key = event.key()

        # 修饰键
        if key == Qt.Key_Control:
            return "ctrl"
        if key == Qt.Key_Alt:
            return "alt"
        if key == Qt.Key_Shift:
            return "shift"
        if key == Qt.Key_Meta:
            return "win"

        # 功能键
        if key == Qt.Key_Escape:
            return "esc"
        if key in (Qt.Key_Return, Qt.Key_Enter):
            return "enter"
        if key == Qt.Key_Tab:
            return "tab"
        if key == Qt.Key_Space:
            return "space"
        if key == Qt.Key_Backspace:
            return "backspace"
        if key == Qt.Key_Delete:
            return "delete"
        if key == Qt.Key_Insert:
            return "insert"
        if key == Qt.Key_Home:
            return "home"
        if key == Qt.Key_End:
            return "end"
        if key == Qt.Key_PageUp:
            return "pageup"
        if key == Qt.Key_PageDown:
            return "pagedown"
        if key == Qt.Key_Print:
            return "printscreen"
        if key == Qt.Key_Pause:
            return "pause"

        # 方向键
        if key == Qt.Key_Up:
            return "up"
        if key == Qt.Key_Down:
            return "down"
        if key == Qt.Key_Left:
            return "left"
        if key == Qt.Key_Right:
            return "right"

        # F1–F12
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"f{key - Qt.Key_F1 + 1}"

        # 字母/数字/符号 → 取 event.text()
        text = event.text()
        if text and text.strip():
            # 跳过修饰键自己的 text
            return text.lower()

        return None
