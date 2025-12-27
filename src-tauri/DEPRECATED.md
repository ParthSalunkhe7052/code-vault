# ⚠️ DEPRECATED: Tauri Desktop App

**Date:** 2024-12-25  
**Status:** DEPRECATED - Not actively maintained

---

## Why?

CodeVault has migrated to a **Web UI + CLI** architecture:

| Component | Purpose | URL/Command |
|:----------|:--------|:------------|
| **Web UI** | Manage projects, licenses, settings | http://localhost:5173 |
| **CLI** | Local compilation with Nuitka/pkg | `codevault-cli build <project-id>` |

This architecture is simpler to deploy, easier to update, and works across platforms without building native binaries.

---

## Should I Delete This Directory?

**Not yet.** The frontend code still references Tauri for certain features:
- Project folder browsing (local file dialogs)
- Direct compilation from desktop
- Prerequisites checking (Nuitka/pkg installation)

These features are now replaced by:
- ✅ Upload ZIP files via web UI
- ✅ Use CLI for local builds: `codevault-cli build <project-id>`
- ✅ CLI `status` command checks prerequisites

---

## Migration Guide

### For Developers
1. Use the web UI at http://localhost:5173
2. Install CLI: `pip install codevault-cli`
3. Login: `codevault-cli login`
4. Build: `codevault-cli build <project-id>`

### For End Users
The web interface provides all functionality:
1. Create/manage projects
2. Upload project ZIP files
3. Configure build settings
4. Copy CLI command to run locally

---

## Files in This Directory

| File | Original Purpose | Replacement |
|:-----|:-----------------|:------------|
| `src/compiler.rs` | Nuitka/pkg compilation | Python CLI `lw_compiler.py` |
| `src/projects.rs` | Local project scanning | ZIP upload via web UI |
| `src/downloader.rs` | File download | Handled by server API |
| `src/settings.rs` | App settings | Web UI Settings page |

---

## When Can This Be Deleted?

When ALL of the following are true:
1. [ ] All frontend `isTauri` conditionals removed
2. [ ] CLI published to PyPI and tested
3. [ ] Documentation updated
4. [ ] No users on desktop app

---

## Questions?

See `docs/MIGRATION_GUIDE.md` for the full transition guide.
