# Copied run_interactive.ps1 adjusted for backend/app layout
$candidates = @(Join-Path $PSScriptRoot '.env', Join-Path $PSScriptRoot '..\.env')
$envFile = $null
foreach ($cand in $candidates) {
    if (Test-Path $cand) { $envFile = $cand; break }
}

if ($envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq '' -or $line -like '#*') { return }
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $name = $parts[0].Trim()
            $value = $parts[1].Trim()
            Set-Item -Path ("Env:{0}" -f $name) -Value $value
        }
    }
    Write-Host ".env cargado desde $envFile"
} else {
    Write-Warning ".env no encontrado. Crea '.env' en la carpeta backend\app o en la carpeta padre. Define PSEUDO_KEY y REGEX_FIRST en la sesión si hace falta."
}

$venvActivate = 'C:\Users\admin\Desktop\PROYECTO\Hackaton_grupo3_backend\venv310\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    Write-Host "Activando virtualenv..."
    & $venvActivate
} else {
    Write-Warning "Activate.ps1 no encontrado en $venvActivate. Activa el venv manualmente si hace falta."
}

$wrapper = Join-Path $PSScriptRoot '..\services\run_cli_wrapper.py'
if (Test-Path $wrapper) {
    Write-Host "Ejecutando pipeline interactivo mediante wrapper (desde backend/app)..."
    python $wrapper --interactive --use-regex --pseudonymize --model es
} else {
    Write-Warning "run_cli_wrapper.py no encontrado en $wrapper"
}