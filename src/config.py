"""설정 저장/불러오기 모듈"""
import json
import os
from pathlib import Path


class Config:
    """프로그램 설정 관리 클래스"""

    DEFAULT_CONFIG = {
        "colors": [
            {"hex": "#FF0000", "tolerance": 30, "enabled": True},
            {"hex": "#00FF00", "tolerance": 30, "enabled": False},
            {"hex": "#0000FF", "tolerance": 30, "enabled": False},
        ],
        "overlay": {
            "x": 100,
            "y": 100,
            "width": 400,
            "height": 300,
            "opacity": 0.8,
        },
        "display": {
            "grayscale_brightness": 50,
            "indicator_size": 10,
            "show_grayscale": True,
        },
        "triangle": {
            "points": [],  # [(x, y), (x, y), (x, y)]
            "enabled": False,
        },
        "saved_positions": {
            "pos1": None,
            "pos2": None,
            "pos3": None,
        },
    }

    def __init__(self):
        self.config_dir = Path(os.getenv("APPDATA", ".")) / "MabinogiDyeHelper"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load()

    def load(self) -> dict:
        """설정 파일 불러오기"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 기본값과 병합
                    return self._merge_config(self.DEFAULT_CONFIG.copy(), loaded)
        except Exception as e:
            print(f"설정 로드 실패: {e}")
        return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, default: dict, loaded: dict) -> dict:
        """기본 설정과 로드된 설정 병합"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_config(result[key], value)
                else:
                    result[key] = value
        return result

    def save(self):
        """설정 파일 저장"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 실패: {e}")

    def get(self, *keys, default=None):
        """중첩 키로 설정값 가져오기"""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value):
        """중첩 키로 설정값 저장"""
        if len(keys) == 0:
            return

        target = self.config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save()


# 전역 설정 인스턴스
config = Config()
