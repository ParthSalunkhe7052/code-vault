import requests
import json
from terminal import Colors, color_print, print_header
from cli_config import get_api_base
from commands.auth import check_logged_in, handle_error


def cmd_projects(args):
    """List user's projects."""
    headers = check_logged_in()
    api_url = get_api_base()

    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            print_header("Your Projects")

            # Handle both flat list and {projects: [...]} response formats
            if isinstance(data, dict) and "projects" in data:
                projects = data["projects"]
            elif isinstance(data, list):
                projects = data
            else:
                projects = []

            if not projects:
                color_print(
                    "  No projects found. Create one on the web dashboard.",
                    Colors.YELLOW,
                )
                return

            for i, p in enumerate(projects, 1):
                settings = p.get("settings", {})
                if isinstance(settings, str):
                    settings = json.loads(settings) if settings else {}

                is_multi = settings.get("is_multi_folder", False)
                project_type = (
                    "[DIR] Multi-folder" if is_multi else "[FILE] Single file"
                )

                print(f"  {Colors.BOLD}{i}. {p['name']}{Colors.RESET}")
                print(f"     ID: {Colors.CYAN}{p['id']}{Colors.RESET}")
                print(f"     Type: {project_type}")
                print()
        else:
            handle_error(resp)
    except Exception as e:
        color_print(f"[X] Error: {e}", Colors.RED)


def cmd_licenses(args):
    """List licenses for a project."""
    headers = check_logged_in()
    api_url = get_api_base()
    project_id = args.project_id

    try:
        resp = requests.get(
            f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            print_header(f"Licenses for Project: {str(project_id)[:16]}...")

            # Handle both flat list and {licenses: [...]} response formats
            if isinstance(data, dict) and "licenses" in data:
                licenses = data["licenses"]
            elif isinstance(data, list):
                licenses = data
            else:
                licenses = []

            if not licenses:
                color_print(
                    "  No licenses found. Create one on the web dashboard.",
                    Colors.YELLOW,
                )
                return

            for i, lic in enumerate(licenses, 1):
                status_color = Colors.GREEN if lic["status"] == "active" else Colors.RED
                print(f"  {Colors.BOLD}{i}. {lic['license_key']}{Colors.RESET}")
                print(f"     Status: {status_color}{lic['status']}{Colors.RESET}")
                if lic.get("client_name"):
                    print(f"     Client: {lic['client_name']}")
                if lic.get("expires_at"):
                    print(f"     Expires: {lic['expires_at']}")
                print()
        else:
            handle_error(resp)
    except Exception as e:
        color_print(f"[X] Error: {e}", Colors.RED)
