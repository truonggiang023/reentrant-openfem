@echo off
setlocal
cd /d "%~dp0"
if not defined OPENCOURANT_ROOT set "OPENCOURANT_ROOT=C:\OpenCourant"
if not exist "%OPENCOURANT_ROOT%\exec\starter_win64.exe" (
  echo Set OPENCOURANT_ROOT to the extracted OpenCourant Windows root.
  pause
  exit /b 1
)
py -3 build_radioss.py --out runs\full --mode TABLE --strain 0.5 --speed 1000 --mesh 1
if errorlevel 1 goto failed
py -3 run_solver.py runs\full --root "%OPENCOURANT_ROOT%" --allow-initial-penetrations --vtk
if errorlevel 1 goto failed
py -3 postprocess.py runs\full
if errorlevel 1 goto failed
echo Finished. Inspect summary and all warnings before interpreting results.
pause
exit /b 0
:failed
echo Failed. Inspect console and logs. Use a new output folder for another Engine run.
pause
exit /b 1
