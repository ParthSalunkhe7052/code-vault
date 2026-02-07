import os
import json
import secrets
import shutil
import zipfile
from pathlib import Path
from cloud_build_cli_wrapper import CloudBuildClient
from google.cloud import storage


def test_build():
    project_root = Path.cwd()
    test_bot_dir = project_root / "TestBot"
    original_zip = test_bot_dir / "TestBot.zip"

    if not original_zip.exists():
        print(f"Error: {original_zip} not found!")
        return

    # 1. Setup IDs
    build_id = f"test_bld_{secrets.token_hex(4)}"
    gcp_project_id = "cloudbuild-486309"
    temp_dir = project_root / f"temp_build_{build_id}"
    temp_dir.mkdir(exist_ok=True)

    print(f"Starting test build: {build_id}")

    # 2. Extract and Add cloud_runner.py
    with zipfile.ZipFile(original_zip, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Cloud Build expects it at .github/scripts/cloud_runner.py
    script_src = project_root / ".github" / "scripts" / "cloud_runner.py"
    script_dest_dir = temp_dir / ".github" / "scripts"
    script_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(script_src, script_dest_dir / "cloud_runner.py")

    # 3. Re-zip
    new_zip_path = project_root / f"source_{build_id}.zip"
    with zipfile.ZipFile(new_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_new:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_dir)
                zip_new.write(file_path, arcname)

    print(f"Created new source zip: {new_zip_path}")

    # 4. Upload Zip to GCS
    gcs_client = storage.Client()
    bucket = gcs_client.bucket("codevault-builds")

    source_blob_name = f"tests/{build_id}/source.zip"
    blob = bucket.blob(source_blob_name)
    blob.upload_from_filename(str(new_zip_path))

    source_url = f"gs://codevault-builds/{source_blob_name}"
    print(f"Uploaded source to: {source_url}")

    # 5. Create Build Config and UPLOAD it
    config = {
        "project_id": "test_project_id",
        "project_name": "TestBot",
        "language": "python",
        "entry_file": "test_bot_main.py",
        "output_name": "TestBot_Executable",
        "target_platforms": ["windows"],
        "license_key": "PICKLE_TEST_KEY",
        "api_url": "https://localhost:8000/api/v1/license/validate",
        "plan_tier": "pro",
        "compatibility_mode": True,
    }
    config_blob = bucket.blob(f"builds/{build_id}/config.json")
    config_blob.upload_from_string(json.dumps(config), content_type="application/json")
    print(f"Uploaded config to: gs://codevault-builds/builds/{build_id}/config.json")

    # 6. Trigger the Build
    client = CloudBuildClient(project_id=gcp_project_id)
    try:
        # Override the config to use the debug yaml
        # We need to tell gcloud to use the other file
        from subprocess import run

        # Manually construct the gcloud command to use the PRODUCTION config
        cmd = [
            client.gcloud_cmd,
            "builds",
            "submit",
            "--config",
            "cloudbuild.yaml",
            "--no-source",
            "--project",
            gcp_project_id,
            "--substitutions",
            f"_BUILD_ID={build_id},_SOURCE_URL={source_url},_CONFIG_URL=gs://codevault-builds/builds/{build_id}/config.json",
            "--format",
            "json",
            "--async",
        ]

        print(f"Running custom debug command...")
        result_proc = run(cmd, capture_output=True, text=True)
        if result_proc.returncode != 0:
            raise Exception(f"Gcloud failed: {result_proc.stderr}")

        output = json.loads(result_proc.stdout)
        gcp_build_id = output.get("id", "unknown")

        print("\nDebug Build Triggered Successfully!")
        print(f"GCP Build ID: {gcp_build_id}")

        # Save info for monitoring
        with open("last_test_build.json", "w") as f:
            json.dump({"build_id": gcp_build_id}, f, indent=2)

    except Exception as e:
        print(f"\nBuild Trigger Failed: {e}")
    finally:
        # Cleanup temp
        shutil.rmtree(temp_dir)
        if new_zip_path.exists():
            new_zip_path.unlink()


if __name__ == "__main__":
    test_build()
