@echo off
REM Open the mask of the latest run in KLayout.
REM
REM   tools\view_mask.cmd examples\edbr_tfln_baseline
REM
REM The DRC marker layout is loaded alongside the mask, so a violation can be
REM located rather than merely counted. The application is the portable build
REM held under %LOCALAPPDATA%; nothing is installed system-wide.

setlocal
set "KL=%LOCALAPPDATA%\KLayout\klayout-0.30.10-win64\klayout_app.exe"
if not exist "%KL%" (
    echo KLayout was not found at "%KL%".
    echo Obtain the portable build from https://www.klayout.org/downloads/Windows/
    exit /b 1
)

set "DESIGN=%~1"
if "%DESIGN%"=="" (
    echo usage: view_mask.cmd ^<design-folder^>
    exit /b 2
)

for /f "delims=" %%d in ('dir /b /ad /o-n "%DESIGN%\runs\2*"') do (
    set "RUN=%DESIGN%\runs\%%d"
    goto :found
)
echo no runs found under "%DESIGN%\runs"
exit /b 1

:found
for %%f in ("%RUN%\*.gds") do set "GDS=%%f"
if "%GDS%"=="" (
    echo the latest run holds no GDS; was the layout stage enabled?
    exit /b 1
)
echo opening %GDS%
start "" "%KL%" "%RUN%\*.gds"
endlocal
