"""项目数据模型定义"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .step import Step


@dataclass
class ProjectSettings:
    """项目全局设置"""

    global_speed_multiplier: float = 1.0  # 全局速度倍率 (0.1 ~ 10.0)
    stop_on_failure: bool = True  # 失败时停止执行
    screenshot_on_failure: bool = True  # 失败时自动截图
    emergency_stop_key: str = "esc"  # 紧急停止热键
    loop_count: int = 1  # 项目级循环次数（1=执行一次，不循环）
    manual_loop_confirm: bool = False  # 手动确认循环（每轮循环结束后等待用户点击确认）

    def to_dict(self) -> dict:
        return {
            "global_speed_multiplier": self.global_speed_multiplier,
            "stop_on_failure": self.stop_on_failure,
            "screenshot_on_failure": self.screenshot_on_failure,
            "emergency_stop_key": self.emergency_stop_key,
            "loop_count": self.loop_count,
            "manual_loop_confirm": self.manual_loop_confirm,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectSettings":
        return cls(
            global_speed_multiplier=data.get("global_speed_multiplier", 1.0),
            stop_on_failure=data.get("stop_on_failure", True),
            screenshot_on_failure=data.get("screenshot_on_failure", True),
            emergency_stop_key=data.get("emergency_stop_key", "esc"),
            loop_count=data.get("loop_count", 1),
            manual_loop_confirm=data.get("manual_loop_confirm", False),
        )


@dataclass
class Project:
    """自动化项目"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新自动化项目"
    description: str = ""
    steps: List[Step] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    def touch(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def add_step(self, step: Step) -> Step:
        """添加步骤"""
        self.steps.append(step)
        self.touch()
        return step

    def remove_step(self, step_id: str):
        """删除步骤"""
        self.steps = [s for s in self.steps if s.id != step_id]
        self.touch()

    def move_step(self, step_id: str, direction: int):
        """移动步骤位置（direction: -1 向上, 1 向下）"""
        idx = next((i for i, s in enumerate(self.steps) if s.id == step_id), -1)
        if idx == -1:
            return
        new_idx = idx + direction
        if 0 <= new_idx < len(self.steps):
            self.steps.insert(new_idx, self.steps.pop(idx))
            self.touch()

    def get_step(self, step_id: str) -> Step | None:
        """获取步骤"""
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def duplicate_step(self, step_id: str) -> Step | None:
        """复制步骤"""
        original = self.get_step(step_id)
        if original is None:
            return None
        data = original.to_dict()
        data["id"] = str(uuid.uuid4())
        data["name"] = f"{original.name} (副本)"
        new_step = Step.from_dict(data)
        idx = next((i for i, s in enumerate(self.steps) if s.id == step_id), len(self.steps) - 1)
        self.steps.insert(idx + 1, new_step)
        self.touch()
        return new_step

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "新自动化项目"),
            description=data.get("description", ""),
            steps=[Step.from_dict(s) for s in data.get("steps", [])],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            settings=ProjectSettings.from_dict(data.get("settings", {})),
        )
