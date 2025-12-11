# How to Configure Gmail SMTP Settings

## Step 1: Get Your Gmail App Password

1. **Go to Google App Passwords**: https://myaccount.google.com/apppasswords
2. **Sign in** to your Google account
3. **If you see "2-Step Verification is off"**:
   - Click "Get Started" to enable 2-Step Verification
   - Follow the setup process
   - Come back to App Passwords after enabling it
4. **Select App**: Choose "Mail"
5. **Select Device**: Choose "Other (Custom name)"
6. **Enter name**: Type "Email Broadcast" or any name you prefer
7. **Click "Generate"**
8. **Copy the 16-character password** (it will look like: `abcd efgh ijkl mnop`)
   - You can remove the spaces when pasting

## Step 2: Update Your .env File

Open the `.env` file in your project root and update these two lines:

**Find these lines:**
```
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
```

**Replace with your actual credentials:**
```
SMTP_USERNAME=your_actual_gmail@gmail.com
SMTP_PASSWORD=your_16_character_app_password
```

**Example:**
```
SMTP_USERNAME=john.doe@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
```

**Important Notes:**
- Use your **actual Gmail address** (the one you use to sign in)
- Use the **App Password** from Step 1, NOT your regular Gmail password
- The App Password can have spaces - they will be ignored
- Make sure there are no extra spaces before or after the `=` sign

## Step 3: Restart Your Flask App

After updating the `.env` file:

1. **Stop the Flask app** (press `Ctrl+C` in the terminal where it's running)
2. **Start it again**:
   ```bash
   python main.py
   ```
   or
   ```bash
   flask --app webapp.app run
   ```

## Troubleshooting

### "App Passwords isn't available for my account"
- You need to enable 2-Step Verification first
- Go to: https://myaccount.google.com/security
- Enable 2-Step Verification, then try App Passwords again

### "Still getting authentication errors"
- Make sure you're using the App Password, not your regular password
- Check for typos in the `.env` file
- Make sure you restarted the Flask app after updating `.env`
- Verify the App Password is still valid (they can be revoked)

### "Can't find the .env file"
- The `.env` file is in the project root: `E:\email_broadcast_project\.env`
- If it doesn't exist, create it with the SMTP settings

## Quick Reference

Your `.env` file should have these SMTP settings:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_actual_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_SENDER_NAME=Broadcast Studio
```

