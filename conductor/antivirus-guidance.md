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
| **Fast Mode** | Low | Directory + launcher script | Development, testing |
| **Standard Mode** | Medium | Single .exe | Distribution |

**For development and testing, use Fast Mode to minimize AV warnings.**

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

1. **Use Fast Mode for testing** - Produces directory output with fewer AV issues

2. **Disable Binary Hash** - If AV warnings are a major concern for your users

3. **Submit False Positive Reports**
   - Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission
   - VirusTotal: Upload file and use "False Positive" submission

4. **Code Signing** (Future)
   - Azure Artifact Signing: $9.99/month
   - Provides immediate SmartScreen trust
   - Requires Microsoft identity verification

## Technical Details

### Nuitka Compilation Flags Used

CodeVault uses these flags to minimize false positives:
- `--company-name=CodeVault`
- `--product-name=<app_name>`
- `--file-version=1.0.0.0`
- `--copyright=Copyright 2025 CodeVault`

These add legitimate metadata to the executable.

### Default Configuration

- Binary hash verification: **OFF** (for AV compatibility)
- Obfuscation: **OFF** (for faster builds)
- Fast mode: **OFF** (produces single .exe by default)

## Future Improvements

When budget allows, implement:
1. Azure Artifact Signing integration ($9.99/month)
2. Code signing step in cloud build pipeline
3. EV certificate for immediate SmartScreen trust
