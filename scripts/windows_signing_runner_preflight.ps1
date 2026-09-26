# SwiftFilez Windows self-hosted signing runner preflight.
# Run in PowerShell as the Windows account that owns the signing certificate.

$ErrorActionPreference = "Stop"

Write-Host "SwiftFilez release-runner preflight" -ForegroundColor Cyan

$required = @(
  @{ Name = "python"; Hint = "Install Python 3.12+ and add it to PATH." },
  @{ Name = "git"; Hint = "Install Git for Windows." },
  @{ Name = "gh"; Hint = "Install GitHub CLI." },
  @{ Name = "signtool.exe"; Hint = "Install Windows SDK Signing Tools and add signtool.exe to PATH." }
)

$failed = $false
foreach ($tool in $required) {
  if (Get-Command $tool.Name -ErrorAction SilentlyContinue) {
    Write-Host "[PASS] $($tool.Name)" -ForegroundColor Green
  } else {
    Write-Host "[FAIL] $($tool.Name) - $($tool.Hint)" -ForegroundColor Red
    $failed = $true
  }
}

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
  Write-Host "[PASS] Inno Setup 6" -ForegroundColor Green
} else {
  Write-Host "[FAIL] Inno Setup 6 - expected $iscc" -ForegroundColor Red
  $failed = $true
}

$certs = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue
if ($certs) {
  Write-Host "[PASS] Code-signing certificate(s) found:" -ForegroundColor Green
  $certs | Select-Object Subject, Thumbprint, HasPrivateKey, NotAfter | Format-Table -AutoSize
} else {
  Write-Host "[FAIL] No code-signing certificate found in Cert:\CurrentUser\My." -ForegroundColor Red
  $failed = $true
}

if ($failed) {
  throw "Runner preflight failed. Fix the items above before publishing a signed release."
}

Write-Host "Runner is ready for SwiftFilez signed Windows releases." -ForegroundColor Cyan
