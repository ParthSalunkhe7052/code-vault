import subprocess
import time
import requests
import sys
import os
import signal
import socket

class ServerManager:
    def __init__(self, port=8000, host="127.0.0.1"):
        self.port = port
        self.host = host
        self.process = None
        self.base_url = f"http://{host}:{port}"
        # Adjust path to server/main.py relative to project root
        self.server_script = os.path.join(os.getcwd(), "server", "main.py")

    def is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) == 0

    def start(self):
        if self.is_port_in_use():
            print(f"Port {self.port} already in use. Assuming server is running.")
            return

        print(f"Starting server at {self.server_script} on port {self.port}...")
        # Assuming python3 is available as 'python' or 'python3'
        cmd = [sys.executable, self.server_script]
        
        env = os.environ.copy()
        env["PORT"] = str(self.port)
        env["PYTHONUNBUFFERED"] = "1"

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.getcwd()
        )

        # Wait for health check
        self.wait_for_health(timeout=30)

    def wait_for_health(self, timeout=30):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try root or specific health endpoint. 
                # Inspecting server/main.py would be better, but generic get usually works to check connectivity
                response = requests.get(self.base_url, timeout=1)
                if response.status_code < 500:
                    print("Server is up!")
                    return
            except requests.ConnectionError:
                time.sleep(1)
                continue
        
        # If we get here, timeout
        self.dump_logs()
        raise RuntimeError(f"Server failed to start within {timeout} seconds")

    def stop(self):
        if self.process:
            print("Stopping server...")
            if sys.platform == "win32":
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None

    def dump_logs(self):
        if self.process:
            stdout, stderr = self.process.communicate()
            print("--- SERVER STDOUT ---")
            print(stdout.decode(errors='replace'))
            print("--- SERVER STDERR ---")
            print(stderr.decode(errors='replace'))

if __name__ == "__main__":
    mgr = ServerManager()
    try:
        mgr.start()
        print("Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mgr.stop()
