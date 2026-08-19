"""截图工具：选择屏幕区域并保存为参考图像"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QGuiApplication,
    QFont,
    QPixmap,
    QImage,
)

import pyautogui

from utils.config import AppConfig


def _pil_to_qpixmap(pil_image) -> QPixmap:
    """PIL Image → QPixmap 转换"""
    img_bytes = pil_image.tobytes("raw", "RGB")
    qimg = QImage(img_bytes, pil_image.width, pil_image.height, pil_image.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


class ScreenshotRegionSelector(QWidget):
    """全屏截图选择器：冻结桌面为背景 + 半透明遮罩 + 拖拽选框

    支持多屏和系统缩放（DPI）。参考 Windows Win+Shift+S 实现：
    - 对每个屏幕分别截取背景，避免不同 DPI 屏幕间拉伸变形
    - 截图时使用选中屏幕的真实 DPR 做坐标转换
    """

    region_selected = Signal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        # 覆盖所有屏幕
        screen_rect = self._total_screen_rect()
        self.setGeometry(screen_rect)
        self.setCursor(Qt.CrossCursor)

        # 为每个屏幕分别截取背景（解决多屏不同 DPI 变形问题）
        self._screen_bg: dict = {}  # screen -> (pixmap, logical_rect)
        self._capture_per_screen()

        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._selected_rect = QRect()

    def _capture_per_screen(self):
        """对每个屏幕分别截取背景（grabWindow 自动处理 DPI 缩放）"""
        for screen in QGuiApplication.screens():
            geom = screen.geometry()
            try:
                pixmap = screen.grabWindow(0, 0, 0, geom.width(), geom.height())
            except Exception:
                continue
            self._screen_bg[screen] = (pixmap, QRect(geom.x(), geom.y(), geom.width(), geom.height()))

    def _capture_full_screen(self) -> QPixmap:
        """兼容旧接口：全屏截图"""
        try:
            img = pyautogui.screenshot()
            return _pil_to_qpixmap(img)
        except Exception:
            return QPixmap()

    def _total_screen_rect(self) -> QRect:
        total = QRect()
        for screen in QGuiApplication.screens():
            total = total.united(screen.geometry())
        return total

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        # 绘制每个屏幕的背景（各自独立缩放，避免多屏 DPI 不同导致变形）
        if self._screen_bg:
            for screen, (pixmap, logical_rect) in self._screen_bg.items():
                painter.drawPixmap(logical_rect, pixmap)
        elif not self._bg_pixmap.isNull() if hasattr(self, '_bg_pixmap') else False:
            painter.drawPixmap(rect, self._bg_pixmap, rect)

        # 半透明黑色遮罩
        painter.fillRect(rect, QColor(0, 0, 0, 120))

        if self._selecting or self._selected_rect.isValid():
            sel_rect = QRect(self._start, self._end).normalized() if self._selecting else self._selected_rect

            # 在遮罩上挖出选中区域的清晰背景
            if self._screen_bg:
                # 按屏幕分别绘制选中区域内的背景
                for screen, (pixmap, logical_rect) in self._screen_bg.items():
                    intersect = logical_rect.intersected(sel_rect)
                    if intersect.isValid():
                        src_x = intersect.x() - logical_rect.x()
                        src_y = intersect.y() - logical_rect.y()
                        src_w = intersect.width()
                        src_h = intersect.height()
                        painter.drawPixmap(intersect, pixmap,
                                           QRect(src_x, src_y, src_w, src_h))
            else:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(sel_rect, Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor("#4CAF50"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            painter.setFont(QFont("Consolas", 11))
            painter.setPen(QColor("#ffffff"))
            info = f"({sel_rect.x()}, {sel_rect.y()})  {sel_rect.width()}×{sel_rect.height()}"
            painter.drawText(10, 24, info)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.globalPosition().toPoint()
            self._end = self._start
            self._selecting = True
            self._selected_rect = QRect()
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._end = event.globalPosition().toPoint()
            self._selected_rect = QRect(self._start, self._end).normalized()
            self.update()
            QTimer.singleShot(200, self._finish_selection)

    def _finish_selection(self):
        if self._selected_rect.isValid() and self._selected_rect.width() > 5 and self._selected_rect.height() > 5:
            self.hide()
            QTimer.singleShot(
                150,
                lambda: (
                    self.region_selected.emit(self._selected_rect),
                    self.close(),
                ),
            )
        else:
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class ScreenshotTool(QWidget):
    """截图工具主控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("截图工具")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(300, 150)

        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            ScreenshotTool {
                background: #2a2a2a;
                border: 2px solid #FF9800;
                border-radius: 8px;
            }
            ScreenshotTool QLabel {
                color: #ffffff;
            }
            ScreenshotTool QPushButton {
                background: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            ScreenshotTool QPushButton:hover {
                background: #FFB74D;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel("📷 截图捕获工具")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("点击按钮后拖拽选择屏幕区域，\n截图将保存为参考图像")
        desc.setStyleSheet("color: #ccc; font-size: 11px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        self.btn_capture = QPushButton("🎯 开始截图")
        self.btn_capture.clicked.connect(self._start_capture)
        layout.addWidget(self.btn_capture)

        self.btn_close = QPushButton("关闭")
        self.btn_close.setStyleSheet("background: #555; color: white; border: none; border-radius: 4px; padding: 6px;")
        self.btn_close.clicked.connect(self.hide)
        layout.addWidget(self.btn_close)

    def _start_capture(self):
        self.hide()
        QTimer.singleShot(300, self._show_selector)

    def _show_selector(self):
        self.selector = ScreenshotRegionSelector()
        self.selector.region_selected.connect(self._on_region_selected)
        self.selector.show()

    def _on_region_selected(self, rect: QRect):
        """处理选择的区域 — 使用选中屏幕的真实 DPR 做坐标转换

        参考 Win+Shift+S：先全屏截图再用物理像素裁剪，避免多屏不同 DPI 时坐标错位。
        """
        try:
            # 找到选中区域中心所在的屏幕，获取其真实 DPR
            screen = QGuiApplication.screenAt(rect.center())
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            dpr = screen.devicePixelRatio()

            # 逻辑坐标 → 物理像素坐标
            px = int(rect.x() * dpr)
            py = int(rect.y() * dpr)
            pw = int(rect.width() * dpr)
            ph = int(rect.height() * dpr)

            # 全屏截图后裁剪（比 region 参数更可靠，避免多屏坐标偏移）
            full_img = pyautogui.screenshot()

            # 边界保护
            px = max(0, min(px, full_img.width - 1))
            py = max(0, min(py, full_img.height - 1))
            pw = min(pw, full_img.width - px)
            ph = min(ph, full_img.height - py)

            if pw <= 0 or ph <= 0:
                raise ValueError("截图区域无效")

            img = full_img.crop((px, py, px + pw, py + ph))

            images_dir = AppConfig.get_images_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(images_dir / f"screenshot_{timestamp}.png")
            img.save(filepath, "PNG")

            QMessageBox.information(
                None, "截图成功",
                f"截图已保存到:\n{filepath}\n\n"
                f"逻辑尺寸: {rect.width()}×{rect.height()}\n"
                f"物理像素: {img.width}×{img.height}",
            )
        except Exception as e:
            QMessageBox.warning(None, "截图失败", f"截图失败: {e}")
        finally:
            self.show()
