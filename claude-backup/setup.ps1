# Claude Code 環境還原腳本
# 使用方式：在 PowerShell 執行 .\setup.ps1
# 若出現執行原則錯誤，先執行：Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

param(
    [string]$ProjectPath = "$env:USERPROFILE\Documents\ClaudeCode"
)

$ClaudeDir = "$env:USERPROFILE\.claude"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Claude Code 環境還原 ===" -ForegroundColor Cyan
Write-Host "Claude 設定目錄：$ClaudeDir"
Write-Host "專案目錄：$ProjectPath"
Write-Host ""

# 1. 建立必要目錄
$SkillDir = "$ClaudeDir\skills\stock-advisor"
$ProjectSlug = $ProjectPath -replace "[:\\]", "-" -replace "^-", ""
$MemoryDir = "$ClaudeDir\projects\$ProjectSlug\memory"

New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
New-Item -ItemType Directory -Force -Path $MemoryDir | Out-Null
New-Item -ItemType Directory -Force -Path $ProjectPath | Out-Null
Write-Host "[1/4] 目錄建立完成" -ForegroundColor Green

# 2. 複製全域設定
Copy-Item -Force "$ScriptDir\settings.json" "$ClaudeDir\settings.json"
Copy-Item -Force "$ScriptDir\statusline-command.sh" "$ClaudeDir\statusline-command.sh"
Write-Host "[2/4] 全域設定還原完成 (settings.json, statusline)" -ForegroundColor Green

# 3. 複製 Skill
Copy-Item -Force "$ScriptDir\skills\stock-advisor\SKILL.md" "$SkillDir\SKILL.md"
Write-Host "[3/4] Skills 還原完成 (stock-advisor)" -ForegroundColor Green

# 4. 複製 Memory
Copy-Item -Force "$ScriptDir\memory\*" "$MemoryDir\"
Write-Host "[4/4] Memory 還原完成" -ForegroundColor Green

# 5. 複製 CLAUDE.md 到專案目錄（若不存在）
$TargetClaude = "$ProjectPath\CLAUDE.md"
if (-not (Test-Path $TargetClaude)) {
    Copy-Item -Force "$ScriptDir\CLAUDE.md" $TargetClaude
    Write-Host "[+]  CLAUDE.md 複製到 $ProjectPath" -ForegroundColor Green
} else {
    Write-Host "[~]  CLAUDE.md 已存在，跳過（避免覆蓋）" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "完成！請重新啟動 Claude Code。" -ForegroundColor Cyan
Write-Host "若 statusline 腳本無法執行，需確認 Git Bash / WSL 已安裝。"
