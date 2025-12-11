from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "storage" / "logs" / "broadcast.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load environment variables
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv()


@dataclass
class SMTPSettings:
    """Configuration for the primary SMTP transport."""

    server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port: int = int(os.getenv("SMTP_PORT", "587"))
    username: str = os.getenv("SMTP_USERNAME", "your_email@gmail.com")
    password: str = os.getenv("SMTP_PASSWORD", "your_app_password")
    sender_name: str = os.getenv("SMTP_SENDER_NAME", "Broadcast Studio")
    
    def __post_init__(self):
        """Validate SMTP settings and warn if using placeholder values"""
        if "your_email" in self.username.lower() or "@" not in self.username:
            import warnings
            warnings.warn(
                f"SMTP_USERNAME appears to be a placeholder: '{self.username}'. "
                "Please update it in your .env file with your actual Gmail address.",
                UserWarning
            )
        if "your_app_password" in self.password.lower() or len(self.password) < 16:
            import warnings
            warnings.warn(
                f"SMTP_PASSWORD appears to be a placeholder or invalid. "
                "Please update it in your .env file with a Gmail App Password (16 characters). "
                "Get one at: https://myaccount.google.com/apppasswords",
                UserWarning
            )


DEFAULT_CONCURRENCY: int = int(os.getenv("DEFAULT_CONCURRENCY", "50"))

