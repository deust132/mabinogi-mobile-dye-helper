"""단축키 관리 모듈"""
import sys
from typing import Callable, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

if sys.platform == "win32":
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    import win32api
    import win32con


class HotkeyManager(QObject):
    """전역 단축키 관리자"""

    # 시그널 정의
    save_position = pyqtSignal(int)  # CTRL+1,2,3: 위치 저장
    move_to_position = pyqtSignal(int)  # ALT+1,2,3: 위치로 이동
    save_triangle = pyqtSignal(int, int, int)  # CTRL+4,5,6: 삼각형 좌표 저장 (index, x, y)
    reset_triangle = pyqtSignal()  # CTRL+7: 삼각형 초기화
    toggle_capture = pyqtSignal()  # CTRL+8: 캡처 토글
    pixel_move = pyqtSignal(int, int)  # 화살표키: 픽셀 단위 이동

    def __init__(self, parent=None):
        super().__init__(parent)

        self.listener: Optional[keyboard.Listener] = None
        self.current_keys: set = set()
        self.saved_positions: Dict[int, tuple] = {}  # {1: (x, y), 2: (x, y), 3: (x, y)}

        # 설정에서 저장된 위치 불러오기
        self._load_saved_positions()

    def _load_saved_positions(self):
        """저장된 위치 불러오기"""
        from .config import config

        positions = config.get("saved_positions", default={})
        for i in range(1, 4):
            key = f"pos{i}"
            if key in positions and positions[key]:
                self.saved_positions[i] = tuple(positions[key])

    def _save_positions(self):
        """위치 저장"""
        from .config import config

        positions = {}
        for i in range(1, 4):
            if i in self.saved_positions:
                positions[f"pos{i}"] = list(self.saved_positions[i])
            else:
                positions[f"pos{i}"] = None
        config.set("saved_positions", value=positions)

    def start(self):
        """단축키 리스닝 시작"""
        if sys.platform != "win32":
            print("단축키 기능은 Windows에서만 사용 가능합니다.")
            return

        if self.listener is not None:
            return

        self.listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self.listener.start()
        print("[단축키] 리스너 시작됨")

    def stop(self):
        """단축키 리스닝 중지"""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            print("[단축키] 리스너 중지됨")

    def _get_key_number(self, key) -> Optional[int]:
        """키에서 숫자 추출 (1-9)"""
        # 가상 키코드로 체크 (CTRL 누른 상태에서도 작동)
        if hasattr(key, 'vk') and key.vk is not None:
            # 숫자키 1-9의 가상 키코드: 0x31 (49) ~ 0x39 (57)
            if 0x31 <= key.vk <= 0x39:
                return key.vk - 0x30  # 1-9 반환
            # 넘패드 1-9: 0x61 (97) ~ 0x69 (105)
            if 0x61 <= key.vk <= 0x69:
                return key.vk - 0x60  # 1-9 반환

        # char로 체크 (백업)
        if hasattr(key, 'char') and key.char is not None:
            if key.char in '123456789':
                return int(key.char)

        return None

    def _on_key_press(self, key):
        """키 눌림 처리"""
        self.current_keys.add(key)

        # 수정자 키 체크
        ctrl_pressed = (
            keyboard.Key.ctrl_l in self.current_keys
            or keyboard.Key.ctrl_r in self.current_keys
        )
        alt_pressed = (
            keyboard.Key.alt_l in self.current_keys
            or keyboard.Key.alt_r in self.current_keys
        )

        # 숫자키 확인
        num = self._get_key_number(key)

        # CTRL + 숫자키
        if ctrl_pressed and not alt_pressed and num is not None:
            print(f"[단축키] CTRL+{num} 감지됨")
            if num == 1:
                self._save_cursor_position(1)
            elif num == 2:
                self._save_cursor_position(2)
            elif num == 3:
                self._save_cursor_position(3)
            elif num == 4:
                self._save_triangle_position(0)
            elif num == 5:
                self._save_triangle_position(1)
            elif num == 6:
                self._save_triangle_position(2)
            elif num == 7:
                self.reset_triangle.emit()
                print("[단축키] 삼각형 초기화")
            elif num == 8:
                self.toggle_capture.emit()
                print("[단축키] 캡처 토글")

        # ALT + 숫자키
        if alt_pressed and not ctrl_pressed and num is not None:
            print(f"[단축키] ALT+{num} 감지됨")
            if num == 1:
                self._move_to_saved_position(1)
            elif num == 2:
                self._move_to_saved_position(2)
            elif num == 3:
                self._move_to_saved_position(3)

        # 화살표 키 (픽셀 단위 이동)
        if ctrl_pressed:
            if key == keyboard.Key.up:
                self.pixel_move.emit(0, -1)
            elif key == keyboard.Key.down:
                self.pixel_move.emit(0, 1)
            elif key == keyboard.Key.left:
                self.pixel_move.emit(-1, 0)
            elif key == keyboard.Key.right:
                self.pixel_move.emit(1, 0)

    def _on_key_release(self, key):
        """키 릴리즈 처리"""
        self.current_keys.discard(key)

    def _save_cursor_position(self, index: int):
        """현재 커서 위치 저장"""
        if sys.platform != "win32":
            return

        x, y = win32api.GetCursorPos()
        self.saved_positions[index] = (x, y)
        self._save_positions()
        self.save_position.emit(index)
        print(f"[단축키] 위치 {index} 저장: ({x}, {y})")

    def _move_to_saved_position(self, index: int):
        """저장된 위치로 커서 이동"""
        if sys.platform != "win32":
            return

        if index in self.saved_positions:
            x, y = self.saved_positions[index]
            win32api.SetCursorPos((x, y))
            self.move_to_position.emit(index)
            print(f"[단축키] 위치 {index}로 이동: ({x}, {y})")

    def _save_triangle_position(self, index: int):
        """삼각형 꼭지점 위치 저장 (현재 커서 위치)"""
        if sys.platform != "win32":
            return

        x, y = win32api.GetCursorPos()
        self.save_triangle.emit(index, x, y)
        print(f"[단축키] 삼각형 꼭지점 {index} 저장: ({x}, {y})")

    def get_cursor_position(self) -> tuple:
        """현재 커서 위치 반환"""
        if sys.platform != "win32":
            return (0, 0)
        return win32api.GetCursorPos()


# 전역 단축키 매니저
hotkey_manager = HotkeyManager()
