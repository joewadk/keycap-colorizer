"""Read-only startup checks shared by the Bash and PowerShell launchers."""
import importlib
from pathlib import Path
import socket
import sys


class StartupError(ValueError):
    pass


def check_dependencies():
    if sys.version_info < (3, 11):
        raise StartupError("Python 3.11 or newer is required. Recreate the backend virtual environment with Windows Python on Windows.")
    for module, package in (("fastapi", "FastAPI"), ("uvicorn", "Uvicorn"), ("bs4", "Beautiful Soup"),
                            ("playwright.async_api", "Playwright"), ("httpx", "httpx"),
                            ("pydantic_settings", "Pydantic Settings"), ("PIL.Image", "Pillow"),
                            ("sqlite3", "SQLite")):
        try:
            importlib.import_module(module)
        except (ImportError, OSError):
            raise StartupError(f"{package} is missing or cannot load. Run the root install.ps1 or install.sh to update dependencies.") from None


def check_configuration():
    from app.config import Settings
    from pydantic import ValidationError
    try:
        settings = Settings()
    except ValidationError:
        # Settings errors can contain secret input values; never print their raw representation.
        raise StartupError("Invalid backend configuration. Check root .env against .env.example; values are not printed for privacy.") from None
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    if path.is_dir():
        raise StartupError("DATABASE_PATH points to a directory; choose a SQLite file path.")
    ancestor = path.parent
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise StartupError("DATABASE_PATH has a parent that is not a directory.")
    print("Local save/restore: SQLite is available; the database is initialized on first storage use.")
    if settings.ai_provider and not (settings.openai_api_key.get_secret_value().strip() and settings.openai_model.strip()):
        print("Warning: AI is selected but OPENAI_API_KEY or OPENAI_MODEL is missing. The sample preview and saving still work.")
    if settings.scraper_provider == "firecrawl" and not settings.firecrawl_api_key.get_secret_value().strip():
        print("Warning: Firecrawl is selected but FIRECRAWL_API_KEY is missing. The sample preview and saving still work.")


def check_port(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            raise StartupError(f"Port {port} is unavailable. Stop the existing service before starting another copy; no process was stopped automatically.") from None


def main() -> int:
    try:
        check_dependencies()
        check_configuration()
        for port in (8000, 5173):
            check_port(port)
    except (StartupError, OSError) as error:
        message = str(error) if isinstance(error, StartupError) else "Startup checks could not access local configuration. Check file permissions."
        print(f"Startup check failed: {message}", file=sys.stderr)
        return 1
    print("Backend checks passed (including image sampling and SQLite). Ports 8000 and 5173 are available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
