# Stripe CLI Troubleshooting Guide

This guide helps resolve common connectivity and authentication issues with the Stripe CLI on Windows, particularly when using VPNs or dealing with "legacy-style API key" errors.

## 1. Upgrade Stripe CLI
Ensure you are running the latest version. Outdated versions may not support newer authentication flows.

**Using Scoop:**
```powershell
scoop update stripe
```

**Using Chocolatey:**
```powershell
choco upgrade stripe-cli
```

**Using Winget:**
```powershell
winget upgrade Stripe.StripeCLI
```

## 2. Proxy & Network Configuration
If you see DNS errors or timeouts, ensure your proxy settings are clean.

### Disable WinHTTP Proxy
Admin PowerShell:
```powershell
netsh winhttp reset proxy
```

### Clear Environment Proxy Variables
PowerShell:
```powershell
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue
```

## 3. Login & API Keys

### "Legacy-style API key unsupported" Error
This error occurs if the CLI tries to use an old Root Secret Key (`sk_test_...`) directly or if the stored config is corrupt.

**Fix:**
1. **Force Re-login via Browser:**
   ```powershell
   stripe login --interactive
   ```
   Follow the browser prompt to authorize. This generates a restricted key automatically.

2. **Manually Create a Restricted Key (If interactive login fails):**
   - Go to [Stripe Dashboard > Developers > API keys](https://dashboard.stripe.com/test/apikeys).
   - Click **+ Create restricted key**.
   - Name it "Stripe CLI Manual Config".
   - Give **Write** access to the resources you are testing (e.g., Webhooks, PaymentIntents).
   - Copy the key (`rk_test_...`).
   - Set it in your environment or use with the inline flag:
     ```powershell
     $env:STRIPE_API_KEY="rk_test_..."
     stripe listen --api-key $env:STRIPE_API_KEY
     ```

## 4. VPN & AVG HTTPS Inspection Mitigation
If `curl` commands fail with SSL/TLS errors or connections hang while on AVG Secure VPN (WireGuard):

1. **AVG Settings:** Check if "Web Shield" or "HTTPS Scanning" is enabled. Temporarily disable it to confirm if it's intercepting the CLI's Go-based TLS handshake.
2. **VPN Protocol:** If WireGuard has MTU issues (common with packet drops), switch to OpenVPN (UDP) in AVG settings if available.
3. **DNS:** Hardcode Google DNS (8.8.8.8) or Cloudflare (1.1.1.1) on your network adapter if local DNS resolution is flaky.

## 5. Diagnostic Script
Run the included diagnostic script to check connectivity:
```powershell
.\scripts\stripe_cli_diagnose.ps1
```
Check the generated log in `.\logs\` for specific error codes.
