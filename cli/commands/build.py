import requests
import json
import tempfile
import zipfile
import shutil
import time
from pathlib import Path
from terminal import Colors, color_print, print_header
from cli_config import get_api_base, DEFAULT_API_BASE
from commands.auth import check_logged_in, handle_error
from compiler_logic import run_compiler, copy_output, inject_license_wrapper, inject_js_wrapper, analyze_and_warn_project
from audit import log_build_start, log_build_success, log_build_failure


def prompt_build_mode():
    """Prompt user to select build mode (fast or normal).

    Returns:
        bool: True for fast mode, False for normal mode
    """
    print(f"\n{Colors.CYAN}Select build mode:{Colors.RESET}\n")
    print(f"  1. {Colors.GREEN}Fast Mode{Colors.RESET} (3-4x faster)")
    print("     • Compiles WITHOUT --onefile")
    print("     • Output is a folder, not a single .exe")
    print("     • Missing: Single-file deployment convenience")
    print("     • Best for: Development, testing, quick iterations\n")
    print(f"  2. {Colors.YELLOW}Normal Mode{Colors.RESET} (standard)")
    print("     • Single .exe file with license protection")
    print("     • Slower (2-3x longer build time)")
    print("     • Better for: Final distribution to customers\n")

    while True:
        mode_choice = input("Choose mode (1=Fast, 2=Normal): ").strip()
        if mode_choice == "1":
            return True
        elif mode_choice == "2":
            return False
        else:
            print(f"{Colors.RED}Invalid choice. Enter 1 or 2.{Colors.RESET}")


def run_local_build(args):
    """Run build on a local file without Server communication."""
    # Ensure user is logged in even for local builds (defense in depth)
    check_logged_in()

    entry_path = Path(args.project_id).resolve()
    if not entry_path.exists():
        print(f"[ERROR] File not found: {entry_path}", flush=True)
        log_build_failure(
            project_id="local_file",
            language="unknown",
            error_message=f"File not found: {entry_path}",
            error_type="file_not_found",
            license_mode="unknown"
        )
        return

    print("\n" + "="*60)
    print("🚀 CODEVAULT BUILD SYSTEM")
    print("="*60 + "\n")

    # Check for obfuscation and lease flags from command-line arguments
    # If not provided, defaults are OFF
    lease_enabled = getattr(args, 'enable_lease', False)
    obfuscate_enabled = getattr(args, 'obfuscate', False)

    # Interactive build mode selection if flag not provided
    fast_build = getattr(args, 'fast_build', None)
    if fast_build is None:
        fast_build = prompt_build_mode()

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
        # NEW: Build optimization options
        "fast_build": fast_build,
        "jobs": getattr(args, 'jobs', None),
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

    # Show build mode
    print(f"Mode: {'FAST BUILD (no onefile)' if config.get('fast_build') else 'Standard (onefile executable)'}")
    print(f"Language: {config['language']}")
    print(f"Output: {config['output_name']}.exe")
    print("="*60 + "\n")

    # Display build options
    print(f"{Colors.CYAN}Build Options:{Colors.RESET}")
    lease_status = f"{Colors.GREEN}ON{Colors.RESET}" if lease_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    obfuscate_status = f"{Colors.GREEN}ON{Colors.RESET}" if obfuscate_enabled else f"{Colors.DIM}OFF{Colors.RESET}"
    print(f"  Offline Lease (24h): [{lease_status}]")
    print(f"  Code Obfuscation:    [{obfuscate_status}]")
    if config.get("jobs"):
        print(f"  CPU Cores:           [{config.get('jobs')}]")
    print()

    # Pre-build time estimation and warnings
    source_dir = entry_path.parent
    print(f"{Colors.YELLOW}⏱️  Build Time Estimation:{Colors.RESET}")
    if config.get("fast_build"):
        print("  Fast mode: Project will be compiled WITHOUT --onefile")
        print("  This is 3-4x faster than standard mode")
    else:
        print("  Standard mode: Single .exe with license protection")
        print("  This may take 20+ minutes for large projects")
    print(f"  {Colors.DIM}Tip: Use --fast-build for testing iterations{Colors.RESET}\n")

    # Analyze project and show detailed warnings
    if not analyze_and_warn_project(source_dir, config):
        return  # User cancelled

    # Log build start
    log_build_start(
        project_id="local_file",
        language=config["language"],
        license_mode=config["license_key"],
        obfuscate_enabled=obfuscate_enabled,
        lease_enabled=lease_enabled,
        source_file=entry_path.name
    )

    build_start_time = time.time()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_project_dir = Path(tmpdir) / "project"
        tmp_project_dir.mkdir()

        print(f"[BUILD] Preparing source from: {source_dir}", flush=True)

        def ignore_patterns(path, names):
            return {
                "__pycache__", "node_modules", ".git", ".env", "dist", "build", "output"
            }

        shutil.copytree(
            source_dir, tmp_project_dir, ignore=ignore_patterns, dirs_exist_ok=True
        )

        injection_success = True
        if config["license_key"]:
            print("[BUILD] Injecting license protection...", flush=True)
            lang = config.get("language", "python")
            if lang == "nodejs":
                injection_success = inject_js_wrapper(tmp_project_dir / config["entry_file"], config)
            else:
                injection_success = inject_license_wrapper(tmp_project_dir, config)

        if not injection_success:
            build_duration = int((time.time() - build_start_time) * 1000)
            log_build_failure(
                project_id="local_file",
                language=config["language"],
                error_message="License wrapper injection failed",
                error_type="injection_failed",
                license_mode=config["license_key"]
            )
            return

        print(f"[BUILD] Compiling with {config['language']}...", flush=True)
        success, build_dir = run_compiler(tmp_project_dir, config)

        if success:
            # Calculate duration before copy
            build_duration = int((time.time() - build_start_time) * 1000)

            copy_output(tmp_project_dir, config, config["license_key"], args.output, build_dir)

            # Get output file size if available
            output_size = 0
            try:
                if build_dir:
                    exe_name = f"{config.get('output_name', 'output')}.exe"
                    exe_path = build_dir / exe_name
                    if exe_path.exists():
                        output_size = exe_path.stat().st_size
            except Exception:
                pass

            log_build_success(
                project_id="local_file",
                language=config["language"],
                duration_ms=build_duration,
                output_size_bytes=output_size,
                license_mode=config["license_key"]
            )
        else:
            build_duration = int((time.time() - build_start_time) * 1000)
            log_build_failure(
                project_id="local_file",
                language=config["language"],
                error_message="Compilation failed",
                error_type="compiler_error",
                license_mode=config["license_key"]
            )
            print(f"\n{Colors.RED}❌ BUILD FAILED{Colors.RESET}\n")


def interactive_build(headers, api_url):
    """Interactive project, license, and build mode selection."""
    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        if resp.status_code != 200:
            handle_error(resp)
            return None, None, None

        projects = resp.json()
        if not projects:
            color_print(
                "❌ No projects found. Create one on the web dashboard.", Colors.RED
            )
            return None, None, None

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
            return None, None, None

        project_id = project["id"]

        resp = requests.get(
            f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10
        )
        license_key = None
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
                            license_key = active_licenses[choice - 1]["license_key"]
                    except (ValueError, IndexError):
                        pass

        # NEW: Ask about build mode
        print(f"\n{Colors.CYAN}Select build mode:{Colors.RESET}\n")
        print(f"  1. {Colors.GREEN}Fast Mode{Colors.RESET} (3-4x faster)")
        print("     • Compiles WITHOUT --onefile")
        print("     • Output is a folder, not a single .exe")
        print("     • Missing: Single-file deployment convenience")
        print("     • Best for: Development, testing, quick iterations\n")
        print(f"  2. {Colors.YELLOW}Normal Mode{Colors.RESET} (standard)")
        print("     • Single .exe file with license protection")
        print("     • Slower (2-3x longer build time)")
        print("     • Better for: Final distribution to customers\n")

        while True:
            mode_choice = input("Choose mode (1=Fast, 2=Normal): ").strip()
            if mode_choice == "1":
                fast_build = True
                break
            elif mode_choice == "2":
                fast_build = False
                break
            else:
                print(f"{Colors.RED}Invalid choice. Enter 1 or 2.{Colors.RESET}")

        return project_id, license_key, fast_build

    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        return None, None, None


def cmd_build(args):
    """Build a project locally using Nuitka or pkg."""
    # CRITICAL: Always check login FIRST before any build operation
    # This ensures users are authenticated before compilation proceeds
    check_logged_in()

    project_id = args.project_id
    license_key = args.license

    if getattr(args, "open", False):
        license_key = None
        color_print("🔓 Open Build Mode: No license protection", Colors.YELLOW)
    elif getattr(args, "generic", False) or not license_key:
        license_key = "GENERIC_BUILD"
        color_print("🔐 License will be prompted at runtime (default)", Colors.CYAN)

    # Check for fast-build shortcut
    if getattr(args, 'fast_build', False):
        color_print("🚀 Fast Build Mode enabled (no onefile, optimized)", Colors.GREEN)

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
        project_id, interactive_license, interactive_fast_build = interactive_build(headers, api_url)
        if not project_id:
            return
        if not getattr(args, "open", False) and interactive_license:
            license_key = interactive_license
        # Use interactive choice if --fast-build flag wasn't provided
        if interactive_fast_build is not None and not getattr(args, 'fast_build', False):
            args.fast_build = interactive_fast_build
    else:
        # Project ID was provided directly - prompt for build mode if not specified
        if getattr(args, 'fast_build', None) is None:
            args.fast_build = prompt_build_mode()

    print_header("CodeVault CLI - Local Compilation")

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

        # Convert server naming to CLI naming
        # Server: skip_obfuscation (True = don't obfuscate), enable_lease
        # CLI: obfuscate_enabled (True = obfuscate), lease_enabled
        config["obfuscate_enabled"] = not config.get("skip_obfuscation", True)
        config["lease_enabled"] = config.get("enable_lease", False)

        # NEW: Add CLI optimization options
        config["fast_build"] = getattr(args, 'fast_build', False)
        config["jobs"] = getattr(args, 'jobs', None)

        # Display what mode was selected
        if config["fast_build"]:
            print(f"      {Colors.GREEN}Build Mode: FAST{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}Build Mode: NORMAL{Colors.RESET}")

        print(f"\n      Project: {config['project_name']}")
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
                    
                    # Load build options from bundle config
                    # Convert server naming to CLI naming
                    # Server: skip_obfuscation (True = don't obfuscate), enable_lease
                    # CLI: obfuscate_enabled (True = obfuscate), lease_enabled
                    if "skip_obfuscation" in bundle_config:
                        config["obfuscate_enabled"] = not bundle_config["skip_obfuscation"]
                    if "enable_lease" in bundle_config:
                        config["lease_enabled"] = bundle_config["enable_lease"]
                except Exception:
                    pass

            # Display build options loaded from bundle
            print(f"\n{Colors.CYAN}Build Options (from project settings):{Colors.RESET}")
            lease_status = f"{Colors.GREEN}ON{Colors.RESET}" if config.get("lease_enabled", False) else f"{Colors.DIM}OFF{Colors.RESET}"
            obfuscate_status = f"{Colors.GREEN}ON{Colors.RESET}" if config.get("obfuscate_enabled", False) else f"{Colors.DIM}OFF{Colors.RESET}"
            print(f"  Offline Lease (24h): [{lease_status}]")
            print(f"  Code Obfuscation:    [{obfuscate_status}]")
            if config.get("jobs"):
                print(f"  CPU Cores:           [{config.get('jobs')}]")
            if config.get("fast_build"):
                print(f"  {Colors.GREEN}Fast Mode:            [ENABLED]{Colors.RESET}")
            print()

            source_dir = project_dir / "source"
            if not source_dir.exists():
                source_dir = project_dir

            # Pre-build time estimation banner
            print(f"{Colors.YELLOW}⏱️  Build Time Estimation:{Colors.RESET}")
            if config.get("fast_build"):
                print("  Fast mode: Project will be compiled WITHOUT --onefile")
                print("  This is 3-4x faster than standard mode")
            else:
                print("  Standard mode: Single .exe with license protection")
                print("  This may take 20+ minutes for large projects")
            print(f"  {Colors.DIM}Tip: Use --fast-build for testing iterations{Colors.RESET}\n")

            # NEW: Analyze project and show warnings
            if not analyze_and_warn_project(source_dir, config):
                print("  Build cancelled by user.")
                return

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
                effective_license = "OPEN_BUILD"

            if not config.get("language"):
                config["language"] = "python" # Default fallback

            # Log build start
            log_build_start(
                project_id=project_id,
                language=config["language"],
                license_mode=effective_license,
                obfuscate_enabled=config.get("obfuscate_enabled", False),
                lease_enabled=config.get("lease_enabled", False),
                source_file=config.get("entry_file", "unknown")
            )

            build_start_time = time.time()

            compiler_name = "pkg" if config.get("language") == "nodejs" else "Nuitka"
            color_print(f"\n[5/5] Compiling with {compiler_name}...", Colors.BLUE)

            success, build_dir = run_compiler(source_dir, config)

            if success:
                copy_output(source_dir, config, effective_license, args.output, build_dir)
                build_duration = int((time.time() - build_start_time) * 1000)

                # Get output file size if available
                output_size = 0
                try:
                    if build_dir:
                        exe_name = f"{config.get('output_name', 'output')}.exe"
                        exe_path = build_dir / exe_name
                        if exe_path.exists():
                            output_size = exe_path.stat().st_size
                except Exception:
                    pass

                log_build_success(
                    project_id=project_id,
                    language=config["language"],
                    duration_ms=build_duration,
                    output_size_bytes=output_size,
                    license_mode=effective_license
                )
                # copy_output already shows completion banner
            else:
                build_duration = int((time.time() - build_start_time) * 1000)
                log_build_failure(
                    project_id=project_id,
                    language=config["language"],
                    error_message="Compilation failed",
                    error_type="compiler_error",
                    license_mode=effective_license
                )
                import sys
                sys.stdout.write('\a\a')  # Double bell for error
                sys.stdout.flush()
                color_print("\n❌ Compilation failed.", Colors.RED)

    except Exception as e:
        build_duration = int((time.time() - build_start_time) * 1000) if 'build_start_time' in locals() else 0
        log_build_failure(
            project_id=project_id if 'project_id' in locals() else "unknown",
            language=config.get("language", "unknown") if 'config' in locals() else "unknown",
            error_message=str(e),
            error_type="exception",
            license_mode=effective_license if 'effective_license' in locals() else "unknown"
        )
        color_print(f"❌ Error: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
