# Antivirus False Positive Guidance

CodeVault compiles Python applications using Nuitka, which produces native executables. These executables may occasionally trigger antivirus warnings due to the nature of compiled binaries.

## Why This Happens

### 1. Onefile Compression
Nuitka's `--onefile` mode creates self-extracting executables that:
- Extract payload to a temp directory at runtime
- Use heavy compression (similar to malware "packers")
- Trigger heuristic detection in some AV engines

### 2. License Protection Code
CodeVault's license protection includes:
- Network requests to external servers
- Hardware fingerprinting (HWID)
- Background threading (heartbeat)
- Binary integrity verification (if enabled)

These patterns resemble malware behavior and can trigger AV heuristics.

### 3. Unsigned Executables
Windows requires code signing certificates for trusted execution. Without signing:
- SmartScreen shows "Unknown Publisher" warning
- Some AV engines flag unsigned binaries

## Build Mode Recommendations

| Mode | AV Risk | Output | Use Case |
|------|---------|--------|----------|
| **Standalone (Default)** | Low | ZIP with EXE + DLLs folder | Development, testing, distribution |
| **Onefile** | Medium | Single .exe | Convenience distribution |

**For best AV compatibility, use Standalone mode (now the default).**

### Standalone vs Onefile

**Standalone Mode** (Recommended):
- Produces a ZIP containing EXE + all required DLLs
- Much lower AV false positive rate
- No self-extraction at runtime
- Slightly larger download but faster startup

**Onefile Mode**:
- Single self-contained executable
- Higher AV false positive risk due to compression/packing
- Convenient for simple distribution
- Slower first startup (extraction time)

## Console Mode

CodeVault forces console mode by default, which reduces AV false positives. This is because:
- Console apps have more predictable behavior
- GUI-only apps with hidden windows can trigger heuristics

If your application is a GUI app (tkinter, PyQt, etc.), the build system will detect this and disable the console window automatically.

## Security Feature Trade-offs

### Binary Hash Verification

| Setting | Protection | AV Risk |
|---------|------------|---------|
| Disabled (default) | Low | Low |
| Enabled | High | Higher |

Binary hash verification protects against tampering but may trigger AV warnings due to self-integrity checking patterns.

### Obfuscation (Node.js only)

| Setting | Protection | AV Risk |
|---------|------------|---------|
| Disabled | Low | Low |
| Enabled | High | Medium |

Obfuscation adds protection layers but can increase file size and trigger some heuristics.

## Solutions

### For End Users

If Windows Defender or other AV blocks the application:

1. **Windows SmartScreen**
   - Click "More info"
   - Click "Run anyway"

2. **Windows Defender**
   - Open Windows Security
   - Go to Virus & threat protection
   - Click "Protection history"
   - Find the blocked item
   - Click "Actions" → "Allow on device"

3. **Add Exclusion**
   - Open Windows Security
   - Go to Virus & threat protection
   - Click "Manage settings"
   - Scroll to "Exclusions"
   - Add the application folder

### For Developers

1. **Use Standalone Mode** - Now the default, produces ZIP with much lower AV false positives

2. **Disable Binary Hash** - If AV warnings are a major concern for your users

3. **Submit False Positive Reports**
   - Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission
   - VirusTotal: Upload file and use "False Positive" submission

4. **Code Signing** (Recommended for production)
   - Azure Artifact Signing: ~$10/month
   - Provides immediate SmartScreen trust
   - Requires Microsoft identity verification

## Technical Details

### Nuitka Compilation Flags Used

CodeVault uses these flags to minimize false positives:
- `--standalone` - Directory output (default, lower AV risk)
- `--windows-console-mode=force` - Forces console window (lower AV risk)
- `--company-name=CodeVault`
- `--product-name=<app_name>`
- `--file-version=1.0.0.0`
- `--copyright=Copyright 2025 CodeVault`

These add legitimate metadata to the executable.

### Default Configuration

- Build mode: **Standalone** (ZIP with EXE + DLLs)
- Console mode: **Forced** (for CLI tools, auto-detected for GUI)
- Binary hash verification: **OFF** (for AV compatibility)
- Obfuscation: **OFF** (for faster builds)

### Cache Strategy

To speed up builds, CodeVault caches:
- pip packages
- MinGW compiler (for Windows cross-compilation)
- ccache (C compilation cache)

This reduces build times from 8-10 minutes to 3-5 minutes for subsequent builds.

## Future Improvements

When budget allows, implement:
1. Azure Artifact Signing integration (~$10/month)
2. Code signing step in cloud build pipeline
3. EV certificate for immediate SmartScreen trust
