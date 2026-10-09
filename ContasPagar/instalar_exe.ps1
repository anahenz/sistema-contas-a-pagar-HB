$ErrorActionPreference = 'Stop'
try {
    $sourceExe = Join-Path $PSScriptRoot 'dist\ContasPagar.exe'
    if (-not (Test-Path $sourceExe)) { throw 'Gere o executavel primeiro com gerar_exe.bat.' }
    $installDir = Join-Path $env:LOCALAPPDATA 'Programs\ContasPagar'
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    $targetExe = Join-Path $installDir 'ContasPagar.exe'
    Copy-Item -LiteralPath $sourceExe -Destination $targetExe -Force
    $shell = New-Object -ComObject WScript.Shell
    $shortcutDirs = @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))
    foreach ($shortcutDir in $shortcutDirs) {
        $shortcut = $shell.CreateShortcut((Join-Path $shortcutDir 'ContasPagar.lnk'))
        $shortcut.TargetPath = $targetExe
        $shortcut.WorkingDirectory = $installDir
        $shortcut.IconLocation = "$targetExe,0"
        $shortcut.Save()
    }
    Write-Host "Instalado em $installDir. Abra pelo atalho ContasPagar."
} catch {
    Write-Host "Falha ao instalar: $($_.Exception.Message)"
    exit 1
}
