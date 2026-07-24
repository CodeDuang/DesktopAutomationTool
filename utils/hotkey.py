"""全局热键注册模块"""
from __future__ import annotations

import threading
from typing import Callable

try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("警告: 'keyboard' 模块未安装，全局热键功能不可用")


class HotkeyManager:
    """全局热键管理器"""

    def __init__(self):
        self._callbacks: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()
        self._active_hooks: dict[str, callable] = {}

    def register(self, key: str, callback: Callable[[], None]):
        """注册一个热键回调"""
        if not HAS_KEYBOARD:
            print(f"无法注册热键 '{key}'：keyboard 模块不可用")
            return

        with self._lock:
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(callback)

            # 如果还没有为这个键注册 hook
            if key not in self._active_hooks:
                handler = kb.hotkey(key, suppress=False)
                if handler:
                    self._active_hooks[key] = handler

    def unregister(self, key: str, callback: Callable[[], None] | None = None):
        """取消注册热键"""
        with self._lock:
            if key not in self._callbacks:
                return
            if callback:
                self._callbacks[key] = [cb for cb in self._callbacks[key] if cb is not callback]
            else:
                self._callbacks[key].clear()

            if not self._callbacks[key]:
                # 清除 hook
                if key in self._active_hooks:
                    try:
                        kb.remove_hotkey(self._active_hooks[key])
                    except Exception:
                        pass
                    del self._active_hooks[key]
                    del self._callbacks[key]

    def trigger(self, key: str):
        """手动触发热键回调"""
        with self._lock:
            callbacks = self._callbacks.get(key, [])
        for cb in callbacks:
            try:
                cb()
            except Exception as e:
                print(f"热键回调异常: {e}")

    def clear_all(self):
        """清除所有热键"""
        with self._lock:
            for key in list(self._active_hooks.keys()):
                try:
                    kb.remove_hotkey(self._active_hooks[key])
                except Exception:
                    pass
            self._active_hooks.clear()
            self._callbacks.clear()


# 全局单例
hotkey_manager = HotkeyManager()
