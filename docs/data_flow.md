# CodeVault Data Flow Analysis

This document outlines the data flow within the CodeVault system, based on the `server/main.py` implementation.

## System Architecture

The system is built on **FastAPI** (Python) using **PostgreSQL** for persistence and a local/cloud file storage abstraction.

```mermaid
graph TD
    User[User / Frontend]
    ClientApp[Compiled Client App]
    API[FastAPI Server]
    DB[(PostgreSQL)]
    Storage[File Storage / Uploads]
    Compiler[Compilation Engine]
    ExtStripe[Stripe]
    ExtEmail[Email Service]
    GeoIP[GeoIP Database]

    %% User Interactions
    User -- HTTPS/JSON --> API
    API -- Read/Write --> DB
    API -- Save/Load Files --> Storage
    
    %% Compilation Flow
    User -- "1. Upload Code" --> API
    User -- "2. Start Compile" --> API
    API -- "3. Dispatch Job" --> Compiler
    Compiler -- Read Source --> Storage
    Compiler -- "4. Inject License Wrapper" --> Compiler
    Compiler -- "5. Build (Nuitka/Pkg)" --> Compiler
    Compiler -- "6. Save Exe" --> Storage
    Compiler -- Update Status --> DB

    %% License Validation Flow
    ClientApp -- "1. Validate License (Key + HWID)" --> API
    API -- Check Status --> DB
    API -- Look up Location --> GeoIP
    API -- "2. Log Attempt" --> DB
    API -- "3. Return Signed Response" --> ClientApp

    %% External Services
    API -- Webhooks/Payments --> ExtStripe
    API -- Send Notifications --> ExtEmail
```

## detailed Flows

### 1. Project Compilation Flow

This process converts user source code into a license-protected executable.

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB
    participant Storage
    participant Worker as Compilation Worker

    User->>API: POST /api/v1/projects/{id}/upload (Source Files)
    API->>Storage: Save files
    API->>DB: Record file metadata
    API-->>User: Upload Success

    User->>API: POST /api/v1/compile/start (Options)
    API->>DB: Create 'compile_job' (pending)
    API->>Worker: Dispatch Background Task
    API-->>User: Job ID

    loop Status Check
        User->>API: GET /api/v1/compile/{job_id}/status
        API->>DB: Fetch progress
        API-->>User: % Complete / Logs
    end

    Note over Worker: Background Processing
    Worker->>DB: Update status 'running'
    Worker->>Storage: Retrieve Source Files
    Worker->>Worker: Install Dependencies (pip/npm)
    Worker->>Worker: **Inject License Wrapper Code**
    Worker->>Worker: Run Compiler (Nuitka/Pkg)
    
    alt Success
        Worker->>Storage: Save .exe to output/
        Worker->>DB: Update status 'completed'
        Worker->>API: Trigger 'compilation.completed' Webhook
    else Failure
        Worker->>DB: Update status 'failed'
        Worker->>API: Trigger 'compilation.failed' Webhook
    end

    User->>API: GET /api/v1/compile/{job_id}/download
    API->>Storage: Stream .exe
    API-->>User: File Download
```

### 2. License Validation Flow

This is the runtime check performed by the compiled application.

```mermaid
sequenceDiagram
    participant App as Client App
    participant API
    participant DB
    participant GeoIP

    Note over App: App Starts (Wrapper Code)
    App->>App: Generate HWID (Hardware ID)
    App->>App: Generate Nonce

    App->>API: POST /api/v1/license/validate
    Note right of App: { key, hwid, nonce, timestamp }

    API->>GeoIP: Lookup Client IP (City/Country)
    API->>DB: Fetch License Details

    alt License Not Found
        API->>DB: Log "invalid" Attempt
        API-->>App: 403 / Invalid Response
        App->>App: Exit / Error
    else License Valid
        API->>DB: Check HWID Binding
        
        alt HWID Mismatch & Max Machines Reached
            API->>DB: Log "hwid_mismatch"
            API-->>App: Error: Max Machines Reached
            App->>App: Exit
        else Binding OK / New Binding
            API->>DB: Update Last Seen / Bind HWID
            API->>DB: Log "valid" Attempt
            API-->>App: Success { signature, features, expires_at }
            App->>App: Verify Signature
            App->>App: **Launch Original Code**
        end
    else License Expired/Revoked
        API->>DB: Log "expired/revoked"
        API-->>App: Error: Expired/Revoked
        App->>App: Exit
    end
```

## Data Models (Simplified)

*   **Users**: `id`, `email`, `password_hash`, `api_key`, `plan`
*   **Projects**: `id`, `user_id`, `name`, `language`, `settings` (JSON)
*   **ProjectFiles**: `id`, `project_id`, `file_path`, `is_cloud`
*   **Licenses**: `id`, `project_id`, `license_key`, `expires_at`, `max_machines`, `features` (JSON)
*   **HardwareBindings**: `id`, `license_id`, `hwid`, `machine_name`
*   **ValidationLogs**: `id`, `license_key`, `ip_address`, `result`, `geo_data`
*   **Webhooks**: `id`, `user_id`, `url`, `events` (JSON)
