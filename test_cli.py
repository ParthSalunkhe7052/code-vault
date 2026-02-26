import sys

sys.path.insert(0, ".")

from cli.codevault_cli.simple_build_runner import run_local_build_simple
from pathlib import Path

print("=== CodeVault Build Test ===")
print(f"Python version: {sys.version}")
print()

config = {"fast_build": False, "license_key": "DEMO"}

try:
    print("Creating test file...")
    with open("test_build_test.py", "w", encoding="utf-8") as f:
        f.write('print("Hello from CodeVault!")\n')

    print("Running build...")
    success, path, error = run_local_build_simple(
        Path("test_build_test.py"), config, "Test Build"
    )

    print()
    if success:
        print("✅ Build successful!")
        if path:
            print(f"   Output: {path}")
            try:
                import os

                size = os.path.getsize(path)
                print(f"   Size: {size:,} bytes")
            except Exception:
                pass
    else:
        print(f"❌ Build failed: {error}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    print(traceback.format_exc())
finally:
    try:
        import os

        if os.path.exists("test_build_test.py"):
            os.remove("test_build_test.py")
    except Exception:
        pass
