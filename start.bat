@echo off
rem Double-click this file to start AuthApp.
cd /d "%~dp0"
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start.ps1"
