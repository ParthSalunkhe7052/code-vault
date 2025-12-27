# Implementation Plan: Desktop App → Web + CLI Migration

**Created:** 2024-12-24
**Status:** PENDING APPROVAL
**Estimated Effort:** 4 Phases (~2-3 days total)

---

## Overview

Migrate CodeVault from Tauri Desktop App to a **SaaS Web UI + Local CLI** architecture.

```
BEFORE: User downloads Desktop App → Everything runs locally
AFTER:  User uses Web UI (manage) + CLI (build locally)
```

---

## Phase 1: Backend API Enhancements
**Goal:** Add endpoint for CLI to download build bundles.
**Effort:** ~2 hours

### Checklist

#### 1.1 Create Build Bundle Endpoint
- [ ] Add `GET /api/v1/projects/{project_id}/build-bundle` to `main.py`
- [ ] Endpoint returns ZIP containing:
  - `source/` folder (all project files)
  - `config.json` (entry_file, output_name, license_key, api_url, options)
  - `assets/` folder (icon if provided)
- [ ] Use existing `storage_service.py` to fetch files

#### 1.2 Update Project Config Endpoint
- [ ] Ensure `GET /projects/{id}/config` returns all build settings:
  - `entry_file`, `output_name`, `language`
  - `license_key` (if selected)
  - `api_url` (validation endpoint)
  - `nuitka_options` or `pkg_options`

#### 1.3 Verify ZIP Upload Works
- [ ] Test `POST /projects/{id}/upload-zip` extracts correctly
- [ ] Confirm file tree is stored in database

### Files to Modify
| File | Changes |
|:---|:---|
| `server/main.py` | Add `/build-bundle` endpoint |
| `server/routes/project_routes.py` | (if exists) Add route |

---

## Phase 2: CLI Enhancements
**Goal:** CLI downloads bundle from server instead of using local folder.
**Effort:** ~3 hours

### Checklist

#### 2.1 Add `build` Command (Bundle Mode)
- [ ] Modify `cmd_build()` in `lw_compiler.py`
- [ ] If `project_id` is a name/UUID (not a path), use bundle mode:
  ```python
  def cmd_build(args):
      if is_local_path(args.project_id):
          run_local_build(args)  # Existing logic
      else:
          run_bundle_build(args)  # NEW: Download from server
  ```

#### 2.2 Implement `run_bundle_build()`
- [ ] Call `GET /projects/{id}/build-bundle`
- [ ] Download ZIP to temp folder
- [ ] Extract source files
- [ ] Read `config.json` for settings
- [ ] Inject license wrapper
- [ ] Run Nuitka (Python) or pkg (Node.js)
- [ ] Copy output to `--output` or `./output/`

#### 2.3 Add Progress Output
- [ ] Print clear progress messages:
  ```
  [1/5] Downloading project bundle...
  [2/5] Extracting files...
  [3/5] Injecting license protection...
  [4/5] Compiling with Nuitka... (this may take 2-5 minutes)
  [5/5] Build complete!
  Output: ./output/MyBot.exe
  ```

#### 2.4 Handle Errors
- [ ] If project not found: "Project 'X' not found. Run `codevault-cli projects` to list."
- [ ] If Nuitka not installed: Auto-install or show instructions
- [ ] If Node.js not installed: Show "Install Node.js from nodejs.org"

### Files to Modify
| File | Changes |
|:---|:---|
| `cli/lw_compiler.py` | Add `run_bundle_build()`, modify `cmd_build()` |
| `cli/cli_config.py` | (maybe) Add bundle cache path |

---

## Phase 3: Web UI Updates
**Goal:** Replace "Build Now" with "Get Build Command".
**Effort:** ~2 hours

### Checklist

#### 3.1 Update ProjectWizard Component
- [ ] Find "Start Build" button in `Projects.jsx` or `ProjectWizard.jsx`
- [ ] Replace with "Get Build Command" section:
  ```jsx
  <div className="build-command-section">
    <p>Run this command to build locally:</p>
    <code>codevault-cli build {project.name}</code>
    <button onClick={copyToClipboard}>Copy</button>
  </div>
  ```

#### 3.2 Remove Cloud Compilation References
- [ ] Remove `handleStartCompile()` function (or make it CLI-only)
- [ ] Remove compile status polling (not needed for local builds)
- [ ] Keep the build settings UI (entry file, output name, etc.)

#### 3.3 Add CLI Download Link
- [ ] Add section in Settings or Dashboard:
  ```
  "Don't have the CLI? Download: [Windows] [Mac] [pip install]"
  ```

#### 3.4 Update Build Settings Page
- [ ] Keep all settings (they're saved to server for CLI to fetch)
- [ ] Remove any "cloud build" toggles

### Files to Modify
| File | Changes |
|:---|:---|
| `frontend/src/pages/Projects.jsx` | Replace compile button |
| `frontend/src/components/projects/ProjectWizard.jsx` | Add CLI command display |
| `frontend/src/pages/Settings.jsx` | Add CLI download link |

---

## Phase 4: Cleanup & Documentation
**Goal:** Remove Tauri, update docs, test end-to-end.
**Effort:** ~1 hour

### Checklist

#### 4.1 Deprecate Tauri App
- [ ] Add `DEPRECATED.md` to `src-tauri/` folder
- [ ] Remove `src-tauri/` from active development
- [ ] Update `Run Desktop App.bat` to show deprecation warning

#### 4.2 Update Documentation
- [ ] Update `README.md` with new workflow
- [ ] Update `docs/PROJECT_DOCUMENTATION.md`
- [ ] Add "Migration Guide" for existing Desktop App users

#### 4.3 End-to-End Testing
- [ ] Test Python project: Upload ZIP → Configure → CLI build
- [ ] Test Node.js project: Upload ZIP → Configure → CLI build
- [ ] Test license validation in built executable

#### 4.4 Package CLI for Distribution
- [ ] Create `setup.py` or `pyproject.toml` for CLI
- [ ] Publish to PyPI: `pip install codevault-cli`
- [ ] (Optional) Package as standalone `.exe` using Nuitka

### Files to Modify/Create
| File | Changes |
|:---|:---|
| `src-tauri/DEPRECATED.md` | Create deprecation notice |
| `README.md` | Update installation instructions |
| `cli/setup.py` | Create for PyPI publishing |

---

## Risk Analysis

| Risk | Mitigation |
|:---|:---|
| Users confused by change | Add migration guide + deprecation warnings |
| CLI download friction | Offer `pip install` AND standalone `.exe` |
| Node.js builds fail on some machines | Clear error messages + troubleshooting docs |
| Progress not visible | Clear terminal output with percentages |

---

## Success Criteria

- [ ] User can upload ZIP via Web UI
- [ ] User can configure build settings via Web UI
- [ ] User can copy CLI command from Web UI
- [ ] CLI downloads bundle and builds locally
- [ ] Python projects compile with Nuitka
- [ ] Node.js projects compile with pkg
- [ ] Built executables validate licenses correctly

---

## Execution Order

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
(Backend)  (CLI)    (Web UI)  (Cleanup)
```

**Each phase is independently testable.**
After Phase 2, CLI can build from existing projects.
After Phase 3, the full new workflow is usable.
Phase 4 is cleanup and polish.
