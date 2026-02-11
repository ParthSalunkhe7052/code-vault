"""
Debug logging system for CodeVault CLI builds.

Provides comprehensive logging with automatic rotation (keeps last 5 builds).
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class BuildLogger:
    """
    Comprehensive build logger with file rotation.

    Keeps last 5 build logs to prevent disk bloat while maintaining
    enough history for debugging.
    """

    MAX_LOG_FILES = 5

    def __init__(self, project_name: str, build_id: Optional[str] = None):
        self.project_name = project_name
        self.build_id = build_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        self.log_entries: list = []
        self.log_file: Optional[Path] = None

        # Setup log directory
        self._setup_log_directory()

    def _setup_log_directory(self):
        """Create log directory and rotate old logs."""
        # Use user's home directory for logs
        log_dir = Path.home() / ".codevault" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old logs (keep only last MAX_LOG_FILES)
        self._rotate_logs(log_dir)

        # Create new log file
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in self.project_name
        )
        self.log_file = log_dir / f"build_{safe_name}_{self.build_id}.log"

        # Write header
        self._write_header()

    def _rotate_logs(self, log_dir: Path):
        """Remove old log files, keeping only MAX_LOG_FILES most recent."""
        try:
            # Get all log files sorted by modification time
            log_files = sorted(
                log_dir.glob("build_*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            # Remove excess logs
            for old_log in log_files[self.MAX_LOG_FILES :]:
                try:
                    old_log.unlink()
                except OSError:
                    pass  # Ignore errors during cleanup
        except Exception:
            pass  # Don't fail if rotation fails

    def _write_header(self):
        """Write log file header."""
        header = f"""
{"=" * 70}
CodeVault Build Log
Project: {self.project_name}
Build ID: {self.build_id}
Started: {datetime.now().isoformat()}
Python: {sys.version}
Platform: {sys.platform}
{"=" * 70}

"""
        if self.log_file:
            try:
                self.log_file.write_text(header, encoding="utf-8")
            except Exception as e:
                print(f"Warning: Could not create log file: {e}", file=sys.stderr)

    def _write_entry(
        self, level: LogLevel, message: str, context: Optional[Dict] = None
    ):
        """Write a log entry to file."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elapsed = time.time() - self.start_time

        entry = f"[{timestamp}] [{level.value}] [{elapsed:8.3f}s] {message}"

        if context:
            try:
                context_str = json.dumps(context, default=str, indent=2)
                entry += f"\n  Context: {context_str}"
            except Exception:
                entry += f"\n  Context: {str(context)}"

        entry += "\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass  # Don't fail if logging fails

    def debug(self, message: str, context: Optional[Dict] = None):
        """Log debug message."""
        self._write_entry(LogLevel.DEBUG, message, context)

    def info(self, message: str, context: Optional[Dict] = None):
        """Log info message."""
        self._write_entry(LogLevel.INFO, message, context)
        self.log_entries.append(
            {"level": "INFO", "message": message, "time": time.time()}
        )

    def warn(self, message: str, context: Optional[Dict] = None):
        """Log warning message."""
        self._write_entry(LogLevel.WARN, message, context)
        self.log_entries.append(
            {"level": "WARN", "message": message, "time": time.time()}
        )

    def error(self, message: str, context: Optional[Dict] = None):
        """Log error message."""
        self._write_entry(LogLevel.ERROR, message, context)
        self.log_entries.append(
            {"level": "ERROR", "message": message, "time": time.time()}
        )

    def fatal(self, message: str, context: Optional[Dict] = None):
        """Log fatal error message."""
        self._write_entry(LogLevel.FATAL, message, context)
        self.log_entries.append(
            {"level": "FATAL", "message": message, "time": time.time()}
        )

    def exception(self, message: str, exc: Exception):
        """Log exception with full traceback."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elapsed = time.time() - self.start_time

        entry = f"[{timestamp}] [{LogLevel.ERROR.value}] [{elapsed:8.3f}s] {message}\n"
        entry += f"  Exception: {type(exc).__name__}: {exc}\n"
        entry += "  Traceback:\n"

        tb_lines = traceback.format_exc().split("\n")
        for line in tb_lines:
            entry += f"    {line}\n"

        entry += "\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    def phase_start(self, phase_name: str, context: Optional[Dict] = None):
        """Log phase start."""
        self.info(f"Starting phase: {phase_name}", context)

    def phase_end(self, phase_name: str, success: bool, context: Optional[Dict] = None):
        """Log phase end."""
        status = "completed" if success else "failed"
        self.info(f"Phase {phase_name} {status}", context)

    def subprocess_start(self, cmd: list, cwd: str, env_vars: Optional[Dict] = None):
        """Log subprocess start."""
        context = {
            "command": " ".join(str(c) for c in cmd[:5]) + "..."
            if len(cmd) > 5
            else " ".join(str(c) for c in cmd),
            "cwd": cwd,
            "env": env_vars or {},
        }
        self.info(f"Starting subprocess: {cmd[0] if cmd else 'unknown'}", context)

    def subprocess_output(self, pid: int, line: str):
        """Log subprocess output line."""
        self.debug(f"[PID {pid}] {line}")

    def subprocess_end(self, pid: int, returncode: int, duration: float):
        """Log subprocess end."""
        context = {"pid": pid, "returncode": returncode, "duration": duration}
        if returncode == 0:
            self.info(f"Subprocess {pid} completed successfully", context)
        else:
            self.error(f"Subprocess {pid} failed with code {returncode}", context)

    def build_complete(self, success: bool, error_message: Optional[str] = None):
        """Log build completion."""
        duration = time.time() - self.start_time
        context = {"success": success, "duration": duration, "error": error_message}

        if success:
            self.info(f"Build completed successfully in {duration:.1f}s", context)
        else:
            self.error(f"Build failed after {duration:.1f}s: {error_message}", context)

        # Write footer
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 70}\n")
                    f.write(f"Build {'SUCCEEDED' if success else 'FAILED'}\n")
                    f.write(f"Finished: {datetime.now().isoformat()}\n")
                    f.write(f"Duration: {duration:.1f}s\n")
                    f.write(f"{'=' * 70}\n")
            except Exception:
                pass

    def get_log_path(self) -> Optional[str]:
        """Get path to current log file."""
        return str(self.log_file) if self.log_file else None

    def get_last_errors(self, count: int = 3) -> list:
        """Get last N error messages."""
        errors = [e for e in self.log_entries if e["level"] in ("ERROR", "FATAL")]
        return errors[-count:]


# Global logger instance (created per build)
_current_logger: Optional[BuildLogger] = None


def get_logger() -> Optional[BuildLogger]:
    """Get current build logger."""
    return _current_logger


def create_logger(project_name: str, build_id: Optional[str] = None) -> BuildLogger:
    """Create new build logger."""
    global _current_logger
    _current_logger = BuildLogger(project_name, build_id)
    return _current_logger


def log_path() -> Optional[str]:
    """Get current log file path."""
    logger = get_logger()
    return logger.get_log_path() if logger else None
