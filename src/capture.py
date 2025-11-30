"""화면 캡처 모듈"""
import numpy as np
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple
import sys

# Windows 전용 모듈 조건부 임포트
if sys.platform == "win32":
    import win32gui
    import win32ui
    import win32con
    from PIL import Image

# DWM 상수
DWMWA_EXTENDED_FRAME_BOUNDS = 9


class ScreenCapture:
    """화면 캡처 클래스"""

    def __init__(self):
        self.target_hwnd: Optional[int] = None
        self.target_title = "마비노기 모바일"

    def find_mabinogi_window(self) -> Optional[int]:
        """마비노기 모바일 윈도우 찾기"""
        if sys.platform != "win32":
            return None

        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.target_title in title:
                    hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)

        if hwnds:
            self.target_hwnd = hwnds[0]
            return self.target_hwnd
        return None

    def get_window_rect_without_shadow(
        self, hwnd: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """그림자 제외한 윈도우 영역 가져오기"""
        if sys.platform != "win32":
            return None

        try:
            rect = wintypes.RECT()
            result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if result == 0:
                return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception as e:
            print(f"DWM 속성 가져오기 실패: {e}")

        # 폴백: 일반 윈도우 영역
        try:
            return win32gui.GetWindowRect(hwnd)
        except Exception:
            return None

    def capture_window(
        self, hwnd: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """윈도우 캡처하여 numpy 배열로 반환"""
        if sys.platform != "win32":
            return None

        if hwnd is None:
            hwnd = self.target_hwnd

        if hwnd is None or not win32gui.IsWindow(hwnd):
            return None

        try:
            # 윈도우 영역 가져오기
            rect = self.get_window_rect_without_shadow(hwnd)
            if rect is None:
                return None

            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                return None

            # DC 가져오기
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            # 비트맵 생성
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # PrintWindow로 캡처 (최소화된 창도 캡처 가능)
            result = ctypes.windll.user32.PrintWindow(
                hwnd, save_dc.GetSafeHdc(), 2
            )

            if result == 0:
                # 폴백: BitBlt 사용
                save_dc.BitBlt(
                    (0, 0),
                    (width, height),
                    mfc_dc,
                    (0, 0),
                    win32con.SRCCOPY,
                )

            # 비트맵을 numpy 배열로 변환
            bmp_info = bitmap.GetInfo()
            bmp_str = bitmap.GetBitmapBits(True)

            img = np.frombuffer(bmp_str, dtype=np.uint8)
            img = img.reshape((height, width, 4))

            # BGRA -> BGR 변환
            img_bgr = img[:, :, :3]

            # 리소스 정리
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return img_bgr.copy()

        except Exception as e:
            print(f"화면 캡처 실패: {e}")
            return None

    def capture_region(
        self, x: int, y: int, width: int, height: int
    ) -> Optional[np.ndarray]:
        """특정 영역만 캡처"""
        if sys.platform != "win32":
            return None

        full_image = self.capture_window()
        if full_image is None:
            return None

        img_h, img_w = full_image.shape[:2]

        # 영역 제한
        x = max(0, min(x, img_w))
        y = max(0, min(y, img_h))
        width = min(width, img_w - x)
        height = min(height, img_h - y)

        if width <= 0 or height <= 0:
            return None

        return full_image[y : y + height, x : x + width].copy()

    def get_window_info(self) -> Optional[dict]:
        """현재 타겟 윈도우 정보 반환"""
        if self.target_hwnd is None:
            return None

        if sys.platform != "win32":
            return None

        try:
            if not win32gui.IsWindow(self.target_hwnd):
                self.target_hwnd = None
                return None

            rect = self.get_window_rect_without_shadow(self.target_hwnd)
            if rect is None:
                return None

            left, top, right, bottom = rect
            return {
                "hwnd": self.target_hwnd,
                "title": win32gui.GetWindowText(self.target_hwnd),
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
            }
        except Exception:
            return None


# 전역 캡처 인스턴스
screen_capture = ScreenCapture()
