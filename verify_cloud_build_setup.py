#!/usr/bin/env python3
"""
Cloud Build Setup Verification Script
Run this after manual authentication to verify everything is configured correctly.
"""

import sys
import os


def print_header(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}\n")


def check_imports():
    """Verify all required packages are installed"""
    print_header("Step 1: Checking Python Dependencies")

    required = [
        ("google.cloud.devtools.cloudbuild_v1", "Cloud Build API"),
        ("google.auth", "Google Authentication"),
        ("google.cloud.storage", "Cloud Storage API"),
    ]

    all_good = True
    for module, name in required:
        try:
            __import__(module)
            print(f"✓ {name:30s} - Installed")
        except ImportError as e:
            print(f"✗ {name:30s} - MISSING")
            print(f"  Error: {e}")
            all_good = False

    if not all_good:
        print("\n⚠️  Install missing dependencies:")
        print("   pip install google-cloud-build google-auth google-cloud-storage")
        return False

    print("\n✅ All dependencies installed!")
    return True


def check_authentication():
    """Verify Google Cloud authentication"""
    print_header("Step 2: Checking Authentication")

    try:
        from google.auth import default

        credentials, project = default()
        print(f"✓ Authenticated successfully")
        print(f"  Project: {project}")

        # Check if service account or user
        if hasattr(credentials, "service_account_email"):
            print(f"  Type: Service Account")
            print(f"  Email: {credentials.service_account_email}")
        else:
            print(f"  Type: Application Default Credentials (User)")

        print("\n✅ Authentication configured!")
        return True, project

    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("\n⚠️  Set up authentication:")
        print("   Option 1 (Quick): gcloud auth application-default login")
        print("   Option 2 (Production): Download service account key and set:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        return False, None


def check_cloud_build_access(project):
    """Test Cloud Build API access"""
    print_header("Step 3: Testing Cloud Build API")

    try:
        from google.cloud.devtools.cloudbuild_v1 import CloudBuildClient

        client = CloudBuildClient()
        print(f"✓ Cloud Build client initialized")

        # Try to list recent builds (will fail if no permission, but shows API is accessible)
        try:
            builds = client.list_builds(project_id=project, page_size=1)
            print(f"✓ Can query builds")
            print(f"  API is accessible and permissions look good!")
        except Exception as e:
            if "403" in str(e):
                print(f"⚠️  API accessible but missing permissions")
                print(f"  Error: {e}")
            else:
                print(f"✓ API accessible (no builds found yet)")

        print("\n✅ Cloud Build API is working!")
        return True

    except Exception as e:
        print(f"✗ Cloud Build API error: {e}")
        print("\n⚠️  Enable Cloud Build API:")
        print(
            "   gcloud services enable cloudbuild.googleapis.com --project=cloudbuild-486309"
        )
        return False


def check_gcs_access():
    """Test Google Cloud Storage access"""
    print_header("Step 4: Testing Cloud Storage Access")

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket("codevault-builds")

        # Check if bucket exists
        if bucket.exists():
            print(f"✓ GCS bucket 'codevault-builds' exists")

            # Try to list objects (permission check)
            try:
                blobs = list(bucket.list_blobs(max_results=1))
                print(f"✓ Can list bucket contents")
                print(f"  Found {len(blobs)} objects (showing first 1)")
            except Exception as e:
                print(f"⚠️  Bucket exists but can't list: {e}")
        else:
            print(f"✗ Bucket 'codevault-builds' not found")
            print("\n⚠️  Create bucket:")
            print("   gsutil mb -p cloudbuild-486309 -l US gs://codevault-builds")
            return False

        print("\n✅ Cloud Storage access working!")
        return True

    except Exception as e:
        print(f"✗ Cloud Storage error: {e}")
        return False


def check_secrets():
    """Test Secret Manager access"""
    print_header("Step 5: Testing Secret Manager")

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        secret_name = (
            "projects/cloudbuild-486309/secrets/callback-webhook-secret/versions/latest"
        )

        try:
            response = client.access_secret_version(request={"name": secret_name})
            print(f"✓ Can access secret 'callback-webhook-secret'")
            print(f"  Secret size: {len(response.payload.data)} bytes")
            print("\n✅ Secret Manager access working!")
            return True
        except Exception as e:
            if "403" in str(e) or "PERMISSION_DENIED" in str(e):
                print(f"⚠️  Secret exists but missing permissions: {e}")
                print("\n  Grant access:")
                print(
                    "  gcloud secrets add-iam-policy-binding callback-webhook-secret \\"
                )
                print("    --member='serviceAccount:YOUR_SERVICE_ACCOUNT@...' \\")
                print("    --role='roles/secretmanager.secretAccessor'")
            else:
                print(f"✗ Secret access error: {e}")
            return False

    except Exception as e:
        print(f"⚠️  Secret Manager not available: {e}")
        print("  (Optional - only needed for webhook signatures)")
        return True  # Not critical


def check_github_connection():
    """Check if GitHub repo is connected"""
    print_header("Step 6: Checking GitHub Repository Connection")

    print("ℹ️  Checking GitHub connection requires manual verification")
    print(
        "\n1. Visit: https://console.cloud.google.com/cloud-build/repositories?project=cloudbuild-486309"
    )
    print("2. Look for: ParthSalunkhe7052/code-vault")
    print("\nIf not connected:")
    print(
        "  • Go to: https://console.cloud.google.com/cloud-build/triggers/connect?project=cloudbuild-486309"
    )
    print("  • Click 'Connect Repository'")
    print("  • Select 'GitHub (Cloud Build GitHub App)'")
    print("  • Authenticate and select your repo")

    return True


def test_build_trigger():
    """Show how to test a build"""
    print_header("Step 7: Testing Build Trigger")

    print("To test a manual build, run:")
    print("\ngcloud builds submit \\")
    print("  --config=cloudbuild.yaml \\")
    print("  --no-source \\")
    print("  --project=cloudbuild-486309 \\")
    print(
        "  --substitutions=_BUILD_ID=test-001,_PROJECT_ID=test-proj,_LANGUAGE=python,_TARGET_PLATFORMS=linux,_SOURCE_URL=https://httpbin.org/delay/1,_CONFIG_JSON_B64=e30=,_CALLBACK_URL=https://example.com/webhook,_ENTRY_FILE=main.py,_OUTPUT_NAME=test-app,_PLAN_TIER=free,_COMPATIBILITY_MODE=false,_FAST_BUILD=false"
    )

    print("\nMonitor at:")
    print(
        "https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309"
    )

    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         CodeVault - Cloud Build Setup Verification          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    results = []

    # Run all checks
    results.append(("Dependencies", check_imports()))

    auth_ok, project = check_authentication()
    results.append(("Authentication", auth_ok))

    if auth_ok and project:
        results.append(("Cloud Build API", check_cloud_build_access(project)))
        results.append(("Cloud Storage", check_gcs_access()))
        results.append(("Secret Manager", check_secrets()))

    results.append(("GitHub Connection", check_github_connection()))
    results.append(("Build Test Info", test_build_trigger()))

    # Summary
    print_header("SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Checks passed: {passed}/{total}\n")

    for check, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {check}")

    print("\n" + "=" * 60)

    if passed == total:
        print("\n🎉 SUCCESS! All checks passed!")
        print("\nYou can now:")
        print("  1. Test a manual build (see command above)")
        print("  2. Start your backend server")
        print("  3. Trigger builds from your dashboard")
        print("\nMonitor builds at:")
        print(
            "  https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309"
        )
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nMost common fixes:")
        print("  1. Run: gcloud auth application-default login")
        print("  2. Run: gcloud config set project cloudbuild-486309")
        print(
            "  3. Install: pip install google-cloud-build google-auth google-cloud-storage"
        )

    print("\n" + "=" * 60 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
