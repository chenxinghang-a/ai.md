@echo off
echo 正在下载 FFmpeg (从 GitHub 镜像)...
echo.

set "DEST=%~dp0tools\ffmpeg.exe"
if exist "%DEST%" (
    echo FFmpeg 已存在: %DEST%
    goto :end
)

mkdir "%~dp0tools" 2>nul

:: 使用 GitHub releases 下载 (约80MB)
curl.exe -L -o "%~dp0tools\ffmpeg-release.7z" "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.7z" --connect-timeout 30

if errorlevel 1 (
    echo.
    echo === 备选方案: 手动下载 ===
    echo 1. 打开 https://www.gyan.dev/ffmpeg/builds/
    2. 下载 ffmpeg-release-essentials.zip
    3. 解压后将 bin\ffmpeg.exe 放到 tools\ 目录
    goto :end
)

echo.
echo 解压中... (需要7z或手动解压)
echo 文件位置: %~dp0tools\ffmpeg-release.7z
echo 请解压后将 bin\ffmpeg.exe 复制到 %DEST%

:end
echo.
pause
