@echo off
setlocal
cd /d "%~dp0"
if not exist "requirements.txt" goto pasta_errada
if exist ".venv\Scripts\python.exe" goto instalar
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto tentar_python
py -3 -m venv .venv
if errorlevel 1 goto erro
goto instalar
:tentar_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto sem_python
python -m venv .venv
if errorlevel 1 goto erro
:instalar
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto erro
echo.
echo Instalacao concluida. Abra iniciar.bat para usar o sistema.
pause
exit /b 0
:sem_python
echo Instale Python 3.11 ou superior em https://www.python.org/downloads/windows/
echo Marque Add Python to PATH durante a instalacao e tente novamente.
pause
exit /b 1
:pasta_errada
echo Extraia todo o ZIP antes de executar este arquivo.
echo Este arquivo deve ficar na mesma pasta de requirements.txt.
pause
exit /b 1
:erro
echo.
echo A instalacao falhou. Copie ou fotografe a mensagem acima.
pause
exit /b 1
