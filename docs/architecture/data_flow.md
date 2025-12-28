# Data Flow & Architecture

## System Overview

```mermaid
graph TD
    Dev[Developer]
    Client[End User]
    
    subgraph "Local Machine (Developer)"
        CLI[CLI Compiler]
        Source[Source Code]
    end
    
    subgraph "Cloud Infrastructure"
        API[FastAPI Server]
        DB[(PostgreSQL)]
        Redis[(Redis Cache)]
    end
    
    subgraph "Client Machine"
        Exe[Protected .exe]
        Lease[Offline Lease File]
    end

    %% Build Flow
    Dev -->|1. Configure & Build| CLI
    Source -->|Read| CLI
    CLI -->|2. Obfuscate & Inject| CLI
    CLI -->|3. Compile (Nuitka/Pkg)| Exe
    
    %% Validation Flow
    Exe -->|4. Validate License| API
    Exe -->|5. Check Offline Lease| Lease
    
    %% Backend Flow
    API -->|Read/Write| DB
    API -->|Cache| Redis
```

## License Validation Logic

1.  **Initialization**: App starts, generates HWID.
2.  **Offline Check**:
    *   Reads `license.lease` file.
    *   Verifies HMAC signature using embedded secret.
    *   Checks Expiration Date.
    *   Checks HWID match.
    *   **IF VALID**: Application runs immediately.
3.  **Online Check** (if offline check fails or lease expired):
    *   Sends Key + HWID to API.
    *   API verifies against DB.
    *   **IF VALID**:
        *   API returns `success` + new `Offline Lease` (valid for 7 days).
        *   App saves lease to disk.
        *   Application runs.
    *   **IF INVALID**:
        *   App shows Error Dialog / Splash Screen.
        *   App exits.

## Compilation Pipeline

1.  **Analysis**: CLI scans project (Python vs Node.js).
2.  **Preparation**:
    *    Installs dependencies (`pip install` / `npm install`).
    *   Injects `wrapper` code (from `wrappers.py`).
3.  **Obfuscation** (Node.js only):
    *   Runs `javascript-obfuscator` on source files.
4.  **Compilation**:
    *   **Python**: Runs `nuitka` -> C -> Machine Code.
    *   **Node.js**: Runs `pkg` -> Bytecode -> Executable.
5.  **Output**: Generates finalized `.exe` in `output/` folder.
