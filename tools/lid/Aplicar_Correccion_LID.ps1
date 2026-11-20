param(
    [Parameter(Mandatory = $true)][string]$ProjectPath
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$package = $PSScriptRoot
$manifestPath = Join-Path $package 'Manifiesto_LID.json'
if (!(Test-Path -LiteralPath $manifestPath)) { throw 'Ejecuta la copia del instalador incluida en la raiz del ZIP extraido.' }
if (!(Test-Path -LiteralPath (Join-Path $project 'ProjectSettings/ProjectVersion.txt'))) { throw 'La ruta no corresponde a la raiz del proyecto Unity.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
function Get-LfHash([string]$Path) {
    $text = [IO.File]::ReadAllText($Path).Replace("`r`n", "`n")
    $bytes = [Text.Encoding]::UTF8.GetBytes($text)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
$pending = @()
foreach ($entry in $manifest.files) {
    if ($entry.path -match '(^[\\/]|(^|[\\/])\.\.([\\/]|$))') { throw 'Ruta relativa invalida en el manifiesto.' }
    $source = Join-Path (Join-Path $package 'Archivos') $entry.path
    $target = Join-Path $project $entry.path
    if (!(Test-Path -LiteralPath $source)) { throw "Falta el archivo del paquete: $($entry.path)" }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.after_sha256) { throw "El paquete esta alterado: $($entry.path)" }
    $current = $null
    if (Test-Path -LiteralPath $target) { $current = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() }
    if ($current -eq $entry.after_sha256) { continue }
    $normalized = $null
    if ($current -and $entry.text_lf) { $normalized = Get-LfHash $target }
    if ($normalized -and $normalized -eq $entry.after_lf_sha256) { continue }
    if ($current -ne $entry.before_sha256 -and !($normalized -and $normalized -eq $entry.before_lf_sha256)) { throw "El archivo tiene otra version o cambios locales: $($entry.path). No se ha copiado nada. Revisa el diff con tu equipo." }
    $pending += $entry
}
if ($pending.Count -eq 0) { Write-Host 'La correccion ya esta aplicada.'; return }
if (Test-Path -LiteralPath (Join-Path $project '.git')) {
    $status = & git -C $project status --porcelain
    if ($LASTEXITCODE -ne 0 -or $status) { throw 'Guarda o resguarda los cambios locales del proyecto antes de aplicar este paquete. No se ha copiado nada.' }
    $branch = & git -C $project branch --show-current
    if ($LASTEXITCODE -ne 0 -or !$branch) { throw 'El repositorio necesita una rama de trabajo activa.' }
    if ($branch -in @('main', 'develop')) {
        & git -C $project switch -c 'fix/lid-sotano-distribucion'
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la rama. Selecciona una rama de trabajo y vuelve a ejecutar el instalador.' }
    }
}
$backup = Join-Path (Split-Path $project -Parent) ('LID_Respaldo_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null
$copied = @()
try {
    # Back up all affected existing files before starting the copy phase.
    foreach ($entry in $pending) {
        $target = Join-Path $project $entry.path
        if (Test-Path -LiteralPath $target) {
            $saved = Join-Path $backup $entry.path
            New-Item -ItemType Directory -Path (Split-Path $saved -Parent) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $saved -Force
        }
    }
    foreach ($entry in $pending) {
        $source = Join-Path (Join-Path $package 'Archivos') $entry.path
        $target = Join-Path $project $entry.path
        New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
        $copied += $entry
        Copy-Item -LiteralPath $source -Destination $target -Force
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.after_sha256) { throw "Fallo al copiar: $($entry.path)" }
    }
} catch {
    foreach ($entry in $copied) {
        $target = Join-Path $project $entry.path
        $saved = Join-Path $backup $entry.path
        if (Test-Path -LiteralPath $saved) { Copy-Item -LiteralPath $saved -Destination $target -Force }
        elseif (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
    }
    throw
}
Write-Host "Correccion aplicada. Respaldo: $backup"
Write-Host 'Abre Unity 6000.3.10f1 y Campus. No vuelvas a generar o integrar otro LID.'
Write-Host 'Ejecuta Tools > UPCH > LID completo > Validar niveles y superposiciones en Campus.'
Write-Host 'Revisa la consola y recorre todas las plantas en Play antes del commit y PR a develop.'
