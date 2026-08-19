"""日志记录模块"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from utils.config import AppConfig


class ExecutionLogger:
    """执行日志记录器"""

    def __init__(self, project_name: str):
        self.project_name = project_name

        # 确保日志目录存在
        self.logs_dir = AppConfig.get_logs_dir()

        # 创建日志文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in "._- ")
        self.log_file = self.logs_dir / f"{safe_name}_{timestamp}.log"

        # 内存日志缓冲区（供UI实时显示）
        self.log_buffer: list[dict] = []

        # 日志回调（由 executor 设置，用于转发日志到 monitor 信号）
        self._log_callback = None

        # 设置文件日志
        self._logger = logging.getLogger(f"execution_{timestamp}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        fh = logging.FileHandler(self.log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

        # 截图目录
        self.screenshots_dir = AppConfig.get_screenshots_dir() / f"{safe_name}_{timestamp}"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def set_log_callback(self, callback):
        """设置日志回调，用于实时转发到 monitor"""
        self._log_callback = callback

    def log(self, level: str, message: str, step_name: str = "", **kwargs):
        """记录一条日志"""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": level,
            "message": message,
            "step_name": step_name,
            **kwargs,
        }
        self.log_buffer.append(entry)

        # 回调转发到 monitor（确保 actions.py 的日志也在运行页面显示）
        if self._log_callback:
            try:
                self._log_callback(entry)
            except Exception:
                pass

        # 写入文件
        full_msg = f"[{step_name}] {message}" if step_name else message
        getattr(self._logger, level.lower(), self._logger.info)(full_msg)

    def info(self, message: str, step_name: str = "", **kwargs):
        self.log("INFO", message, step_name, **kwargs)

    def warn(self, message: str, step_name: str = "", **kwargs):
        self.log("WARNING", message, step_name, **kwargs)

    def error(self, message: str, step_name: str = "", **kwargs):
        self.log("ERROR", message, step_name, **kwargs)

    def debug(self, message: str, step_name: str = "", **kwargs):
        self.log("DEBUG", message, step_name, **kwargs)

    def screenshot_path(self, step_name: str) -> str:
        """生成截图文件路径"""
        timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
        safe_step = "".join(c for c in step_name if c.isalnum() or c in "._- ")
        return str(self.screenshots_dir / f"{safe_step}_{timestamp}.png")

    def get_logs(self) -> list[dict]:
        """获取内存中的日志列表"""
        return self.log_buffer

    def clear_buffer(self):
        """清空日志缓冲区"""
        self.log_buffer.clear()
