# Cloud Build

CodeVault Cloud Build enables you to compile your Python and Node.js applications into native executables without installing Nuitka, pkg, or heavy C compilers locally.

## Overview

Cloud Build leverages isolated containerized environments to securely compile your code. It supports multi-platform targets (Windows, Linux, macOS) and automatically handles license injection, code obfuscation, and artifact storage.

### Key Features

- **Zero Setup**: No need to install Python, Node.js, or C compilers locally.
- **Cross-Platform**: Build for Windows, Linux, and macOS from a single dashboard.
- **Security**: Builds run in isolated ephemeral containers. Source code is encrypted in transit and at rest.
- **Performance**: 
  - **Standard Mode**: Full optimizations + single-file bundling (~20 mins).
  - **Fast Mode**: Directory output for rapid testing (3-4x faster).
- **Integration**: Real-time logs via WebSocket and artifacts stored in Cloudflare R2.

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
3. Select your **Target Platform** (Windows, Linux, macOS).
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

| Feature | Free Tier | Pro Tier | Enterprise |
|---------|-----------|----------|------------|
| **Builds/Month** | 5 | 100 | Unlimited |
| **Concurrency** | 1 Job | 3 Concurrent | 10+ Concurrent |
| **Retention** | 7 Days | 30 Days | 90 Days |
| **Platforms** | Windows only | All Platforms | All Platforms |
| **Priority** | Low | High | Dedicated |

## Technical details

- **Infrastructure**: GitHub Actions Runners + Docker
- **Storage**: Cloudflare R2 (Global CDN)
- **Queue**: Redis-backed priority queue
- **Encryption**: AES-256 for source bundles
