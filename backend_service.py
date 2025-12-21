"""
Backend Service - Headless Mode Launcher
Runs the License Wrapper backend API without opening a browser.
Designed to be started by the Tauri desktop application.

Usage:
    python backend_service.py [--port PORT]
"""

import os
import sys
import signal
import logging
import argparse
from pathlib import Path

# Setup logging first
LOG_DIR = Path(os.getenv('APPDATA', Path.home())) / 'license-wrapper' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'backend.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add server directory to path
SERVER_DIR = Path(__file__).parent / 'server'
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

def find_free_port(start_port: int = 8765, max_attempts: int = 6) -> int:
    """Find a free port starting from start_port."""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            logger.warning(f"Port {port} in use, trying next...")
    
    raise RuntimeError(f"No free ports found in range {start_port}-{start_port + max_attempts}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, stopping backend...")
    sys.exit(0)


def run_backend(port: int):
    """Run the backend server."""
    import uvicorn
    
    # Change to server directory for proper imports
    os.chdir(SERVER_DIR)
    
    logger.info(f"Starting backend on port {port}...")
    logger.info(f"Log file: {LOG_FILE}")
    
    # Write port file for Tauri to read
    port_file = LOG_DIR / 'backend.port'
    port_file.write_text(str(port))
    logger.info(f"Port file written: {port_file}")
    
    try:
        # Import app from server/main.py
        from main import app
        
        # Run without auto-reload in production
        uvicorn.run(
            app,
            host='127.0.0.1',
            port=port,
            log_level='info',
            access_log=True,
            # No reload in production
            reload=False,
        )
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        raise
    finally:
        # Cleanup port file on exit
        if port_file.exists():
            port_file.unlink()


def main():
    parser = argparse.ArgumentParser(description='License Wrapper Backend Service')
    parser.add_argument('--port', type=int, default=8765, help='Port to run on (default: 8765)')
    parser.add_argument('--auto-port', action='store_true', help='Auto-find free port if default busy')
    args = parser.parse_args()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        port = args.port
        if args.auto_port:
            port = find_free_port(args.port)
        
        logger.info("=" * 50)
        logger.info("License Wrapper Backend Service")
        logger.info(f"Port: {port}")
        logger.info(f"PID: {os.getpid()}")
        logger.info("=" * 50)
        
        run_backend(port)
        
    except Exception as e:
        logger.error(f"Backend service failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
