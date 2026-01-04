import requests
import json
import tempfile
import zipfile
import shutil
from pathlib import Path
from terminal import Colors, color_print, print_header
from cli_config import get_api_base, DEFAULT_API_BASE
from commands.auth import check_logged_in, handle_error
from compiler_logic import run_compiler, copy_output, inject_license_wrapper, inject_js_wrapper

def run_local_build(args):
    """Run build on a local file without Server communication."""
    entry_path = Path(args.project_id).resolve()
    if not entry_path.exists():
        print(f"[ERROR] File not found: {entry_path}", flush=True)
        return

    print("[BUILD] License Wrapper - Local Build Mode", flush=True)

    # Get lease and obfuscate flags (default OFF)
    lease_enabled = getattr(args, "lease", False)
    obfuscate_enabled = getattr(args, "obfuscate", False)

    config = {
        "project_name": entry_path.stem,
        "entry_file": entry_path.name,
        "output_name": Path(args.output).stem if args.output else entry_path.stem,
        "language": args.language
        or ("nodejs" if entry_path.suffix == ".js" else "python"),
        "license_key": args.license or "GENERIC_BUILD",
        "server_url": args.api_url or DEFAULT_API_BASE,
        "lease_enabled": lease_enabled,
        "obfuscate_enabled": obfuscate_enabled,
    }

    if args.generic:
        config["license_key"] = "GENERIC_BUILD"
        print(
            "[BUILD] Generic Build Mode: License will be prompted at runtime",
            flush=True,
        )
    elif args.demo:
        config["license_key"] = "DEMO"
        config["demo_duration"] = args.demo_duration or 60
        print(f"[BUILD] Demo Mode: {config['demo_duration']} minutes", flush=True)

    # Display advanced options state
    print()
    print(f"[BUILD] {Colors.CYAN}Advanced Options:{Colors.RESET}")
    lease_status = f"{Colors.GREEN}ON{Colors.RESET}" if lease_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    obfuscate_status = f"{Colors.GREEN}ON{Colors.RESET}" if obfuscate_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    print(f"        Offline Lease (24h): [{lease_status}]")
    print(f"        Code Obfuscation:    [{obfuscate_status}]")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_project_dir = Path(tmpdir) / "project"
        tmp_project_dir.mkdir()

        source_dir = entry_path.parent
        print(f"[BUILD] Preparing source from: {source_dir}", flush=True)

        def ignore_patterns(path, names):
            return {
                "__pycache__", "node_modules", ".git", ".env", "dist", "build", "output"
            }

        shutil.copytree(
            source_dir, tmp_project_dir, ignore=ignore_patterns, dirs_exist_ok=True
        )

        if config["license_key"]:
            print("[BUILD] Injecting license protection...", flush=True)
            lang = config.get("language", "python")
            if lang == "nodejs":
                inject_js_wrapper(tmp_project_dir / config["entry_file"], config)
            else:
                inject_license_wrapper(tmp_project_dir, config)

        print(f"[BUILD] Compiling with {config['language']}...", flush=True)
        success, build_dir = run_compiler(tmp_project_dir, config)

        if success:
            copy_output(tmp_project_dir, config, config["license_key"], args.output, build_dir)
        else:
            print("[ERROR] Compilation failed.", flush=True)


def interactive_build(headers, api_url):
    """Interactive project and license selection."""
    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        if resp.status_code != 200:
            handle_error(resp)
            return None, None

        projects = resp.json()
        if not projects:
            color_print(
                "❌ No projects found. Create one on the web dashboard.", Colors.RED
            )
            return None, None

        print(f"\n{Colors.CYAN}Select a project to build:{Colors.RESET}\n")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p['name']} ({p['id'][:16]}...)")

        try:
            choice = int(input("\nEnter number: ").strip())
            if choice < 1 or choice > len(projects):
                raise ValueError()
            project = projects[choice - 1]
        except (ValueError, IndexError):
            color_print("❌ Invalid selection.", Colors.RED)
            return None, None

        project_id = project["id"]

        resp = requests.get(
            f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            licenses = resp.json()
            if licenses:
                active_licenses = [lic for lic in licenses if lic["status"] == "active"]
                if active_licenses:
                    print(
                        f"\n{Colors.CYAN}Select a license (or 0 for no license):{Colors.RESET}\n"
                    )
                    print("  0. No license (demo mode)")
                    for i, lic in enumerate(active_licenses, 1):
                        client = (
                            f" - {lic['client_name']}" if lic.get("client_name") else ""
                        )
                        print(f"  {i}. {lic['license_key']}{client}")

                    try:
                        choice = int(input("\nEnter number: ").strip())
                        if choice > 0 and choice <= len(active_licenses):
                            return project_id, active_licenses[choice - 1][
                                "license_key"
                            ]
                    except (ValueError, IndexError):
                        pass

        return project_id, None

    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        return None, None


def cmd_build(args):
    """Build a project locally using Nuitka or pkg."""
    project_id = args.project_id
    license_key = args.license

    # Get lease and obfuscate flags (default OFF)
    lease_enabled = getattr(args, "lease", False)
    obfuscate_enabled = getattr(args, "obfuscate", False)

    if getattr(args, "open", False):
        license_key = None
        color_print("🔓 Open Build Mode: No license protection", Colors.YELLOW)
    elif getattr(args, "generic", False) or not license_key:
        license_key = "GENERIC_BUILD"
        color_print("🔐 License will be prompted at runtime (default)", Colors.CYAN)

    if project_id and (
        Path(project_id).exists()
        or project_id.endswith(".py")
        or project_id.endswith(".js")
    ):
        run_local_build(args)
        return

    headers = check_logged_in()
    api_url = get_api_base()

    if not project_id:
        project_id, interactive_license = interactive_build(headers, api_url)
        if not project_id:
            return
        if not getattr(args, "open", False) and interactive_license:
            license_key = interactive_license

    print_header("CodeVault CLI - Local Compilation")

    # Display advanced options state
    print(f"{Colors.CYAN}Advanced Options:{Colors.RESET}")
    lease_status = f"{Colors.GREEN}ON{Colors.RESET}" if lease_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    obfuscate_status = f"{Colors.GREEN}ON{Colors.RESET}" if obfuscate_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    print(f"  Offline Lease (24h): [{lease_status}]")
    print(f"  Code Obfuscation:    [{obfuscate_status}]")
    print()

    try:
        color_print("[1/5] Fetching project configuration...", Colors.BLUE)
        params = {}
        if license_key:
            params["license_key"] = license_key
        resp = requests.get(
            f"{api_url}/projects/{project_id}/compile-config",
            headers=headers,
            params=params,
            timeout=10,
        )

        if resp.status_code != 200:
            handle_error(resp)
            return

        config = resp.json()
        config["lease_enabled"] = lease_enabled
        config["obfuscate_enabled"] = obfuscate_enabled

        print(f"      Project: {config['project_name']}")
        print(f"      Entry file: {config['entry_file']}")
        print(f"      Output: {config['output_name']}.exe")

        if args.language:
            config["language"] = args.language

        if not config.get("language"):
            entry_ext = Path(config.get("entry_file", "")).suffix.lower()
            if entry_ext in [".js", ".mjs", ".cjs", ".ts"]:
                config["language"] = "nodejs"
                print("      🔍 Auto-detected: Node.js project")
            else:
                config["language"] = "python"

        print(f"      Language: {config.get('language')}")

        color_print("\n[2/5] Downloading project bundle...", Colors.BLUE)
        bundle_params = {}
        if license_key:
            bundle_params["license_id"] = license_key

        resp = requests.get(
            f"{api_url}/projects/{project_id}/build-bundle",
            headers=headers,
            params=bundle_params,
            timeout=120,
            stream=True,
        )

        if resp.status_code != 200:
            if resp.status_code == 400:
                color_print("\n❌ Error: No source files found.", Colors.RED)
            handle_error(resp)
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            bundle_path = tmpdir / "bundle.zip"
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(bundle_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(downloaded * 100 / total_size)
                            print(f"\r      Downloaded: {pct}%", end="", flush=True)
            print()

            project_dir = tmpdir / "project"
            project_dir.mkdir()

            color_print("[3/5] Extracting source files...", Colors.BLUE)
            try:
                with zipfile.ZipFile(bundle_path, "r") as zf:
                    zf.extractall(project_dir)
            except zipfile.BadZipFile:
                color_print("❌ Error: Invalid bundle file received.", Colors.RED)
                return

            bundle_config_path = project_dir / "config.json"
            if bundle_config_path.exists():
                try:
                    bundle_config = json.loads(bundle_config_path.read_text())
                    for key in ["license_key", "api_url", "server_url", "language"]:
                        if key in bundle_config and bundle_config[key]:
                            config[key] = bundle_config[key]
                except Exception:
                    pass

            source_dir = project_dir / "source"
            if not source_dir.exists():
                source_dir = project_dir

            color_print("[4/5] Injecting license protection...", Colors.BLUE)
            effective_license = license_key or config.get("license_key")
            if effective_license:
                config["license_key"] = effective_license
                if config.get("language") == "nodejs":
                    inject_js_wrapper(source_dir / config["entry_file"], config)
                else:
                    inject_license_wrapper(source_dir, config)
                print(f"      License mode: {effective_license}")
            else:
                print("      No license protection (open build)")

            if not config.get("language"):
                config["language"] = "python" # Default fallback
            
            compiler_name = "pkg" if config.get("language") == "nodejs" else "Nuitka"
            color_print(f"\n[5/5] Compiling with {compiler_name}...", Colors.BLUE)

            success, build_dir = run_compiler(source_dir, config)

            if success:
                copy_output(source_dir, config, effective_license, args.output, build_dir)
                color_print("\n✅ Build complete!", Colors.GREEN)
            else:
                color_print("\n❌ Compilation failed.", Colors.RED)

    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
