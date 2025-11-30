"""색상 검출 모듈"""
import numpy as np
import cv2
from typing import List, Tuple, Optional


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """HEX 색상을 RGB로 변환"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """RGB를 HEX 색상으로 변환"""
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    """HEX 색상을 BGR로 변환 (OpenCV용)"""
    r, g, b = hex_to_rgb(hex_color)
    return (b, g, r)


class ColorDetector:
    """색상 검출 클래스"""

    def __init__(self):
        self.target_colors: List[dict] = []
        self.ignore_white_bar = True  # 흰색 막대 무시
        self.ignore_picker_ring = True  # 피커 고리 무시

    def set_target_colors(self, colors: List[dict]):
        """
        목표 색상 설정
        colors: [{"hex": "#FF0000", "tolerance": 30, "enabled": True}, ...]
        """
        self.target_colors = [c for c in colors if c.get("enabled", True)]

    def detect_colors(
        self, image: np.ndarray, return_mask: bool = False
    ) -> Tuple[np.ndarray, Optional[np.ndarray], List[Tuple[int, int]]]:
        """
        이미지에서 목표 색상 검출

        Args:
            image: BGR 이미지 (OpenCV 형식)
            return_mask: 마스크 반환 여부

        Returns:
            result_image: 흑백 처리된 결과 이미지
            mask: 검출된 색상 마스크 (return_mask=True일 때)
            positions: 검출된 색상 위치들 [(x, y), ...]
        """
        if image is None or len(self.target_colors) == 0:
            return image, None, []

        # 결과 마스크 초기화
        combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        positions = []

        for color_info in self.target_colors:
            hex_color = color_info.get("hex", "#FFFFFF")
            tolerance = color_info.get("tolerance", 30)

            # BGR 색상으로 변환
            target_bgr = hex_to_bgr(hex_color)

            # 색상 범위 계산
            lower = np.array(
                [max(0, c - tolerance) for c in target_bgr], dtype=np.uint8
            )
            upper = np.array(
                [min(255, c + tolerance) for c in target_bgr], dtype=np.uint8
            )

            # 색상 마스크 생성
            mask = cv2.inRange(image, lower, upper)

            # 흰색 막대/피커 고리 제외 처리
            if self.ignore_white_bar and hex_color.upper() == "#FFFFFF":
                mask = self._remove_white_bar_region(image, mask)

            # 마스크 합치기
            combined_mask = cv2.bitwise_or(combined_mask, mask)

            # 검출 위치 찾기
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for cnt in contours:
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    positions.append((cx, cy))

        # 흑백 이미지 생성
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # 검출된 색상 부분만 원본 색상 유지
        result = gray_bgr.copy()
        result[combined_mask > 0] = image[combined_mask > 0]

        if return_mask:
            return result, combined_mask, positions
        return result, None, positions

    def _remove_white_bar_region(
        self, image: np.ndarray, mask: np.ndarray
    ) -> np.ndarray:
        """흰색 막대 영역 제거"""
        # 세로로 긴 흰색 영역(막대) 감지 및 제거
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        result_mask = mask.copy()
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = h / w if w > 0 else 0

            # 세로로 긴 영역(막대)이거나 원형(피커 고리)인 경우 제외
            if aspect_ratio > 3:  # 세로 막대
                cv2.drawContours(result_mask, [cnt], -1, 0, -1)
            elif 0.8 < aspect_ratio < 1.2:  # 원형 (피커)
                area = cv2.contourArea(cnt)
                circle_area = np.pi * (min(w, h) / 2) ** 2
                if area > 0 and circle_area / area > 0.7:  # 원에 가까운 경우
                    cv2.drawContours(result_mask, [cnt], -1, 0, -1)

        return result_mask

    def get_pixel_color(self, image: np.ndarray, x: int, y: int) -> str:
        """특정 픽셀의 색상을 HEX로 반환"""
        if image is None:
            return "#000000"

        h, w = image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            b, g, r = image[y, x]
            return rgb_to_hex(r, g, b)
        return "#000000"

    def apply_brightness(
        self, image: np.ndarray, brightness: int = 50
    ) -> np.ndarray:
        """흑백 영역 밝기 조절 (0-100)"""
        if brightness == 50:
            return image

        # 밝기 조절 (-127 ~ 127)
        beta = int((brightness - 50) * 2.54)
        adjusted = cv2.convertScaleAbs(image, alpha=1, beta=beta)
        return adjusted
