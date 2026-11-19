# Windows setup. Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"

function Need($cmd, $wingetId) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "Installing $wingetId ..."
        winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements
        Write-Host "Close and reopen PowerShell after installs so PATH updates, then run this script again."
        exit 1
    }
}

Need "python" "Python.Python.3.12"
Need "ffmpeg" "Gyan.FFmpeg"
Need "git" "Git.Git"

python --version
ffmpeg -version | Select-Object -First 1

if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest

if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example" }

# Downloads the free Kokoro voice model (~350 MB) once.
& .\.venv\Scripts\python.exe -c "from factory.voice_engine.kokoro import ensure_models; ensure_models()"

# 3D renderer: three.js in headless Chromium. Playwright is installed here (not in package.json, because
# the cloud container ships its own). On exFAT drives Playwright's browser installer cannot lock files:
# set PLAYWRIGHT_BROWSERS_PATH to a folder on the same drive and unpack the browsers there by hand.
Push-Location renderer; npm install; npm install --no-save playwright; npx playwright install chromium; Pop-Location
# With an NVIDIA/AMD GPU, set $env:RENDER_GPU="1" before producing: ~0.1-0.2 s per frame instead of ~3 s.

& .\.venv\Scripts\python.exe -m pytest -q
Write-Host ""
Write-Host "Done. Render the first Short with:"
Write-Host "  .\.venv\Scripts\python.exe -m factory produce falling-slinky"
