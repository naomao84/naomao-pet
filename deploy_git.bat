@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo  [미니펫 뽕뽕이] GitHub 배포 (naomao84/naomao-pet)
echo ========================================================
echo.
echo GitHub 인증 창(브라우저)이 나타나면 naomao84 계정으로 승인해주세요.
echo.
git push -u origin main
echo.
if %ERRORLEVEL% equ 0 (
    echo [성공] GitHub 배포가 성공적으로 완료되었습니다!
) else (
    echo [확인] 푸시 중 문제가 발생했습니다. 위 안내를 확인해주세요.
)
echo.
pause

