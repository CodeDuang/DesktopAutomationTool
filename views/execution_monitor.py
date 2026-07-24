"""执行监控窗口：实时日志、循环计数、进度显示"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QProgressBar,
    QGroupBox,
    QWidget,
    QPlainTextEdit,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from models.project import Project
from engine.executor import ExecutorThread


class ExecutionMonitor(QDialog):
    """执行监控对话框"""

    def __init__(self, project: Project, start_index: int = 0, single_step: bool = False, parent=None):
        super().__init__(parent)
        self.project = project
        self.start_index = start_index
        self.single_step = single_step
        self.executor: ExecutorThread | None = None
        self._total_steps = len([s for s in project.steps if s.enabled])

        self.setWindowTitle(f"执行中 - {project.name}" + (" (单步)" if single_step else ""))
        self.setMinimumSize(750, 550)
        self.resize(800, 600)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._build_ui()
        self._start_execution()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ---- 进度信息 ----
        info_layout = QHBoxLayout()
        self.lbl_status = QLabel("⏳ 准备执行...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.lbl_status)
        info_layout.addStretch()

        self.lbl_loop_count = QLabel("")
        self.lbl_loop_count.setStyleSheet("font-size: 14px; color: #E91E63; font-weight: bold;")
        info_layout.addWidget(self.lbl_loop_count)

        main_layout.addLayout(info_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self._total_steps if not self.single_step else 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m 步骤")
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)

        # 当前步骤
        self.lbl_current_step = QLabel("")
        self.lbl_current_step.setStyleSheet("color: #1976D2; font-size: 12px;")
        main_layout.addWidget(self.lbl_current_step)

        # ---- 日志输出 ----
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view.setMaximumBlockCount(5000)  # 防止内存占用过多
        log_layout.addWidget(self.log_view)

        main_layout.addWidget(log_group)

        # ---- 控制按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_stop = QPushButton("⏹ 紧急停止")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setStyleSheet("background: #f44336; color: white; font-weight: bold; padding: 10px 24px; font-size: 14px;")
        btn_layout.addWidget(self.btn_stop)

        self.btn_confirm_loop = QPushButton("▶ 继续下一轮循环")
        self.btn_confirm_loop.clicked.connect(self._confirm_loop)
        self.btn_confirm_loop.setEnabled(False)
        self.btn_confirm_loop.setVisible(False)
        self.btn_confirm_loop.setStyleSheet("background: #4CAF50; color: white; font-weight: bold; padding: 10px 24px; font-size: 14px;")
        btn_layout.addWidget(self.btn_confirm_loop)

        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self._close)
        self.btn_close.setEnabled(False)
        btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(btn_layout)

        # 提示文字
        hint = QLabel("💡 提示: 按 ESC 键可紧急停止  |  移动鼠标到左上角也可紧急停止（PyAutoGUI 安全机制）")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        main_layout.addWidget(hint)

    def _start_execution(self):
        """启动执行线程"""
        self.executor = ExecutorThread(self.project, self.start_index, self.single_step)
        self.executor.log_signal.connect(self._on_log)
        self.executor.progress_signal.connect(self._on_progress)
        self.executor.loop_count_signal.connect(self._on_loop_count)
        self.executor.finished_signal.connect(self._on_finished)
        self.executor.step_result_signal.connect(self._on_step_result)
        self.executor.stopped_signal.connect(self._on_stopped)
        self.executor.loop_confirm_signal.connect(self._on_loop_confirm_waiting)
        self.executor.start()

    def _on_log(self, entry: dict):
        """接收日志信号"""
        level = entry.get("level", "INFO")
        msg = entry.get("message", "")
        step_name = entry.get("step_name", "")

        # 构建显示文本
        prefix = ""
        if step_name:
            prefix = f"[{step_name}] "

        text = f"{prefix}{msg}"

        # 根据日志级别着色
        color_map = {
            "ERROR": QColor("#f44336"),
            "WARNING": QColor("#ff9800"),
            "INFO": QColor("#4caf50"),
            "DEBUG": QColor("#9e9e9e"),
        }
        color = color_map.get(level, QColor("#ffffff"))

        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + "\n", fmt)

        # 自动滚动到底部
        self.log_view.moveCursor(QTextCursor.End)
        self.log_view.ensureCursorVisible()

    def _on_progress(self, current_idx: int, total: int, step_name: str):
        """更新进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current_idx + 1)
        self.lbl_current_step.setText(f"📌 当前步骤: [{current_idx + 1}/{total}] {step_name}")
        self.lbl_status.setText("▶ 执行中...")

    def _on_loop_count(self, count: int):
        """更新循环计数"""
        self.lbl_loop_count.setText(f"🔄 第 {count} 轮")

    def _on_step_result(self, idx: int, success: bool, message: str):
        """步骤执行结果"""
        if not success:
            self.lbl_status.setText(f"⚠ 步骤 {idx + 1} 失败")

    def _on_finished(self, success: bool, message: str):
        """执行完成"""
        if success:
            self.lbl_status.setText("✅ 执行完成")
            self.lbl_current_step.setText("所有步骤已执行完毕")
        else:
            self.lbl_status.setText(f"❌ 执行终止: {message}")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.lbl_loop_count.setText("")
        self.btn_stop.setEnabled(False)
        self.btn_close.setEnabled(True)

    def _on_stopped(self):
        """用户手动停止"""
        self.lbl_status.setText("⏹ 已停止")
        self.lbl_current_step.setText("用户手动停止了执行")
        self.lbl_loop_count.setText("")
        self.btn_stop.setEnabled(False)
        self.btn_confirm_loop.setEnabled(False)
        self.btn_confirm_loop.setVisible(False)
        self.btn_close.setEnabled(True)

    def _on_loop_confirm_waiting(self, loop_num: int):
        """手动循环模式：等待用户确认"""
        self.lbl_status.setText(f"🔔 第 {loop_num} 轮完成 — 等待确认继续...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF9800;")
        self.btn_confirm_loop.setEnabled(True)
        self.btn_confirm_loop.setVisible(True)
        self.btn_confirm_loop.setText(f"▶ 继续第 {loop_num + 1} 轮循环")

    def _confirm_loop(self):
        """用户确认继续下一轮循环"""
        self.btn_confirm_loop.setEnabled(False)
        self.btn_confirm_loop.setText("⏳ 等待中...")
        self.lbl_status.setText("▶ 执行中...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        if self.executor:
            self.executor.confirm_next_loop()

    def _stop(self):
        """停止按钮"""
        if self.executor and self.executor.isRunning():
            self.lbl_status.setText("⏹ 正在停止...")
            self.btn_stop.setEnabled(False)
            self.executor.stop()

    def _close(self):
        """关闭窗口"""
        if self.executor and self.executor.isRunning():
            self.executor.stop()
            self.executor.wait(3000)
        self.accept()

    def closeEvent(self, event):
        """窗口关闭时确保停止执行"""
        if self.executor and self.executor.isRunning():
            self.executor.stop()
            self.executor.wait(3000)
        event.accept()

    def keyPressEvent(self, event):
        """ESC 键紧急停止"""
        if event.key() == Qt.Key_Escape:
            self._stop()
        super().keyPressEvent(event)
