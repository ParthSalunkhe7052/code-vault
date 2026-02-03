#!/usr/bin/env python3
"""
CodeVault - Automated Google Cloud Build Setup Script
=====================================================
This script automates the entire Cloud Build configuration process.

Requirements:
- Google Cloud SDK (gcloud CLI) installed
- You must be authenticated: gcloud auth login
- Owner or Editor role on the project

Usage:
    python setup_cloud_build.py
"""

import subprocess
import sys
import json
import os
import time
from pathlib import Path

# Configuration
PROJECT_ID = "cloudbuild-486309"
REGION = "global"
GCS_BUCKET_NAME = "codevault-builds"
GCS_BUCKET_LOCATION = "US"  # Multi-region
GITHUB_REPO_OWNER = "ParthSalunkhe7052"
GITHUB_REPO_NAME = "code-vault"
SERVICE_ACCOUNT_EMAIL = "codevault-ai-agent@cloudbuild-486309.iam.gserviceaccount.com"

# Add gcloud to PATH if on Windows
GCLOUD_PATH = r"C:\Users\parth\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
if os.path.exists(GCLOUD_PATH):
    os.environ["PATH"] = GCLOUD_PATH + os.pathsep + os.environ.get("PATH", "")


# Helper function to get the correct gcloud command
def get_gcloud_cmd():
    """Get the correct gcloud command for the platform"""
    return "gcloud.cmd" if sys.platform == "win32" else "gcloud"


def get_gsutil_cmd():
    """Get the correct gsutil command for the platform"""
    return "gsutil.cmd" if sys.platform == "win32" else "gsutil"


# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(message):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(message):
    """Print a success message"""
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.FAIL}[ERROR] {message}{Colors.ENDC}")


def print_info(message):
    """Print an info message"""
    print(f"{Colors.OKCYAN}[INFO] {message}{Colors.ENDC}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.WARNING}[WARNING] {message}{Colors.ENDC}")


def run_command(cmd, description, check=True, capture_output=True):
    """
    Run a shell command with nice output

    Args:
        cmd: Command to run (list or string)
        description: Description of what the command does
        check: Whether to raise exception on failure
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess object
    """
    print_info(f"{description}...")

    try:
        if isinstance(cmd, str):
            cmd = cmd.split()

        result = subprocess.run(
            cmd, check=check, capture_output=capture_output, text=True
        )

        print_success(f"{description} - Done")
        return result

    except subprocess.CalledProcessError as e:
        print_error(f"{description} - Failed")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        if not check:
            return e
        raise


def check_gcloud_installed():
    """Check if gcloud CLI is installed"""
    print_header("Step 1: Checking Prerequisites")

    # On Windows, use gcloud.cmd
    gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"

    try:
        result = subprocess.run(
            [gcloud_cmd, "version"], capture_output=True, text=True, check=True
        )
        print_success("gcloud CLI is installed")
        return True
    except FileNotFoundError:
        print_error("gcloud CLI is not installed")
        print("\nPlease install Google Cloud SDK:")
        print("  Windows: https://cloud.google.com/sdk/docs/install-sdk#windows")
        print("  macOS:   brew install --cask google-cloud-sdk")
        print("  Linux:   https://cloud.google.com/sdk/docs/install-sdk#linux")
        return False


def check_authentication():
    """Check if user is authenticated"""
    print_info("Checking authentication...")

    gcloud = get_gcloud_cmd()

    result = subprocess.run(
        [gcloud, "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        print_success(f"Authenticated as: {result.stdout.strip()}")
        return True
    else:
        print_warning("Not authenticated")
        print("\nPlease run: gcloud auth login")

        response = input("\nWould you like to authenticate now? (y/n): ")
        if response.lower() == "y":
            subprocess.run([gcloud, "auth", "login"], check=True)
            print_success("Authentication complete")
            return True
        else:
            print_error("Authentication required to continue")
            return False


def set_project():
    """Set the active project"""
    print_header("Step 2: Setting Project")

    run_command(
        [get_gcloud_cmd(), "config", "set", "project", PROJECT_ID],
        f"Setting project to {PROJECT_ID}",
    )


def enable_apis():
    """Enable required Google Cloud APIs"""
    print_header("Step 3: Enabling Required APIs")

    apis = [
        ("cloudbuild.googleapis.com", "Cloud Build API"),
        ("storage.googleapis.com", "Cloud Storage API"),
        ("secretmanager.googleapis.com", "Secret Manager API"),
        ("cloudresourcemanager.googleapis.com", "Cloud Resource Manager API"),
    ]

    for api, description in apis:
        run_command(
            [get_gcloud_cmd(), "services", "enable", api, "--project", PROJECT_ID],
            f"Enabling {description}",
        )

    print_success("All APIs enabled")
    time.sleep(2)  # Wait for APIs to propagate


def create_gcs_bucket():
    """Create Google Cloud Storage bucket"""
    print_header("Step 4: Creating Cloud Storage Bucket")

    # Check if bucket exists
    result = subprocess.run(
        [get_gsutil_cmd(), "ls", "-b", f"gs://{GCS_BUCKET_NAME}"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print_warning(f"Bucket gs://{GCS_BUCKET_NAME} already exists")
    else:
        run_command(
            [get_gsutil_cmd(),
                "mb",
                "-p",
                PROJECT_ID,
                "-l",
                GCS_BUCKET_LOCATION,
                f"gs://{GCS_BUCKET_NAME}",
            ],
            f"Creating bucket gs://{GCS_BUCKET_NAME}",
        )

    # Set uniform bucket-level access
    run_command(
        [
            get_gsutil_cmd(),
            "uniformbucketlevelaccess",
            "set",
            "on",
            f"gs://{GCS_BUCKET_NAME}",
        ],
        "Setting uniform bucket-level access",
    )

    # Grant Storage Object Admin to service account
    run_command(
        [
            get_gsutil_cmd(),
            "iam",
            "ch",
            f"serviceAccount:{SERVICE_ACCOUNT_EMAIL}:roles/storage.objectAdmin",
            f"gs://{GCS_BUCKET_NAME}",
        ],
        "Granting permissions to service account",
    )


def create_secrets():
    """Create secrets in Secret Manager"""
    print_header("Step 5: Creating Secrets")

    print_info("We need to create secrets for your webhook callback")
    print_info("These are the same secrets you use in GitHub Actions\n")

    # Check if secret exists
    result = subprocess.run(
        [get_gcloud_cmd(),
            "secrets",
            "describe",
            "callback-webhook-secret",
            "--project",
            PROJECT_ID,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print_warning("Secret 'callback-webhook-secret' already exists")
        update = input("Would you like to update it? (y/n): ")

        if update.lower() == "y":
            secret_value = input("Enter your webhook secret (HMAC key): ").strip()
            if secret_value:
                # Create new version
                proc = subprocess.Popen(
                    [get_gcloud_cmd(),
                        "secrets",
                        "versions",
                        "add",
                        "callback-webhook-secret",
                        "--data-file=-",
                        "--project",
                        PROJECT_ID,
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                proc.communicate(input=secret_value)
                print_success("Secret updated")
    else:
        secret_value = input("Enter your webhook secret (HMAC key): ").strip()

        if not secret_value:
            print_error("Secret value cannot be empty")
            sys.exit(1)

        # Create secret
        run_command(
            [get_gcloud_cmd(),
                "secrets",
                "create",
                "callback-webhook-secret",
                "--replication-policy=automatic",
                "--project",
                PROJECT_ID,
            ],
            "Creating secret",
        )

        # Add secret value
        proc = subprocess.Popen(
            [get_gcloud_cmd(),
                "secrets",
                "versions",
                "add",
                "callback-webhook-secret",
                "--data-file=-",
                "--project",
                PROJECT_ID,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        proc.communicate(input=secret_value)
        print_success("Secret created")

    # Grant access to service account
    run_command(
        [get_gcloud_cmd(),
            "secrets",
            "add-iam-policy-binding",
            "callback-webhook-secret",
            "--member",
            f"serviceAccount:{SERVICE_ACCOUNT_EMAIL}",
            "--role",
            "roles/secretmanager.secretAccessor",
            "--project",
            PROJECT_ID,
        ],
        "Granting secret access to service account",
    )


def connect_github():
    """Guide user to connect GitHub repository"""
    print_header("Step 6: Connecting GitHub Repository")

    print_info("GitHub connection requires OAuth authentication through the web UI")
    print_info("This is a one-time setup that takes about 2 minutes\n")

    print(f"{Colors.BOLD}Please follow these steps:{Colors.ENDC}")
    print(f"1. Open this URL in your browser:")
    print(
        f"   {Colors.OKCYAN}https://console.cloud.google.com/cloud-build/triggers/connect?project={PROJECT_ID}{Colors.ENDC}"
    )
    print(f"2. Click 'Connect Repository'")
    print(f"3. Select 'GitHub (Cloud Build GitHub App)'")
    print(f"4. Authenticate with GitHub")
    print(f"5. Select repository: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    print(f"6. Click 'Connect'\n")

    input("Press Enter once you've completed the GitHub connection... ")
    print_success("GitHub connection noted")


def push_cloudbuild_yaml():
    """Commit and push cloudbuild.yaml to repository"""
    print_header("Step 7: Pushing cloudbuild.yaml to Repository")

    # Check if we're in a git repo
    if not Path(".git").exists():
        print_warning("Not in a git repository")
        print_info("The cloudbuild.yaml file has been created in the current directory")
        print_info("Please commit and push it to your repository manually:")
        print(f"  git add cloudbuild.yaml")
        print(f"  git commit -m 'Add Google Cloud Build configuration'")
        print(f"  git push")
        return

    # Check if file exists
    if not Path("cloudbuild.yaml").exists():
        print_error("cloudbuild.yaml not found in current directory")
        return

    # Add to git
    run_command(
        ["git", "add", "cloudbuild.yaml"], "Adding cloudbuild.yaml to git", check=False
    )

    # Commit
    result = run_command(
        [
            "git",
            "commit",
            "-m",
            "Add Google Cloud Build configuration for production builds",
        ],
        "Committing cloudbuild.yaml",
        check=False,
    )

    if "nothing to commit" in result.stdout or "nothing to commit" in (
        result.stderr or ""
    ):
        print_warning("cloudbuild.yaml already committed")

    # Push
    push = input("\nWould you like to push to GitHub now? (y/n): ")
    if push.lower() == "y":
        run_command(["git", "push"], "Pushing to GitHub", capture_output=False)


def test_setup():
    """Test the Cloud Build setup"""
    print_header("Step 8: Testing Setup")

    # Verify bucket
    result = subprocess.run(
        [get_gsutil_cmd(), "ls", "-b", f"gs://{GCS_BUCKET_NAME}"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print_success(f"Bucket gs://{GCS_BUCKET_NAME} is accessible")
    else:
        print_error("Bucket not accessible")

    # Verify secret
    result = subprocess.run(
        [get_gcloud_cmd(),
            "secrets",
            "describe",
            "callback-webhook-secret",
            "--project",
            PROJECT_ID,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print_success("Secret 'callback-webhook-secret' exists")
    else:
        print_error("Secret not found")

    # Check APIs
    result = subprocess.run(
        [get_gcloud_cmd(),
            "services",
            "list",
            "--enabled",
            "--filter=cloudbuild.googleapis.com",
            "--format=value(name)",
            "--project",
            PROJECT_ID,
        ],
        capture_output=True,
        text=True,
    )

    if "cloudbuild.googleapis.com" in result.stdout:
        print_success("Cloud Build API is enabled")
    else:
        print_error("Cloud Build API not enabled")


def print_next_steps():
    """Print next steps for the user"""
    print_header("Setup Complete! 🎉")

    print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}\n")

    print(f"{Colors.OKGREEN}1. Update Your Backend Code{Colors.ENDC}")
    print(f"   Replace GitHub Actions API calls with Cloud Build API")
    print(f"   Use the 'cloud_build_integration.py' file that was created\n")

    print(
        f"{Colors.OKGREEN}2. Install Python Dependencies on Your Backend{Colors.ENDC}"
    )
    print(f"   pip install google-cloud-build google-auth\n")

    print(f"{Colors.OKGREEN}3. Set Environment Variable on Digital Ocean{Colors.ENDC}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials\n")
    print(f"   OR authenticate with: gcloud auth application-default login\n")

    print(f"{Colors.OKGREEN}4. Test a Build{Colors.ENDC}")
    print(f"   You can test manually in the console:")
    print(
        f"   {Colors.OKCYAN}https://console.cloud.google.com/cloud-build/builds?project={PROJECT_ID}{Colors.ENDC}\n"
    )

    print(f"{Colors.OKGREEN}5. Monitor Your First Build{Colors.ENDC}")
    print(f"   View logs at:")
    print(
        f"   {Colors.OKCYAN}https://console.cloud.google.com/cloud-build/builds?project={PROJECT_ID}{Colors.ENDC}\n"
    )

    print(f"{Colors.BOLD}Important Files:{Colors.ENDC}")
    print(f"  ✓ cloudbuild.yaml - Build configuration (in your repo)")
    print(f"  ✓ cloud_build_integration.py - Backend integration code")
    print(f"  ✓ GCS Bucket: gs://{GCS_BUCKET_NAME}")
    print(f"\n{Colors.BOLD}Need Help?{Colors.ENDC}")
    print(f"  Documentation: https://cloud.google.com/build/docs")
    print(f"  Support: https://cloud.google.com/support")


def main():
    """Main setup flow"""
    print_header("CodeVault - Google Cloud Build Setup")
    print(f"Project: {PROJECT_ID}")
    print(f"Repository: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    print(f"Bucket: {GCS_BUCKET_NAME}\n")

    try:
        # Step 1: Check prerequisites
        if not check_gcloud_installed():
            sys.exit(1)

        if not check_authentication():
            sys.exit(1)

        # Step 2: Set project
        set_project()

        # Step 3: Enable APIs
        enable_apis()

        # Step 4: Create GCS bucket
        create_gcs_bucket()

        # Step 5: Create secrets
        create_secrets()

        # Step 6: Connect GitHub
        connect_github()

        # Step 7: Push cloudbuild.yaml
        push_cloudbuild_yaml()

        # Step 8: Test setup
        test_setup()

        # Print next steps
        print_next_steps()

    except KeyboardInterrupt:
        print_error("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nSetup failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
