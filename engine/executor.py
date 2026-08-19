"""执行引擎：主循环、步骤调度、异常处理"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker, QWaitCondition

from models.project import Project
from models.step import Step, StepType, VerifyMode, VerifyType
from engine import actions
from engine.logger import ExecutionLogger
from engine import image_finder


class ExecutorThread(QThread):
    """在后台线程中执行自动化项目"""

    # 信号：发送到主线程更新 UI
    log_signal = Signal(dict)  # 日志条目
    progress_signal = Signal(int, int, str)  # 当前步骤索引, 总步骤数, 步骤名
    loop_count_signal = Signal(int)  # 当前循环轮数
    finished_signal = Signal(bool, str)  # 执行完成 (成功?, 消息)
    stopped_signal = Signal()  # 用户手动停止
    step_result_signal = Signal(int, bool, str)  # 步骤执行结果 (index, 成功?, 消息)
    loop_confirm_signal = Signal(int)  # 手动循环确认请求 (当前轮数)

    def __init__(self, project: Project, start_index: int = 0, single_step: bool = False):
        super().__init__()
        self.project = project
        self.start_index = start_index
        self.single_step = single_step
        self._stop_requested = False
        self._mutex = QMutex()
        self._wait_mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self.logger: ExecutionLogger | None = None

    def stop(self):
        """请求停止执行（也会唤醒手动循环等待）"""
        with QMutexLocker(self._mutex):
            self._stop_requested = True
        # 唤醒可能的 wait 阻塞
        with QMutexLocker(self._wait_mutex):
            self._wait_condition.wakeAll()

    def confirm_next_loop(self):
        """用户确认继续下一轮循环（手动模式）"""
        with QMutexLocker(self._wait_mutex):
            self._wait_condition.wakeAll()

    def is_stop_requested(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._stop_requested

    def run(self):
        """主执行循环（在后台线程中运行）

        项目级循环：如果 settings.loop_count > 1，则整体重复执行步骤1→N。
        """
        self.logger = ExecutionLogger(self.project.name)
        # 将日志回调绑定到日志转发，使 actions.py 中的 logger.info/error 等
        # 也能实时转发到运行页面的日志显示（通过 emit_log_signal 避免循环）
        self.logger.set_log_callback(self._log_forward_to_signal)
        settings = self.project.settings

        # 设置 pyautogui 参数
        import pyautogui

        pyautogui.PAUSE = 0.1 / settings.global_speed_multiplier
        pyautogui.FAILSAFE = True

        # 获取要执行的步骤列表
        all_steps = [s for s in self.project.steps if s.enabled]
        if self.single_step and self.start_index < len(all_steps):
            steps_to_run = [all_steps[self.start_index]]
            self.start_index = 0
        else:
            steps_to_run = all_steps[self.start_index :]

        if not steps_to_run:
            self._emit_log("WARNING", "没有可执行的步骤")
            self.finished_signal.emit(False, "没有可执行的步骤")
            return

        total_steps = len(steps_to_run)
        loop_count = settings.loop_count if not self.single_step else 1

        self._emit_log("INFO", f"开始执行项目: {self.project.name}")
        self._emit_log("INFO", f"总步骤: {total_steps} (从第 {self.start_index + 1} 步开始)")
        self._emit_log("INFO", f"项目循环次数: {loop_count}")
        self._emit_log("INFO", f"速度倍率: {settings.global_speed_multiplier}x")
        if settings.manual_loop_confirm and loop_count > 1 and not self.single_step:
            self._emit_log("INFO", "🔔 手动确认循环模式已启用——每轮完成后等待确认")

        # === 项目级循环 ===
        for loop_iteration in range(1, loop_count + 1):
            if self.is_stop_requested():
                self._emit_log("WARNING", "用户手动停止执行")
                self.stopped_signal.emit()
                return

            if loop_count > 1:
                self.loop_count_signal.emit(loop_iteration)
                self._emit_log("INFO", f"========== 项目循环 第 {loop_iteration}/{loop_count} 轮 ==========")

            # === 步骤序列执行 ===
            for i, step in enumerate(steps_to_run):
                if self.is_stop_requested():
                    self._emit_log("WARNING", "用户手动停止执行")
                    self.stopped_signal.emit()
                    return

                actual_index = self.start_index + i
                step_repeat_count = step.repeat_count if not self.single_step else 1

                # === 步骤级循环 ===
                for step_repeat in range(1, step_repeat_count + 1):
                    if self.is_stop_requested():
                        self._emit_log("WARNING", "用户手动停止执行")
                        self.stopped_signal.emit()
                        return

                    if step_repeat_count > 1:
                        self._emit_log("INFO", f"--- 步骤「{step.name}」第 {step_repeat}/{step_repeat_count} 次 ---")

                    self.progress_signal.emit(actual_index, total_steps, step.name)

                    # 执行前等待
                    wait_before = step.wait_before_ms / (1000.0 * settings.global_speed_multiplier)
                    if wait_before > 0:
                        self._emit_log("DEBUG", f"执行前等待 {wait_before:.2f}s", step.name)
                        self._sleep(wait_before)

                    # 执行步骤（传入项目级循环轮数）
                    result = self._execute_step(step, loop_iteration)

                    # 发送步骤结果
                    self.step_result_signal.emit(actual_index, result.success, result.message)

                    # 执行后等待
                    wait_after = step.wait_after_ms / (1000.0 * settings.global_speed_multiplier)
                    if wait_after > 0 and not self.is_stop_requested():
                        self._sleep(wait_after)

                    # 失败处理
                    if not result.success:
                        if step.on_failure.log_error:
                            self._emit_log("ERROR", f"步骤失败: {result.message}", step.name)

                        if step.on_failure.screenshot or settings.screenshot_on_failure:
                            screenshot_path = self.logger.screenshot_path(step.name)
                            if image_finder.take_screenshot(screenshot_path):
                                self._emit_log("INFO", f"失败截图已保存: {screenshot_path}", step.name)
                                result.screenshot_path = screenshot_path

                        # 步骤级重试
                        if step.on_failure.retry_count > 0:
                            for retry in range(step.on_failure.retry_count):
                                if self.is_stop_requested():
                                    break
                                self._emit_log("INFO", f"重试 {retry + 1}/{step.on_failure.retry_count}...", step.name)
                                self._sleep(step.on_failure.retry_interval_ms / 1000.0)
                                retry_result = self._execute_step(step, loop_iteration)
                                if retry_result.success:
                                    self._emit_log("INFO", f"重试成功", step.name)
                                    result = retry_result
                                    break

                        if not result.success and settings.stop_on_failure:
                            self._emit_log("ERROR", "执行因失败而停止", step.name)
                            self.finished_signal.emit(False, f"步骤失败: {step.name} - {result.message}")
                            return

                    # === 验证阶段（步骤级循环每次重复后执行） ===
                    vc = step.verify_config
                    if vc and vc.enabled:
                        verify_passed = self._execute_verify(step, vc)
                        if not verify_passed:
                            if settings.stop_on_failure:
                                self._emit_log("ERROR", f"验证未通过，执行停止", step.name)
                                self.finished_signal.emit(False, f"步骤验证失败: {step.name}")
                                return

            # === 本轮循环完成，检查是否需要手动确认 ===
            is_last_loop = loop_iteration >= loop_count
            if not is_last_loop and settings.manual_loop_confirm and not self.single_step:
                self._emit_log("INFO", f"🔔 第 {loop_iteration}/{loop_count} 轮完成，等待用户确认继续...")
                self._emit_log("INFO", "请在监控窗口点击「▶ 继续下一轮循环」按钮")
                self.loop_confirm_signal.emit(loop_iteration)

                # 等待用户确认或停止
                with QMutexLocker(self._wait_mutex):
                    if not self.is_stop_requested():
                        self._wait_condition.wait(self._wait_mutex)

                if self.is_stop_requested():
                    self._emit_log("WARNING", "用户手动停止执行")
                    self.stopped_signal.emit()
                    return
                self._emit_log("INFO", f"✅ 用户确认，开始第 {loop_iteration + 1}/{loop_count} 轮")

        self._emit_log("INFO", "项目执行完成 ✅")
        self.finished_signal.emit(True, "执行完成")

    def _execute_verify(self, step: Step, vc) -> bool:
        """执行步骤验证，返回是否通过"""
        check_interval = 0.5
        timeout_sec = vc.timeout_ms / 1000.0 if vc.verify_mode == VerifyMode.TIMED else None
        start_time = time.time()

        self._emit_log("INFO", f"🔍 开始验证（{VerifyMode.display_name(vc.verify_mode)}）...", step.name)

        while True:
            if self.is_stop_requested():
                self._emit_log("WARNING", "验证阶段用户手动停止", step.name)
                return False

            verify_result = self._run_verify_check(vc, step.name)

            if verify_result.success:
                self._emit_log("INFO", f"✅ 验证通过", step.name)
                return True

            if vc.verify_mode == VerifyMode.TIMED:
                elapsed = time.time() - start_time
                if elapsed >= timeout_sec:
                    self._emit_log("ERROR", f"❌ 验证超时（{vc.timeout_ms}ms）- {verify_result.message}", step.name)
                    return False
                self._emit_log("DEBUG", f"验证等待中 ({elapsed:.0f}s / {vc.timeout_ms/1000:.0f}s)...", step.name)
            else:
                self._emit_log("DEBUG", f"验证等待中...（按停止键取消）", step.name)

            self._sleep(check_interval)

    def _run_verify_check(self, vc, step_name: str) -> actions.ActionResult:
        """运行一次验证检查"""
        if vc.verify_type == VerifyType.IMAGE_MATCH:
            return actions.execute_verify_image_match(vc, self.logger, step_name)
        else:
            return actions.ActionResult(False, f"未知验证类型: {vc.verify_type}")

    def _execute_step(self, step: Step, loop_index: int) -> actions.ActionResult:
        """执行单个步骤（不处理循环）"""
        step_type = step.type
        params = step.params

        try:
            if step_type == StepType.KEYBOARD_SHORTCUT:
                return actions.execute_keyboard_shortcut(params, self.logger, step.name)
            elif step_type == StepType.IMAGE_CLICK:
                return actions.execute_image_click(params, self.logger, step.name)
            elif step_type == StepType.IMAGE_RELATIVE_CLICK:
                return actions.execute_image_relative_click(params, self.logger, step.name)
            elif step_type == StepType.IMAGE_KEYBOARD:
                return actions.execute_image_keyboard(params, self.logger, step.name)
            elif step_type == StepType.INPUT_TEXT:
                return actions.execute_input_text(params, self.logger, step.name, loop_index)
            elif step_type == StepType.WAIT_FOR_IMAGE:
                return actions.execute_wait_for_image(params, self.logger, step.name)
            elif step_type == StepType.OCR_CLICK:
                return actions.execute_ocr_click(params, self.logger, step.name)
            elif step_type == StepType.WAIT:
                return actions.execute_wait(params, self.logger, step.name)
            elif step_type == StepType.CONDITION:
                return actions.execute_condition(params, self.logger, step.name)
            else:
                return actions.ActionResult(False, f"未知步骤类型: {step_type}")
        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            self._emit_log("ERROR", f"步骤执行异常:\n{tb}", step.name)
            return actions.ActionResult(False, f"执行异常: {e}")

    def _sleep(self, seconds: float):
        """分段等待（支持快速响应停止请求）"""
        if seconds <= 0:
            return
        interval = 0.1  # 每 100ms 检查一次停止请求
        elapsed = 0.0
        while elapsed < seconds:
            if self.is_stop_requested():
                return
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval

    def _log_forward_to_signal(self, entry: dict):
        """日志回调：仅转发到 monitor 信号（不做文件写入，避免循环）"""
        self.log_signal.emit(entry)

    def _emit_log(self, level: str, message: str, step_name: str = ""):
        """写文件日志（logger.log 会通过回调自动发 monitor 信号，所以这里不再重复 emit）"""
        if self.logger:
            self.logger.log(level, message, step_name)
