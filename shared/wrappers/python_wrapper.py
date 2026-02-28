from pathlib import Path
from typing import Dict, Any
from cli.url_utils import normalize_server_url
from cli.audit import log_security_event, log_build_failure
from cli.generators.python_generator import get_python_wrapper
from shared.security.validation import validate_entry_file, PathTraversalError

def inject_license_wrapper(project_dir: Path, config: Dict[str, Any]) -> bool:
    """Inject license validation code into entry file."""
    entry_file_path = config.get("entry_file", "")
    license_key = config.get("license_key", "DEMO")

    try:
        entry_file = validate_entry_file(entry_file_path, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event("traversal_injection", {"error": str(e), "entry_file": entry_file_path})
        return False

    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file_path}", flush=True)
        log_security_event("missing_entry_file", {"entry_file": entry_file_path})
        return False

    try:
        original_code = entry_file.read_text(encoding="utf-8")
        server_url = config.get("server_url", "http://localhost:8000")
        server_url = normalize_server_url(server_url)
        lease_enabled = config.get("lease_enabled", False)
        show_branding = config.get("show_branding", True)

        branding_status = "ENABLED (Free tier)" if show_branding else "DISABLED (Pro/Enterprise)"
        print(f"[BUILD] Branding: {branding_status}", flush=True)

        public_key = config.get("signing_public_key") or ""
        heartbeat_interval = config.get("heartbeat_interval", 300)

        app_name = config.get("app_name") or config.get("project_name") or "Protected Application"
        brand_name = config.get("brand_name", "CodeVault")
        brand_url = config.get("brand_url", "https://codevault.dev")
        brand_primary_color = config.get("brand_primary_color", "#6366f1")
        binary_hash = config.get("binary_hash", "skip")

        wrapper = get_python_wrapper(
            license_key,
            server_url,
            None,
            lease_enabled,
            show_branding,
            public_key=public_key,
            heartbeat_interval=heartbeat_interval,
            app_name=app_name,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_primary_color=brand_primary_color,
            binary_hash=binary_hash,
        )
        entry_file.write_text(wrapper + original_code, encoding="utf-8")
        print(f"[BUILD] Injected wrapper into: {entry_file.name}", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to inject wrapper: {e}", flush=True)
        log_build_failure(
            project_id=config.get("project_id"),
            language="python",
            error_message=f"Wrapper injection failed: {str(e)}",
            error_type="injection_error",
            license_mode=license_key,
        )
        return False