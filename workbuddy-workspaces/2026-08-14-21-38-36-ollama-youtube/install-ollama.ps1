#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

# ============================================================
#  Ollama 一键装 D 盘 + 拉 TranslateGemma 4B 模型
#  目标目录: D:\AI\{Ollama, models, logs, scripts}
#  运行: powershell -ExecutionPolicy Bypass -File .\install-ollama.ps1
# ============================================================

# --- 配置 ---
$ROOT       = 'D:\AI'
$OLLAMA_DIR = "$ROOT\Ollama"
$MODELS_DIR = "$ROOT\models"
$LOG_DIR    = "$ROOT\logs"
$SCRIPT_DIR = "$ROOT\scripts"
$SETUP_URL  = 'https://ollama.com/download/OllamaSetup.exe'
$SETUP_FILE = "$OLLAMA_DIR\OllamaSetup.exe"

# 主推模型 + 备选模型
$PRIMARY_MODEL = 'translategemma:4b'   # 专为翻译优化, 3.3GB, 55 语言
$BACKUP_MODEL  = 'qwen3:4b'             # 通用 LLM, 中文母语, 备用对比

function Step($n, $msg, $color = 'Cyan') {
    Write-Host "[$n] $msg" -ForegroundColor $color
}
function OK($msg) { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }

# --- 1. 检查 D 盘 ---
Step '1/8' '检查 D 盘空间...'
if (-not (Test-Path 'D:\')) { Write-Error 'D 盘不存在'; exit 1 }
$d = Get-PSDrive D
$freeGB = [math]::Round($d.Free / 1GB, 1)
if ($freeGB -lt 20) { Write-Error "D 盘剩 $freeGB GB，至少要 20GB"; exit 1 }
OK "D 盘剩余 $freeGB GB"

# --- 2. 创建目录 ---
Step '2/8' '创建目录结构...'
foreach ($p in @($ROOT, $OLLAMA_DIR, $MODELS_DIR, $LOG_DIR, $SCRIPT_DIR)) {
    New-Item -ItemType Directory -Force -Path $p | Out-Null
}
OK "目录就绪:"
Write-Host "    $OLLAMA_DIR  (Ollama 程序)"
Write-Host "    $MODELS_DIR  (模型数据)"
Write-Host "    $LOG_DIR     (日志)"
Write-Host "    $SCRIPT_DIR  (脚本)"

# --- 3. 检查是否已装 ---
Step '3/8' '检查 Ollama 是否已安装...'
$needInstall = $true
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    OK "Ollama 已存在: $($ollamaPath.Source)"
    $reinstall = Read-Host '  重新安装? (y/N)'
    if ($reinstall -ne 'y') { $needInstall = $false }
    else {
        Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 1
    }
}

# --- 4. 下载安装包 ---
if ($needInstall) {
    if (Test-Path $SETUP_FILE -and (Get-Item $SETUP_FILE).Length -gt 1MB) {
        Step '4/8' '已存在 OllamaSetup.exe, 跳过下载'
    } else {
        Step '4/8' '下载 OllamaSetup.exe...'
        Invoke-WebRequest -Uri $SETUP_URL -OutFile $SETUP_FILE
    }
    OK "安装包: $SETUP_FILE"

    # --- 5. 静默安装到 D:\AI\Ollama ---
    Step '5/8' "静默安装 Ollama 到 $OLLAMA_DIR (可能要 30-60 秒)..."
    $proc = Start-Process -FilePath $SETUP_FILE -ArgumentList "/DIR=`"$OLLAMA_DIR`"" -Wait -PassThru
    if ($proc.ExitCode -ne 0) { Warn "退出码 $($proc.ExitCode), 可能需要手动检查" }
    else { OK '安装完成' }
}

# --- 6. 设置环境变量 ---
Step '6/8' "设置环境变量 OLLAMA_MODELS=$MODELS_DIR"
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $MODELS_DIR, 'User')
$env:OLLAMA_MODELS = $MODELS_DIR
OK '用户级环境变量已设 (新终端生效)'

# --- 7. 启动服务 ---
Step '7/8' '启动 Ollama 服务 (后台)...'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
# 杀掉旧进程
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput "$LOG_DIR\ollama-serve.log" -RedirectStandardError "$LOG_DIR\ollama-serve.err"
$ok = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 3
        $ok = $true
        break
    } catch { Write-Host '.' -NoNewline }
}
Write-Host ''
if ($ok) { OK 'Ollama 服务已在 http://localhost:11434' }
else { Warn '服务启动慢, 请稍等手动检查 ollama serve' }

# --- 8. 拉模型 ---
Step '8/8' "拉模型 $PRIMARY_MODEL (3.3GB)..."
& ollama pull $PRIMARY_MODEL *>&1 | Tee-Object -FilePath "$LOG_DIR\pull-primary.log"

$pull2 = Read-Host "  也拉 $BACKUP_MODEL 备用对比? (Y/n)"
if ($pull2 -ne 'n') {
    & ollama pull $BACKUP_MODEL *>&1 | Tee-Object -FilePath "$LOG_DIR\pull-backup.log"
}

# --- 完成 ---
Write-Host ''
Write-Host '================================================' -ForegroundColor Green
Write-Host '  ✅ 全部完成' -ForegroundColor Green
Write-Host '================================================' -ForegroundColor Green
Write-Host ''
Write-Host "Ollama 程序:   $OLLAMA_DIR"
Write-Host "模型存储:      $MODELS_DIR"
Write-Host "日志:          $LOG_DIR"
Write-Host ''
Write-Host '服务:        http://localhost:11434'
Write-Host 'OpenAI 兼容: http://localhost:11434/v1/chat/completions'
Write-Host ''
Write-Host '--- 油猴脚本配置 (Tampermonkey 菜单) ---' -ForegroundColor Yellow
Write-Host '🤖 Chat 端点: http://localhost:11434/v1/chat/completions'
Write-Host '🔑 Chat Key:  (留空)'
Write-Host "🎯 Chat 模型: $PRIMARY_MODEL  (推荐)"
Write-Host "                或 $BACKUP_MODEL  (备选)"
Write-Host ''
Write-Host '--- 已安装模型 ---' -ForegroundColor Yellow
& ollama list
Write-Host ''
Write-Host '常用命令:'
Write-Host '  ollama list             查所有模型'
Write-Host '  ollama run <name>       交互式跑模型'
Write-Host '  ollama rm <name>        删模型'
Write-Host '  ollama stop <name>      卸载模型从内存'
Write-Host ''
