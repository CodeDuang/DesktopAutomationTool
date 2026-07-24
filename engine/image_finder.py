"""图像查找模块：图像匹配 + OCR 文字识别"""
from __future__ import annotations

import time
from typing import Optional

import pyautogui
import cv2
import numpy as np
from PIL import Image


# pyautogui 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def find_image_on_screen(
    image_path: str,
    confidence: float = 0.90,
    grayscale: bool = False,
    region: tuple | None = None,
) -> Optional[tuple[int, int, int, int]]:
    """
    在屏幕上查找图像，返回 (left, top, width, height) 或 None

    Args:
        image_path: 参考图像路径
        confidence: 匹配置信度 (0-1)
        grayscale: 是否使用灰度匹配（更快但可能降低准确率）
        region: 搜索区域 (left, top, width, height)，None 表示全屏
    """
    try:
        location = pyautogui.locateOnScreen(
            image_path,
            confidence=confidence,
            grayscale=grayscale,
            region=region,
        )
        return location
    except pyautogui.ImageNotFoundException:
        return None
    except Exception as e:
        print(f"图像查找异常: {e}")
        return None


def find_all_images_on_screen(
    image_path: str,
    confidence: float = 0.90,
    grayscale: bool = False,
    region: tuple | None = None,
) -> list[tuple[int, int, int, int]]:
    """
    查找屏幕上所有匹配的图像
    """
    try:
        locations = list(pyautogui.locateAllOnScreen(
            image_path,
            confidence=confidence,
            grayscale=grayscale,
            region=region,
        ))
        return locations
    except Exception as e:
        print(f"图像查找异常: {e}")
        return []


def wait_for_image(
    image_path: str,
    confidence: float = 0.85,
    timeout_ms: int = 30000,
    check_interval_ms: int = 500,
) -> Optional[tuple[int, int, int, int]]:
    """
    等待图像出现（带超时）

    Returns:
        图像位置，超时返回 None
    """
    start_time = time.time()
    timeout_sec = timeout_ms / 1000.0
    interval_sec = check_interval_ms / 1000.0

    while time.time() - start_time < timeout_sec:
        location = find_image_on_screen(image_path, confidence=confidence)
        if location is not None:
            return location
        time.sleep(interval_sec)

    return None


def find_text_on_screen(
    text: str,
    language: str = "chi_sim+eng",
    confidence: float = 0.70,
) -> list[dict]:
    """
    使用 OCR 在屏幕上查找文字，返回匹配位置列表

    Args:
        text: 要查找的文字
        language: OCR 语言代码
        confidence: 文字匹配置信度

    Returns:
        [{text, left, top, width, height, confidence}, ...]
    """
    try:
        import pytesseract
    except ImportError:
        print("pytesseract 未安装，OCR 功能不可用")
        return []

    try:
        # 截取全屏
        screenshot = pyautogui.screenshot()
        # 使用 pytesseract 识别并获取位置信息
        data = pytesseract.image_to_data(
            screenshot,
            lang=language,
            output_type=pytesseract.Output.DICT,
        )

        matches = []
        n = len(data["text"])
        for i in range(n):
            recognized = data["text"][i].strip()
            if not recognized:
                continue
            # 模糊匹配
            if text.lower() in recognized.lower() or recognized.lower() in text.lower():
                conf = int(data["conf"][i]) / 100.0
                if conf >= confidence:
                    matches.append({
                        "text": recognized,
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                        "confidence": conf,
                    })
        return matches
    except Exception as e:
        print(f"OCR 识别异常: {e}")
        return []


def click_location(
    left: int,
    top: int,
    width: int,
    height: int,
    offset_x: int = 0,
    offset_y: int = 0,
    click_type: str = "left",
) -> bool:
    """
    点击指定位置的中心（可带偏移）

    Args:
        left, top, width, height: 目标区域
        offset_x, offset_y: 相对中心的偏移
        click_type: left, right, middle, double
    """
    center_x = left + width // 2 + offset_x
    center_y = top + height // 2 + offset_y

    try:
        if click_type == "double":
            pyautogui.doubleClick(center_x, center_y)
        elif click_type == "right":
            pyautogui.rightClick(center_x, center_y)
        elif click_type == "middle":
            pyautogui.middleClick(center_x, center_y)
        else:
            pyautogui.click(center_x, center_y)
        return True
    except Exception as e:
        print(f"点击失败: {e}")
        return False


def take_screenshot(filepath: str) -> bool:
    """截图并保存"""
    try:
        img = pyautogui.screenshot()
        img.save(filepath)
        return True
    except Exception as e:
        print(f"截图失败: {e}")
        return False