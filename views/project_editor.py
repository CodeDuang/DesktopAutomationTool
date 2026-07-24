"""项目编辑器：步骤列表管理"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QLabel,
    QSplitter,
    QWidget,
    QMenu,
    QTextEdit,
    QLineEdit,
    QSpinBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction

from models.project import Project, ProjectSettings
from models.step import Step, StepType, FailureConfig
from utils import storage
from views.step_dialog import StepDialog
from views.execution_monitor import ExecutionMonitor


class ProjectEditorWindow(QDialog):
    """项目编辑对话框"""

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self._modified = False
        self._executor = None  # 执行引擎引用

        self.setWindowTitle(f"编辑项目 - {project.name}")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 750)

        self._build_ui()
        self._refresh_step_table()

    def _build_ui(self):
        """构建UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---- 项目基本信息 ----
        info_group = QGroupBox("项目信息")
        info_layout = QFormLayout(info_group)

        self.edit_name = QLineEdit(self.project.name)
        self.edit_name.textChanged.connect(self._mark_modified)
        info_layout.addRow("项目名称:", self.edit_name)

        self.edit_desc = QTextEdit()
        self.edit_desc.setMaximumHeight(60)
        self.edit_desc.setPlainText(self.project.description)
        self.edit_desc.textChanged.connect(self._mark_modified)
        info_layout.addRow("项目描述:", self.edit_desc)

        main_layout.addWidget(info_group)

        # ---- 步骤列表 + 工具栏 ----
        step_header = QHBoxLayout()
        step_label = QLabel("📋 步骤列表")
        step_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        step_header.addWidget(step_label)
        step_header.addStretch()

        self.btn_add = QPushButton("➕ 添加步骤")
        self.btn_add.clicked.connect(self._add_step)
        step_header.addWidget(self.btn_add)
        main_layout.addLayout(step_header)

        self.step_table = QTableWidget()
        self.step_table.setColumnCount(4)
        self.step_table.setHorizontalHeaderLabels(["启用", "步骤名称", "类型", "等待时间"])
        self.step_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.step_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.step_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.step_table.setColumnWidth(0, 50)
        self.step_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.step_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.step_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.step_table.setAlternatingRowColors(True)
        self.step_table.verticalHeader().setVisible(False)
        self.step_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.step_table.customContextMenuRequested.connect(self._show_step_menu)
        self.step_table.doubleClicked.connect(self._edit_selected_step)
        main_layout.addWidget(self.step_table)

        # 步骤操作按钮
        step_btn_layout = QHBoxLayout()
        step_btn_layout.setSpacing(6)

        self.btn_edit = QPushButton("✏ 编辑")
        self.btn_edit.clicked.connect(self._edit_selected_step)
        step_btn_layout.addWidget(self.btn_edit)

        self.btn_delete_step = QPushButton("🗑 删除")
        self.btn_delete_step.clicked.connect(self._delete_step)
        step_btn_layout.addWidget(self.btn_delete_step)

        self.btn_dup = QPushButton("📋 复制")
        self.btn_dup.clicked.connect(self._duplicate_step)
        step_btn_layout.addWidget(self.btn_dup)

        self.btn_up = QPushButton("⬆ 上移")
        self.btn_up.clicked.connect(lambda: self._move_step(-1))
        step_btn_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("⬇ 下移")
        self.btn_down.clicked.connect(lambda: self._move_step(1))
        step_btn_layout.addWidget(self.btn_down)

        step_btn_layout.addStretch()

        self.btn_enable_all = QPushButton("☑ 全部启用")
        self.btn_enable_all.clicked.connect(lambda: self._set_all_enabled(True))
        step_btn_layout.addWidget(self.btn_enable_all)

        self.btn_disable_all = QPushButton("⛔ 禁用/启用")
        self.btn_disable_all.clicked.connect(self._toggle_selected_step)
        self.btn_disable_all.setToolTip("切换当前选中步骤的启用/禁用状态")
        step_btn_layout.addWidget(self.btn_disable_all)

        main_layout.addLayout(step_btn_layout)

        # ---- 项目设置 ----
        settings_group = QGroupBox("项目设置")
        settings_layout = QFormLayout(settings_group)

        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 10.0)
        self.spin_speed.setSingleStep(0.1)
        self.spin_speed.setValue(self.project.settings.global_speed_multiplier)
        self.spin_speed.setToolTip("1.0 = 正常速度，0.5 = 半速（更慢），2.0 = 双倍速")
        self.spin_speed.valueChanged.connect(self._mark_modified)
        settings_layout.addRow("执行速度倍率:", self.spin_speed)

        self.spin_loop_count = QSpinBox()
        self.spin_loop_count.setRange(1, 999999)
        self.spin_loop_count.setValue(self.project.settings.loop_count)
        self.spin_loop_count.setToolTip("项目整体循环次数。设置为1表示步骤1→N执行一次；设置为10表示步骤1→N重复执行10轮")
        self.spin_loop_count.valueChanged.connect(self._mark_modified)
        settings_layout.addRow("项目循环次数:", self.spin_loop_count)

        self.chk_stop_on_fail = QCheckBox("失败时停止执行")
        self.chk_stop_on_fail.setChecked(self.project.settings.stop_on_failure)
        self.chk_stop_on_fail.toggled.connect(self._mark_modified)
        settings_layout.addRow("", self.chk_stop_on_fail)

        self.chk_screenshot = QCheckBox("失败时自动截图")
        self.chk_screenshot.setChecked(self.project.settings.screenshot_on_failure)
        self.chk_screenshot.toggled.connect(self._mark_modified)
        settings_layout.addRow("", self.chk_screenshot)

        self.chk_manual_loop = QCheckBox("手动确认循环（每轮项目循环完成后等待用户点击继续）")
        self.chk_manual_loop.setChecked(self.project.settings.manual_loop_confirm)
        self.chk_manual_loop.setToolTip("勾选后，每轮循环结束不会自动开始下一轮，需在监控窗口点击确认按钮")
        self.chk_manual_loop.toggled.connect(self._mark_modified)
        settings_layout.addRow("", self.chk_manual_loop)

        self.combo_stop_key = QComboBox()
        self.combo_stop_key.addItems(["esc", "f1", "f2", "f3", "f4", "f5", "f6", "f8", "f10", "f12"])
        self.combo_stop_key.setCurrentText(self.project.settings.emergency_stop_key)
        self.combo_stop_key.currentTextChanged.connect(self._mark_modified)
        settings_layout.addRow("紧急停止键:", self.combo_stop_key)

        main_layout.addWidget(settings_group)

        # ---- 底部按钮 ----
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self.btn_save = QPushButton("💾 保存")
        self.btn_save.clicked.connect(self._save_and_close)
        self.btn_save.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        bottom_layout.addWidget(self.btn_save)

        self.btn_save_continue = QPushButton("💾 保存并继续编辑")
        self.btn_save_continue.clicked.connect(self._save)
        bottom_layout.addWidget(self.btn_save_continue)

        bottom_layout.addStretch()

        self.btn_run = QPushButton("▶ 运行")
        self.btn_run.clicked.connect(self._run_project)
        self.btn_run.setStyleSheet("background: #2196F3; color: white; font-weight: bold;")
        bottom_layout.addWidget(self.btn_run)

        self.btn_run_step = QPushButton("▶| 从当前步骤运行")
        self.btn_run_step.clicked.connect(lambda: self._run_project(from_current=True))
        bottom_layout.addWidget(self.btn_run_step)

        self.btn_single_step = QPushButton("⏭ 单步执行")
        self.btn_single_step.clicked.connect(self._run_single_step)
        bottom_layout.addWidget(self.btn_single_step)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(bottom_layout)

    # ---- 步骤表格操作 ----

    def _refresh_step_table(self):
        """刷新步骤表格"""
        steps = self.project.steps
        self.step_table.setRowCount(len(steps))
        for row, step in enumerate(steps):
            # 启用列
            enabled_item = QTableWidgetItem("✅" if step.enabled else "⛔")
            enabled_item.setTextAlignment(Qt.AlignCenter)
            enabled_item.setData(Qt.UserRole, step.id)
            self.step_table.setItem(row, 0, enabled_item)

            # 名称
            self.step_table.setItem(row, 1, QTableWidgetItem(step.name))

            # 类型
            type_name = StepType.display_name(step.type)
            self.step_table.setItem(row, 2, QTableWidgetItem(type_name))

            # 等待时间
            wait_text = f"前{step.wait_before_ms}ms / 后{step.wait_after_ms}ms"
            self.step_table.setItem(row, 3, QTableWidgetItem(wait_text))

    def _get_selected_step_id(self) -> str | None:
        """获取当前选中步骤的 ID"""
        row = self.step_table.currentRow()
        if row < 0:
            return None
        item = self.step_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _get_selected_step_index(self) -> int:
        return self.step_table.currentRow()

    def _add_step(self):
        """添加新步骤"""
        step = Step(name="新步骤", type=StepType.WAIT)
        step.ensure_params()
        dlg = StepDialog(step, is_new=True, parent=self)
        def _on_add_accepted():
            self.project.add_step(dlg.step)
            self._mark_modified()
            self._refresh_step_table()
        dlg.accepted.connect(_on_add_accepted)
        dlg.setModal(False)
        dlg.show()

    def _edit_selected_step(self):
        """编辑选中步骤"""
        step_id = self._get_selected_step_id()
        if not step_id:
            return
        step = self.project.get_step(step_id)
        if step is None:
            return
        dlg = StepDialog(step, is_new=False, parent=self)
        def _on_edit_accepted():
            self._mark_modified()
            self._refresh_step_table()
        dlg.accepted.connect(_on_edit_accepted)
        dlg.setModal(False)
        dlg.show()

    def _delete_step(self):
        """删除选中步骤"""
        step_id = self._get_selected_step_id()
        if not step_id:
            return
        row = self.step_table.currentRow()
        name = self.step_table.item(row, 1).text()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f'确定要删除步骤 "{name}" 吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.project.remove_step(step_id)
            self._mark_modified()
            self._refresh_step_table()

    def _duplicate_step(self):
        """复制选中步骤"""
        step_id = self._get_selected_step_id()
        if not step_id:
            return
        new_step = self.project.duplicate_step(step_id)
        if new_step:
            self._mark_modified()
            self._refresh_step_table()

    def _move_step(self, direction: int):
        """移动步骤"""
        step_id = self._get_selected_step_id()
        if not step_id:
            return
        self.project.move_step(step_id, direction)
        self._mark_modified()
        self._refresh_step_table()
        # 保持选中
        new_idx = next((i for i, s in enumerate(self.project.steps) if s.id == step_id), -1)
        if new_idx >= 0:
            self.step_table.selectRow(new_idx)

    def _set_all_enabled(self, enabled: bool):
        """设置所有步骤的启用状态"""
        for step in self.project.steps:
            step.enabled = enabled
        self._mark_modified()
        self._refresh_step_table()

    def _toggle_selected_step(self):
        """切换当前选中步骤的启用/禁用状态"""
        step_id = self._get_selected_step_id()
        if not step_id:
            QMessageBox.information(self, "提示", "请先选择一个步骤")
            return
        step = self.project.get_step(step_id)
        if step is None:
            return
        step.enabled = not step.enabled
        self._mark_modified()
        self._refresh_step_table()

    def _show_step_menu(self, pos):
        """右键菜单"""
        step_id = self._get_selected_step_id()
        if not step_id:
            return
        menu = QMenu(self)
        menu.addAction("✏ 编辑", self._edit_selected_step)
        menu.addAction("📋 复制", self._duplicate_step)
        menu.addSeparator()
        menu.addAction("⬆ 上移", lambda: self._move_step(-1))
        menu.addAction("⬇ 下移", lambda: self._move_step(1))
        menu.addSeparator()
        menu.addAction("🗑 删除", self._delete_step)
        menu.exec(self.step_table.viewport().mapToGlobal(pos))

    # ---- 保存操作 ----

    def _mark_modified(self):
        self._modified = True

    def _collect_settings(self) -> ProjectSettings:
        """从 UI 收集当前设置"""
        return ProjectSettings(
            global_speed_multiplier=self.spin_speed.value(),
            stop_on_failure=self.chk_stop_on_fail.isChecked(),
            screenshot_on_failure=self.chk_screenshot.isChecked(),
            emergency_stop_key=self.combo_stop_key.currentText(),
            loop_count=self.spin_loop_count.value(),
            manual_loop_confirm=self.chk_manual_loop.isChecked(),
        )

    def _save(self):
        """保存项目"""
        self.project.name = self.edit_name.text().strip()
        self.project.description = self.edit_desc.toPlainText().strip()
        self.project.settings = self._collect_settings()
        self.project.touch()
        if storage.save_project(self.project):
            self._modified = False
            self.setWindowTitle(f"编辑项目 - {self.project.name}")
            return True
        else:
            QMessageBox.warning(self, "错误", "保存项目失败")
            return False

    def _save_and_close(self):
        """保存并关闭"""
        if self._save():
            self.accept()

    def closeEvent(self, event):
        """关闭窗口时提示保存"""
        if self._modified:
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "项目有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Save:
                if not self._save():
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        # 如果正在执行，停止
        if self._executor and self._executor.isRunning():
            self._executor.stop()
            self._executor.wait(3000)
        event.accept()

    # ---- 运行控制 ----

    def _run_project(self, from_current=False):
        """运行项目"""
        if not self.project.steps:
            QMessageBox.information(self, "提示", "项目没有步骤，请先添加步骤")
            return
        # 保存
        self._save()
        # 重新加载最新版本
        self.project = storage.load_project(self.project.id)
        if self.project is None:
            return

        start_index = self._get_selected_step_index() if from_current else 0
        if start_index < 0:
            start_index = 0

        monitor = ExecutionMonitor(self.project, start_index, parent=self)
        monitor.exec()

    def _run_single_step(self):
        """单步执行"""
        step_id = self._get_selected_step_id()
        if not step_id:
            QMessageBox.information(self, "提示", "请先选择一个步骤")
            return
        self._save()
        self.project = storage.load_project(self.project.id)
        if self.project is None:
            return

        idx = self._get_selected_step_index()
        monitor = ExecutionMonitor(self.project, idx, single_step=True, parent=self)
        monitor.exec()
