"""Ed25519 signature verification utilities for CodeVault."""

import base64
import json
from typing import Any, Dict

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


def verify_ed25519_signature(result: Dict[str, Any], public_key_pem: str) -> bool:
    """
    Verify Ed25519 signature from server response.

    Args:
        result: Server response dict with signature and data
        public_key_pem: PEM-encoded Ed25519 public key

    Returns:
        True if signature is valid

    Raises:
        RuntimeError: If cryptography library is not available
        ValueError: If signature verification fails
    """
    if not HAS_CRYPTO:
        raise RuntimeError(CRYPTO_REQUIRED_ERROR)

    server_sig = result.get("signature")
    if not server_sig:
        raise ValueError("Server response is unsigned - missing digital signature")

    if not public_key_pem or not public_key_pem.strip():
        raise ValueError("No public key configured for signature verification")

    features_json = json.dumps(sorted(result.get("features", [])), sort_keys=True)
    variables_json = json.dumps(result.get("variables", {}), sort_keys=True)

    msg = "|".join(
        str(v)
        for v in [
            result.get("status", ""),
            result.get("expires_at", "") or "",
            features_json,
            variables_json,
            result.get("client_nonce", "") or result.get("nonce", ""),
            result.get("server_nonce", ""),
            result.get("timestamp", "") or "",
            result.get("server_time", "") or "",
        ]
    )

    try:
        pub_key = load_pem_public_key(public_key_pem.encode())
        sig_bytes = base64.b64decode(server_sig)
        pub_key.verify(sig_bytes, msg.encode())
        return True
    except Exception as e:
        raise ValueError(f"Signature verification failed: {e}")
