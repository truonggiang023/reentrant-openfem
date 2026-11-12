@echo off
setlocal
cd /d "%~dp0"
if not defined OPENCOURANT_ROOT set "OPENCOURANT_ROOT=C:\OpenCourant"
if not exist "%OPENCOURANT_ROOT%\exec\starter_win64.exe" (
  echo Set OPENCOURANT_ROOT to the extracted OpenCourant Windows root.
  pause
  exit /b 1
)
py -3 run_cases.py --run --root "%OPENCOURANT_ROOT%" --threads 1
if errorlevel 1 (
  echo Run failed. Inspect logs; do not reuse existing history outputs.
  pause
  exit /b 1
)
echo Done. These are NEW geometry hypotheses; not a confirmed reproduction of the paper.
pause
