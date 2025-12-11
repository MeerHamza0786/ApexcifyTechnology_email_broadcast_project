# PowerShell script to update SMTP credentials in .env file
# Usage: .\update_smtp.ps1

Write-Host "`n=== SMTP Configuration Updater ===" -ForegroundColor Cyan
Write-Host "`nThis script will help you update your SMTP credentials in the .env file.`n" -ForegroundColor Yellow

# Get Gmail address
$gmail = Read-Host "Enter your Gmail address (e.g., yourname@gmail.com)"
if (-not $gmail -or $gmail -notmatch "@") {
    Write-Host "Invalid email address. Exiting." -ForegroundColor Red
    exit 1
}

# Get App Password
Write-Host "`nEnter your Gmail App Password (16 characters)" -ForegroundColor Yellow
Write-Host "Get one at: https://myaccount.google.com/apppasswords" -ForegroundColor Gray
$appPassword = Read-Host "App Password" -AsSecureString
$appPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($appPassword)
)

if (-not $appPasswordPlain -or $appPasswordPlain.Length -lt 10) {
    Write-Host "App Password seems too short. Please check and try again." -ForegroundColor Red
    exit 1
}

# Remove spaces from app password
$appPasswordPlain = $appPasswordPlain -replace '\s', ''

Write-Host "`nUpdating .env file..." -ForegroundColor Green

# Read current .env file
$envContent = Get-Content .env -Raw

# Update SMTP_USERNAME
$envContent = $envContent -replace 'SMTP_USERNAME=.*', "SMTP_USERNAME=$gmail"

# Update SMTP_PASSWORD
$envContent = $envContent -replace 'SMTP_PASSWORD=.*', "SMTP_PASSWORD=$appPasswordPlain"

# Write back to file
$envContent | Set-Content .env -NoNewline

Write-Host "✓ .env file updated successfully!" -ForegroundColor Green
Write-Host "`nUpdated values:" -ForegroundColor Cyan
Write-Host "  SMTP_USERNAME=$gmail" -ForegroundColor White
Write-Host "  SMTP_PASSWORD=*** (hidden)" -ForegroundColor White
Write-Host "`n⚠️  IMPORTANT: Restart your Flask app for changes to take effect!" -ForegroundColor Yellow
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

