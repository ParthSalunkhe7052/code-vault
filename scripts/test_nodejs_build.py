#!/usr/bin/env python3
"""
CodeVault - Autonomous Node.js Build Tester
Tests the Node.js cloud build pipeline by:
1. Creating a test project via API
2. Uploading test file
3. Starting cloud build
4. Downloading and running the resulting EXE
5. Validating output and fixing issues
"""

import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List


# Colors for terminal
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class NodeJSTester:
    """Autonomous Node.js build tester using CodeVault API"""

    def __init__(self, api_url: str = "https://code-vault-b66848f67c75.herokuapp.com"):
        self.api_url = api_url
        self.test_run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.temp_dir = Path(tempfile.mkdtemp(prefix="nodejs_test_"))
        self.auth_token = None
        self.project_id = None

    def login(self, email: str, password: str) -> bool:
        """Login to get auth token"""
        print(f"{Colors.OKCYAN}[INFO] Logging in as {email}...{Colors.ENDC}")

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/auth/login",
                data={"username": email, "password": password},
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                print(f"{Colors.OKGREEN}[OK] Logged in successfully{Colors.ENDC}")
                return True
            else:
                print(
                    f"{Colors.FAIL}[ERROR] Login failed: {response.text}{Colors.ENDC}"
                )
                return False
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR] Login error: {e}{Colors.ENDC}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def create_test_project(self, name: str) -> Optional[str]:
        """Create a test project"""
        print(f"{Colors.OKCYAN}[INFO] Creating test project: {name}...{Colors.ENDC}")

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/projects",
                headers=self.get_headers(),
                json={
                    "name": name,
                    "description": "Node.js build test",
                    "language": "nodejs",
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                self.project_id = data.get("id")
                print(
                    f"{Colors.OKGREEN}[OK] Project created: {self.project_id}{Colors.ENDC}"
                )
                return self.project_id
            else:
                print(
                    f"{Colors.FAIL}[ERROR] Create project failed: {response.text}{Colors.ENDC}"
                )
                return None
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR] Create project error: {e}{Colors.ENDC}")
            return None

    def upload_test_file(self, test_case: Dict) -> bool:
        """Upload test file to project"""
        print(f"{Colors.OKCYAN}[INFO] Uploading test file...{Colors.ENDC}")

        # Create test file
        test_file = self.temp_dir / test_case["filename"]
        test_file.write_text(test_case["code"], encoding="utf-8")

        try:
            with open(test_file, "rb") as f:
                response = requests.post(
                    f"{self.api_url}/api/v1/projects/{self.project_id}/upload",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    files={"file": (test_case["filename"], f, "text/javascript")},
                )

            if response.status_code in [200, 201]:
                print(
                    f"{Colors.OKGREEN}[OK] File uploaded: {test_case['filename']}{Colors.ENDC}"
                )
                return True
            else:
                print(
                    f"{Colors.FAIL}[ERROR] Upload failed: {response.text}{Colors.ENDC}"
                )
                return False
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR] Upload error: {e}{Colors.ENDC}")
            return False

    def start_build(self, platform: str = "windows") -> Optional[str]:
        """Start cloud build"""
        print(
            f"{Colors.OKCYAN}[INFO] Starting cloud build for {platform}...{Colors.ENDC}"
        )

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/cloud-build/start",
                headers=self.get_headers(),
                json={"project_id": self.project_id, "target_platforms": [platform]},
            )

            if response.status_code in [200, 201]:
                data = response.json()
                build_id = data.get("build_id")
                print(f"{Colors.OKGREEN}[OK] Build started: {build_id}{Colors.ENDC}")
                return build_id
            else:
                print(
                    f"{Colors.FAIL}[ERROR] Start build failed: {response.text}{Colors.ENDC}"
                )
                return None
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR] Start build error: {e}{Colors.ENDC}")
            return None

    def poll_build_status(self, build_id: str, timeout: int = 600) -> Dict[str, Any]:
        """Poll build status until completion"""
        print(
            f"{Colors.OKCYAN}[INFO] Polling build status (timeout: {timeout}s)...{Colors.ENDC}"
        )

        start_time = time.time()
        poll_interval = 10

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.api_url}/api/v1/cloud-build/{build_id}/status",
                    headers=self.get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    progress = data.get("progress", 0)
                    elapsed = int(time.time() - start_time)

                    print(f"  [{elapsed}s] Status: {status} ({progress}%)")

                    if status in ["completed", "failed", "cancelled"]:
                        return data
                else:
                    # Try GCP sync endpoint
                    response = requests.get(
                        f"{self.api_url}/api/v1/cloud-build/{build_id}/gcp-sync",
                        headers=self.get_headers(),
                    )
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status", "unknown")
                        elapsed = int(time.time() - start_time)
                        print(f"  [{elapsed}s] GCP Sync Status: {status}")

                        if status in ["completed", "failed", "cancelled"]:
                            return data

                time.sleep(poll_interval)

            except Exception as e:
                print(f"{Colors.WARNING}[WARN] Poll error: {e}{Colors.ENDC}")
                time.sleep(5)

        return {"status": "timeout"}

    def download_artifact(self, build_id: str) -> Optional[Path]:
        """Download the built EXE"""
        print(f"{Colors.OKCYAN}[INFO] Downloading artifact...{Colors.ENDC}")

        try:
            response = requests.get(
                f"{self.api_url}/api/v1/cloud-build/{build_id}/download",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                download_url = data.get("download_url") or data.get("url")

                if download_url:
                    # Download the file
                    exe_response = requests.get(download_url)
                    if exe_response.status_code == 200:
                        exe_path = self.temp_dir / f"test_{build_id}.exe"
                        exe_path.write_bytes(exe_response.content)
                        print(
                            f"{Colors.OKGREEN}[OK] Downloaded: {exe_path} ({exe_path.stat().st_size} bytes){Colors.ENDC}"
                        )
                        return exe_path
                    else:
                        print(
                            f"{Colors.FAIL}[ERROR] Download from URL failed: {exe_response.status_code}{Colors.ENDC}"
                        )
                else:
                    print(
                        f"{Colors.FAIL}[ERROR] No download URL in response{Colors.ENDC}"
                    )
            else:
                print(
                    f"{Colors.FAIL}[ERROR] Download request failed: {response.text}{Colors.ENDC}"
                )

        except Exception as e:
            print(f"{Colors.FAIL}[ERROR] Download error: {e}{Colors.ENDC}")

        return None

    def run_exe(self, exe_path: Path, timeout: int = 30) -> Tuple[int, str, str]:
        """Run the EXE and capture output"""
        print(f"{Colors.OKCYAN}[INFO] Running EXE: {exe_path}{Colors.ENDC}")

        try:
            result = subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(exe_path.parent),
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return -1, "", "Process timed out"
        except Exception as e:
            return -1, "", str(e)

    def validate_output(
        self, test_case: Dict, stdout: str, stderr: str, returncode: int
    ) -> bool:
        """Validate the test output"""
        print(f"\n{Colors.HEADER}=== OUTPUT ==={Colors.ENDC}")

        if stdout:
            print(f"{Colors.OKBLUE}{stdout}{Colors.ENDC}")
        if stderr:
            print(f"{Colors.WARNING}{stderr}{Colors.ENDC}")

        print(f"\n{Colors.HEADER}=== VALIDATION ==={Colors.ENDC}")

        expected = test_case.get("expected_output", [])
        all_found = True

        for exp in expected:
            if exp in stdout:
                print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Found: '{exp}'")
            else:
                print(f"  {Colors.FAIL}✗{Colors.ENDC} Missing: '{exp}'")
                all_found = False

        if returncode == 0:
            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Exit code: 0")
        else:
            print(f"  {Colors.FAIL}✗{Colors.ENDC} Exit code: {returncode}")
            all_found = False

        return all_found

    def get_test_cases(self) -> Dict[str, Dict]:
        """Define test cases"""
        return {
            "simple_console": {
                "name": "Simple Console Output",
                "filename": "index.js",
                "code": """// Simple console test
console.log("Hello from CodeVault!");
console.log("Test PASSED");
process.exit(0);
""",
                "expected_output": ["Hello from CodeVault!", "Test PASSED"],
                "timeout": 10,
            },
            "fs_operations": {
                "name": "File System Operations",
                "filename": "index.js",
                "code": """// File system test
const fs = require('fs');
const path = require('path');
const os = require('os');

const testFile = path.join(os.tmpdir(), 'codevault_test.txt');

fs.writeFileSync(testFile, 'CodeVault FS Test');
console.log('Write: OK');

const content = fs.readFileSync(testFile, 'utf8');
console.log('Read:', content);

fs.unlinkSync(testFile);
console.log('Delete: OK');

console.log('FS Test PASSED');
process.exit(0);
""",
                "expected_output": [
                    "Write: OK",
                    "Read: CodeVault FS Test",
                    "Delete: OK",
                    "FS Test PASSED",
                ],
                "timeout": 15,
            },
            "modules_test": {
                "name": "Built-in Modules",
                "filename": "index.js",
                "code": """// Modules test
const os = require('os');
const path = require('path');
const crypto = require('crypto');

console.log('Platform:', os.platform());
console.log('Arch:', os.arch());
console.log('Path join:', path.join('a', 'b', 'c'));

const hash = crypto.createHash('sha256').update('test').digest('hex');
console.log('Hash:', hash.substring(0, 8) + '...');

console.log('Modules Test PASSED');
process.exit(0);
""",
                "expected_output": [
                    "Platform:",
                    "Arch:",
                    "Path join:",
                    "Hash:",
                    "Modules Test PASSED",
                ],
                "timeout": 15,
            },
            "async_code": {
                "name": "Async/Await Operations",
                "filename": "index.js",
                "code": """// Async test
const fs = require('fs').promises;
const path = require('path');
const os = require('os');

async function runAsyncTests() {
    console.log('Starting async tests...');
    
    await new Promise(r => setTimeout(r, 100));
    console.log('Timeout: OK');
    
    const testFile = path.join(os.tmpdir(), 'async_test.txt');
    await fs.writeFile(testFile, 'async content');
    const content = await fs.readFile(testFile, 'utf8');
    console.log('Async read:', content);
    await fs.unlink(testFile);
    
    const results = await Promise.all([
        Promise.resolve(1),
        Promise.resolve(2),
        Promise.resolve(3)
    ]);
    console.log('Promise.all:', results.join(','));
    
    console.log('Async Test PASSED');
    process.exit(0);
}

runAsyncTests().catch(err => {
    console.error('Async error:', err);
    process.exit(1);
});
""",
                "expected_output": [
                    "Starting async tests...",
                    "Timeout: OK",
                    "Async read: async content",
                    "Promise.all:",
                    "Async Test PASSED",
                ],
                "timeout": 20,
            },
        }

    def run_test(self, test_key: str) -> Dict[str, Any]:
        """Run a single test case"""
        test_cases = self.get_test_cases()

        if test_key not in test_cases:
            print(f"{Colors.FAIL}[ERROR] Unknown test: {test_key}{Colors.ENDC}")
            return {"success": False, "error": f"Unknown test: {test_key}"}

        test_case = test_cases[test_key]
        result = {
            "test": test_key,
            "name": test_case["name"],
            "success": False,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "error": None,
        }

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}TEST: {test_case['name']}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

        try:
            # Step 1: Create project
            print(f"\n{Colors.BOLD}Step 1: Creating test project{Colors.ENDC}")
            project_name = f"NodeJSTest_{self.test_run_id}"
            if not self.create_test_project(project_name):
                result["error"] = "Failed to create project"
                return result

            # Step 2: Upload test file
            print(f"\n{Colors.BOLD}Step 2: Uploading test file{Colors.ENDC}")
            if not self.upload_test_file(test_case):
                result["error"] = "Failed to upload file"
                return result

            # Step 3: Start build
            print(f"\n{Colors.BOLD}Step 3: Starting cloud build{Colors.ENDC}")
            build_id = self.start_build()
            if not build_id:
                result["error"] = "Failed to start build"
                return result

            # Step 4: Poll status
            print(f"\n{Colors.BOLD}Step 4: Waiting for build{Colors.ENDC}")
            build_result = self.poll_build_status(build_id)

            if build_result.get("status") != "completed":
                result["error"] = (
                    f"Build failed with status: {build_result.get('status')}"
                )
                result["build_result"] = build_result
                print(
                    f"{Colors.FAIL}[FAIL] Build status: {build_result.get('status')}{Colors.ENDC}"
                )
                return result

            # Step 5: Download artifact
            print(f"\n{Colors.BOLD}Step 5: Downloading artifact{Colors.ENDC}")
            exe_path = self.download_artifact(build_id)

            if not exe_path:
                result["error"] = "Failed to download artifact"
                return result

            # Step 6: Run EXE
            print(f"\n{Colors.BOLD}Step 6: Running EXE{Colors.ENDC}")
            returncode, stdout, stderr = self.run_exe(
                exe_path, test_case.get("timeout", 30)
            )

            # Step 7: Validate
            print(f"\n{Colors.BOLD}Step 7: Validating output{Colors.ENDC}")
            result["success"] = self.validate_output(
                test_case, stdout, stderr, returncode
            )

            result["returncode"] = returncode
            result["stdout"] = stdout[:500] if len(stdout) > 500 else stdout
            result["stderr"] = stderr[:500] if len(stderr) > 500 else stderr

        except Exception as e:
            result["error"] = str(e)
            print(f"{Colors.FAIL}[ERROR] {e}{Colors.ENDC}")

        finally:
            result["end_time"] = datetime.now().isoformat()

        return result

    def run_all_tests(self) -> List[Dict]:
        """Run all test cases"""
        test_cases = self.get_test_cases()
        results = []

        print(f"\n{Colors.HEADER}{'#' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}#  CODEVAULT NODE.JS BUILD TEST SUITE{Colors.ENDC}")
        print(f"{Colors.HEADER}#  Run ID: {self.test_run_id}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'#' * 60}{Colors.ENDC}")

        for test_key in test_cases:
            result = self.run_test(test_key)
            results.append(result)

            if result["success"]:
                print(f"\n{Colors.OKGREEN}{'=' * 60}{Colors.ENDC}")
                print(f"{Colors.OKGREEN}TEST PASSED: {result['name']}{Colors.ENDC}")
                print(f"{Colors.OKGREEN}{'=' * 60}{Colors.ENDC}")
            else:
                print(f"\n{Colors.FAIL}{'=' * 60}{Colors.ENDC}")
                print(f"{Colors.FAIL}TEST FAILED: {result['name']}{Colors.ENDC}")
                if result.get("error"):
                    print(f"{Colors.FAIL}Error: {result['error']}{Colors.ENDC}")
                print(f"{Colors.FAIL}{'=' * 60}{Colors.ENDC}")
                break

        # Summary
        self.print_summary(results)

        return results

    def print_summary(self, results: List[Dict]):
        """Print test summary"""
        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}TEST SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

        passed = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])
        total = len(results)

        for r in results:
            status = (
                f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}"
                if r["success"]
                else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
            )
            print(f"  {status} - {r['name']}")
            if r.get("error") and not r["success"]:
                print(f"         {Colors.FAIL}{r['error'][:60]}{Colors.ENDC}")

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(
            f"  Total: {total} | Passed: {Colors.OKGREEN}{passed}{Colors.ENDC} | Failed: {Colors.FAIL}{failed}{Colors.ENDC}"
        )
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description="CodeVault Node.js Build Tester")
    parser.add_argument(
        "--api", default="https://code-vault-b66848f67c75.herokuapp.com", help="API URL"
    )
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--test", help="Run specific test")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    # Create tester
    tester = NodeJSTester(api_url=args.api)

    # Login
    if not tester.login(args.email, args.password):
        print(f"{Colors.FAIL}[FATAL] Login failed{Colors.ENDC}")
        sys.exit(1)

    try:
        if args.test:
            result = tester.run_test(args.test)
            sys.exit(0 if result["success"] else 1)
        else:
            results = tester.run_all_tests()
            sys.exit(0 if all(r["success"] for r in results) else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
