@echo off
setlocal

if "%1"=="test" goto test
if "%1"=="figures" goto figures
if "%1"=="docs" goto docs
goto help

:test
python -m pytest -q
goto end

:figures
python main.py
goto end

:docs
sphinx-build -b html docs docs\_build\html
goto end

:help
echo Usage: make.bat [test^|figures^|docs]
exit /b 1

:end
endlocal
