$ErrorActionPreference = "Continue"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = ".\logs"

# Create logs directory if it doesn't exist
if (!(Test-Path $LogDir)) { 
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null 
}

$LogFile = "$LogDir\stripe_cli_diagnose_$Timestamp.txt"

# Capture all output
Start-Transcript -Path $LogFile

Write-Host "=========================================="
Write-Host "Stripe CLI Diagnostics - $Timestamp"
Write-Host "=========================================="
Write-Host ""

Write-Host "[1] Checking Stripe CLI Version and Path"
Write-Host "------------------------------------------"
try {
    stripe version
} catch {
    Write-Warning "Stripe CLI not found or error running 'stripe version'"
}
$stripePath = Get-Command stripe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if ($stripePath) {
    Write-Host "CLI Path: $stripePath"
} else {
    Write-Warning "Stripe executable not found in PATH"
}
Write-Host ""

Write-Host "[2] Checking Proxy Configuration"
Write-Host "------------------------------------------"
Write-Host "WinHTTP Proxy:"
netsh winhttp show proxy

Write-Host "`nEnvironment Variables (Proxy):"
$envProxies = Get-ChildItem env: | Where-Object { $_.Name -match 'proxy' }
if ($envProxies) {
    $envProxies | Format-Table -AutoSize
} else {
    Write-Host "No proxy environment variables found."
}
Write-Host ""

Write-Host "[3] HTTPS Head Checks (curl)"
Write-Host "------------------------------------------"
Write-Host "Testing: https://dashboard.stripe.com/stripecli/auth"
try {
    # Using curl.exe specifically to test external connectivity, not PowerShell's curl alias
    & curl.exe -I https://dashboard.stripe.com/stripecli/auth --connect-timeout 5
} catch {
    Write-Error "Failed to run curl check for dashboard"
}

Write-Host "`nTesting: https://api.stripe.com/v1/"
try {
    & curl.exe -I https://api.stripe.com/v1/ --connect-timeout 5
} catch {
    Write-Error "Failed to run curl check for api"
}
Write-Host ""

Write-Host "[4] TCP Connection Checks (Port 443)"
Write-Host "------------------------------------------"
Write-Host "Testing dashboard.stripe.com:443..."
Test-NetConnection dashboard.stripe.com -Port 443

Write-Host "`nTesting api.stripe.com:443..."
Test-NetConnection api.stripe.com -Port 443
Write-Host ""

Write-Host "[5] DNS Resolution Checks"
Write-Host "------------------------------------------"
Write-Host "Resolving dashboard.stripe.com..."
try {
    Resolve-DnsName dashboard.stripe.com -ErrorAction Stop | Format-Table -AutoSize
} catch {
    Write-Error "DNS Resolution failed for dashboard.stripe.com: $_"
}

Write-Host "`nResolving api.stripe.com..."
try {
    Resolve-DnsName api.stripe.com -ErrorAction Stop | Format-Table -AutoSize
} catch {
    Write-Error "DNS Resolution failed for api.stripe.com: $_"
}
Write-Host ""

Stop-Transcript

Write-Host "Diagnosis complete."
Write-Host "Log saved to: $LogFile"
