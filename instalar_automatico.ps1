$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$logDir = Join-Path $env:LOCALAPPDATA 'ContasPagar\logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ('instalacao-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
$transcribing = $false
$mutex = New-Object System.Threading.Mutex($false, 'Local\ContasPagarInstaller')
$locked = $false
function Find-Python {
    $candidates = @()
    foreach ($name in @('py.exe', 'python.exe')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                $result = & $cmd.Source -c 'import sys; print(sys.executable) if (3,11) <= sys.version_info[:2] <= (3,13) else None' 2>$null
                if ($LASTEXITCODE -eq 0 -and $result) { $candidates += [string]($result | Select-Object -Last 1) }
            } catch {}
        }
    }
    foreach ($v in @('313','312','311')) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe")
        $candidates += (Join-Path $env:ProgramFiles "Python$v\python.exe")
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) and sys.maxsize > 2**32 else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
    return $null
}
try {
    $locked = $mutex.WaitOne(0)
    if (-not $locked) { throw 'A instalacao ja esta em andamento. Aguarde a outra janela.' }
    Start-Transcript -Path $log | Out-Null
    $transcribing = $true
    if (-not (Test-Path (Join-Path $PSScriptRoot 'app\views'))) { throw 'Extraia todo o ZIP antes de abrir INSTALAR.bat.' }
    Write-Host 'CONTAS A PAGAR - Instalacao automatica'
    Write-Host 'Mantenha a internet conectada. Esta etapa pode levar alguns minutos.'
    Write-Host '[1/4] Verificando Python...'
    $python = Find-Python
    if (-not $python) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
            throw 'Python compativel nao encontrado. Instale Python 3.13 de 64 bits em python.org e abra INSTALAR.bat novamente. O Windows nao disponibilizou o winget para instalacao automatica.'
        }
        Write-Host 'Instalando Python 3.13 para este usuario...'
        & winget.exe install --id Python.Python.3.13 --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
        $python = Find-Python
        if (-not $python) { throw 'Nao foi possivel instalar/localizar Python. Veja a mensagem do instalador acima.' }
    }
    # Each installation is isolated. Existing shortcuts and application data
    # are untouched until dependencies have been installed and verified.
    $installDir = Join-Path $env:LOCALAPPDATA ('Programs\ContasPagar\releases\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    Write-Host '[2/4] Copiando o aplicativo e preparando o ambiente...'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'app') -Destination $installDir -Recurse
    foreach ($name in @('main.py','requirements.txt','iniciar.bat')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $installDir
    }
    & $python -m venv (Join-Path $installDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente Python.' }
    $venvPython = Join-Path $installDir '.venv\Scripts\python.exe'
    Write-Host '[3/4] Instalando dependencias...'
    & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $installDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar dependencias. Verifique a internet e execute INSTALAR.bat novamente.' }
    & $venvPython -c 'from PySide6 import QtWidgets, QtNetwork; import sqlalchemy, openpyxl, reportlab'
    if ($LASTEXITCODE -ne 0) { throw 'As dependencias nao passaram na verificacao. Consulte o log.' }
    Write-Host '[4/4] Criando atalhos...'
    $shell = New-Object -ComObject WScript.Shell
    $pythonw = Join-Path $installDir '.venv\Scripts\pythonw.exe'
    foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        $shortcut = $shell.CreateShortcut((Join-Path $folder 'ContasPagar.lnk'))
        $shortcut.TargetPath = $pythonw
        $shortcut.Arguments = '"' + (Join-Path $installDir 'main.py') + '"'
        $shortcut.WorkingDirectory = $installDir
        $shortcut.IconLocation = (Join-Path $installDir 'app\assets\app.ico')
        $shortcut.Save()
    }
    Write-Host 'Instalacao concluida! Use o atalho ContasPagar na area de trabalho.'
    [System.Windows.Forms.MessageBox]::Show('Instalacao concluida! O aplicativo sera aberto. Nas proximas vezes, use o atalho ContasPagar na area de trabalho.', 'ContasPagar') | Out-Null
    Start-Process -FilePath $pythonw -ArgumentList ('"' + (Join-Path $installDir 'main.py') + '"') -WorkingDirectory $installDir
} catch {
    Write-Host ('ERRO: ' + $_.Exception.Message) -ForegroundColor Red
    [System.Windows.Forms.MessageBox]::Show(($_.Exception.Message + "`r`n`r`nLog: " + $log), 'Falha na instalacao') | Out-Null
    exit 1
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
