@echo off
title cs榜 启动器（设置 / 重置管理员）
:: ============================================================
::  ① 改下面两行为你想要的管理员账号与密码
::  ② 两种情况：
::     · 第一次用（还没建过库）      -> 直接双击本文件
::     · 已经用过、忘了密码 / 想改密 -> 把 BB_ADMIN_RESET 改成 1 再双击
:: ============================================================
set BB_ADMIN_USER=admin
set BB_ADMIN_PASSWORD=请改成你的密码
set BB_ADMIN_RESET=0
::   0 = 仅首次创建数据库时使用上面的账号密码
::   1 = 每次启动都强制重置为上面的账号密码（榜单数据完整保留）
:: ============================================================

cd /d "%~dp0"
set EXE=csboard.exe
if not exist "%EXE%" for %%F in (csboard*.exe) do set EXE=%%F
if not exist "%EXE%" (
  echo.
  echo   [x] 本目录没找到 csboard.exe
  echo       请把本文件放到 csboard.exe 所在的同一个文件夹里再运行
  echo.
  pause
  exit /b 1
)
echo.
echo   正在启动 cs榜 ...
echo   启动文件   : %EXE%
echo   管理员账号 : %BB_ADMIN_USER%
echo   重置模式   : %BB_ADMIN_RESET%   （1 = 本次启动强制重置密码，数据不受影响）
echo.
"%EXE%"
pause