"""主页面：项目列表管理"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QMenu,
    QLabel,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
    QStyle,
    QApplication,
    QGroupBox,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QIcon

from models.project import Project
from utils import storage
from utils.config import AppConfig
from views.project_editor import ProjectEditorWindow


class ProjectNameDialog(QDialog):
    """新建/重命名 项目对话框"""

    def __init__(self, parent=None, title="新建项目", name="", description=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("请输入项目名称")
        layout.addRow("项目名称:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入项目描述（可选）")
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlainText(description)
        layout.addRow("项目描述:", self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.desc_edit.toPlainText().strip()


class SettingsDialog(QDialog):
    """应用设置对话框：配置日志和截图保存目录"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("应用设置")
        self.setMinimumWidth(550)
        self.setModal(True)
        self._build_ui()
        self._load_current_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- 日志目录 ---
        logs_group = QGroupBox("执行日志保存目录")
        logs_layout = QVBoxLayout(logs_group)
        logs_row = QHBoxLayout()
        self.edit_logs_dir = QLineEdit()
        self.edit_logs_dir.setPlaceholderText("留空使用默认目录 (data/logs/)")
        self.edit_logs_dir.setReadOnly(True)
        logs_row.addWidget(self.edit_logs_dir)
        btn_logs = QPushButton("浏览...")
        btn_logs.clicked.connect(lambda: self._browse_dir(self.edit_logs_dir))
        logs_row.addWidget(btn_logs)
        btn_logs_reset = QPushButton("恢复默认")
        btn_logs_reset.clicked.connect(lambda: self.edit_logs_dir.setText(""))
        logs_row.addWidget(btn_logs_reset)
        logs_layout.addLayout(logs_row)
        layout.addWidget(logs_group)

        # --- 截图目录 ---
        ss_group = QGroupBox("失败截图保存目录")
        ss_layout = QVBoxLayout(ss_group)
        ss_row = QHBoxLayout()
        self.edit_ss_dir = QLineEdit()
        self.edit_ss_dir.setPlaceholderText("留空使用默认目录 (data/screenshots/)")
        self.edit_ss_dir.setReadOnly(True)
        ss_row.addWidget(self.edit_ss_dir)
        btn_ss = QPushButton("浏览...")
        btn_ss.clicked.connect(lambda: self._browse_dir(self.edit_ss_dir))
        ss_row.addWidget(btn_ss)
        btn_ss_reset = QPushButton("恢复默认")
        btn_ss_reset.clicked.connect(lambda: self.edit_ss_dir.setText(""))
        ss_row.addWidget(btn_ss_reset)
        ss_layout.addLayout(ss_row)
        layout.addWidget(ss_group)

        layout.addStretch()

        # --- 按钮 ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_dir(self, target_edit: QLineEdit):
        dirpath = QFileDialog.getExistingDirectory(self, "选择目录", target_edit.text() or "")
        if dirpath:
            target_edit.setText(dirpath)

    def _load_current_settings(self):
        settings = AppConfig.load_settings()
        self.edit_logs_dir.setText(settings.get("logs_dir", ""))
        self.edit_ss_dir.setText(settings.get("screenshots_dir", ""))

    def _save_and_close(self):
        logs_dir = self.edit_logs_dir.text().strip()
        ss_dir = self.edit_ss_dir.text().strip()

        # 验证：如果目录不为空，检查目录是否存在
        if logs_dir and not os.path.isdir(logs_dir):
            QMessageBox.warning(self, "验证失败", f"日志目录不存在或无法访问:\n{logs_dir}")
            return
        if ss_dir and not os.path.isdir(ss_dir):
            QMessageBox.warning(self, "验证失败", f"截图目录不存在或无法访问:\n{ss_dir}")
            return

        # 合并保存（保留已有设置，只更新变更的字段）
        current = AppConfig.load_settings()
        current["logs_dir"] = logs_dir
        current["screenshots_dir"] = ss_dir
        AppConfig.save_settings(current)

        QMessageBox.information(self, "成功", "设置已保存。")
        self.accept()


class MainWindow(QMainWindow):
    """主窗口：项目列表"""

    project_list_updated = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setMinimumSize(800, 550)
        self.resize(900, 600)

        # 应用样式
        self._setup_style()

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ---- 标题栏 ----
        title_layout = QHBoxLayout()
        title_label = QLabel(AppConfig.APP_NAME)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        version_label = QLabel(f"v{AppConfig.APP_VERSION}")
        version_label.setStyleSheet("color: gray;")
        title_layout.addWidget(version_label)
        main_layout.addLayout(title_layout)

        # ---- 搜索和过滤栏 ----
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索项目...")
        self.search_edit.textChanged.connect(self._refresh_table)
        search_layout.addWidget(self.search_edit)
        main_layout.addLayout(search_layout)

        # ---- 项目表格 ----
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["项目名称", "步骤数", "更新时间", "描述"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_selected_project)
        main_layout.addWidget(self.table)

        # ---- 工具栏按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_new = QPushButton("➕ 新建项目")
        self.btn_new.clicked.connect(self._new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("✏ 编辑项目")
        self.btn_edit.clicked.connect(self._edit_selected_project)
        btn_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑 删除项目")
        self.btn_delete.clicked.connect(self._delete_project)
        btn_layout.addWidget(self.btn_delete)

        self.btn_duplicate = QPushButton("📋 复制项目")
        self.btn_duplicate.clicked.connect(self._duplicate_project)
        btn_layout.addWidget(self.btn_duplicate)

        self.btn_clear_cache = QPushButton("🧹 清除缓存")
        self.btn_clear_cache.clicked.connect(self._clear_cache)
        btn_layout.addWidget(self.btn_clear_cache)

        btn_layout.addStretch()

        self.btn_import = QPushButton("📥 导入")
        self.btn_import.clicked.connect(self._import_project)
        btn_layout.addWidget(self.btn_import)

        self.btn_export = QPushButton("📤 导出")
        self.btn_export.clicked.connect(self._export_project)
        btn_layout.addWidget(self.btn_export)

        main_layout.addLayout(btn_layout)

        # 状态栏
        self.statusBar().showMessage("就绪")

        # 加载数据
        self._refresh_table()

    def closeEvent(self, event):
        """关闭主窗口时：清理工具窗口并退出应用"""
        # 停止坐标拾取器定时器
        if hasattr(self, 'coord_picker'):
            self.coord_picker.stop_tracking()
            self.coord_picker.hide()
        # 隐藏截图工具
        if hasattr(self, 'screenshot_tool'):
            self.screenshot_tool.hide()
        # 退出应用
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
        event.accept()

    def _setup_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px 8px;
            }
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f8f8f8;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #e8e8e8;
                border-color: #aaa;
            }
            QPushButton:pressed {
                background: #ddd;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
            }
        """)

    def _refresh_table(self):
        """刷新项目列表"""
        keyword = self.search_edit.text().strip().lower() if self.search_edit.text() else ""
        projects = storage.list_projects()
        if keyword:
            projects = [p for p in projects if keyword in p["name"].lower() or keyword in p.get("description", "").lower()]

        self.table.setRowCount(len(projects))
        for row, proj in enumerate(projects):
            self.table.setItem(row, 0, QTableWidgetItem(proj["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(proj["step_count"])))
            # 格式化时间
            updated = proj.get("updated_at", "")
            if updated:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(updated)
                    updated = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            self.table.setItem(row, 2, QTableWidgetItem(updated))
            desc = proj.get("description", "")
            self.table.setItem(row, 3, QTableWidgetItem(desc[:80] + ("..." if len(desc) > 80 else "")))
            # 存储项目 ID
            self.table.item(row, 0).setData(Qt.UserRole, proj["id"])

        self.statusBar().showMessage(f"共 {len(projects)} 个项目")

    def _get_selected_project_id(self) -> str | None:
        """获取当前选中行的项目 ID"""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _new_project(self):
        """新建项目"""
        dlg = ProjectNameDialog(self)
        if dlg.exec() == QDialog.Accepted:
            name, desc = dlg.get_values()
            if not name:
                QMessageBox.warning(self, "提示", "项目名称不能为空")
                return
            project = Project(name=name, description=desc)
            storage.save_project(project)
            self._refresh_table()
            # 自动打开编辑
            self._open_editor(project.id)

    def _edit_selected_project(self):
        """编辑选中项目"""
        pid = self._get_selected_project_id()
        if not pid:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return
        self._open_editor(pid)

    def _open_editor(self, project_id: str):
        """打开项目编辑器"""
        project = storage.load_project(project_id)
        if project is None:
            QMessageBox.warning(self, "错误", "无法加载项目")
            return
        editor = ProjectEditorWindow(project, parent=self)
        editor.finished.connect(self._refresh_table)
        editor.setModal(False)
        editor.show()

    def _delete_project(self):
        """删除项目"""
        pid = self._get_selected_project_id()
        if not pid:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return
        row = self.table.currentRow()
        name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f'确定要删除项目 "{name}" 吗？\n此操作不可恢复。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            storage.delete_project(pid)
            self._refresh_table()

    def _duplicate_project(self):
        """复制项目"""
        pid = self._get_selected_project_id()
        if not pid:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return
        project = storage.load_project(pid)
        if project is None:
            return
        new_project = Project.from_dict(project.to_dict())
        new_project.id = str(uuid.uuid4())  # 强制生成新 ID，避免覆盖原项目
        new_project.name = f"{project.name} (副本)"
        storage.save_project(new_project)
        self._refresh_table()

    def _export_project(self):
        """导出项目"""
        pid = self._get_selected_project_id()
        if not pid:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return
        project = storage.load_project(pid)
        if project is None:
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "导出项目", f"{project.name}.json", "JSON 文件 (*.json)")
        if filepath:
            if storage.export_project(project, filepath):
                QMessageBox.information(self, "成功", f"项目已导出到: {filepath}")
            else:
                QMessageBox.warning(self, "失败", "导出项目失败")

    def _import_project(self):
        """导入项目"""
        filepath, _ = QFileDialog.getOpenFileName(self, "导入项目", "", "JSON 文件 (*.json)")
        if filepath:
            project = storage.import_project(filepath)
            if project:
                storage.save_project(project)
                self._refresh_table()
                QMessageBox.information(self, "成功", f'项目 "{project.name}" 导入成功')
            else:
                QMessageBox.warning(self, "失败", "导入项目失败，请检查文件格式")

    def _clear_cache(self):
        """清除日志和截图缓存"""
        reply = QMessageBox.question(
            self,
            "确认清除缓存",
            "确定要清除所有日志和截图缓存吗？\n"
            "此操作将删除 data/logs/ 和 data/screenshots/ 目录下的所有文件。\n"
            "项目数据和设置不会被清除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                file_count, byte_count = AppConfig.clear_cache()
                size_mb = byte_count / (1024 * 1024)
                self.statusBar().showMessage(f"已清除缓存：删除 {file_count} 个文件，释放 {size_mb:.1f} MB")
                QMessageBox.information(
                    self,
                    "清除完成",
                    f"共删除 {file_count} 个缓存文件，释放 {size_mb:.2f} MB 空间。",
                )
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清除缓存失败: {e}")

    def _show_context_menu(self, pos):
        """右键菜单"""
        pid = self._get_selected_project_id()
        if not pid:
            return
        menu = QMenu(self)
        menu.addAction("✏ 编辑", self._edit_selected_project)
        menu.addAction("📋 复制", self._duplicate_project)
        menu.addSeparator()
        menu.addAction("📤 导出", self._export_project)
        menu.addSeparator()
        menu.addAction("🗑 删除", self._delete_project)
        menu.exec(self.table.viewport().mapToGlobal(pos))
