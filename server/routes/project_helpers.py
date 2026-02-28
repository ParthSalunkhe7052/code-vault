"""
Project helper functions for CodeVault API.
Extracted from main.py for modularity.
"""

import json
from pathlib import Path

# Maximum bytes to read from each source file when detecting entry points.
# The patterns we look for (__main__, argparse) always appear near the top or
# bottom of a file — reading 8 KB is more than enough for the vast majority of
# real-world scripts while avoiding loading multi-MB auto-generated files into
# memory on every request.
_ENTRY_SCAN_BYTES = 8 * 1024  # 8 KB

# File extensions recognised as JavaScript/TypeScript sources (lowercased).
_JS_EXTENSIONS = frozenset([".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"])

# File extensions recognised as Python sources (lowercased).
_PYTHON_EXTENSIONS = frozenset([".py", ".pyw"])

# Common configuration and data file extensions to include in the file tree.
_CONFIG_EXTENSIONS = frozenset([
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", 
    ".txt", ".md", ".csv", ".xml", ".sql"
])

# Directories to skip during scanning to improve performance and reduce noise.
_SKIP_DIRS = frozenset([
    "__pycache__", "node_modules", "venv", ".venv", ".git", ".idea", 
    ".vscode", "dist", "build", "target", "env"
])


def _read_partial(path: Path, max_bytes: int = _ENTRY_SCAN_BYTES) -> str:
    """Read at most *max_bytes* from *path*, decoded as UTF-8 (lossy).

    Reading only the head of each file is sufficient for the heuristics used
    in entry-point detection and is significantly faster than loading the
    entire file into memory.
    """
    try:
        with path.open("rb") as fh:
            return fh.read(max_bytes).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def detect_entry_point_smart(base_path: Path, files: list) -> dict:
    """Smart entry point detection with confidence scoring.

    Scores files based on:
    - Has ``if __name__ == "__main__":`` block (+100)
    - Common entry names like main.py, app.py, run.py (+50)
    - Root level file (+25)
    - Uses argparse (+10)

    Optimisations vs. the original implementation:

    * Only the first ``_ENTRY_SCAN_BYTES`` bytes of each file are read instead
      of the full content.  This cuts disk I/O by an order of magnitude for
      large projects.
    * Early exit: as soon as a candidate reaches the maximum possible score
      (185 = 100 + 50 + 25 + 10) scanning stops immediately.
    * Files that can never beat the current best score are skipped.
    """
    candidates = []
    common_names = {"main.py", "app.py", "run.py", "cli.py", "__main__.py", "start.py"}
    best_score = -1

    for file_path in files:
        filename = Path(file_path).name
        is_root = "/" not in file_path and "\\" not in file_path

        # Fast upper-bound estimate before touching the filesystem.
        max_possible = 0
        if filename in common_names:
            max_possible += 50
        if is_root:
            max_possible += 25
        # Content-dependent scores (100 __main__ + 10 argparse = 110)
        max_possible += 110

        # Skip this file entirely if it cannot improve on the best we have.
        if candidates and max_possible <= best_score:
            continue

        full_path = base_path / file_path
        if not full_path.exists():
            continue

        score = 0
        reasons = []

        content = _read_partial(full_path)
        if not content and not filename in common_names and not is_root:
            continue

        if "if __name__" in content and "__main__" in content:
            score += 100
            reasons.append("has __main__ block")

        if filename in common_names:
            score += 50
            reasons.append(f"common entry name '{filename}'")

        if is_root:
            score += 25
            reasons.append("root level file")

        if "import argparse" in content or "from argparse" in content:
            score += 10
            reasons.append("uses argparse")

        if score > 0 or not candidates:
            candidates.append(
                {
                    "file": file_path,
                    "score": score,
                    "reason": ", ".join(reasons) if reasons else "default",
                }
            )
            if score > best_score:
                best_score = score
                # Perfect score — no other file can do better.
                if best_score >= 185:
                    break

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return {"entry_point": None, "confidence": "low", "candidates": []}

    best = candidates[0]

    if best["score"] >= 125:
        confidence = "high"
    elif best["score"] >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "entry_point": best["file"],
        "confidence": confidence,
        "candidates": candidates[:5],
    }


def scan_project_structure(base_path: Path) -> dict:
    """Scan uploaded project and return file tree with dependencies."""
    files = []
    folders = set()
    dependencies = {"python": [], "has_requirements": False}

    allowed_extensions = _PYTHON_EXTENSIONS | _CONFIG_EXTENSIONS

    for item in base_path.rglob("*"):
        # Skip noise directories early.
        if any(skip in item.parts for skip in _SKIP_DIRS):
            continue
            
        if not item.is_file():
            continue
            
        if item.suffix.lower() not in allowed_extensions:
            continue

        relative_path = item.relative_to(base_path)
        file_str = str(relative_path).replace("\\", "/")
        files.append(file_str)

        # Collect all ancestor directories.
        for parent in relative_path.parents:
            parent_str = str(parent).replace("\\", "/")
            if parent_str == ".":
                break
            folders.add(parent_str)

    entry_detection = detect_entry_point_smart(base_path, files)

    req_file = base_path / "requirements.txt"
    if req_file.exists():
        dependencies["has_requirements"] = True
        try:
            dependencies["python"] = [
                line.strip()
                for line in req_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        except Exception as e:
            print(f"Warning: Could not parse requirements.txt: {e}")

    return {
        "files": sorted(files),
        "folders": sorted(list(folders)),
        "entry_point": entry_detection["entry_point"],
        "entry_point_confidence": entry_detection["confidence"],
        "entry_point_candidates": entry_detection["candidates"],
        "total_files": len(files),
        "dependencies": dependencies,
    }


def detect_nodejs_entry_point(base_path: Path, files: list) -> dict:
    """Smart entry point detection for Node.js projects.

    Scores files based on:
    - package.json "main" field (+200)
    - Common entry names like index.js, main.js, app.js (+100)
    - Root level file (+25)

    Optimisations vs. the original implementation:

    * The duplicate-candidate check uses a ``set`` instead of rebuilding a
      list comprehension on every iteration, reducing the inner-loop from
      O(candidates²) to O(1) per lookup.
    """
    candidates = []
    common_names = {"index.js", "main.js", "app.js", "server.js", "start.js", "cli.js"}

    pkg_json = base_path / "package.json"
    if pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
            main_entry = pkg_data.get("main")
            if main_entry and main_entry in files:
                candidates.append(
                    {
                        "file": main_entry,
                        "score": 200,
                        "reason": "package.json main field",
                    }
                )
        except Exception:
            pass

    # Build lookup set once — O(1) per membership test vs. O(n) list rebuild.
    seen_files = {c["file"] for c in candidates}

    for file_path in files:
        if file_path in seen_files:
            continue

        score = 0
        reasons = []

        filename = Path(file_path).name

        if filename in common_names:
            score += 100
            reasons.append(f"common entry name '{filename}'")

        if "/" not in file_path and "\\" not in file_path:
            score += 25
            reasons.append("root level file")

        if score > 0:
            candidates.append(
                {
                    "file": file_path,
                    "score": score,
                    "reason": ", ".join(reasons) if reasons else "default",
                }
            )
            seen_files.add(file_path)

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return {"entry_point": None, "confidence": "low", "candidates": []}

    best = candidates[0]

    if best["score"] >= 150:
        confidence = "high"
    elif best["score"] >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "entry_point": best["file"],
        "confidence": confidence,
        "candidates": candidates[:5],
    }


def scan_nodejs_project_structure(base_path: Path) -> dict:
    """Scan uploaded Node.js project and return file tree with dependencies."""
    files = []
    folders = set()
    dependencies = {"nodejs": [], "has_package_json": False}

    allowed_extensions = _JS_EXTENSIONS | _CONFIG_EXTENSIONS

    for item in base_path.rglob("*"):
        # Skip noise directories early.
        if any(skip in item.parts for skip in _SKIP_DIRS):
            continue
            
        if not item.is_file():
            continue
            
        if item.suffix.lower() not in allowed_extensions:
            continue

        relative_path = item.relative_to(base_path)
        file_str = str(relative_path).replace("\\", "/")
        files.append(file_str)

        for parent in relative_path.parents:
            parent_str = str(parent).replace("\\", "/")
            if parent_str == ".":
                break
            folders.add(parent_str)

    entry_detection = detect_nodejs_entry_point(base_path, files)

    pkg_json = base_path / "package.json"
    if pkg_json.exists():
        dependencies["has_package_json"] = True
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = list(pkg_data.get("dependencies", {}).keys())
            dev_deps = list(pkg_data.get("devDependencies", {}).keys())
            dependencies["nodejs"] = deps + dev_deps
        except Exception as e:
            print(f"Warning: Could not parse package.json: {e}")

    return {
        "files": sorted(files),
        "folders": sorted(list(folders)),
        "entry_point": entry_detection["entry_point"],
        "entry_point_confidence": entry_detection["confidence"],
        "entry_point_candidates": entry_detection["candidates"],
        "total_files": len(files),
        "dependencies": dependencies,
    }
