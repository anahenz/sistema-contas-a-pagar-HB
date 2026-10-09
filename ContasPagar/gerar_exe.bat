@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Execute instalar_dependencias.bat primeiro.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ContasPagar.spec
if errorlevel 1 (
 echo Nao foi possivel gerar o executavel. Veja a mensagem acima.
 pause
 exit /b 1
)
echo Executavel criado em dist\ContasPagar.exe
pause
