"""步骤编辑对话框"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QScrollArea,
    QWidget,
    QLabel,
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QToolTip

from models.step import Step, StepType, FailureConfig, VerifyConfig, VerifyType, VerifyMode
from views.widgets.hotkey_recorder import HotkeyRecorder


class StepDialog(QDialog):
    """步骤编辑对话框"""

    def __init__(self, step: Step, is_new: bool = False, parent=None):
        super().__init__(parent)
        self.step = step
        self.is_new = is_new

        self.setWindowTitle("添加步骤" if is_new else f"编辑步骤 - {step.name}")
        self.setMinimumWidth(660)
        self.setMinimumHeight(500)
        self.resize(700, 620)
        self.setModal(True)

        self._build_ui()
        self._load_step_data()

    def _build_ui(self):
        # 外层布局包含滚动区 + 底部按钮
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 滚动区域（内容会滚动，按钮不滚动） ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(6)

        # ---- 基本信息 ----
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setVerticalSpacing(4)

        self.edit_name = QLineEdit()
        self.edit_name.setMinimumHeight(32)
        self.edit_name.setPlaceholderText("给这个步骤起个名字")
        basic_layout.addRow("步骤名称:", self.edit_name)

        self.combo_type = QComboBox()
        self.combo_type.setMinimumHeight(30)
        self.combo_type.blockSignals(True)
        for st in StepType:
            self.combo_type.addItem(StepType.display_name(st), st)
        self.combo_type.blockSignals(False)
        basic_layout.addRow("步骤类型:", self.combo_type)

        scroll_layout.addWidget(basic_group)

        # ---- 类型参数（动态内容区） ----
        self.params_group = QGroupBox("步骤参数")
        self.params_layout = QFormLayout(self.params_group)
        self.params_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        self.params_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.params_layout.setVerticalSpacing(4)
        self._param_widgets = {}  # key -> widget 映射
        scroll_layout.addWidget(self.params_group)

        # ---- 高级设置 ----
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setVerticalSpacing(4)

        self.spin_wait_before = QSpinBox()
        self.spin_wait_before.setMinimumHeight(26)
        self.spin_wait_before.setRange(0, 600000)
        self.spin_wait_before.setSuffix(" 毫秒")
        self.spin_wait_before.setSingleStep(100)
        self.spin_wait_before.setToolTip("步骤执行前等待的时间")
        advanced_layout.addRow("执行前等待:", self.spin_wait_before)

        self.spin_wait_after = QSpinBox()
        self.spin_wait_after.setMinimumHeight(26)
        self.spin_wait_after.setRange(0, 600000)
        self.spin_wait_after.setSuffix(" 毫秒")
        self.spin_wait_after.setSingleStep(100)
        self.spin_wait_after.setToolTip("步骤执行后等待的时间")
        advanced_layout.addRow("执行后等待:", self.spin_wait_after)

        self.spin_repeat = QSpinBox()
        self.spin_repeat.setMinimumHeight(26)
        self.spin_repeat.setRange(1, 999999)
        self.spin_repeat.setValue(1)
        self.spin_repeat.setToolTip("步骤自身循环次数。设置为1表示执行一次；设置为5表示该步骤重复执行5次后再继续下一步")
        advanced_layout.addRow("循环次数:", self.spin_repeat)

        scroll_layout.addWidget(advanced_group)

        # ---- 失败处理 ----
        failure_group = QGroupBox("失败处理")
        failure_layout = QFormLayout(failure_group)

        self.chk_fail_screenshot = QCheckBox("失败时截图")
        self.chk_fail_screenshot.setChecked(True)
        failure_layout.addRow("", self.chk_fail_screenshot)

        self.chk_fail_log = QCheckBox("失败时记录日志")
        self.chk_fail_log.setChecked(True)
        failure_layout.addRow("", self.chk_fail_log)

        self.spin_retry = QSpinBox()
        self.spin_retry.setMinimumHeight(26)
        self.spin_retry.setRange(0, 10)
        self.spin_retry.setToolTip("失败后重试次数（0 = 不重试）")
        failure_layout.addRow("重试次数:", self.spin_retry)

        self.spin_retry_interval = QSpinBox()
        self.spin_retry_interval.setMinimumHeight(26)
        self.spin_retry_interval.setRange(100, 60000)
        self.spin_retry_interval.setSuffix(" 毫秒")
        self.spin_retry_interval.setSingleStep(500)
        self.spin_retry_interval.setToolTip("每次重试之间的等待间隔")
        failure_layout.addRow("重试间隔:", self.spin_retry_interval)

        scroll_layout.addWidget(failure_group)

        # ---- 验证设置 ----
        self.verify_group = QGroupBox("验证设置（可选）")
        self.verify_group.setCheckable(True)
        self.verify_group.setChecked(self.step.verify_config.enabled)
        self.verify_group.toggled.connect(self._on_verify_group_toggled)
        verify_layout = QFormLayout(self.verify_group)
        verify_layout.setVerticalSpacing(4)

        self.combo_verify_type = QComboBox()
        self.combo_verify_type.setMinimumHeight(30)
        for vt in VerifyType:
            self.combo_verify_type.addItem(VerifyType.display_name(vt), vt)
        self.combo_verify_type.currentIndexChanged.connect(self._on_verify_type_changed)
        verify_layout.addRow("验证方法:", self.combo_verify_type)

        # 验证参数（动态刷新）
        self.verify_params_group = QGroupBox("验证参数")
        self.verify_params_layout = QFormLayout(self.verify_params_group)
        self.verify_params_layout.setVerticalSpacing(4)
        self._verify_widgets = {}
        verify_layout.addRow(self.verify_params_group)

        self.combo_verify_mode = QComboBox()
        self.combo_verify_mode.setMinimumHeight(30)
        for vm in VerifyMode:
            self.combo_verify_mode.addItem(VerifyMode.display_name(vm), vm)
        self.combo_verify_mode.currentIndexChanged.connect(self._on_verify_mode_changed)
        verify_layout.addRow("验证模式:", self.combo_verify_mode)

        self.spin_verify_timeout = QSpinBox()
        self.spin_verify_timeout.setMinimumHeight(26)
        self.spin_verify_timeout.setRange(1000, 3600000)
        self.spin_verify_timeout.setValue(self.step.verify_config.timeout_ms)
        self.spin_verify_timeout.setSuffix(" ms")
        self.spin_verify_timeout.setSingleStep(1000)
        self.spin_verify_timeout.setToolTip("定时验证模式下，超过该时间未通过则报错")
        self.spin_verify_timeout.valueChanged.connect(self._on_verify_timeout_changed)
        verify_layout.addRow("超时时间:", self.spin_verify_timeout)

        scroll_layout.addWidget(self.verify_group)
        scroll_layout.addStretch()

        # 将滚动区域加入外层
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # ---- 按钮（固定在底部，不滚动） ----
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(12, 8, 12, 12)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(buttons)
        main_layout.addLayout(btn_layout)

        # 连接类型切换信号
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)

        # 首次验证参数构建
        if self.verify_group.isChecked() or self.step.verify_config.enabled:
            self._on_verify_type_changed()

    def eventFilter(self, obj, event):
        """事件过滤器：鼠标移入帮助按钮时立即显示提示，移出时隐藏"""
        if obj is self._help_btn:
            if event.type() == QEvent.Enter:
                from PySide6.QtGui import QCursor
                QToolTip.showText(QCursor.pos(), self._help_explanation, self)
                return True
            elif event.type() == QEvent.Leave:
                QToolTip.hideText()
                return True
        return super().eventFilter(obj, event)

    def _on_type_changed(self):
        """切换步骤类型时重建参数表单"""
        # 清除旧控件
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)
        self._param_widgets.clear()

        step_type = self.combo_type.currentData()
        if step_type is None:
            return

        if step_type == StepType.KEYBOARD_SHORTCUT:
            self._build_keyboard_params()
        elif step_type == StepType.IMAGE_CLICK:
            self._build_image_click_params()
        elif step_type == StepType.IMAGE_RELATIVE_CLICK:
            self._build_image_relative_params()
        elif step_type == StepType.IMAGE_KEYBOARD:
            self._build_image_keyboard_params()
        elif step_type == StepType.INPUT_TEXT:
            self._build_input_text_params()
        elif step_type == StepType.WAIT_FOR_IMAGE:
            self._build_wait_image_params()
        elif step_type == StepType.OCR_CLICK:
            self._build_ocr_params()
        elif step_type == StepType.WAIT:
            self._build_wait_params()
        elif step_type == StepType.CONDITION:
            self._build_condition_params()

    def _on_verify_group_toggled(self, checked):
        """验证组勾选状态变更"""
        self.step.verify_config.enabled = checked
        if checked and not self._verify_widgets:
            self._on_verify_type_changed()

    def _on_verify_type_changed(self):
        """切换验证方法时重建参数表单"""
        while self.verify_params_layout.rowCount() > 0:
            self.verify_params_layout.removeRow(0)
        self._verify_widgets.clear()

        vt = self.combo_verify_type.currentData()
        if vt is None:
            return
        if vt == VerifyType.IMAGE_MATCH:
            self._build_verify_image_match_params()

    def _on_verify_timeout_changed(self, value):
        """验证超时时长变更"""
        self.step.verify_config.timeout_ms = value

    def _on_verify_mode_changed(self):
        """切换验证模式时显示/隐藏超时时间"""
        vm = self.combo_verify_mode.currentData()
        timeout_visible = vm == VerifyMode.TIMED
        self.spin_verify_timeout.setVisible(timeout_visible)
        label_item = self.verify_group.layout().labelForField(self.spin_verify_timeout)
        if label_item:
            label_item.setVisible(timeout_visible)

    def _build_verify_image_match_params(self):
        layout = QHBoxLayout()
        w = QLineEdit()
        w.setMinimumHeight(32)
        w.setPlaceholderText("选择验证参考图像...")
        layout.addWidget(w)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w))
        layout.addWidget(btn)
        self.verify_params_layout.addRow("参考图像:", layout)
        self._verify_widgets["image_path"] = w

        w2 = QDoubleSpinBox()
        w2.setMinimumHeight(28)
        w2.setRange(0.50, 1.0)
        w2.setSingleStep(0.05)
        w2.setValue(0.90)
        self.verify_params_layout.addRow("置信度:", w2)
        self._verify_widgets["confidence"] = w2

    def _load_verify_params(self):
        """从 step.verify_config 加载验证设置"""
        vc = self.step.verify_config
        self.verify_group.setChecked(vc.enabled)

        idx = self.combo_verify_type.findData(vc.verify_type)
        if idx >= 0:
            self.combo_verify_type.setCurrentIndex(idx)

        idx2 = self.combo_verify_mode.findData(vc.verify_mode)
        if idx2 >= 0:
            self.combo_verify_mode.setCurrentIndex(idx2)

        self.spin_verify_timeout.setValue(vc.timeout_ms)
        self._on_verify_mode_changed()

        # 如果验证参数控件未构建，先构建
        if not self._verify_widgets:
            self._on_verify_type_changed()

        # 填充验证参数值
        for key, widget in self._verify_widgets.items():
            value = vc.params.get(key, "")
            if isinstance(widget, QLineEdit):
                widget.setText(str(value) if value else "")
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))

    def _collect_verify_config(self) -> VerifyConfig:
        """从 UI 收集验证配置"""
        params = {}
        for key, widget in self._verify_widgets.items():
            if isinstance(widget, QLineEdit):
                params[key] = widget.text()
            elif isinstance(widget, QDoubleSpinBox):
                params[key] = widget.value()
        vt = self.combo_verify_type.currentData() or VerifyType.IMAGE_MATCH
        vm = self.combo_verify_mode.currentData() or VerifyMode.CONTINUOUS
        return VerifyConfig(
            enabled=self.verify_group.isChecked(),
            verify_type=vt,
            verify_mode=vm,
            params=params,
            timeout_ms=self.spin_verify_timeout.value(),
        )

    def _add_param_row(self, label: str, widget, key: str):
        """添加参数行并注册，固定输入控件最小高度"""
        if isinstance(widget, QLineEdit):
            widget.setMinimumHeight(32)
        elif isinstance(widget, QPlainTextEdit):
            pass  # 高度已在 build 时设置
        elif isinstance(widget, QComboBox):
            widget.setMinimumHeight(30)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setMinimumHeight(28)
        elif isinstance(widget, QHBoxLayout):
            for i in range(widget.count()):
                child = widget.itemAt(i).widget()
                if isinstance(child, QLineEdit):
                    child.setMinimumHeight(32)
                elif isinstance(child, QComboBox):
                    child.setMinimumHeight(30)
                elif isinstance(child, (QSpinBox, QDoubleSpinBox)):
                    child.setMinimumHeight(28)
        self.params_layout.addRow(label, widget)
        self._param_widgets[key] = widget

    def _browse_image(self, line_edit: QLineEdit):
        """浏览图片文件"""
        filepath, _ = QFileDialog.getOpenFileName(self, "选择图像文件", "", "图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)")
        if filepath:
            line_edit.setText(filepath)

    # ---- 各类型参数表单构建 ----

    def _build_keyboard_params(self):
        w = HotkeyRecorder()
        self._add_param_row("快捷键:", w, "keys")

        w2 = QSpinBox()
        w2.setRange(0, 5000)
        w2.setSuffix(" ms")
        w2.setValue(100)
        w2.setToolTip("按键之间的间隔时间")
        self._add_param_row("按键间隔:", w2, "press_interval_ms")

    def _build_image_click_params(self):
        layout = QHBoxLayout()
        w = QLineEdit()
        w.setPlaceholderText("选择用于匹配的参考图像...")
        layout.addWidget(w)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w))
        layout.addWidget(btn)
        self._add_param_row("图像路径:", layout, "image_path")
        # param_widgets 里存的是 QLineEdit
        self._param_widgets["image_path"] = w

        w2 = QDoubleSpinBox()
        w2.setRange(0.50, 1.0)
        w2.setSingleStep(0.05)
        w2.setValue(0.90)
        w2.setToolTip("匹配置信度，值越高越精确，默认0.90")
        self._add_param_row("置信度:", w2, "confidence")

        w3 = QComboBox()
        w3.addItems(["left", "right", "middle", "double"])
        self._add_param_row("点击类型:", w3, "click_type")

        w4 = QCheckBox()
        w4.setToolTip("启用灰度匹配可提高约30%速度，但可能降低准确率")
        self._add_param_row("灰度匹配:", w4, "grayscale")

    def _build_image_relative_params(self):
        layout = QHBoxLayout()
        w = QLineEdit()
        w.setPlaceholderText("选择锚点图像...")
        layout.addWidget(w)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w))
        layout.addWidget(btn)
        self._add_param_row("锚点图像:", layout, "image_path")
        self._param_widgets["image_path"] = w

        w2 = QDoubleSpinBox()
        w2.setRange(0.50, 1.0)
        w2.setSingleStep(0.05)
        w2.setValue(0.90)
        self._add_param_row("置信度:", w2, "confidence")

        w3 = QSpinBox()
        w3.setRange(-9999, 9999)
        w3.setToolTip("相对图像中心的 X 偏移（像素）")
        self._add_param_row("X 偏移:", w3, "offset_x")

        w4 = QSpinBox()
        w4.setRange(-9999, 9999)
        w4.setToolTip("相对图像中心的 Y 偏移（像素）")
        self._add_param_row("Y 偏移:", w4, "offset_y")

        w5 = QComboBox()
        w5.addItems(["left", "right", "middle", "double"])
        self._add_param_row("点击类型:", w5, "click_type")

    def _build_image_keyboard_params(self):
        layout = QHBoxLayout()
        w = QLineEdit()
        w.setPlaceholderText("选择用于匹配的参考图像...")
        layout.addWidget(w)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w))
        layout.addWidget(btn)
        self._add_param_row("图像路径:", layout, "image_path")
        self._param_widgets["image_path"] = w

        w2 = QDoubleSpinBox()
        w2.setRange(0.50, 1.0)
        w2.setSingleStep(0.05)
        w2.setValue(0.90)
        w2.setToolTip("匹配置信度，值越高越精确，默认0.90")
        self._add_param_row("置信度:", w2, "confidence")

        w3 = HotkeyRecorder()
        self._add_param_row("快捷键:", w3, "keys")

        w4 = QSpinBox()
        w4.setRange(0, 5000)
        w4.setSuffix(" ms")
        w4.setValue(100)
        w4.setToolTip("按键之间的间隔时间（留空快捷键则不按键）")
        self._add_param_row("按键间隔:", w4, "press_interval_ms")

    def _build_input_text_params(self):
        w = QComboBox()
        w.addItem("固定文本（支持多行）", "fixed")
        w.addItem("循环轮数数字", "loop_index")
        w.addItem("剪贴板内容", "clipboard")
        w.currentIndexChanged.connect(self._on_input_type_changed)

        text_source_layout = QHBoxLayout()
        text_source_layout.addWidget(w)
        help_explanation = (
            "固定文本（支持多行）处理机制：\n"
            "1. 每行作为一轮输入的内容\n"
            "2. 执行时读取第一行后自动进入下一行\n"
            "3. 配合循环次数可实现逐行逐轮输入\n"
            "4. 行输入完毕后自动从头重新开始\n"
            "例：输入「A\\nB\\nC」→ 第1轮A→第2轮B→第3轮C→第4轮A..."
        )
        help_btn = QLabel("?")
        help_btn.setFixedSize(22, 22)
        help_btn.setAlignment(Qt.AlignCenter)
        help_btn.setToolTip(help_explanation)
        help_btn.installEventFilter(self)
        self._help_explanation = help_explanation
        self._help_btn = help_btn
        help_btn.setStyleSheet(
            "border: 1px solid #1976D2;"
            "border-radius: 11px;"
            "color: #1976D2;"
            "font-weight: bold;"
            "background: #f0f4ff;"
            "font-size: 13px;"
        )
        text_source_layout.addWidget(help_btn)
        text_source_layout.addStretch()
        self._add_param_row("文本来源:", text_source_layout, "text_type")
        self._param_widgets["text_type"] = w  # 确保后续逻辑仍然操作 combo 本身

        self._input_value_widget = QPlainTextEdit()
        self._input_value_widget.setPlaceholderText(
            "输入要发送的文本，每行作为一轮输入的文本\n"
            "执行时逐行读取，完成一行后自动进入下一行"
        )
        self._input_value_widget.setMinimumHeight(100)
        self._input_value_widget.setMaximumHeight(200)
        self._add_param_row("文本内容:", self._input_value_widget, "text_value")

        self._input_loop_start = QSpinBox()
        self._input_loop_start.setRange(0, 999999)
        self._input_loop_start.setValue(1)
        self._input_loop_start.setToolTip("循环起始值")
        self._add_param_row("起始值:", self._input_loop_start, "loop_index_start")
        self._input_loop_start.setVisible(False)

        self._input_loop_step = QSpinBox()
        self._input_loop_step.setRange(1, 100)
        self._input_loop_step.setValue(1)
        self._input_loop_step.setToolTip("每次循环增加的值")
        self._add_param_row("增量:", self._input_loop_step, "loop_index_step")
        self._input_loop_step.setVisible(False)

        # 默认状态
        self._on_input_type_changed(0)

    def _on_input_type_changed(self, index):
        text_type = self._param_widgets["text_type"].currentData()
        is_fixed = text_type == "fixed"
        is_loop = text_type == "loop_index"
        self._input_value_widget.setVisible(is_fixed)
        self._input_loop_start.setVisible(is_loop)
        self._input_loop_step.setVisible(is_loop)
        # 更新标签
        if hasattr(self, "_input_value_label"):
            self.params_layout.labelForField(self._input_value_widget).setText("文本内容:" if is_fixed else "")

    def _build_wait_image_params(self):
        layout = QHBoxLayout()
        w = QLineEdit()
        w.setPlaceholderText("选择等待出现的图像...")
        layout.addWidget(w)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w))
        layout.addWidget(btn)
        self._add_param_row("等待图像:", layout, "image_path")
        self._param_widgets["image_path"] = w

        w2 = QDoubleSpinBox()
        w2.setRange(0.50, 1.0)
        w2.setSingleStep(0.05)
        w2.setValue(0.85)
        self._add_param_row("置信度:", w2, "confidence")

        w3 = QSpinBox()
        w3.setRange(100, 600000)
        w3.setSingleStep(1000)
        w3.setValue(30000)
        w3.setSuffix(" ms")
        w3.setToolTip("等待超时时间（默认30秒）")
        self._add_param_row("超时时间:", w3, "timeout_ms")

        w4 = QSpinBox()
        w4.setRange(100, 10000)
        w4.setSingleStep(100)
        w4.setValue(500)
        w4.setSuffix(" ms")
        w4.setToolTip("检查图像是否出现的间隔")
        self._add_param_row("检查间隔:", w4, "check_interval_ms")

    def _build_ocr_params(self):
        w = QLineEdit()
        w.setPlaceholderText("输入要识别的文字（例如列名）")
        w.setToolTip("支持中文、英文。Tesseract 需要提前安装。")
        self._add_param_row("识别文字:", w, "text")

        w2 = QLineEdit()
        w2.setText("chi_sim+eng")
        w2.setToolTip("OCR 语言代码：chi_sim=简体中文, eng=英文")
        self._add_param_row("语言:", w2, "language")

        w3 = QDoubleSpinBox()
        w3.setRange(0.50, 1.0)
        w3.setSingleStep(0.05)
        w3.setValue(0.70)
        self._add_param_row("置信度:", w3, "confidence")

        w4 = QSpinBox()
        w4.setRange(-999, 999)
        w4.setValue(0)
        w4.setToolTip("相对识别文字中心的 X 偏移")
        self._add_param_row("X 偏移:", w4, "click_offset_x")

        w5 = QSpinBox()
        w5.setRange(-999, 999)
        w5.setValue(0)
        w5.setToolTip("相对识别文字中心的 Y 偏移")
        self._add_param_row("Y 偏移:", w5, "click_offset_y")

    def _build_wait_params(self):
        w = QSpinBox()
        w.setRange(100, 3600000)
        w.setSingleStep(500)
        w.setValue(2000)
        w.setSuffix(" ms")
        w.setToolTip("等待时间（毫秒）")
        self._add_param_row("等待时间:", w, "duration_ms")

    def _build_condition_params(self):
        w = QComboBox()
        w.addItem("图像存在时执行", "image_exists")
        w.addItem("图像不存在时执行", "image_not_exists")
        self._add_param_row("条件类型:", w, "condition_type")

        layout = QHBoxLayout()
        w2 = QLineEdit()
        w2.setPlaceholderText("选择条件图像...")
        layout.addWidget(w2)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._browse_image(w2))
        layout.addWidget(btn)
        self._add_param_row("条件图像:", layout, "image_path")
        self._param_widgets["image_path"] = w2

        w3 = QDoubleSpinBox()
        w3.setRange(0.50, 1.0)
        w3.setSingleStep(0.05)
        w3.setValue(0.90)
        self._add_param_row("置信度:", w3, "confidence")

    # ---- 加载/保存 ----

    def _load_step_data(self):
        """从 Step 对象加载数据到 UI"""
        self.edit_name.setText(self.step.name)

        # 选择步骤类型（setCurrentIndex 在 index 未变化时不触发信号，需手动构建参数）
        idx = self.combo_type.findData(self.step.type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        if not self._param_widgets:
            self._on_type_changed()

        # 基础参数
        self.spin_wait_before.setValue(self.step.wait_before_ms)
        self.spin_wait_after.setValue(self.step.wait_after_ms)
        self.spin_repeat.setValue(self.step.repeat_count)

        # 失败处理
        self.chk_fail_screenshot.setChecked(self.step.on_failure.screenshot)
        self.chk_fail_log.setChecked(self.step.on_failure.log_error)
        self.spin_retry.setValue(self.step.on_failure.retry_count)
        self.spin_retry_interval.setValue(self.step.on_failure.retry_interval_ms)

        # 验证设置
        self._load_verify_params()

        # 步骤类型参数
        self._load_params_to_widgets()

    def _load_params_to_widgets(self):
        """将 step.params 填充到对应控件"""
        params = self.step.params
        for key, widget in self._param_widgets.items():
            if key not in params:
                continue
            value = params[key]

            if isinstance(widget, QLineEdit):
                # 特殊处理 QLineEdit 可能嵌套在 layout 中
                pass
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(str(value) if value else "")
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText(str(value))

        # 处理 QLineEdit 和 HotkeyRecorder（可能直接存储或嵌套在 QHBoxLayout 中）
        for key, widget in self._param_widgets.items():
            if key not in params:
                continue
            value = params[key]
            if isinstance(widget, QLineEdit):
                widget.setText(str(value) if value else "")
            elif isinstance(widget, QPlainTextEdit):
                pass  # 已在上方处理
            elif isinstance(widget, HotkeyRecorder):
                widget.setText(str(value) if value else "")
            elif isinstance(widget, QHBoxLayout):
                # 找到其中的 QLineEdit
                for i in range(widget.count()):
                    child = widget.itemAt(i).widget()
                    if isinstance(child, QLineEdit):
                        child.setText(str(value) if value else "")
                        break

    def _collect_params_from_widgets(self) -> dict:
        """从 UI 控件收集参数"""
        params = {}
        for key, widget in self._param_widgets.items():
            if isinstance(widget, QLineEdit):
                params[key] = widget.text()
            elif isinstance(widget, QPlainTextEdit):
                params[key] = widget.toPlainText()
            elif isinstance(widget, QSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                params[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                params[key] = widget.currentData() or widget.currentText()
            elif isinstance(widget, HotkeyRecorder):
                params[key] = widget.text()
            elif isinstance(widget, QHBoxLayout):
                # 找到其中的 QLineEdit
                for i in range(widget.count()):
                    child = widget.itemAt(i).widget()
                    if isinstance(child, QLineEdit):
                        params[key] = child.text()
                        break
        return params

    def _on_accept(self):
        """确认按钮"""
        # 验证
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "验证失败", "请输入步骤名称")
            return

        step_type = self.combo_type.currentData()
        params = self._collect_params_from_widgets()

        # 验证特定类型必填参数
        if step_type in (StepType.IMAGE_CLICK, StepType.IMAGE_RELATIVE_CLICK, StepType.WAIT_FOR_IMAGE, StepType.CONDITION):
            if not params.get("image_path", "").strip():
                QMessageBox.warning(self, "验证失败", "请选择参考图像")
                return
        if step_type == StepType.OCR_CLICK:
            if not params.get("text", "").strip():
                QMessageBox.warning(self, "验证失败", "请输入要识别的文字")
                return
        if step_type == StepType.INPUT_TEXT:
            if params.get("text_type") == "fixed" and not params.get("text_value", ""):
                QMessageBox.warning(self, "验证失败", "请输入文本内容")
                return

        # 更新 Step 对象
        self.step.name = name
        self.step.type = step_type
        self.step.params = params
        self.step.wait_before_ms = self.spin_wait_before.value()
        self.step.wait_after_ms = self.spin_wait_after.value()
        self.step.repeat_count = self.spin_repeat.value()

        # 失败处理
        self.step.on_failure = FailureConfig(
            screenshot=self.chk_fail_screenshot.isChecked(),
            log_error=self.chk_fail_log.isChecked(),
            retry_count=self.spin_retry.value(),
            retry_interval_ms=self.spin_retry_interval.value(),
        )

        # 验证配置
        self.step.verify_config = self._collect_verify_config()

        self.accept()