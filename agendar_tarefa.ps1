# Auto-eleva para Administrador se necessario
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$NomeTarefa    = "PharmaFlow_Scraper_Semanal"
$PastaTrabalho = Split-Path -Parent $PSCommandPath
$Python        = (Get-Command python).Source
$Script        = Join-Path $PastaTrabalho "main.py"
$LogDir        = Join-Path $PastaTrabalho "logs"
$LogFile       = Join-Path $LogDir "pipeline.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false -ErrorAction SilentlyContinue

$Acao = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Script`"" `
    -WorkingDirectory $PastaTrabalho

$Gatilho = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Sunday `
    -At "22:00"

$Configuracoes = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName   $NomeTarefa `
    -Action     $Acao `
    -Trigger    $Gatilho `
    -Settings   $Configuracoes `
    -RunLevel   Highest `
    -Description "PharmaFlow: coleta semanal das 70 farmacias via PharmaChatBot"

Write-Host ""
Write-Host "Tarefa '$NomeTarefa' criada com sucesso!" -ForegroundColor Green
Write-Host "Execucao: todo domingo as 22:00" -ForegroundColor Cyan
Write-Host "Log: $LogFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para testar agora rode:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$NomeTarefa'" -ForegroundColor White
Write-Host ""
Read-Host "Pressione Enter para fechar"
