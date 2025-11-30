@echo off
chcp 65001 >nul
echo ========================================
echo 마비노기 모바일 염색 도우미 빌드 스크립트
echo ========================================
echo.

echo [1/3] 가상환경 확인...
if not exist "venv" (
    echo 가상환경 생성 중...
    python -m venv venv
)

echo [2/3] 의존성 설치...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo [3/3] 실행 파일 빌드...
pyinstaller build.spec --clean

echo.
echo ========================================
echo 빌드 완료!
echo 실행 파일: dist\MabinogiDyeHelper.exe
echo ========================================
pause
