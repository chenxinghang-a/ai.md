@echo off
chcp 65001 >nul
title ModbusDiag Git 初始化
echo ============================================
echo  ModbusDiag - Git仓库初始化
echo ============================================
echo.
set GIT=C:\Users\cxx\WorkBuddy\Claw\tools\mingit\cmd\git.exe
set PROJ=C:\Users\cxx\WorkBuddy\Claw\ModbusDiag
set PROXY=http://127.0.0.1:7890

cd /d "%PROJ%"

echo [1/4] 初始化仓库...
"%GIT%" init

echo [2/4] 配置代理...
"%GIT%" config http.proxy %PROXY%

echo [3/4] 添加文件...
"%GIT%" add -A

echo [4/4] 提交...
"%GIT%" commit -m "init: ModbusDiag v1.0 - 便携式Modbus诊断仪"
echo.
echo 如需推送到远程:
echo %GIT% remote add origin https://github.com/你的用户名/ModbusDiag.git
echo %GIT% push -u origin main
echo.
pause
