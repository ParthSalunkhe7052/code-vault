# Cloud Build

CodeVault Cloud Build enables you to compile your Python and Node.js applications into native executables without installing Nuitka, pkg, or heavy C compilers locally.

## Overview

Cloud Build leverages isolated containerized environments to securely compile your code. It supports multi-platform targets (Windows and Linux) and automatically handles license injection, code obfuscation, and artifact storage. macOS cloud builds are currently unavailable.

### Key Features

- **Zero Setup**: No need to install Python, Node.js, or C compilers locally.
- **Cross-Platform**: Build for Windows and Linux from a single dashboard.
- **Security**: Builds run in isolated ephemeral containers. Source code is encrypted in transit and at rest.
- **Performance**: 
  - **Standard Mode**: Full optimizations + single-file bundling (~20 mins).
  - **Fast Mode**: Directory output for rapid testing (3-4x faster).
- **Integration**: Real-time logs via WebSocket and artifacts stored in Google Cloud Storage (GCS).

## How It Works

1. **Initiation**: You trigger a build via the [Web Dashboard](../frontend) or [CLI](../cli).
2. **Secure Upload**: Your source code is bundled and uploaded to a secure, private bucket.
3. **Queueing**: The build job is prioritized based on your tier and added to the Redis queue.
4. **Compilation**:
   - An isolated runner picks up the job.
   - License checks and obfuscation are applied.
   - Nuitka (Python) or pkg (Node.js) compiles the code.
5. **Delivery**: The final executable is uploaded to secure storage, and you receive a download link.

## Usage

### Web Dashboard

1. Navigate to your **Project Dashboard**.
2. Click **New Build**.
3. Select your **Target Platform** (Windows or Linux).
4. Choose **Build Mode**:
   - *Standard*: For production (protected .exe).
   - *Fast*: For internal testing.
5. Click **Start Build**. You can watch the real-time logs in the console window.

### CLI

You can trigger cloud builds directly from your terminal:

```bash
# Standard cloud build
codevault build --cloud --project-id <id>

# Fast mode (development)
codevault build --cloud --fast --project-id <id>
```

## Tiers & Limits

| Feature | Free Tier | Pro Tier | Business |
|---------|-----------|----------|------------|
| **Builds/Month** | 0 | 25 | 100 |
| **Platforms** | Windows only | Windows, Linux | Windows, Linux |
| **Queue Priority** | Low | Medium | High |

## Technical details

- **Infrastructure**: Google Cloud Build + Docker
- **Storage**: Google Cloud Storage (artifacts) and Cloudflare R2 (source uploads)
- **Queue**: Redis-backed priority queue
- **Encryption**: AES-256 for source bundles
