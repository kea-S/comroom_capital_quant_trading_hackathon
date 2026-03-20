from pathlib import Path

# Anchor to this file's directory (bot/execution)
CONFIG_DIR = Path(__file__).resolve().parent

# Default logs file relative to the config directory:
# ../logs/logs.txt (matches your repo layout)
LOG_FILE = (CONFIG_DIR / ".." / "logs" / "logs.txt").resolve()

# Convenience: logs directory
LOGS_DIR = LOG_FILE.parent

__all__ = ["CONFIG_DIR", "LOG_FILE", "LOGS_DIR"]
