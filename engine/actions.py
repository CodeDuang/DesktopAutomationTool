"""各步骤类型的执行实现"""

from __future__ import annotations

import time
import pyautogui
import pyperclip

from engine import image_finder
from engine.logger import ExecutionLogger


class ActionResult:
    """动作执行结果"""

    def __init__(self, success: bool, message: str = "", screenshot_path: str = ""):
        self.success = success
        self.message = message
        self.screenshot_path = screenshot_path


def execute_verify_image_match(vconfig, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """执行图像匹配验证

    vconfig: VerifyConfig 对象
    返回 True 表示验证通过（图像存在），False 表示未通过
    """
    from models.step import VerifyConfig
    image_path = vconfig.params.get("image_path", "")
    confidence = float(vconfig.params.get("confidence", 0.90))

    if not image_path:
        return ActionResult(False, "验证图像路径为空")

    location = image_finder.find_image_on_screen(image_path, confidence)
    if location is not None:
        logger.info(f"✅ 验证通过 - 图像已匹配: {image_path}", step_name)
        return ActionResult(True, f"验证通过: {image_path}")
    else:
        return ActionResult(False, f"验证未通过 - 图像未找到: {image_path}")


def execute_keyboard_shortcut(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    执行键盘快捷键

    params: {"keys": "ctrl+c", "press_interval_ms": 100}
    支持键盘按键和鼠标滚轮（wheel_up / wheel_down）
    """
    keys_str = params.get("keys", "")
    interval = params.get("press_interval_ms", 100) / 1000.0

    if not keys_str:
        return ActionResult(False, "快捷键配置为空")

    try:
        # 解析快捷键：分离键盘按键和鼠标滚轮
        key_parts = [k.strip().lower() for k in keys_str.split("+")]
        keyboard_keys = []
        wheel_direction = None

        for k in key_parts:
            if k == "wheel_up":
                wheel_direction = "up"
            elif k == "wheel_down":
                wheel_direction = "down"
            else:
                keyboard_keys.append(k)

        # 先执行键盘组合键（如果有）
        if keyboard_keys:
            logger.info(f"⌨ 按下快捷键: {'+'.join(keyboard_keys)}", step_name)
            pyautogui.hotkey(*keyboard_keys, interval=interval)

        # 再执行鼠标滚轮（如果有）
        if wheel_direction:
            scroll_amount = 3 if wheel_direction == "up" else -3
            logger.info(f"🖱 鼠标滚轮: wheel_{wheel_direction}", step_name)
            pyautogui.scroll(scroll_amount)

        # 日志增加明细
        parts_detail = []
        if keyboard_keys:
            parts_detail.append(f"按键: {'+'.join(keyboard_keys)}")
        if wheel_direction:
            parts_detail.append(f"滚轮: {wheel_direction}")
        detail = " | ".join(parts_detail)
        logger.info(f"✓ 快捷键执行完成: {detail}", step_name)
        return ActionResult(True, f"快捷键 {keys_str} 执行成功")
    except Exception as e:
        logger.error(f"快捷键执行失败: {e}", step_name)
        return ActionResult(False, f"快捷键执行失败: {e}")


def execute_image_click(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    图像匹配点击

    params: {"image_path": "", "confidence": 0.9, "click_type": "left", "grayscale": false}
    """
    image_path = params.get("image_path", "")
    confidence = float(params.get("confidence", 0.90))
    click_type = params.get("click_type", "left")
    grayscale = bool(params.get("grayscale", False))

    if not image_path:
        return ActionResult(False, "图像路径为空")

    logger.info(f"🖼 正在查找图像: {image_path} (置信度: {confidence})", step_name)

    location = image_finder.find_image_on_screen(image_path, confidence, grayscale)

    if location is None:
        return ActionResult(False, f"未找到匹配图像: {image_path}")

    logger.info(f"✅ 找到图像: {image_path} → 位置: {location}", step_name)
    logger.info(f"📍 点击图像中心: ({location[0] + location[2]//2}, {location[1] + location[3]//2}), 点击类型: {click_type}", step_name)
    success = image_finder.click_location(
        location[0],
        location[1],
        location[2],
        location[3],
        click_type=click_type,
    )

    if success:
        logger.info(f"✅ 图像点击成功 ({click_type})", step_name)
        return ActionResult(True, f"图像匹配点击成功: {image_path}")
    else:
        return ActionResult(False, "点击操作失败")


def execute_image_keyboard(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    图像匹配后按快捷键

    params: {"image_path": "", "confidence": 0.90, "keys": "ctrl+c", "press_interval_ms": 100}
    """
    image_path = params.get("image_path", "")
    confidence = float(params.get("confidence", 0.90))
    keys_str = params.get("keys", "")
    interval = params.get("press_interval_ms", 100) / 1000.0

    if not image_path:
        return ActionResult(False, "图像路径为空")

    logger.info(f"正在查找图像: {image_path} (置信度: {confidence})", step_name)
    location = image_finder.find_image_on_screen(image_path, confidence)

    if location is None:
        return ActionResult(False, f"未找到匹配图像: {image_path}")

    logger.info(f"找到图像，位置: {location}", step_name)

    # 如果配置了快捷键，则按下
    if keys_str:
        result = execute_keyboard_shortcut(params, logger, step_name)
        return ActionResult(result.success, f"图像匹配→快捷键: {image_path} → {keys_str}")
    else:
        logger.info("未配置快捷键，仅匹配图像", step_name)
        return ActionResult(True, f"图像匹配成功（无快捷键）: {image_path}")


def execute_image_relative_click(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    图像匹配后在相对坐标处点击

    params: {"image_path": "", "confidence": 0.9, "offset_x": 0, "offset_y": 0, "click_type": "left"}
    """
    image_path = params.get("image_path", "")
    confidence = float(params.get("confidence", 0.90))
    offset_x = int(params.get("offset_x", 0))
    offset_y = int(params.get("offset_y", 0))
    click_type = params.get("click_type", "left")

    if not image_path:
        return ActionResult(False, "图像路径为空")

    logger.info(f"正在查找锚点图像: {image_path}", step_name)

    location = image_finder.find_image_on_screen(image_path, confidence)

    if location is None:
        return ActionResult(False, f"未找到锚点图像: {image_path}")

    logger.info(f"找到锚点，偏移: ({offset_x}, {offset_y})", step_name)
    success = image_finder.click_location(
        location[0],
        location[1],
        location[2],
        location[3],
        offset_x=offset_x,
        offset_y=offset_y,
        click_type=click_type,
    )

    if success:
        logger.info(f"偏移点击成功 ({offset_x}, {offset_y})", step_name)
        return ActionResult(True, f"图像相对坐标点击成功")
    else:
        return ActionResult(False, "点击操作失败")


def execute_input_text(params: dict, logger: ExecutionLogger, step_name: str, loop_index: int = 1) -> ActionResult:
    """
    输入文本（支持多行固定文本逐行输入）

    params: {
        "text_type": "fixed" | "loop_index" | "clipboard",
        "text_value": "固定文本内容（多行用\\n分隔）",
        "loop_index_start": 1,
        "loop_index_step": 1,
    }

    多行模式说明：text_value 包含多行时，每次执行只输入第一行，
    然后从 text_value 中删除已输入的行。（支持按循环轮数逐行输入）
    """
    text_type = params.get("text_type", "fixed")

    if text_type == "clipboard":
        try:
            text = pyperclip.paste()
            logger.info(f"📋 从剪贴板获取内容: '{text[:80]}'", step_name)
            if not text:
                return ActionResult(False, "剪贴板为空")
        except Exception as e:
            return ActionResult(False, f"读取剪贴板失败: {e}")

    elif text_type == "loop_index":
        start = int(params.get("loop_index_start", 1))
        step = int(params.get("loop_index_step", 1))
        text = str(start + (loop_index - 1) * step)
        logger.info(f"🔢 输入循环索引值: {text} (第{loop_index}轮)", step_name)

    else:  # fixed — 支持多行逐行
        raw_text = params.get("text_value", "")

        # 保存原始完整文本（用于恢复跨循环状态）
        if "_saved_text_value" not in params:
            params["_saved_text_value"] = raw_text
        original_text = params["_saved_text_value"]

        if not original_text:
            return ActionResult(False, "文本内容为空")

        # 读取当前行索引，从 0 开始
        line_index = params.get("_text_line_index", 0)
        lines = original_text.split('\n')

        if line_index >= len(lines):
            # 所有行已输入完毕，重置
            line_index = 0
            params["_text_line_index"] = 0

        text = lines[line_index].strip()

        if not text:
            # 跳过空行，继续下一行
            params["_text_line_index"] = line_index + 1
            return ActionResult(False, f"第 {line_index + 1} 行为空，跳过")

        # 更新行索引到下一行
        params["_text_line_index"] = line_index + 1

        remaining_lines = len(lines) - (line_index + 1)
        if remaining_lines > 0:
            logger.info(f"📝 输入文本: '{text}'（第 {line_index + 1}/{len(lines)} 行，剩余 {remaining_lines} 行）", step_name)
        else:
            logger.info(f"📝 输入文本: '{text}'（第 {line_index + 1}/{len(lines)} 行，最后一行）", step_name)

    try:
        # pyautogui.write() 不支持中文，使用剪贴板 + Ctrl+V 方式
        pyperclip.copy(str(text))
        pyautogui.hotkey('ctrl', 'v')
        return ActionResult(True, f"文本输入成功: '{text}'")
    except Exception as e:
        return ActionResult(False, f"文本输入失败: {e}")


def execute_wait_for_image(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    等待图像出现

    params: {"image_path": "", "confidence": 0.85, "timeout_ms": 30000, "check_interval_ms": 500}
    """
    image_path = params.get("image_path", "")
    confidence = float(params.get("confidence", 0.85))
    timeout_ms = int(params.get("timeout_ms", 30000))
    check_interval_ms = int(params.get("check_interval_ms", 500))

    if not image_path:
        return ActionResult(False, "图像路径为空")

    logger.info(f"等待图像出现: {image_path} (超时: {timeout_ms}ms)", step_name)

    location = image_finder.wait_for_image(image_path, confidence, timeout_ms, check_interval_ms)

    if location is None:
        return ActionResult(False, f"等待超时，图像未出现: {image_path}")

    logger.info(f"图像已出现，位置: {location}", step_name)
    return ActionResult(True, f"图像出现: {image_path}")


def execute_ocr_click(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    OCR 文字识别点击

    params: {"text": "", "language": "chi_sim+eng", "confidence": 0.7, "click_offset_x": 0, "click_offset_y": 0}
    """
    text = params.get("text", "")
    language = params.get("language", "chi_sim+eng")
    confidence = float(params.get("confidence", 0.70))
    offset_x = int(params.get("click_offset_x", 0))
    offset_y = int(params.get("click_offset_y", 0))

    if not text:
        return ActionResult(False, "识别文字内容为空")

    logger.info(f"OCR 查找文字: '{text}'", step_name)

    matches = image_finder.find_text_on_screen(text, language, confidence)

    if not matches:
        return ActionResult(False, f"OCR 未找到匹配文字: '{text}'")

    # 取第一个匹配
    match = matches[0]
    logger.info(
        f"找到文字 '{match['text']}' 在 ({match['left']}, {match['top']}), " f"大小 {match['width']}x{match['height']}",
        step_name,
    )

    success = image_finder.click_location(
        match["left"],
        match["top"],
        match["width"],
        match["height"],
        offset_x=offset_x,
        offset_y=offset_y,
    )

    if success:
        logger.info(f"OCR 文字点击成功: '{match['text']}'", step_name)
        return ActionResult(True, f"OCR 点击成功: '{match['text']}'")
    else:
        return ActionResult(False, "OCR 点击操作失败")


def execute_wait(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    等待指定时间

    params: {"duration_ms": 2000}
    """
    duration_ms = int(params.get("duration_ms", 2000))
    logger.info(f"等待 {duration_ms}ms...", step_name)
    time.sleep(duration_ms / 1000.0)
    return ActionResult(True, f"等待完成 ({duration_ms}ms)")


def execute_condition(params: dict, logger: ExecutionLogger, step_name: str) -> ActionResult:
    """
    条件判断

    params: {
        "condition_type": "image_exists" | "image_not_exists",
        "image_path": "",
        "confidence": 0.90,
    }
    返回成功时表示"条件成立"，message 中包含 condition_met: True/False
    """
    condition_type = params.get("condition_type", "image_exists")
    image_path = params.get("image_path", "")
    confidence = float(params.get("confidence", 0.90))

    if not image_path:
        return ActionResult(False, "条件图像路径为空")

    location = image_finder.find_image_on_screen(image_path, confidence)

    if condition_type == "image_exists":
        condition_met = location is not None
        msg = f"图像{'存在' if condition_met else '不存在'}: {image_path}"
    else:  # image_not_exists
        condition_met = location is None
        msg = f"图像{'不存在' if condition_met else '存在'}: {image_path}"

    logger.info(msg, step_name)
    result = ActionResult(True, msg)
    result.condition_met = condition_met  # type: ignore
    return result
