import hashlib
import json
import time
import urllib.request
import threading
import base64
import platform
import secrets
import atexit
from typing import Optional, Dict, Any

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

CRYPTO_REQUIRED_ERROR = (
    "The 'cryptography' library is required for secure license validation. "
    "Install it with: pip install cryptography"
)


class CodeVaultError(Exception):
    """Base exception for CodeVault SDK."""

    pass


class CodeVaultClient:
    def __init__(
        self, license_key: str, server_url: str, public_key_pem: Optional[str] = None
    ):
        if not server_url.startswith(("http://", "https://")):
            raise CodeVaultError("server_url must use http:// or https:// scheme")
        self.license_key = license_key
        self.server_url = server_url.rstrip("/")
        self.public_key_pem = public_key_pem
        self.session_token = None
        self.features = []
        self.variables = {}
        self._heartbeat_thread = None
        self._stop_heartbeat = threading.Event()

        # Auto-release session on exit
        atexit.register(self.release)

    def _get_hwid(self) -> str:
        """Generate a stable hardware ID."""
        info = f"{platform.node()}|{platform.machine()}|{platform.processor()}"
        return hashlib.sha256(info.encode()).hexdigest()[:32]

    def _verify_signature(self, result: Dict[str, Any]) -> bool:
        """Verify the Ed25519 signature of the server response."""
        if not HAS_CRYPTO:
            raise CodeVaultError(CRYPTO_REQUIRED_ERROR)

        if not self.public_key_pem:
            raise CodeVaultError(
                "No public key configured. Signature verification is mandatory."
            )

        signature = result.get("signature")
        if not signature:
            raise CodeVaultError(
                "Server response missing signature. Response may be tampered."
            )

        try:
            features_json = json.dumps(
                sorted(result.get("features", [])), sort_keys=True
            )
            variables_json = json.dumps(result.get("variables", {}), sort_keys=True)

            msg = "|".join(
                str(v)
                for v in [
                    result.get("status", ""),
                    result.get("expires_at", "") or "",
                    features_json,
                    variables_json,
                    result.get("client_nonce", ""),
                    result.get("server_nonce", ""),
                    result.get("timestamp", ""),
                    result.get("server_time", ""),
                ]
            )

            pub_key = load_pem_public_key(self.public_key_pem.encode())
            sig_bytes = base64.b64decode(signature)
            pub_key.verify(sig_bytes, msg.encode())
            return True
        except Exception as e:
            raise CodeVaultError(f"Signature verification failed: {e}")

    def validate(self) -> bool:
        """Validate the license with the server."""
        hwid = self._get_hwid()
        nonce = secrets.token_hex(16)

        payload = json.dumps(
            {
                "license_key": self.license_key,
                "hwid": hwid,
                "machine_name": platform.node(),
                "nonce": nonce,
                "timestamp": int(time.time()),
            }
        ).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.server_url}/api/v1/license/validate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))

                if not self._verify_signature(result):
                    raise CodeVaultError("Server response signature invalid")

                if result.get("status") == "valid":
                    self.features = result.get("features", [])
                    self.variables = result.get("variables", {})
                    self.session_token = self.variables.get("_cv_session_token")

                    # Start heartbeat if interval is provided
                    interval = result.get("heartbeat_interval", 300)
                    self._start_heartbeat(interval)

                    return True
                else:
                    return False
        except Exception as e:
            if isinstance(e, CodeVaultError):
                raise
            raise CodeVaultError(f"Connection failed: {e}")

    def _start_heartbeat(self, interval: int):
        """Start the background heartbeat thread."""
        if self._heartbeat_thread:
            return

        def loop():
            while not self._stop_heartbeat.wait(interval):
                try:
                    self._send_heartbeat()
                except Exception:
                    pass

        self._heartbeat_thread = threading.Thread(target=loop, daemon=True)
        self._heartbeat_thread.start()

    def _send_heartbeat(self):
        """Send a single heartbeat request."""
        hwid = self._get_hwid()
        payload = json.dumps(
            {
                "license_key": self.license_key,
                "hwid": hwid,
                "nonce": secrets.token_hex(16),
                "timestamp": int(time.time()),
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self.server_url}/api/v1/license/heartbeat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass

    def release(self):
        """Release the license session."""
        self._stop_heartbeat.set()
        if not self.session_token:
            return

        try:
            payload = json.dumps(
                {
                    "license_key": self.license_key,
                    "hwid": self._get_hwid(),
                    "session_token": self.session_token,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                f"{self.server_url}/api/v1/license/release",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except Exception:
            pass
        finally:
            self.session_token = None
