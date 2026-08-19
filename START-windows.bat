@echo off
REM Spousteci skript pro PROTC_OTISK (Windows) - aktivuje .venv (poprve ho
REM rovnou vytvori a nainstaluje zavislosti) a preda vsechny argumenty do
REM protc_otisk.py. Dik tomu se nemusi pred kazdym behem rucne psat
REM ".venv\Scripts\activate".
REM
REM Pouziti stejne jako "python protc_otisk.py", jen kratsi (nebo rovnou
REM dvojklik ve Windows Exploreru):
REM   START-windows.bat login
REM   START-windows.bat snapshot
REM   START-windows.bat snapshot --limit 3 --headed
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    echo Prvni spusteni - vytvarim virtualni prostredi ^(.venv^)...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -q -r requirements.txt
    playwright install chromium
) else (
    call .venv\Scripts\activate.bat
)

python protc_otisk.py %*

REM Pri dvojkliku (zadne argumenty) by se okno hned po skonceni zavrelo -
REM misto pouheho "stiskni klavesu a zavri" se necha otevrene jako normalni
REM interaktivni prompt (venv zustava aktivni), takze se rovnou da psat
REM "python protc_otisk.py login" apod. bez dalsiho dvojkliku. Pri spusteni
REM z prikazove radky (nejaky argument zadany) se to preskoci.
if "%~1"=="" (
    echo.
    cmd /k
)
