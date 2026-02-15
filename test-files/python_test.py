"""
CodeVault Cloud Build Test - Python
A simple test file to verify cloud compilation works correctly.
"""

import sys
import os
import time


def run_tests():
    print("=" * 50)
    print("CodeVault Cloud Build - Python Test Suite")
    print("=" * 50)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Python Version
    print("Test 1: Python Version Check")
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    print(f"  Python version: {py_version}")
    if sys.version_info >= (3, 8):
        print("  Result: PASS (Python 3.8+)")
        tests_passed += 1
    else:
        print("  Result: FAIL (Python too old)")
        tests_failed += 1
    print()

    # Test 2: Platform Detection
    print("Test 2: Platform Detection")
    platform = sys.platform
    print(f"  Platform: {platform}")
    print(f"  OS: {os.name}")
    print("  Result: PASS")
    tests_passed += 1
    print()

    # Test 3: Working Directory
    print("Test 3: Working Directory")
    cwd = os.getcwd()
    print(f"  Current directory: {cwd}")
    print("  Result: PASS")
    tests_passed += 1
    print()

    # Test 4: Basic Math Operations
    print("Test 4: Basic Math Operations")
    result = (10 + 20) * 2 - 5
    expected = 55
    if result == expected:
        print(f"  Calculation: (10 + 20) * 2 - 5 = {result}")
        print("  Result: PASS")
        tests_passed += 1
    else:
        print(f"  Expected {expected}, got {result}")
        print("  Result: FAIL")
        tests_failed += 1
    print()

    # Test 5: String Operations
    print("Test 5: String Operations")
    test_str = "Hello, CodeVault!"
    upper = test_str.upper()
    length = len(test_str)
    if upper == "HELLO, CODEVAULT!" and length == 17:
        print(f"  Original: '{test_str}'")
        print(f"  Upper: '{upper}'")
        print(f"  Length: {length}")
        print("  Result: PASS")
        tests_passed += 1
    else:
        print("  Result: FAIL")
        tests_failed += 1
    print()

    # Test 6: List Operations
    print("Test 6: List Operations")
    numbers = [1, 2, 3, 4, 5]
    doubled = [x * 2 for x in numbers]
    if doubled == [2, 4, 6, 8, 10]:
        print(f"  Input: {numbers}")
        print(f"  Doubled: {doubled}")
        print("  Result: PASS")
        tests_passed += 1
    else:
        print("  Result: FAIL")
        tests_failed += 1
    print()

    # Test 7: Dictionary Operations
    print("Test 7: Dictionary Operations")
    config = {"app_name": "CodeVault", "version": "1.0.0", "debug": False}
    if config["app_name"] == "CodeVault" and "version" in config:
        print(f"  Config: {config}")
        print("  Result: PASS")
        tests_passed += 1
    else:
        print("  Result: FAIL")
        tests_failed += 1
    print()

    # Test 8: File Operations (write/read)
    print("Test 8: File Operations")
    try:
        test_file = "test_output.txt"
        with open(test_file, "w") as f:
            f.write("CodeVault test file\n")
        with open(test_file, "r") as f:
            content = f.read()
        os.remove(test_file)
        if content == "CodeVault test file\n":
            print("  Write/Read/Delete: SUCCESS")
            print("  Result: PASS")
            tests_passed += 1
        else:
            print("  Content mismatch")
            print("  Result: FAIL")
            tests_failed += 1
    except Exception as e:
        print(f"  Error: {e}")
        print("  Result: FAIL")
        tests_failed += 1
    print()

    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"  Tests Passed: {tests_passed}")
    print(f"  Tests Failed: {tests_failed}")
    print(f"  Total Tests: {tests_passed + tests_failed}")
    print()

    if tests_failed == 0:
        print("  Status: ALL TESTS PASSED!")
    else:
        print(f"  Status: {tests_failed} TEST(S) FAILED")

    print("=" * 50)

    # Keep window open for 5 seconds if running as compiled exe
    print("\nClosing in 5 seconds...")
    time.sleep(5)

    return tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
