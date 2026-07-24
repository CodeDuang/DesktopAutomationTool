"""项目持久化存储：JSON 格式读写"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from models.project import Project
from utils.config import AppConfig


def _project_path(project_id: str) -> Path:
    return AppConfig.get_projects_dir() / f"{project_id}.json"


def save_project(project: Project) -> bool:
    """保存项目到文件"""
    try:
        project.touch()
        path = _project_path(project.id)
        data = project.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存项目失败: {e}")
        return False


def load_project(project_id: str) -> Optional[Project]:
    """从文件加载项目"""
    try:
        path = _project_path(project_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Project.from_dict(data)
    except Exception as e:
        print(f"加载项目失败: {e}")
        return None


def delete_project(project_id: str) -> bool:
    """删除项目文件"""
    try:
        path = _project_path(project_id)
        if path.exists():
            os.remove(path)
        return True
    except Exception as e:
        print(f"删除项目失败: {e}")
        return False


def list_projects() -> List[dict]:
    """列出所有项目（仅返回摘要信息）"""
    projects = []
    projects_dir = AppConfig.get_projects_dir()
    if not projects_dir.exists():
        return projects

    for filepath in sorted(projects_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects.append({
                "id": data.get("id", ""),
                "name": data.get("name", "未命名项目"),
                "description": data.get("description", ""),
                "step_count": len(data.get("steps", [])),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            continue
    return projects


def export_project(project: Project, filepath: str) -> bool:
    """导出项目为 JSON 文件"""
    try:
        data = project.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"导出项目失败: {e}")
        return False


def import_project(filepath: str) -> Optional[Project]:
    """从 JSON 文件导入项目"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Project.from_dict(data)
    except Exception as e:
        print(f"导入项目失败: {e}")
        return None
