from __future__ import annotations

import os
import sys
import signal
import logging
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from webapp.app import app


# Configuration
HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "true").lower() in ("true", "1", "yes")
THREADED = os.getenv("FLASK_THREADED", "true").lower() in ("true", "1", "yes")
USE_RELOADER = os.getenv("FLASK_USE_RELOADER", "true").lower() in ("true", "1", "yes")


def setup_logging() -> None:
    """Configure application logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory if it doesn't exist
    log_dir = Path("storage/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "app.log", encoding="utf-8")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def setup_directories() -> None:
    """Ensure required directories exist"""
    directories = [
        "storage/logs",
        "storage/temp",
        "storage/backups",
        "storage/uploads"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def check_environment() -> None:
    """Check and validate environment configuration"""
    logger = logging.getLogger(__name__)
    
    # Check for required environment variables
    required_vars = ["APP_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.warning("Application may not function correctly!")
    
    # Warn about default/insecure configurations
    if os.getenv("APP_SECRET") == "dev-secret-change-me":
        logger.warning("⚠️  Using default APP_SECRET! Change this in production!")
    
    if os.getenv("ADMIN_PASSWORD") == "admin":
        logger.warning("⚠️  Using default ADMIN_PASSWORD! Change this immediately!")
    
    # Check if running in production with debug mode
    if not DEBUG and os.getenv("FLASK_ENV") == "production":
        logger.info("✓ Running in PRODUCTION mode")
    elif DEBUG:
        logger.warning("⚠️  Running in DEBUG mode - DO NOT use in production!")


def signal_handler(signum: int, frame) -> NoReturn:
    """Handle shutdown signals gracefully"""
    logger = logging.getLogger(__name__)
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal. Shutting down gracefully...")
    
    # Perform cleanup operations here if needed
    # e.g., close database connections, save state, etc.
    
    logger.info("Application shutdown complete.")
    sys.exit(0)


def register_signal_handlers() -> None:
    """Register handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def display_startup_banner() -> None:
    """Display application startup information"""
    logger = logging.getLogger(__name__)
    
    banner = f"""
╔══════════════════════════════════════════════════════════╗
║          Email Broadcast Application                     ║
╚══════════════════════════════════════════════════════════╝

Server Information:
  • Host:        {HOST}
  • Port:        {PORT}
  • Debug Mode:  {DEBUG}
  • Threaded:    {THREADED}
  • Reloader:    {USE_RELOADER}
  • Environment: {os.getenv('FLASK_ENV', 'development')}

Access the application at:
  → http://{HOST if HOST != '0.0.0.0' else 'localhost'}:{PORT}
  → http://127.0.0.1:{PORT}

Press CTRL+C to quit
"""
    
    print(banner)
    logger.info("Application started successfully")


def validate_dependencies() -> bool:
    """Validate that all required dependencies are available"""
    logger = logging.getLogger(__name__)
    required_modules = [
        "flask",
        "dotenv",
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        logger.error("Install them using: pip install -r requirements.txt")
        return False
    
    return True


def run_preflight_checks() -> bool:
    """Run all preflight checks before starting the server"""
    logger = logging.getLogger(__name__)
    
    checks = [
        ("Validating dependencies", validate_dependencies),
        ("Setting up directories", lambda: (setup_directories(), True)[1]),
        ("Checking environment", lambda: (check_environment(), True)[1]),
    ]
    
    logger.info("Running preflight checks...")
    
    for check_name, check_func in checks:
        try:
            logger.info(f"  → {check_name}...")
            result = check_func()
            if result is False:
                logger.error(f"  ✗ {check_name} failed!")
                return False
            logger.info(f"  ✓ {check_name} passed")
        except Exception as e:
            logger.error(f"  ✗ {check_name} failed: {e}")
            return False
    
    logger.info("All preflight checks passed!")
    return True


def get_app_info() -> dict:
    """Get application information for health checks"""
    return {
        "name": "Email Broadcast Application",
        "version": "1.0.0",
        "python_version": sys.version.split()[0],
        "debug": DEBUG,
        "environment": os.getenv("FLASK_ENV", "development")
    }


def main() -> None:
    """Main application entry point"""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Run preflight checks
        if not run_preflight_checks():
            logger.error("Preflight checks failed. Exiting.")
            sys.exit(1)
        
        # Register signal handlers for graceful shutdown
        register_signal_handlers()
        
        # Display startup banner
        display_startup_banner()
        
        # Additional app configuration
        app.config["APP_INFO"] = get_app_info()
        
        # Start the Flask application
        app.run(
            host=HOST,
            port=PORT,
            debug=DEBUG,
            threaded=THREADED,
            use_reloader=USE_RELOADER,
            load_dotenv=False  # Already loaded above
        )
        
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {PORT} is already in use!")
            logger.error(f"Try using a different port: FLASK_PORT=5001 python {sys.argv[0]}")
        else:
            logger.error(f"OS Error: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()