"""오버레이 창 모듈"""
import sys
import numpy as np
import cv2
from typing import Optional, List, Tuple

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QImage,
    QPixmap,
    QPolygon,
    QBrush,
)

from .color_detector import ColorDetector, hex_to_rgb
from .capture import screen_capture
from .config import config


class OverlayWindow(QWidget):
    """투명 오버레이 창"""

    # 시그널 정의
    color_detected = pyqtSignal(list)  # 검출된 색상 위치들
    region_changed = pyqtSignal(int, int, int, int)  # x, y, w, h

    def __init__(self, parent=None):
        super().__init__(parent)

        # 윈도우 설정
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 상태 변수
        self.is_running = False
        self.capture_region = QRect(100, 100, 400, 300)
        self.result_image: Optional[np.ndarray] = None
        self.detected_positions: List[Tuple[int, int]] = []

        # 3색 가이드라인 (삼각형)
        self.triangle_points: List[Tuple[int, int]] = []
        self.triangle_enabled = False

        # 색상 검출기
        self.detector = ColorDetector()

        # 표시 설정
        self.show_grayscale = True
        self.grayscale_brightness = 50
        self.indicator_size = 10

        # 타이머 (실시간 캡처)
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self._capture_and_detect)

        # 점멸 효과
        self.blink_visible = True
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._toggle_blink)

        # 설정 불러오기
        self._load_settings()

    def _toggle_blink(self):
        """점멸 토글"""
        self.blink_visible = not self.blink_visible
        self.update()

    def _load_settings(self):
        """설정 불러오기"""
        overlay_config = config.get("overlay", default={})
        self.capture_region = QRect(
            overlay_config.get("x", 100),
            overlay_config.get("y", 100),
            overlay_config.get("width", 400),
            overlay_config.get("height", 300),
        )

        display_config = config.get("display", default={})
        self.grayscale_brightness = display_config.get("grayscale_brightness", 50)
        self.indicator_size = display_config.get("indicator_size", 10)
        self.show_grayscale = display_config.get("show_grayscale", True)

        triangle_config = config.get("triangle", default={})
        points = triangle_config.get("points", [])
        self.triangle_points = [tuple(p) for p in points if len(p) == 2]
        self.triangle_enabled = triangle_config.get("enabled", False)

        colors = config.get("colors", default=[])
        self.detector.set_target_colors(colors)

    def _save_settings(self):
        """설정 저장"""
        config.set(
            "overlay",
            value={
                "x": self.capture_region.x(),
                "y": self.capture_region.y(),
                "width": self.capture_region.width(),
                "height": self.capture_region.height(),
            },
        )
        config.set(
            "triangle",
            value={
                "points": list(self.triangle_points),
                "enabled": self.triangle_enabled,
            },
        )

    def start(self):
        """캡처 시작"""
        if self.is_running:
            return

        # 마비노기 윈도우 찾기
        hwnd = screen_capture.find_mabinogi_window()
        if hwnd is None:
            print("마비노기 모바일 창을 찾을 수 없습니다.")
            return

        self.is_running = True
        self.show()
        self.capture_timer.start(33)  # ~30 FPS
        self.blink_timer.start(500)  # 점멸 효과 0.5초

    def stop(self):
        """캡처 중지"""
        self.is_running = False
        self.capture_timer.stop()
        self.blink_timer.stop()
        self.result_image = None
        self.detected_positions = []
        self.hide()
        self._save_settings()

    def set_colors(self, colors: List[dict]):
        """검출할 색상 설정"""
        self.detector.set_target_colors(colors)
        config.set("colors", value=colors)

    def set_region(self, x: int, y: int, width: int, height: int):
        """캡처 영역 설정"""
        self.capture_region = QRect(x, y, width, height)
        self.region_changed.emit(x, y, width, height)
        self._save_settings()

    def set_triangle_point(self, index: int, x: int, y: int):
        """삼각형 꼭지점 설정 (index: 0, 1, 2)"""
        while len(self.triangle_points) <= index:
            self.triangle_points.append((0, 0))
        self.triangle_points[index] = (x, y)

        if len(self.triangle_points) >= 3:
            self.triangle_enabled = True

        self._save_settings()

    def reset_triangle(self):
        """삼각형 초기화"""
        self.triangle_points = []
        self.triangle_enabled = False
        self._save_settings()

    def _capture_and_detect(self):
        """화면 캡처 및 색상 검출"""
        if not self.is_running:
            return

        # 영역 캡처
        image = screen_capture.capture_region(
            self.capture_region.x(),
            self.capture_region.y(),
            self.capture_region.width(),
            self.capture_region.height(),
        )

        if image is None:
            return

        # 색상 검출
        if self.show_grayscale:
            result, mask, positions = self.detector.detect_colors(
                image, return_mask=True
            )
            # 밝기 조절
            result = self.detector.apply_brightness(result, self.grayscale_brightness)
            self.result_image = result
        else:
            _, _, positions = self.detector.detect_colors(image, return_mask=False)
            self.result_image = image

        self.detected_positions = positions

        if positions:
            self.color_detected.emit(positions)

        # 화면 갱신
        self.update()

    def paintEvent(self, event):
        """오버레이 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 윈도우 정보 가져오기
        win_info = screen_capture.get_window_info()
        if win_info is None:
            return

        win_x = win_info["x"]
        win_y = win_info["y"]

        # 캡처 영역 테두리 (빨간색)
        border_rect = QRect(
            win_x + self.capture_region.x(),
            win_y + self.capture_region.y(),
            self.capture_region.width(),
            self.capture_region.height(),
        )

        # 결과 이미지 그리기
        if self.result_image is not None and self.show_grayscale:
            h, w = self.result_image.shape[:2]
            bytes_per_line = 3 * w
            q_image = QImage(
                self.result_image.data,
                w,
                h,
                bytes_per_line,
                QImage.Format_BGR888,
            )
            pixmap = QPixmap.fromImage(q_image)
            painter.drawPixmap(border_rect.topLeft(), pixmap)

        # 캡처 영역 테두리
        pen = QPen(QColor(255, 0, 0), 2)
        painter.setPen(pen)
        painter.drawRect(border_rect)

        # 검출된 위치 표시 (점멸 효과 적용)
        if self.blink_visible:
            for pos_x, pos_y in self.detected_positions:
                abs_x = win_x + self.capture_region.x() + pos_x
                abs_y = win_y + self.capture_region.y() + pos_y

                # 원형 표시
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.setBrush(QBrush(QColor(0, 255, 0, 100)))
                painter.drawEllipse(
                    QPoint(abs_x, abs_y),
                    self.indicator_size,
                    self.indicator_size,
                )

        # 3색 가이드라인 (삼각형) 그리기
        if self.triangle_enabled and len(self.triangle_points) >= 3:
            self._draw_triangle_guide(painter)

    def _draw_triangle_guide(self, painter: QPainter):
        """삼각형 가이드라인 그리기"""
        # 삼각형 꼭지점 (절대 좌표)
        points = []
        for px, py in self.triangle_points[:3]:
            points.append(QPoint(px, py))

        # 삼각형 그리기
        pen = QPen(QColor(255, 255, 0), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 0, 30)))

        polygon = QPolygon(points)
        painter.drawPolygon(polygon)

        # 꼭지점 표시
        for i, point in enumerate(points):
            # 꼭지점 원
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setBrush(QBrush(QColor(255, 255, 0, 150)))
            painter.drawEllipse(point, 8, 8)

            # 번호 표시
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(point.x() - 4, point.y() + 4, str(i + 4))

        # 수직 가이드라인 그리기
        screen_height = QApplication.primaryScreen().geometry().height()
        pen = QPen(QColor(255, 255, 0, 100), 1, Qt.DotLine)
        painter.setPen(pen)

        for point in points:
            painter.drawLine(point.x(), 0, point.x(), screen_height)

    def resizeEvent(self, event):
        """창 크기 변경 시 전체 화면으로"""
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)


class RegionSelector(QWidget):
    """영역 선택 위젯"""

    region_selected = pyqtSignal(int, int, int, int)

    def __init__(self, initial_rect: QRect = None, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.region = initial_rect or QRect(100, 100, 400, 300)
        self.dragging = False
        self.resizing = False
        self.drag_start = QPoint()
        self.resize_start = QPoint()
        self.resize_corner = ""

        self.setMouseTracking(True)

    def set_region(self, rect: QRect):
        """영역 설정"""
        self.region = rect
        self.update()

    def paintEvent(self, event):
        """영역 테두리 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 빨간색 테두리
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 0, 0, 30)))
        painter.drawRect(self.region)

        # 모서리 핸들
        handle_size = 10
        corners = [
            (self.region.topLeft(), "tl"),
            (self.region.topRight(), "tr"),
            (self.region.bottomLeft(), "bl"),
            (self.region.bottomRight(), "br"),
        ]

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for corner, _ in corners:
            painter.drawRect(
                corner.x() - handle_size // 2,
                corner.y() - handle_size // 2,
                handle_size,
                handle_size,
            )

    def mousePressEvent(self, event):
        """마우스 클릭"""
        if event.button() == Qt.LeftButton:
            # 크기 조절 핸들 체크
            corner = self._get_corner_at(event.pos())
            if corner:
                self.resizing = True
                self.resize_corner = corner
                self.resize_start = event.pos()
            elif self.region.contains(event.pos()):
                self.dragging = True
                self.drag_start = event.pos() - self.region.topLeft()
        elif event.button() == Qt.RightButton:
            # 우클릭: 이동
            if self.region.contains(event.pos()):
                self.dragging = True
                self.drag_start = event.pos() - self.region.topLeft()

    def mouseMoveEvent(self, event):
        """마우스 이동"""
        if self.dragging:
            new_pos = event.pos() - self.drag_start
            self.region.moveTo(new_pos)
            self.update()
        elif self.resizing:
            self._resize_region(event.pos())
            self.update()
        else:
            # 커서 모양 변경
            corner = self._get_corner_at(event.pos())
            if corner in ["tl", "br"]:
                self.setCursor(Qt.SizeFDiagCursor)
            elif corner in ["tr", "bl"]:
                self.setCursor(Qt.SizeBDiagCursor)
            elif self.region.contains(event.pos()):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """마우스 릴리즈"""
        if self.dragging or self.resizing:
            self.dragging = False
            self.resizing = False
            self.region_selected.emit(
                self.region.x(),
                self.region.y(),
                self.region.width(),
                self.region.height(),
            )

    def _get_corner_at(self, pos: QPoint) -> str:
        """마우스 위치의 모서리 반환"""
        handle_size = 15
        corners = {
            "tl": self.region.topLeft(),
            "tr": self.region.topRight(),
            "bl": self.region.bottomLeft(),
            "br": self.region.bottomRight(),
        }

        for name, corner in corners.items():
            if (
                abs(pos.x() - corner.x()) < handle_size
                and abs(pos.y() - corner.y()) < handle_size
            ):
                return name
        return ""

    def _resize_region(self, pos: QPoint):
        """영역 크기 조절"""
        if self.resize_corner == "br":
            self.region.setBottomRight(pos)
        elif self.resize_corner == "bl":
            self.region.setBottomLeft(pos)
        elif self.resize_corner == "tr":
            self.region.setTopRight(pos)
        elif self.resize_corner == "tl":
            self.region.setTopLeft(pos)

        # 최소 크기 보장
        if self.region.width() < 50:
            self.region.setWidth(50)
        if self.region.height() < 50:
            self.region.setHeight(50)
