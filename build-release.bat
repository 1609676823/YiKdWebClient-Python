@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0" || (
    echo [ERROR] Cannot enter the project directory.
    exit /b 1
)

if not exist "pyproject.toml" (
    echo [ERROR] pyproject.toml was not found in "%CD%".
    exit /b 1
)

if not exist "src\yikd_web_client" (
    echo [ERROR] The expected package directory was not found in "%CD%".
    exit /b 1
)

set "VENV_DIR=%CD%\.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Creating the local virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
        if not errorlevel 1 (
            py -3 -m venv "%VENV_DIR%"
            if errorlevel 1 goto :failed
            goto :venv_ready
        )
    )

    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
        if not errorlevel 1 (
            python -m venv "%VENV_DIR%"
            if errorlevel 1 goto :failed
            goto :venv_ready
        )
    )

    echo [ERROR] Python 3.9 or newer was not found.
    echo [ERROR] Install Python from https://www.python.org/downloads/ and try again.
    exit /b 1
)

:venv_ready
"%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] The Python in .venv is older than 3.9 or cannot be started.
    echo [ERROR] Remove .venv, install Python 3.9 or newer, and run this script again.
    exit /b 1
)

echo [1/6] Cleaning old build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
for /d %%D in ("src\*.egg-info") do if exist "%%~fD" rmdir /s /q "%%~fD"

echo [2/6] Installing the project and release tools...
"%PYTHON_EXE%" -m pip install -e ".[dev]"
if errorlevel 1 goto :failed

echo [3/6] Running Ruff...
"%PYTHON_EXE%" -m ruff check src tests examples
if errorlevel 1 goto :failed

echo [4/6] Running unit tests...
"%PYTHON_EXE%" -m unittest discover -s tests -v
if errorlevel 1 goto :failed

echo [5/6] Building wheel and source distribution...
"%PYTHON_EXE%" -m build
if errorlevel 1 goto :failed

echo [6/6] Validating the distribution metadata...
"%PYTHON_EXE%" -m twine check --strict dist\*
if errorlevel 1 goto :failed

echo.
echo [SUCCESS] Release artifacts are ready:
for %%F in ("dist\*") do echo          %%~nxF
echo.
echo To upload them manually to PyPI, run:
echo   .venv\Scripts\python.exe -m twine upload dist\*
echo.
exit /b 0

:failed
echo.
echo [ERROR] Release build failed. Review the output above.
exit /b 1
