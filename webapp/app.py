from __future__ import annotations

import os
import sys
from pathlib import Path
from functools import wraps
from datetime import datetime, timedelta
import shutil

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.recipients import RECEIVER_EMAILS
from app.core.message import EMAIL_SUBJECT, EMAIL_BODY
from app.services.mailer import send_bulk_email
from app.utils.logger import log_info

try:
    from .forms import BroadcastForm, RecipientForm, LoginForm
except ImportError:
    from forms import BroadcastForm, RecipientForm, LoginForm

# Load .env file from project root
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv()  # Fallback to default location

# Configuration - strip whitespace and ensure no hidden characters
APP_SECRET = os.getenv("APP_SECRET") or "dev-secret-change-me"
ADMIN_USERNAME = (os.getenv("ADMIN_USERNAME", "admin") or "admin").strip()
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD", "admin") or "admin").strip()

# Log loaded credentials for debugging (remove in production)
log_info(f"Loaded admin credentials - Username: '{ADMIN_USERNAME}' (len: {len(ADMIN_USERNAME)}), Password: '{ADMIN_PASSWORD[:3]}***' (len: {len(ADMIN_PASSWORD)})")
SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 3600))  # 1 hour default
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
RATE_LIMIT_WINDOW = 300  # 5 minutes

app = Flask(__name__)
app.config.update(
    SECRET_KEY=APP_SECRET,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_LIFETIME),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max request size
)

# In-memory storage for login attempts (use Redis in production)
login_attempts = {}


def clean_old_attempts():
    """Remove login attempts older than RATE_LIMIT_WINDOW"""
    now = datetime.now()
    expired = [
        ip for ip, data in login_attempts.items()
        if (now - data['first_attempt']).total_seconds() > RATE_LIMIT_WINDOW
    ]
    for ip in expired:
        del login_attempts[ip]


def is_rate_limited(ip: str) -> bool:
    """Check if IP is rate limited"""
    clean_old_attempts()
    if ip in login_attempts:
        attempts = login_attempts[ip]
        if attempts['count'] >= MAX_LOGIN_ATTEMPTS:
            time_passed = (datetime.now() - attempts['first_attempt']).total_seconds()
            if time_passed < RATE_LIMIT_WINDOW:
                return True
            else:
                del login_attempts[ip]
    return False


def record_failed_attempt(ip: str):
    """Record a failed login attempt"""
    now = datetime.now()
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 1, 'first_attempt': now}
    else:
        login_attempts[ip]['count'] += 1


def clear_failed_attempts(ip: str):
    """Clear failed attempts for an IP"""
    if ip in login_attempts:
        del login_attempts[ip]


def is_logged_in() -> bool:
    """Check if user is logged in and session is valid"""
    if not session.get("logged_in", False):
        return False
    
    # Check session expiry
    login_time = session.get("login_time")
    if login_time:
        elapsed = (datetime.now() - datetime.fromisoformat(login_time)).total_seconds()
        if elapsed > SESSION_LIFETIME:
            session.clear()
            return False
    
    return True


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def make_session_permanent():
    """Make session permanent and refresh on each request"""
    session.permanent = True
    if is_logged_in():
        session.modified = True


@app.context_processor
def inject_globals():
    """Expose common values to all templates."""
    return {
        "current_year": datetime.utcnow().year,
        "app_name": "Email Broadcast",
        "logged_in": is_logged_in(),
    }


@app.route("/", methods=["GET"])
def index():
    if not is_logged_in():
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    
    ip_address = request.remote_addr
    
    # Clear rate limiting on GET request (allows fresh login attempts)
    if request.method == "GET":
        clear_failed_attempts(ip_address)
    
    # Convert request.form to dict for form initialization
    # Flask's request.form is a MultiDict - dict() conversion gets first value automatically
    form_data = dict(request.form) if request.method == "POST" else None
    form = LoginForm(form_data)
    
    if request.method == "POST":
        # Check rate limiting
        if is_rate_limited(ip_address):
            remaining_time = RATE_LIMIT_WINDOW - (
                datetime.now() - login_attempts[ip_address]['first_attempt']
            ).total_seconds()
            flash(
                f"Too many failed attempts. Please try again in {int(remaining_time)} seconds.",
                "danger"
            )
            log_info(f"Rate limited login attempt from {ip_address}")
            return render_template("login.html", form=form), 429
        
        if form.validate():
            username = (form.username or "").strip()
            password = (form.password or "").strip()
            
            # Compare credentials (case-sensitive)
            username_match = username == ADMIN_USERNAME
            password_match = password == ADMIN_PASSWORD
            
            # Debug logging with full details
            log_info(f"Login attempt - Username: '{username}' (expected: '{ADMIN_USERNAME}'), Match: {username_match}")
            log_info(f"Password provided: '{password}' (length: {len(password)})")
            log_info(f"Password expected: '{ADMIN_PASSWORD}' (length: {len(ADMIN_PASSWORD)})")
            log_info(f"Password match: {password_match}")
            log_info(f"Password bytes comparison: {password.encode() == ADMIN_PASSWORD.encode()}")
            
            if username_match and password_match:
                session.clear()
                session["logged_in"] = True
                session["login_time"] = datetime.now().isoformat()
                session["ip_address"] = ip_address
                session["username"] = username
                clear_failed_attempts(ip_address)
                
                flash("Logged in successfully.", "success")
                log_info(f"Successful login from {ip_address} as {username}")
                
                # Redirect to next page if specified
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))
            
            record_failed_attempt(ip_address)
            attempts_left = MAX_LOGIN_ATTEMPTS - login_attempts.get(ip_address, {}).get('count', 0)
            form.add_error("password", "Incorrect username or password.")
            flash(
                f"Invalid credentials. {max(0, attempts_left)} attempt(s) remaining.",
                "danger"
            )
            log_info(f"Failed login attempt from {ip_address} (user: {username})")
        else:
            flash("Please fix the highlighted errors.", "danger")
    
    return render_template("login.html", form=form)


@app.route("/reset-login-attempts", methods=["GET"])
def reset_login_attempts():
    """Reset login attempts for debugging - remove in production"""
    ip_address = request.remote_addr
    clear_failed_attempts(ip_address)
    flash("Login attempts reset. You can try logging in again.", "info")
    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    ip_address = session.get("ip_address", "unknown")
    session.clear()
    flash("Logged out successfully.", "info")
    log_info(f"User logged out from {ip_address}")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Read last 50 log lines
    logpath = Path("storage") / "logs" / "broadcast.log"
    last_logs = []
    
    if logpath.exists():
        try:
            with open(logpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_logs = [line.strip() for line in lines[-50:][::-1]]
        except Exception as e:
            last_logs = [f"(Could not read log file: {e})"]
            log_info(f"Error reading log file: {e}")
    
    # Calculate statistics
    stats = {
        'total_recipients': len(RECEIVER_EMAILS),
        'session_time': _get_session_duration(),
        'login_time': session.get('login_time', 'Unknown')
    }
    
    return render_template(
        "dashboard.html",
        recipients_count=len(RECEIVER_EMAILS),
        recipients=RECEIVER_EMAILS[:10],  # Show first 10
        logs=last_logs,
        stats=stats
    )


@app.route("/recipients", methods=["GET", "POST"])
@login_required
def recipients():
    form_data = dict(request.form) if request.method == "POST" else None
    form = RecipientForm(form_data)
    
    if request.method == "POST":
        if form.validate():
            new_addresses = form.flatten_addresses()
            added = _merge_recipients(new_addresses)
            
            if added:
                if _persist_recipients():
                    flash(f"Successfully added {added} recipient(s).", "success")
                    log_info(f"Added {added} new recipients. Total: {len(RECEIVER_EMAILS)}")
                else:
                    flash(f"Added {added} recipient(s) but failed to persist to file.", "warning")
            else:
                flash("No new recipients were added (all duplicates).", "info")
            
            return redirect(url_for("recipients"))
        else:
            flash("Please fix the highlighted errors.", "danger")
    
    return render_template(
        "recipients.html",
        recipients=RECEIVER_EMAILS,
        form=form,
        total_count=len(RECEIVER_EMAILS)
    )


@app.route("/recipients/delete/<int:index>", methods=["POST"])
@login_required
def delete_recipient(index):
    """Delete a recipient by index"""
    if 0 <= index < len(RECEIVER_EMAILS):
        removed_email = RECEIVER_EMAILS.pop(index)
        if _persist_recipients():
            flash(f"Removed recipient: {removed_email}", "success")
            log_info(f"Removed recipient: {removed_email}")
        else:
            RECEIVER_EMAILS.insert(index, removed_email)  # Rollback
            flash("Failed to persist changes.", "danger")
    else:
        flash("Invalid recipient index.", "danger")
    
    return redirect(url_for("recipients"))


@app.route("/recipients/clear", methods=["POST"])
@login_required
def clear_recipients():
    """Clear all recipients"""
    count = len(RECEIVER_EMAILS)
    RECEIVER_EMAILS.clear()
    
    if _persist_recipients():
        flash(f"Cleared all {count} recipients.", "success")
        log_info(f"Cleared all {count} recipients")
    else:
        flash("Failed to persist changes.", "danger")
    
    return redirect(url_for("recipients"))


@app.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    if not RECEIVER_EMAILS:
        flash("No recipients configured. Please add recipients first.", "warning")
        return redirect(url_for("recipients"))
    
    form_data = dict(request.form) if request.method == "POST" else None
    form = BroadcastForm(form_data)
    
    if request.method == "GET":
        if not form.subject:
            form.subject = EMAIL_SUBJECT
        if not form.body:
            form.body = EMAIL_BODY
    
    if request.method == "POST":
        if form.validate():
            try:
                # Check SMTP configuration before sending
                from app.config import SMTPSettings
                smtp_settings = SMTPSettings()
                
                if "your_email" in smtp_settings.username.lower() or "@" not in smtp_settings.username:
                    flash(
                        "❌ SMTP Not Configured!\n\n"
                        f"Current SMTP_USERNAME: '{smtp_settings.username}'\n\n"
                        "Please update your .env file with your actual Gmail address:\n"
                        "SMTP_USERNAME=your_actual_email@gmail.com\n\n"
                        "Then restart the Flask app.",
                        "danger"
                    )
                    return render_template(
                        "compose.html",
                        form=form,
                        recipients=RECEIVER_EMAILS,
                        recipient_count=len(RECEIVER_EMAILS)
                    )
                
                if "your_app_password" in smtp_settings.password.lower() or len(smtp_settings.password) < 16:
                    flash(
                        "❌ SMTP Password Not Configured!\n\n"
                        "Please update your .env file with a Gmail App Password:\n"
                        "SMTP_PASSWORD=your_16_character_app_password\n\n"
                        "Get one at: https://myaccount.google.com/apppasswords\n\n"
                        "Then restart the Flask app.",
                        "danger"
                    )
                    return render_template(
                        "compose.html",
                        form=form,
                        recipients=RECEIVER_EMAILS,
                        recipient_count=len(RECEIVER_EMAILS)
                    )
                
                subject = form.subject.strip()
                body = form.body.strip()
                
                send_bulk_email(
                    subject=subject,
                    message=body,
                    recipients=RECEIVER_EMAILS,
                    concurrency=form.concurrency,
                )
                
                log_info(
                    f"Broadcast sent: subject='{subject}' to {len(RECEIVER_EMAILS)} recipients"
                )
                flash(
                    f"✓ Broadcast sent successfully to {len(RECEIVER_EMAILS)} recipients.",
                    "success"
                )
                return redirect(url_for("dashboard"))
                
            except Exception as exc:
                error_msg = str(exc)
                log_info(f"Broadcast failed: {exc}")
                
                # Provide helpful error messages for common issues
                if "535" in error_msg or "BadCredentials" in error_msg or "not accepted" in error_msg:
                    flash(
                        "❌ SMTP Authentication Failed!\n\n"
                        "Your Gmail credentials are not configured correctly.\n\n"
                        "Please update your .env file with:\n"
                        "1. SMTP_USERNAME=your_actual_email@gmail.com\n"
                        "2. SMTP_PASSWORD=your_gmail_app_password\n\n"
                        "Get a Gmail App Password at: https://myaccount.google.com/apppasswords\n\n"
                        "After updating, restart the Flask app.",
                        "danger"
                    )
                elif "your_email" in error_msg.lower() or "your_app_password" in error_msg.lower():
                    flash(
                        "❌ SMTP Not Configured!\n\n"
                        "Please update your .env file with your Gmail credentials.\n"
                        "See the error details in the console for more information.",
                        "danger"
                    )
                else:
                    flash(f"Error sending broadcast: {exc}", "danger")
        else:
            flash("Please fix the highlighted errors.", "danger")
    
    return render_template(
        "compose.html",
        form=form,
        recipients=RECEIVER_EMAILS,
        recipient_count=len(RECEIVER_EMAILS)
    )


@app.route("/api/recipients/count", methods=["GET"])
@login_required
def api_recipient_count():
    """API endpoint to get recipient count"""
    return jsonify({
        'count': len(RECEIVER_EMAILS),
        'timestamp': datetime.now().isoformat()
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route("/debug/credentials", methods=["GET"])
def debug_credentials():
    """Debug endpoint to check loaded credentials (remove in production)"""
    return jsonify({
        'admin_username': ADMIN_USERNAME,
        'admin_username_length': len(ADMIN_USERNAME),
        'admin_password_length': len(ADMIN_PASSWORD),
        'admin_password_preview': ADMIN_PASSWORD[:3] + '***' if len(ADMIN_PASSWORD) > 3 else '***',
        'env_file_exists': (PROJECT_ROOT / ".env").exists(),
        'env_file_path': str(PROJECT_ROOT / ".env")
    }), 200


def _persist_recipients() -> bool:
    """
    Persist current RECEIVER_EMAILS back into app/core/recipients.py.
    Returns True if successful, False otherwise.
    """
    try:
        path = PROJECT_ROOT / "app" / "core" / "recipients.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        addresses = "\n".join(f'                "{addr}",' for addr in RECEIVER_EMAILS)
        content = f'''from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RecipientList:
    """Immutable list of email recipients"""
    addresses: List[str]

    @classmethod
    def demo(cls) -> "RecipientList":
        """Create a demo recipient list"""
        return cls(
            [
{addresses}
            ]
        )


RECEIVER_EMAILS = RecipientList.demo().addresses.copy()
'''
        
        # Backup existing file
        if path.exists():
            backup_path = path.with_suffix('.py.bak')
            shutil.copy2(path, backup_path)
        
        path.write_text(content, encoding="utf-8")
        log_info(f"Recipients persisted to {path} ({len(RECEIVER_EMAILS)} total)")
        return True
        
    except Exception as exc:
        log_info(f"Failed to persist recipients: {exc}")
        return False


def _merge_recipients(addresses: list[str]) -> int:
    """
    Merge new addresses into RECEIVER_EMAILS, avoiding duplicates.
    Returns the count of newly added addresses.
    """
    added = 0
    seen = {addr.lower().strip() for addr in RECEIVER_EMAILS}
    
    for address in addresses:
        key = address.lower().strip()
        if key and key not in seen:
            RECEIVER_EMAILS.append(address.strip())
            seen.add(key)
            added += 1
    
    return added


def _get_session_duration() -> str:
    """Get human-readable session duration"""
    login_time = session.get('login_time')
    if not login_time:
        return "Unknown"
    
    try:
        elapsed = (datetime.now() - datetime.fromisoformat(login_time)).total_seconds()
        if elapsed < 60:
            return f"{int(elapsed)} seconds"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)} minutes"
        else:
            return f"{int(elapsed / 3600)} hours"
    except Exception:
        return "Unknown"


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    log_info(f"Server error: {e}")
    return render_template('errors/500.html'), 500


@app.errorhandler(429)
def rate_limit_error(e):
    """Handle rate limit errors"""
    return render_template('errors/429.html'), 429


if __name__ == "__main__":
    # Ensure required directories exist
    Path("storage/logs").mkdir(parents=True, exist_ok=True)
    
    # Display loaded credentials for verification
    print(f"\n{'='*60}")
    print(f"Email Broadcast System Starting...")
    print(f"{'='*60}")
    print(f"Admin Username: {ADMIN_USERNAME}")
    print(f"Admin Password: {'*' * len(ADMIN_PASSWORD)} (length: {len(ADMIN_PASSWORD)})")
    print(f"{'='*60}\n")
    
    # Warn if using default credentials
    if ADMIN_PASSWORD == "admin":
        print("⚠️  WARNING: Using default admin password. Please set ADMIN_PASSWORD in .env\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)