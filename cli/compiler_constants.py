"""
Compiler constants for CodeVault CLI.

This module defines version pins for external tools used during compilation.
Centralizing these makes updates easier and documents the expected versions.
"""

# Node.js packaging tool version
# Used for: Bundling Node.js applications into executables
# Source: https://github.com/vercel/pkg
# Changelog: https://github.com/vercel/pkg/releases
PKG_VERSION = "5.8.1"

# JavaScript obfuscator version
# Used for: Code protection through obfuscation
# Source: https://github.com/javascript-obfuscator/javascript-obfuscator
# Changelog: https://github.com/javascript-obfuscator/javascript-obfuscator/releases
# Note: Version 4.1.0 is used for CLI consistency. Server uses 5.x
JAVASCRIPT_OBFUSCATOR_VERSION = "4.1.0"

# Nuitka minimum version requirement
# Used for: Python to C compilation
NUITKA_MIN_VERSION = "2.0"

# Timeout values (in seconds)
COMPILE_TIMEOUT = 600  # 10 minutes for Nuitka
PKG_TIMEOUT = 300      # 5 minutes for pkg
OBFUSCATE_TIMEOUT = 45 # 45 seconds per file (optimized)

# Parallel processing workers
PARALLEL_WORKERS = 4

# Build attempt limits
MAX_BUILD_ATTEMPTS = 3

# Resource warnings
MEMORY_WARNING_MB = 2048  # Warn if system memory is below this
