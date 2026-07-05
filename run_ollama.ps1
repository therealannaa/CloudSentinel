<#
  Quick Ollama runner for CloudKC-Bench arms on Windows (free, local, GPU-accelerated).

  Prereqs (one-time):
    1. Install Ollama for Windows:  https://ollama.com/download/windows
       (it runs as a background service and auto-uses your NVIDIA GPU)
    2. Pull a model sized to your VRAM:
         ollama pull llama3.2:3b        # great for a 4 GB RTX 2050
       (or qwen2.5:3b ; 7B models also work but partly offload to CPU)
    3. Install deps:  pip install -r requirements-bench.txt

  Usage (PowerShell, from the repo folder):
    .\run_ollama.ps1            # smoke test: 1 scenario, arm A2, 1 seed
    .\run_ollama.ps1 full      # full ablation A1-A4 x dev x 3 seeds

  Env overrides: $env:LLM_MODEL, $env:ENVIRONMENT (default 'synthetic' = no Docker needed).
#>
param([string]$Mode = "smoke")
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not $env:LLM_BASE_URL) { $env:LLM_BASE_URL = "http://localhost:11434/v1" }
if (-not $env:LLM_API_KEY)  { $env:LLM_API_KEY  = "ollama" }
if (-not $env:LLM_MODEL)    { $env:LLM_MODEL    = "llama3.2:3b" }
$envName = if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { "synthetic" }

# Verify Ollama is reachable before spending time.
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "ERROR: Ollama not reachable at http://localhost:11434" -ForegroundColor Red
    Write-Host "  Install:  https://ollama.com/download/windows"
    Write-Host "  Pull:     ollama pull $($env:LLM_MODEL)"
    exit 1
}
Write-Host "Ollama reachable. Model=$($env:LLM_MODEL)  env=$envName" -ForegroundColor Green

if ($Mode -eq "full") {
    python -m benchmark.cli run-arms --arms A1,A2,A3,A4 --set dev --seeds 3 `
        --environment $envName --csv results_ollama.csv
} else {
    Write-Host "Smoke test (1 scenario, arm A2, 1 seed). Run '.\run_ollama.ps1 full' for the ablation."
    python -m benchmark.cli run-arms --arms A2 --set dev --limit 1 --seeds 1 --environment $envName
}
