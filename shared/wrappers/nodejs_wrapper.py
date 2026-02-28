import json
from pathlib import Path
from typing import Dict, Any
from cli.url_utils import normalize_server_url
from cli.audit import log_security_event, log_build_failure
from cli.generators.nodejs_generator import get_nodejs_wrapper_inline

def inject_js_wrapper(entry_file: Path, config: Dict[str, Any]) -> bool:
    """Inject JS license wrapper by wrapping entry file in async IIFE."""
    license_key = config.get("license_key", "DEMO")

    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file}", flush=True)
        log_security_event("missing_entry_file_js", {"entry_file": str(entry_file)})
        return False

    try:
        original_code = entry_file.read_text(encoding="utf-8")
        server_url = config.get("server_url", "http://localhost:8000")
        server_url = normalize_server_url(server_url)
        lease_enabled = config.get("lease_enabled", False)
        show_branding = config.get("show_branding", True)

        branding_status = "ENABLED (Free tier)" if show_branding else "DISABLED (Pro/Enterprise)"
        print(f"[BUILD] Branding: {branding_status}", flush=True)

        shebang = ""
        if original_code.startswith("#!"):
            first_newline = original_code.find("
")
            if first_newline != -1:
                shebang = original_code[: first_newline + 1]
                original_code = original_code[first_newline + 1 :]
                print(f"[BUILD] Stripped shebang: {shebang.strip()}", flush=True)

        public_key = config.get("signing_public_key") or ""
        heartbeat_interval = config.get("heartbeat_interval", 300)
        app_name = config.get("app_name") or config.get("project_name") or "Protected Application"
        binary_hash = config.get("binary_hash", "skip")

        prefix, suffix = get_nodejs_wrapper_inline(
            license_key,
            server_url,
            lease_enabled,
            show_branding,
            public_key=public_key,
            heartbeat_interval=heartbeat_interval,
            app_name=app_name,
            binary_hash=binary_hash,
        )
        
        entry_name = entry_file.name
        
        bootstrap_code = f"""{shebang}{prefix}
        // Load user code
        try {{
            require('./{entry_name}');
        }} catch (e) {{
            if (e.code === 'ERR_REQUIRE_ESM') {{
                // Fallback to dynamic import for ESM
                await import('./{entry_name}');
            }} else {{
                throw e;
            }}
        }}
{suffix}"""

        bootstrap_file = entry_file.parent / "_cv_bootstrap.js"
        bootstrap_file.write_text(bootstrap_code, encoding="utf-8")
        
        package_json = entry_file.parent / "package.json"
        if package_json.exists():
            try:
                pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
                pkg_data["bin"] = "_cv_bootstrap.js"
                pkg_data["main"] = "_cv_bootstrap.js"
                package_json.write_text(json.dumps(pkg_data, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[WARN] Could not update package.json: {e}")
                
        print(f"[BUILD] Created JS bootstrap wrapper: {bootstrap_file.name}", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to inject JS wrapper: {e}", flush=True)
        log_build_failure(
            project_id=config.get("project_id"),
            language="nodejs",
            error_message=f"JS wrapper injection failed: {str(e)}",
            error_type="injection_error",
            license_mode=license_key,
        )
        return False