# Test Files for CodeVault Cloud Build

These files are used to test the cloud compilation feature.

## Python Test (`python_test.py`)

Simple Python script that runs 8 tests:
- Python version check
- Platform detection  
- Working directory
- Math operations
- String operations
- List operations
- Dictionary operations
- File operations

Run locally: `python python_test.py`

## Node.js Test (`node_test.js`)

Simple Node.js script that runs 10 tests:
- Node version check
- Platform detection
- Working directory
- Math operations
- String operations
- Array operations
- Object operations
- File operations
- Async/Promise operations
- System memory

Run locally: `node node_test.py`

## Notes

- Both scripts output test results to console
- Scripts pause for 5 seconds before exiting (so you can see results in compiled EXE)
- Return exit code 0 on success, 1 on failure