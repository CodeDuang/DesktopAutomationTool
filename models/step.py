"""步骤数据模型定义"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VerifyType(Enum):
    """验证方法枚举（扩展点：新增验证方法在此添加）"""
    IMAGE_MATCH = "image_match"  # 图像匹配验证

    @classmethod
    def display_name(cls, vtype: "VerifyType") -> str:
        names = {
            cls.IMAGE_MATCH: "🖼 图像匹配验证",
        }
        return names.get(vtype, vtype.value)


class VerifyMode(Enum):
    """验证模式枚举"""
    CONTINUOUS = "continuous"   # 持续验证，直到通过或用户停止
    TIMED = "timed"             # 设定时间内验证，超时报错

    @classmethod
    def display_name(cls, mode: "VerifyMode") -> str:
        names = {
            cls.CONTINUOUS: "持续验证（直到通过）",
            cls.TIMED: "定时验证（超时报错）",
        }
        return names.get(mode, mode.value)


class StepType(Enum):
    """步骤类型枚举"""

    KEYBOARD_SHORTCUT = "keyboard_shortcut"  # 模拟键盘快捷键
    IMAGE_CLICK = "image_click"  # 图像匹配后点击中心
    IMAGE_RELATIVE_CLICK = "image_relative_click"  # 图像匹配后在偏移坐标点击
    IMAGE_KEYBOARD = "image_keyboard"  # 图像匹配后按快捷键
    INPUT_TEXT = "input_text"  # 输入文本
    WAIT_FOR_IMAGE = "wait_for_image"  # 等待图像出现
    OCR_CLICK = "ocr_click"  # OCR 文字识别后点击
    WAIT = "wait"  # 纯粹等待
    CONDITION = "condition"  # 条件分支

    @classmethod
    def display_name(cls, step_type: "StepType") -> str:
        names = {
            cls.KEYBOARD_SHORTCUT: "⌨ 键盘快捷键",
            cls.IMAGE_CLICK: "🖼 图像匹配点击",
            cls.IMAGE_RELATIVE_CLICK: "🖼 图像匹配(相对坐标)点击",
            cls.IMAGE_KEYBOARD: "🖼⌨ 图像匹配→快捷键",
            cls.INPUT_TEXT: "📝 输入文本",
            cls.WAIT_FOR_IMAGE: "⏳ 等待图像出现",
            cls.OCR_CLICK: "🔤 OCR文字识别点击",
            cls.WAIT: "⏱ 等待",
            cls.CONDITION: "🔀 条件判断",
        }
        return names.get(step_type, step_type.value)

    @classmethod
    def description(cls, step_type: "StepType") -> str:
        descs = {
            cls.KEYBOARD_SHORTCUT: "模拟按下键盘快捷键组合（如 Ctrl+C）",
            cls.IMAGE_CLICK: "在屏幕上查找指定图像，找到后点击图像中心位置",
            cls.IMAGE_RELATIVE_CLICK: "在屏幕上查找指定图像，找到后点击图像周围的相对坐标位置",
            cls.IMAGE_KEYBOARD: "在屏幕上查找指定图像，找到后按下设定的快捷键组合",
            cls.INPUT_TEXT: "输入文本内容：固定文本、循环轮数数字、或剪贴板内容",
            cls.WAIT_FOR_IMAGE: "等待指定图像出现在屏幕上（带超时控制）",
            cls.OCR_CLICK: "使用OCR识别屏幕上的文字，找到后点击该文字位置",
            cls.WAIT: "等待指定的时间（毫秒）",
            cls.CONDITION: "根据图像是否存在决定执行哪个分支",
        }
        return descs.get(step_type, "")


@dataclass
class FailureConfig:
    """失败处理配置"""

    screenshot: bool = True  # 失败时截图
    log_error: bool = True  # 失败时记录日志
    retry_count: int = 0  # 重试次数
    retry_interval_ms: int = 1000  # 重试间隔

    def to_dict(self) -> dict:
        return {
            "screenshot": self.screenshot,
            "log_error": self.log_error,
            "retry_count": self.retry_count,
            "retry_interval_ms": self.retry_interval_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FailureConfig":
        return cls(
            screenshot=data.get("screenshot", True),
            log_error=data.get("log_error", True),
            retry_count=data.get("retry_count", 0),
            retry_interval_ms=data.get("retry_interval_ms", 1000),
        )


@dataclass
class VerifyConfig:
    """步骤验证配置"""
    enabled: bool = False                           # 是否启用验证
    verify_type: VerifyType = VerifyType.IMAGE_MATCH  # 验证方法
    verify_mode: VerifyMode = VerifyMode.CONTINUOUS   # 验证模式
    params: dict = field(default_factory=lambda: {    # 验证参数（根据 verify_type 不同）
        "image_path": "",
        "confidence": 0.90,
    })
    timeout_ms: int = 30000                          # TIMED 模式的超时时间

    @classmethod
    def get_default_params(cls, verify_type: VerifyType) -> dict:
        defaults = {
            VerifyType.IMAGE_MATCH: {
                "image_path": "",
                "confidence": 0.90,
            },
        }
        return defaults.get(verify_type, {})

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "verify_type": self.verify_type.value,
            "verify_mode": self.verify_mode.value,
            "params": self.params,
            "timeout_ms": self.timeout_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VerifyConfig":
        vt = VerifyType(data.get("verify_type", "image_match"))
        return cls(
            enabled=data.get("enabled", False),
            verify_type=vt,
            verify_mode=VerifyMode(data.get("verify_mode", "continuous")),
            params={**cls.get_default_params(vt), **data.get("params", {})},
            timeout_ms=data.get("timeout_ms", 30000),
        )


@dataclass
class Step:
    """自动化步骤"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新步骤"
    type: StepType = StepType.WAIT
    params: dict = field(default_factory=dict)
    wait_before_ms: int = 500  # 步骤执行前等待
    wait_after_ms: int = 500  # 步骤执行后等待
    repeat_count: int = 1  # 步骤自身循环次数（1=执行一次不循环）
    on_failure: FailureConfig = field(default_factory=FailureConfig)
    enabled: bool = True
    verify_config: VerifyConfig = field(default_factory=VerifyConfig)  # 验证配置

    def get_default_params(self) -> dict:
        """根据步骤类型返回默认参数"""
        defaults = {
            StepType.KEYBOARD_SHORTCUT: {
                "keys": "ctrl+c",
                "press_interval_ms": 100,
            },
            StepType.IMAGE_CLICK: {
                "image_path": "",
                "confidence": 0.90,
                "click_type": "left",
                "grayscale": False,
            },
            StepType.IMAGE_RELATIVE_CLICK: {
                "image_path": "",
                "confidence": 0.90,
                "offset_x": 0,
                "offset_y": 0,
                "click_type": "left",
            },
            StepType.IMAGE_KEYBOARD: {
                "image_path": "",
                "confidence": 0.90,
                "keys": "ctrl+c",
                "press_interval_ms": 100,
            },
            StepType.INPUT_TEXT: {
                "text_type": "fixed",  # "fixed" | "loop_index" | "clipboard"
                "text_value": "",
                "use_clipboard": False,
                "use_loop_index": False,
                "loop_index_start": 1,  # 循环起始值
                "loop_index_step": 1,  # 循环增量
            },
            StepType.WAIT_FOR_IMAGE: {
                "image_path": "",
                "confidence": 0.85,
                "timeout_ms": 30000,
                "check_interval_ms": 500,
            },
            StepType.OCR_CLICK: {
                "text": "",
                "language": "chi_sim+eng",
                "confidence": 0.7,
                "click_offset_x": 0,
                "click_offset_y": 0,
            },
            StepType.WAIT: {
                "duration_ms": 2000,
            },
            StepType.CONDITION: {
                "condition_type": "image_exists",
                "image_path": "",
                "confidence": 0.90,
                "true_branch_name": "找到图像",
                "false_branch_name": "未找到图像",
            },
        }
        return defaults.get(self.type, {})

    def ensure_params(self):
        """确保 params 包含所有默认键"""
        defaults = self.get_default_params()
        for key, value in defaults.items():
            if key not in self.params:
                self.params[key] = value

    def to_dict(self) -> dict:
        self.ensure_params()
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "params": self.params,
            "wait_before_ms": self.wait_before_ms,
            "wait_after_ms": self.wait_after_ms,
            "repeat_count": self.repeat_count,
            "on_failure": self.on_failure.to_dict(),
            "enabled": self.enabled,
            "verify_config": self.verify_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Step":
        step = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "新步骤"),
            type=StepType(data.get("type", "wait")),
            params=data.get("params", {}),
            wait_before_ms=data.get("wait_before_ms", 500),
            wait_after_ms=data.get("wait_after_ms", 500),
            repeat_count=data.get("repeat_count", 1),
            on_failure=FailureConfig.from_dict(data.get("on_failure", {})),
            enabled=data.get("enabled", True),
            verify_config=VerifyConfig.from_dict(data.get("verify_config", {})),
        )
        step.ensure_params()
        return step
