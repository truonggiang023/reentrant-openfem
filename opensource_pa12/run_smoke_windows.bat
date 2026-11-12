@echo off
setlocal
cd /d "%~dp0"
if not defined OPENCOURANT_ROOT set "OPENCOURANT_ROOT=C:\OpenCourant"
if not exist "%OPENCOURANT_ROOT%\exec\starter_win64.exe" (
  echo Download OpenCourant for Windows and set OPENCOURANT_ROOT to its extracted root.
  echo Expected: %OPENCOURANT_ROOT%\exec\starter_win64.exe
  pause
  exit /b 1
)
py -3 build_radioss.py --out runs\smoke --smoke --strain 0.1
if errorlevel 1 goto failed
py -3 run_solver.py runs\smoke --root "%OPENCOURANT_ROOT%" --allow-initial-penetrations --vtk
if errorlevel 1 goto failed
py -3 postprocess.py runs\smoke
if errorlevel 1 goto failed
echo Finished. Check runs\smoke\summary.json and logs. This is NOT paper validation.
pause
exit /b 0
:failed
echo Failed. Inspect console and log files. Use a new output folder for another Engine run.
pause
exit /b 1
