@echo off
echo Running ProductFind Test Suite...
cd /d "%~dp0"
.\.venv\Scripts\pytest.exe -v
