"""메인 윈도우 UI 모듈"""
import sys
from typing import List
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSlider,
    QCheckBox,
    QGroupBox,
    QColorDialog,
    QSpinBox,
    QFrame,
    QMessageBox,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon

from .overlay import OverlayWindow, RegionSelector
from .hotkeys import hotkey_manager, HotkeyManager
from .capture import screen_capture
from .config import config


class ColorWidget(QFrame):
    """색상 선택 위젯"""

    def __init__(self, index: int, color_info: dict, parent=None):
        super().__init__(parent)
        self.index = index
        self.color_info = color_info

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._setup_ui()
        self._update_color_display()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 활성화 체크박스
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(self.color_info.get("enabled", True))
        self.enabled_check.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_check)

        # 색상 라벨
        self.color_label = QLabel(f"색상 {self.index + 1}")
        layout.addWidget(self.color_label)

        # 색상 미리보기
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setFrameStyle(QFrame.Box)
        layout.addWidget(self.color_preview)

        # HEX 입력
        self.hex_input = QLineEdit(self.color_info.get("hex", "#FFFFFF"))
        self.hex_input.setMaximumWidth(80)
        self.hex_input.textChanged.connect(self._on_hex_changed)
        layout.addWidget(self.hex_input)

        # 색상 선택 버튼
        self.pick_btn = QPushButton("선택")
        self.pick_btn.setMaximumWidth(50)
        self.pick_btn.clicked.connect(self._pick_color)
        layout.addWidget(self.pick_btn)

        # 오차 슬라이더
        layout.addWidget(QLabel("오차:"))
        self.tolerance_slider = QSlider(Qt.Horizontal)
        self.tolerance_slider.setMinimum(0)
        self.tolerance_slider.setMaximum(100)
        self.tolerance_slider.setValue(self.color_info.get("tolerance", 30))
        self.tolerance_slider.setMaximumWidth(100)
        self.tolerance_slider.valueChanged.connect(self._on_tolerance_changed)
        layout.addWidget(self.tolerance_slider)

        self.tolerance_label = QLabel(f"{self.tolerance_slider.value()}")
        self.tolerance_label.setMinimumWidth(25)
        layout.addWidget(self.tolerance_label)

    def _update_color_display(self):
        """색상 미리보기 업데이트"""
        hex_color = self.color_info.get("hex", "#FFFFFF")
        self.color_preview.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid black;"
        )

    def _on_hex_changed(self, text: str):
        """HEX 입력 변경"""
        if len(text) == 7 and text.startswith("#"):
            try:
                # 유효한 HEX 색상인지 확인
                int(text[1:], 16)
                self.color_info["hex"] = text.upper()
                self._update_color_display()
            except ValueError:
                pass

    def _on_tolerance_changed(self, value: int):
        """오차 변경"""
        self.color_info["tolerance"] = value
        self.tolerance_label.setText(str(value))

    def _on_enabled_changed(self, state: int):
        """활성화 상태 변경"""
        self.color_info["enabled"] = state == Qt.Checked

    def _pick_color(self):
        """색상 선택 다이얼로그"""
        current_color = QColor(self.color_info.get("hex", "#FFFFFF"))
        color = QColorDialog.getColor(current_color, self, "색상 선택")
        if color.isValid():
            hex_color = color.name().upper()
            self.color_info["hex"] = hex_color
            self.hex_input.setText(hex_color)
            self._update_color_display()

    def get_color_info(self) -> dict:
        """색상 정보 반환"""
        return self.color_info.copy()


class MainWindow(QMainWindow):
    """메인 설정 창"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("마비노기 모바일 염색 도우미")
        self.setMinimumSize(500, 600)

        # 컴포넌트 초기화
        self.overlay: OverlayWindow = None
        self.region_selector: RegionSelector = None
        self.color_widgets: List[ColorWidget] = []

        # UI 설정
        self._setup_ui()
        self._connect_signals()
        self._load_settings()

        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)

    def _setup_ui(self):
        """UI 구성"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 상태 표시
        self._create_status_group(layout)

        # 색상 설정
        self._create_color_group(layout)

        # 표시 설정
        self._create_display_group(layout)

        # 단축키 안내
        self._create_hotkey_group(layout)

        # 제어 버튼
        self._create_control_group(layout)

        layout.addStretch()

    def _create_status_group(self, parent_layout):
        """상태 표시 그룹"""
        group = QGroupBox("상태")
        layout = QVBoxLayout(group)

        # 게임 창 상태
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("마비노기 모바일:"))
        self.game_status_label = QLabel("찾는 중...")
        self.game_status_label.setStyleSheet("color: orange;")
        status_layout.addWidget(self.game_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # 캡처 상태
        capture_layout = QHBoxLayout()
        capture_layout.addWidget(QLabel("캡처 상태:"))
        self.capture_status_label = QLabel("중지")
        self.capture_status_label.setStyleSheet("color: gray;")
        capture_layout.addWidget(self.capture_status_label)
        capture_layout.addStretch()
        layout.addLayout(capture_layout)

        parent_layout.addWidget(group)

    def _create_color_group(self, parent_layout):
        """색상 설정 그룹"""
        group = QGroupBox("색상 설정")
        layout = QVBoxLayout(group)

        # 색상 위젯들 - 기본 3개 색상
        colors = config.get("colors", default=[])
        if not colors or len(colors) < 3:
            colors = [
                {"hex": "#FF0000", "tolerance": 30, "enabled": True},
                {"hex": "#00FF00", "tolerance": 30, "enabled": True},
                {"hex": "#0000FF", "tolerance": 30, "enabled": True},
            ]

        for i, color_info in enumerate(colors[:3]):  # 최대 3개
            widget = ColorWidget(i, color_info)
            self.color_widgets.append(widget)
            layout.addWidget(widget)

        parent_layout.addWidget(group)

    def _create_display_group(self, parent_layout):
        """표시 설정 그룹"""
        group = QGroupBox("표시 설정")
        layout = QVBoxLayout(group)

        # 흑백 처리 옵션
        self.grayscale_check = QCheckBox("흑백 처리 (검출 색상만 컬러)")
        self.grayscale_check.setChecked(config.get("display", "show_grayscale", default=True))
        layout.addWidget(self.grayscale_check)

        # 밝기 조절
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("흑백 밝기:"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(
            config.get("display", "grayscale_brightness", default=50)
        )
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_label = QLabel(f"{self.brightness_slider.value()}")
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_label.setText(str(v))
        )
        brightness_layout.addWidget(self.brightness_label)
        layout.addLayout(brightness_layout)

        # 표시 크기
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("표시 크기:"))
        self.indicator_size_spin = QSpinBox()
        self.indicator_size_spin.setMinimum(5)
        self.indicator_size_spin.setMaximum(50)
        self.indicator_size_spin.setValue(
            config.get("display", "indicator_size", default=10)
        )
        size_layout.addWidget(self.indicator_size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        parent_layout.addWidget(group)

    def _create_hotkey_group(self, parent_layout):
        """단축키 안내 그룹"""
        group = QGroupBox("단축키")
        layout = QVBoxLayout(group)

        hotkeys = [
            ("CTRL + 1,2,3", "커서 좌표 저장"),
            ("ALT + 1,2,3", "저장된 좌표로 이동"),
            ("CTRL + 4,5,6", "삼각형 꼭지점 저장"),
            ("CTRL + 7", "삼각형 초기화"),
            ("CTRL + 8", "캡처 시작/중지"),
            ("CTRL + 방향키", "커서 픽셀 단위 이동"),
        ]

        for key, desc in hotkeys:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet("font-weight: bold; color: #0066cc;")
            key_label.setMinimumWidth(120)
            row.addWidget(key_label)
            row.addWidget(QLabel(desc))
            row.addStretch()
            layout.addLayout(row)

        parent_layout.addWidget(group)

    def _create_control_group(self, parent_layout):
        """제어 버튼 그룹"""
        group = QGroupBox("제어")
        layout = QVBoxLayout(group)

        # 영역 설정 버튼
        region_layout = QHBoxLayout()
        self.region_btn = QPushButton("영역 설정")
        self.region_btn.clicked.connect(self._toggle_region_selector)
        region_layout.addWidget(self.region_btn)

        self.region_label = QLabel("영역: 미설정")
        region_layout.addWidget(self.region_label)
        region_layout.addStretch()
        layout.addLayout(region_layout)

        # 시작/중지 버튼
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("시작")
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.start_btn.clicked.connect(self._start_capture)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        self.stop_btn.clicked.connect(self._stop_capture)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # 삼각형 초기화 버튼
        self.reset_triangle_btn = QPushButton("삼각형 초기화 (CTRL+7)")
        self.reset_triangle_btn.clicked.connect(self._reset_triangle)
        layout.addWidget(self.reset_triangle_btn)

        parent_layout.addWidget(group)

    def _connect_signals(self):
        """시그널 연결"""
        # 단축키 매니저 시그널
        hotkey_manager.save_position.connect(self._on_position_saved)
        hotkey_manager.move_to_position.connect(self._on_position_moved)
        hotkey_manager.save_triangle.connect(self._on_triangle_saved)
        hotkey_manager.reset_triangle.connect(self._reset_triangle)
        hotkey_manager.toggle_capture.connect(self._toggle_capture)
        hotkey_manager.pixel_move.connect(self._on_pixel_move)

    def _load_settings(self):
        """설정 불러오기"""
        overlay_config = config.get("overlay", default={})
        x = overlay_config.get("x", 100)
        y = overlay_config.get("y", 100)
        w = overlay_config.get("width", 400)
        h = overlay_config.get("height", 300)
        self.region_label.setText(f"영역: ({x}, {y}) {w}x{h}")

    def _update_status(self):
        """상태 업데이트"""
        # 게임 창 상태 확인
        hwnd = screen_capture.find_mabinogi_window()
        if hwnd:
            self.game_status_label.setText("발견됨")
            self.game_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.game_status_label.setText("찾을 수 없음")
            self.game_status_label.setStyleSheet("color: red;")

    def _toggle_region_selector(self):
        """영역 선택기 토글"""
        if self.region_selector is None:
            # 영역 선택기 생성
            overlay_config = config.get("overlay", default={})
            from PyQt5.QtCore import QRect

            initial_rect = QRect(
                overlay_config.get("x", 100),
                overlay_config.get("y", 100),
                overlay_config.get("width", 400),
                overlay_config.get("height", 300),
            )

            self.region_selector = RegionSelector(initial_rect)
            self.region_selector.region_selected.connect(self._on_region_selected)

            # 전체 화면으로 설정
            screen = QApplication.primaryScreen().geometry()
            self.region_selector.setGeometry(screen)
            self.region_selector.show()

            self.region_btn.setText("영역 설정 완료")
        else:
            # 영역 선택기 닫기
            self.region_selector.close()
            self.region_selector = None
            self.region_btn.setText("영역 설정")

    def _on_region_selected(self, x: int, y: int, w: int, h: int):
        """영역 선택 완료"""
        self.region_label.setText(f"영역: ({x}, {y}) {w}x{h}")
        config.set(
            "overlay",
            value={"x": x, "y": y, "width": w, "height": h},
        )

        if self.overlay:
            self.overlay.set_region(x, y, w, h)

    def _start_capture(self):
        """캡처 시작"""
        # 게임 창 확인
        hwnd = screen_capture.find_mabinogi_window()
        if hwnd is None:
            QMessageBox.warning(
                self,
                "경고",
                "마비노기 모바일 창을 찾을 수 없습니다.\n게임을 먼저 실행해주세요.",
            )
            return

        # 영역 선택기 닫기
        if self.region_selector:
            self._toggle_region_selector()

        # 색상 설정 저장
        colors = [w.get_color_info() for w in self.color_widgets]
        config.set("colors", value=colors)

        # 표시 설정 저장
        config.set(
            "display",
            value={
                "show_grayscale": self.grayscale_check.isChecked(),
                "grayscale_brightness": self.brightness_slider.value(),
                "indicator_size": self.indicator_size_spin.value(),
            },
        )

        # 오버레이 생성 및 시작
        if self.overlay is None:
            self.overlay = OverlayWindow()

        self.overlay.show_grayscale = self.grayscale_check.isChecked()
        self.overlay.grayscale_brightness = self.brightness_slider.value()
        self.overlay.indicator_size = self.indicator_size_spin.value()
        self.overlay.set_colors(colors)
        self.overlay.start()

        # 단축키 시작
        hotkey_manager.start()

        # UI 업데이트
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.capture_status_label.setText("실행 중")
        self.capture_status_label.setStyleSheet("color: green; font-weight: bold;")

    def _stop_capture(self):
        """캡처 중지"""
        if self.overlay:
            self.overlay.stop()

        hotkey_manager.stop()

        # UI 업데이트
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.capture_status_label.setText("중지")
        self.capture_status_label.setStyleSheet("color: gray;")

    def _toggle_capture(self):
        """캡처 토글"""
        if self.overlay and self.overlay.is_running:
            self._stop_capture()
        else:
            self._start_capture()

    def _reset_triangle(self):
        """삼각형 초기화"""
        if self.overlay:
            self.overlay.reset_triangle()

    def _on_position_saved(self, index: int):
        """위치 저장 알림"""
        self.statusBar().showMessage(f"위치 {index} 저장됨", 2000)

    def _on_position_moved(self, index: int):
        """위치 이동 알림"""
        self.statusBar().showMessage(f"위치 {index}로 이동", 2000)

    def _on_triangle_saved(self, index: int, x: int, y: int):
        """삼각형 꼭지점 저장"""
        if self.overlay:
            # 화면 절대 좌표로 저장
            self.overlay.set_triangle_point(index, x, y)
            self.statusBar().showMessage(f"삼각형 꼭지점 {index + 4} 저장됨 ({x}, {y})", 2000)

    def _on_pixel_move(self, dx: int, dy: int):
        """픽셀 단위 커서 이동"""
        if sys.platform == "win32":
            import win32api

            x, y = win32api.GetCursorPos()
            win32api.SetCursorPos((x + dx, y + dy))

    def closeEvent(self, event):
        """창 닫기 이벤트"""
        self._stop_capture()

        if self.region_selector:
            self.region_selector.close()

        event.accept()
