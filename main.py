"""
마비노기 모바일 염색 도우미
Mabinogi Mobile Dye Helper

주요 기능:
- 화면 내 특정 색상 검출
- 지정 색상 외 영역 흑백 처리
- HEX 코드로 색상 입력
- 3색 가이드라인 (삼각형)
- 단축키 지원

단축키:
- CTRL + 1,2,3: 커서 좌표 저장
- ALT + 1,2,3: 저장된 좌표로 이동
- CTRL + 4,5,6: 삼각형 좌표 저장
- CTRL + 7: 삼각형 초기화
- CTRL + 8: 캡처 시작/중지
- CTRL + 방향키: 픽셀 단위 이동
"""
import sys
import os

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Qt 플러그인 경로 설정 (PyQt5 설치 문제 해결)
if sys.platform == "win32":
    try:
        import PyQt5
        pyqt_path = os.path.dirname(PyQt5.__file__)
        plugin_path = os.path.join(pyqt_path, "Qt5", "plugins")
        if os.path.exists(plugin_path):
            os.environ["QT_PLUGIN_PATH"] = plugin_path
        # 대체 경로
        plugin_path2 = os.path.join(pyqt_path, "Qt", "plugins")
        if os.path.exists(plugin_path2):
            os.environ["QT_PLUGIN_PATH"] = plugin_path2
    except Exception:
        pass


def check_platform():
    """플랫폼 확인"""
    if sys.platform != "win32":
        print("이 프로그램은 Windows 전용입니다.")
        print("Windows에서 실행해주세요.")
        return False
    return True


def check_admin():
    """관리자 권한 확인 (경고만 표시, 실행은 계속)"""
    if sys.platform == "win32":
        import ctypes

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("=" * 50)
                print("경고: 관리자 권한 없이 실행 중입니다.")
                print("일부 기능(단축키 등)이 작동하지 않을 수 있습니다.")
                print("문제가 있으면 프로그램을 우클릭 후")
                print("'관리자 권한으로 실행'을 선택하세요.")
                print("=" * 50)
                return False
        except Exception:
            pass
    return True


def main():
    """메인 함수"""
    # 플랫폼 확인
    if not check_platform():
        input("아무 키나 누르세요...")
        return 1

    # 관리자 권한 확인 (경고만 표시, 계속 실행)
    check_admin()

    # PyQt5 애플리케이션 시작
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt

    # High DPI 지원
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 다크 모드 팔레트 설정
    from PyQt5.QtGui import QPalette, QColor

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(dark_palette)
    app.setStyleSheet(
        "QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }"
    )

    # 메인 윈도우 생성
    from src.main_window import MainWindow

    window = MainWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
