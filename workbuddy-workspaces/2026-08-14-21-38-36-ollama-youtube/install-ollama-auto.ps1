#Requires -Version 5.1
$ErrorActionPreference = 'Continue'

# Ollama unattended install to D drive, pull TranslateGemma 4B
# All progress logged to D:\AI\logs\install.log

$ROOT       = 'D:\AI'
$OLLAMA_DIR = "$ROOT\Ollama"
$MODELS_DIR = "$ROOT\models"
$LOG_DIR    = "$ROOT\logs"
$SCRIPT_DIR = "$ROOT\scripts"
$SETUP_URL  = 'https://ollama.com/download/OllamaSetup.exe'
$SETUP_FILE = "$OLLAMA_DIR\OllamaSetup.exe"
$INSTALL_LOG = "$LOG_DIR\install.log"
$MODELS = @('translategemma:4b', 'qwen3:4b')

function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
    Add-Content -Path $INSTALL_LOG -Value $line -Encoding utf8
}

if (Test-Path $INSTALL_LOG) { Remove-Item $INSTALL_LOG -Force }
Log '===== Ollama unattended install start ====='

# Step 1: check D drive
Log 'Step 1/7: check D drive'
if (-not (Test-Path 'D:\')) {
    Log 'FATAL: D drive not exist, exit'
    exit 1
}
$d = Get-PSDrive D
$freeGB = [math]::Round($d.Free / 1GB, 1)
Log "  D drive free $freeGB GB"
if ($freeGB -lt 20) {
    Log "FATAL: D drive only $freeGB GB free, need at least 20GB"
    exit 1
}

# Step 2: create dirs
Log 'Step 2/7: create dirs'
foreach ($p in @($ROOT, $OLLAMA_DIR, $MODELS_DIR, $LOG_DIR, $SCRIPT_DIR)) {
    New-Item -ItemType Directory -Force -Path $p | Out-Null
    Log "  created: $p"
}

# Step 3: download installer
Log 'Step 3/7: download OllamaSetup.exe'
if (Test-Path $SETUP_FILE -and (Get-Item $SETUP_FILE).Length -gt 1MB) {
    Log "  already exists $SETUP_FILE, skip"
} else {
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $SETUP_URL -OutFile $SETUP_FILE -UseBasicParsing
        $sizeMB = [math]::Round((Get-Item $SETUP_FILE).Length / 1MB, 1)
        Log "  download done, size $sizeMB MB"
    } catch {
        Log "FATAL: download fail - $_"
        exit 1
    }
}

# Step 4: silent install
Log 'Step 4/7: silent install Ollama'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
$ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaExe) {
    Log "  ollama already installed at $($ollamaExe.Source), skip"
} else {
    Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1
    try {
        $proc = Start-Process -FilePath $SETUP_FILE -ArgumentList "/DIR=`"$OLLAMA_DIR`"" -Wait -PassThru
        Log "  install exit code $($proc.ExitCode)"
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    } catch {
        Log "FATAL: install fail - $_"
        exit 1
    }
}

# Step 5: set env var
Log 'Step 5/7: set OLLAMA_MODELS env var'
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $MODELS_DIR, 'User')
$env:OLLAMA_MODELS = $MODELS_DIR
Log "  OLLAMA_MODELS = $MODELS_DIR"

# Step 6: start server
Log 'Step 6/7: start ollama serve'
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
$serveLog = "$LOG_DIR\ollama-serve.log"
$serveErr = "$LOG_DIR\ollama-serve.err"
Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput $serveLog -RedirectStandardError $serveErr
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 3 -ErrorAction Stop
        $ok = $true
        $count = $r.models.Count
        Log "  service ready, $count models installed"
        break
    } catch { }
}
if (-not $ok) {
    Log 'WARN: service slow to start, but model pull will wait'
}

# Step 7: pull models
foreach ($m in $MODELS) {
    Log "Step 7/7: pull model $m"
    $pullLog = "$LOG_DIR\pull-$($m.Replace(':','_')).log"
    & ollama pull $m *>&1 | Out-File -FilePath $pullLog -Encoding utf8
    Log "  $m pull done, log at $pullLog"
}

# Done
Log '===== ALL DONE ====='
& ollama list | Out-File -FilePath "$LOG_DIR\final-list.txt" -Encoding utf8
Log 'done. see D:\AI\logs\'
