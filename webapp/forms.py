from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional, Any
from html import escape

# Enhanced email regex with better validation
EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Common disposable email domains to block (optional)
DISPOSABLE_DOMAINS = {
    "tempmail.com", "throwaway.email", "guerrillamail.com",
    "10minutemail.com", "mailinator.com"
}


@dataclass
class BaseForm:
    """Base form class with validation and error handling"""
    errors: dict[str, str] = field(default_factory=dict)
    warnings: dict[str, str] = field(default_factory=dict)

    def add_error(self, field: str, message: str) -> None:
        """Add an error message for a field"""
        self.errors[field] = message

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning message for a field"""
        self.warnings[field] = message

    def has_errors(self) -> bool:
        """Check if form has any errors"""
        return bool(self.errors)

    def has_warnings(self) -> bool:
        """Check if form has any warnings"""
        return bool(self.warnings)

    def get_error(self, field: str) -> Optional[str]:
        """Get error message for a specific field"""
        return self.errors.get(field)

    def clear_errors(self) -> None:
        """Clear all errors"""
        self.errors.clear()

    def validate(self) -> bool:  # pragma: no cover - interface helper
        """Validate form data. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement validate()")

    def sanitize_input(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize user input by stripping whitespace and optionally truncating"""
        sanitized = (value or "").strip()
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized


class LoginForm(BaseForm):
    """Form for user login with enhanced validation"""
    
    MAX_USERNAME_LENGTH = 100
    MAX_PASSWORD_LENGTH = 128
    MIN_PASSWORD_LENGTH = 6

    def __init__(self, formdata: Optional[dict] = None):
        super().__init__()
        formdata = formdata or {}
        self.username = self.sanitize_input(
            formdata.get("username", ""),
            self.MAX_USERNAME_LENGTH
        )
        self.password = self.sanitize_input(
            formdata.get("password", ""),
            self.MAX_PASSWORD_LENGTH
        )
        self.remember_me = bool(formdata.get("remember_me", False))

    def validate(self) -> bool:
        """Validate login form"""
        if not self.username:
            self.add_error("username", "Username is required.")
        elif len(self.username) < 3:
            self.add_error("username", "Username must be at least 3 characters.")
        elif len(self.username) > self.MAX_USERNAME_LENGTH:
            self.add_error("username", f"Username must be less than {self.MAX_USERNAME_LENGTH} characters.")
        
        if not self.password:
            self.add_error("password", "Password is required.")
        elif len(self.password) < self.MIN_PASSWORD_LENGTH:
            self.add_error("password", f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters.")
        elif len(self.password) > self.MAX_PASSWORD_LENGTH:
            self.add_error("password", f"Password must be less than {self.MAX_PASSWORD_LENGTH} characters.")
        
        return not self.has_errors()


class RecipientForm(BaseForm):
    """Form for managing email recipients with advanced validation"""
    
    MAX_ADDRESSES = 1000
    MAX_EMAIL_LENGTH = 254  # RFC 5321 standard

    def __init__(self, formdata: Optional[dict] = None):
        super().__init__()
        formdata = formdata or {}
        self.addresses = self.sanitize_input(formdata.get("addresses", ""))
        self.block_disposable = bool(formdata.get("block_disposable", True))
        self.deduplicate = bool(formdata.get("deduplicate", True))

    def flatten_addresses(self) -> list[str]:
        """Parse and flatten email addresses from text input"""
        # Split by comma, semicolon, newline, or space
        tokens: Iterable[str] = re.split(r"[,;\n\s]+", self.addresses)
        addresses = []
        seen = set()
        
        for token in tokens:
            token = token.strip().lower()
            if not token:
                continue
            
            # Remove duplicates if enabled
            if self.deduplicate:
                if token in seen:
                    continue
                seen.add(token)
            
            addresses.append(token)
        
        return addresses

    def validate_email(self, email: str) -> tuple[bool, Optional[str]]:
        """
        Validate a single email address.
        Returns (is_valid, error_message)
        """
        # Check length
        if len(email) > self.MAX_EMAIL_LENGTH:
            return False, f"Email too long (max {self.MAX_EMAIL_LENGTH} chars)"
        
        # Check format
        if not EMAIL_RE.match(email):
            return False, "Invalid email format"
        
        # Check for disposable email domains if enabled
        if self.block_disposable:
            domain = email.split('@')[1].lower()
            if domain in DISPOSABLE_DOMAINS:
                return False, f"Disposable email domain not allowed: {domain}"
        
        # Check for consecutive dots
        if ".." in email:
            return False, "Consecutive dots not allowed"
        
        # Check local part (before @)
        local, domain = email.split('@')
        if not local or not domain:
            return False, "Missing local or domain part"
        
        # Check if domain has valid TLD
        if '.' not in domain:
            return False, "Domain must have a TLD"
        
        return True, None

    def validate(self) -> bool:
        """Validate recipient form"""
        if not self.addresses:
            self.add_error("addresses", "Please provide at least one recipient.")
            return False

        cleaned = self.flatten_addresses()
        
        # Check if we have any addresses
        if not cleaned:
            self.add_error("addresses", "No valid email addresses found.")
            return False
        
        # Check maximum addresses limit
        if len(cleaned) > self.MAX_ADDRESSES:
            self.add_error(
                "addresses",
                f"Too many addresses. Maximum allowed: {self.MAX_ADDRESSES}, provided: {len(cleaned)}"
            )
            return False

        # Validate each address
        invalid_addresses = []
        warning_addresses = []
        
        for addr in cleaned:
            is_valid, error_msg = self.validate_email(addr)
            if not is_valid:
                invalid_addresses.append(f"{addr} ({error_msg})")
            elif self.block_disposable and any(d in addr for d in DISPOSABLE_DOMAINS):
                warning_addresses.append(addr)
        
        # Report invalid addresses (limit to first 5 for readability)
        if invalid_addresses:
            displayed = invalid_addresses[:5]
            more_count = len(invalid_addresses) - 5
            error_msg = f"Invalid addresses: {'; '.join(displayed)}"
            if more_count > 0:
                error_msg += f" (and {more_count} more)"
            self.add_error("addresses", error_msg)
        
        # Add warnings for suspicious addresses
        if warning_addresses and not invalid_addresses:
            self.add_warning(
                "addresses",
                f"Warning: {len(warning_addresses)} disposable email(s) detected"
            )
        
        return not self.has_errors()

    def get_valid_addresses(self) -> list[str]:
        """Return only valid email addresses"""
        cleaned = self.flatten_addresses()
        valid = []
        
        for addr in cleaned:
            is_valid, _ = self.validate_email(addr)
            if is_valid:
                valid.append(addr)
        
        return valid

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the provided addresses"""
        cleaned = self.flatten_addresses()
        valid = self.get_valid_addresses()
        
        domains = {}
        for addr in valid:
            domain = addr.split('@')[1]
            domains[domain] = domains.get(domain, 0) + 1
        
        return {
            'total': len(cleaned),
            'valid': len(valid),
            'invalid': len(cleaned) - len(valid),
            'unique_domains': len(domains),
            'top_domains': sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
        }


class BroadcastForm(BaseForm):
    """Form for composing and sending broadcast emails"""
    
    MIN_SUBJECT_LENGTH = 3
    MAX_SUBJECT_LENGTH = 200
    MIN_BODY_LENGTH = 10
    MAX_BODY_LENGTH = 50000
    MIN_CONCURRENCY = 1
    MAX_CONCURRENCY = 500
    DEFAULT_CONCURRENCY = 50

    def __init__(self, formdata: Optional[dict] = None):
        super().__init__()
        formdata = formdata or {}
        
        self.subject = self.sanitize_input(
            formdata.get("subject", ""),
            self.MAX_SUBJECT_LENGTH
        )
        self.body = self.sanitize_input(
            formdata.get("body", ""),
            self.MAX_BODY_LENGTH
        )
        self.concurrency_raw = self.sanitize_input(
            formdata.get("concurrency", ""),
            10
        ) or str(self.DEFAULT_CONCURRENCY)
        self.concurrency = self.DEFAULT_CONCURRENCY
        
        self.send_test = bool(formdata.get("send_test", False))
        self.test_email = self.sanitize_input(formdata.get("test_email", ""), 254)
        self.schedule_send = bool(formdata.get("schedule_send", False))

    def validate(self) -> bool:
        """Validate broadcast form"""
        # Validate subject
        if not self.subject:
            self.add_error("subject", "Subject is required.")
        elif len(self.subject) < self.MIN_SUBJECT_LENGTH:
            self.add_error("subject", f"Subject must be at least {self.MIN_SUBJECT_LENGTH} characters.")
        elif len(self.subject) > self.MAX_SUBJECT_LENGTH:
            self.add_error("subject", f"Subject must be less than {self.MAX_SUBJECT_LENGTH} characters.")
        
        # Check for common spam trigger words
        if self.subject:
            spam_words = ['free', 'urgent', 'act now', 'limited time', 'winner', 'congratulations']
            subject_lower = self.subject.lower()
            found_spam = [word for word in spam_words if word in subject_lower]
            if found_spam:
                self.add_warning(
                    "subject",
                    f"Subject contains potential spam triggers: {', '.join(found_spam)}"
                )
        
        # Validate body
        if not self.body:
            self.add_error("body", "Message body is required.")
        elif len(self.body) < self.MIN_BODY_LENGTH:
            self.add_error("body", f"Message must be at least {self.MIN_BODY_LENGTH} characters.")
        elif len(self.body) > self.MAX_BODY_LENGTH:
            self.add_error("body", f"Message must be less than {self.MAX_BODY_LENGTH} characters.")
        
        # Check for unsubscribe link (best practice)
        if self.body and 'unsubscribe' not in self.body.lower():
            self.add_warning(
                "body",
                "Consider adding an unsubscribe link to comply with email regulations"
            )
        
        # Validate concurrency
        try:
            concurrency_val = int(self.concurrency_raw)
            if concurrency_val < self.MIN_CONCURRENCY:
                self.concurrency = self.MIN_CONCURRENCY
                self.add_warning("concurrency", f"Concurrency set to minimum value: {self.MIN_CONCURRENCY}")
            elif concurrency_val > self.MAX_CONCURRENCY:
                self.concurrency = self.MAX_CONCURRENCY
                self.add_warning("concurrency", f"Concurrency set to maximum value: {self.MAX_CONCURRENCY}")
            else:
                self.concurrency = concurrency_val
        except ValueError:
            self.add_error("concurrency", "Concurrency must be a valid integer.")
            self.concurrency = self.DEFAULT_CONCURRENCY
        
        # Validate test email if test mode is enabled
        if self.send_test:
            if not self.test_email:
                self.add_error("test_email", "Test email address is required for test mode.")
            elif not EMAIL_RE.match(self.test_email):
                self.add_error("test_email", "Invalid test email address format.")
        
        return not self.has_errors()

    def get_word_count(self) -> int:
        """Get word count of the message body"""
        return len(self.body.split())

    def get_character_count(self) -> int:
        """Get character count of the message body"""
        return len(self.body)

    def estimate_send_time(self, recipient_count: int) -> float:
        """
        Estimate send time in seconds based on concurrency and recipient count.
        Assumes ~0.5 seconds per email.
        """
        if self.concurrency <= 0:
            return 0.0
        
        emails_per_batch = self.concurrency
        time_per_batch = 0.5  # seconds
        num_batches = (recipient_count + emails_per_batch - 1) // emails_per_batch
        
        return num_batches * time_per_batch

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the broadcast message"""
        return {
            'subject_length': len(self.subject),
            'body_length': len(self.body),
            'word_count': self.get_word_count(),
            'has_html': '<' in self.body and '>' in self.body,
            'has_links': 'http://' in self.body or 'https://' in self.body,
            'concurrency': self.concurrency
        }


class SettingsForm(BaseForm):
    """Form for application settings"""
    
    def __init__(self, formdata: Optional[dict] = None):
        super().__init__()
        formdata = formdata or {}
        
        self.smtp_host = self.sanitize_input(formdata.get("smtp_host", ""), 255)
        self.smtp_port = self.sanitize_input(formdata.get("smtp_port", ""), 10)
        self.smtp_username = self.sanitize_input(formdata.get("smtp_username", ""), 255)
        self.smtp_password = formdata.get("smtp_password", "")  # Don't strip password
        self.use_tls = bool(formdata.get("use_tls", True))
        self.use_ssl = bool(formdata.get("use_ssl", False))
        self.timeout = self.sanitize_input(formdata.get("timeout", "30"), 10)

    def validate(self) -> bool:
        """Validate settings form"""
        if self.smtp_host and not self.smtp_host.replace('.', '').replace('-', '').isalnum():
            self.add_error("smtp_host", "Invalid SMTP host format.")
        
        if self.smtp_port:
            try:
                port = int(self.smtp_port)
                if port < 1 or port > 65535:
                    self.add_error("smtp_port", "Port must be between 1 and 65535.")
            except ValueError:
                self.add_error("smtp_port", "Port must be a valid integer.")
        
        if self.smtp_username and not EMAIL_RE.match(self.smtp_username):
            self.add_warning("smtp_username", "SMTP username should typically be an email address.")
        
        if self.use_tls and self.use_ssl:
            self.add_error("ssl_tls", "Cannot use both TLS and SSL simultaneously. Choose one.")
        
        if self.timeout:
            try:
                timeout_val = int(self.timeout)
                if timeout_val < 5 or timeout_val > 300:
                    self.add_error("timeout", "Timeout must be between 5 and 300 seconds.")
            except ValueError:
                self.add_error("timeout", "Timeout must be a valid integer.")
        
        return not self.has_errors()


# Utility functions for form handling
def escape_html(text: str) -> str:
    """Escape HTML characters in text"""
    return escape(text)


def validate_email_address(email: str) -> bool:
    """Quick email validation utility function"""
    return bool(EMAIL_RE.match(email.strip().lower()))


def parse_email_list(text: str, deduplicate: bool = True) -> list[str]:
    """Parse a list of emails from text, with optional deduplication"""
    tokens = re.split(r"[,;\n\s]+", text)
    emails = []
    seen = set()
    
    for token in tokens:
        email = token.strip().lower()
        if email and validate_email_address(email):
            if not deduplicate or email not in seen:
                emails.append(email)
                if deduplicate:
                    seen.add(email)
    
    return emails