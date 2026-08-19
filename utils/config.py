"""应用配置管理"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


class AppConfig:
    """全局应用配置"""

    # 应用信息
    APP_NAME = "桌面自动化工具"
    APP_VERSION = "1.2.0"

    _settings_cache: dict | None = None

    # 数据目录
    @classmethod
    def get_data_dir(cls) -> Path:
        """获取数据存储目录"""
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent.parent.parent
        data_dir = base / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @classmethod
    def get_projects_dir(cls) -> Path:
        """获取项目存储目录"""
        projects_dir = cls.get_data_dir() / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        return projects_dir

    @classmethod
    def get_screenshots_dir(cls) -> Path:
        """获取截图存储目录（可从设置中覆盖）"""
        custom = cls._load_settings().get("screenshots_dir", "")
        if custom and os.path.isdir(custom):
            return Path(custom)
        screenshots_dir = cls.get_data_dir() / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        return screenshots_dir

    @classmethod
    def get_logs_dir(cls) -> Path:
        """获取日志存储目录（可从设置中覆盖）"""
        custom = cls._load_settings().get("logs_dir", "")
        if custom and os.path.isdir(custom):
            return Path(custom)
        logs_dir = cls.get_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    @classmethod
    def get_images_dir(cls) -> Path:
        """获取参考图像存储目录"""
        images_dir = cls.get_data_dir() / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    @classmethod
    def _settings_path(cls) -> Path:
        return cls.get_data_dir() / "app_settings.json"

    @classmethod
    def _load_settings(cls) -> dict:
        if cls._settings_cache is not None:
            return cls._settings_cache
        path = cls._settings_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cls._settings_cache = json.load(f)
            except Exception:
                cls._settings_cache = {}
        else:
            cls._settings_cache = {}
        return cls._settings_cache

    @classmethod
    def load_settings(cls) -> dict:
        """公开方法：加载应用设置"""
        return cls._load_settings()

    @classmethod
    def save_settings(cls, settings: dict):
        cls._settings_cache = dict(settings)
        path = cls._settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cls._settings_cache, f, ensure_ascii=False, indent=2)

    @classmethod
    def reload_settings(cls):
        cls._settings_cache = None

    @classmethod
    def clear_cache(cls) -> tuple[int, int]:
        """清除所有缓存文件（日志和截图），返回 (删除文件数, 释放字节数)"""
        import shutil
        total_files = 0
        total_bytes = 0

        dirs_to_clean = [
            cls.get_logs_dir(),
            cls.get_screenshots_dir(),
        ]

        for d in dirs_to_clean:
            if d.exists():
                # 统计
                for f in d.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_bytes += f.stat().st_size
                # 删除目录内所有内容，保留空目录
                for item in d.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)
                    except Exception:
                        pass

        return total_files, total_bytes

    # 默认设置
    DEFAULT_SPEED_MULTIPLIER = 1.0
    DEFAULT_STOP_ON_FAILURE = True
    DEFAULT_SCREENSHOT_ON_FAILURE = True
    DEFAULT_EMERGENCY_STOP_KEY = "esc"
    DEFAULT_CONFIDENCE = 0.90

    # PyAutoGUI 安全设置
    PYTAUTOGUI_PAUSE = 0.1
    FAILSAFE_ENABLED = True
