"""
Project helper functions for CodeVault API.
Extracted from main.py for modularity.
"""

import json
from pathlib import Path


def detect_entry_point_smart(base_path: Path, files: list) -> dict:
    """
    Smart entry point detection with confidence scoring.
    Scores files based on:
    - Has `if __name__ == "__main__":` block (+100)
    - Common entry names like main.py, app.py, run.py (+50)
    - Root level file (+25)
    """
    candidates = []
    common_names = ["main.py", "app.py", "run.py", "cli.py", "__main__.py", "start.py"]

    for file_path in files:
        full_path = base_path / file_path
        if not full_path.exists():
            continue

        score = 0
        reasons = []

        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")

            if "if __name__" in content and "__main__" in content:
                score += 100
                reasons.append("has __main__ block")

            filename = Path(file_path).name
            if filename in common_names:
                score += 50
                reasons.append(f"common entry name '{filename}'")

            if "/" not in file_path and "\\" not in file_path:
                score += 25
                reasons.append("root level file")

            if "import argparse" in content or "from argparse" in content:
                score += 10
                reasons.append("uses argparse")

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            continue

        if score > 0 or not candidates:
            candidates.append(
                {
                    "file": file_path,
                    "score": score,
                    "reason": ", ".join(reasons) if reasons else "default",
                }
            )

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
    """
    Scan uploaded project and return file tree with dependencies.
    """
    files = []
    folders = set()
    dependencies = {"python": [], "has_requirements": False}

    for py_file in base_path.rglob("*.py"):
        relative_path = py_file.relative_to(base_path)
        files.append(str(relative_path).replace("\\", "/"))

        for parent in relative_path.parents:
            if str(parent) != ".":
                folders.add(str(parent).replace("\\", "/"))

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
    """
    Smart entry point detection for Node.js projects.
    Scores files based on:
    - package.json "main" field (+200)
    - Common entry names like index.js, main.js, app.js (+100)
    - Root level file (+25)
    """
    candidates = []
    common_names = ["index.js", "main.js", "app.js", "server.js", "start.js", "cli.js"]

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

    for file_path in files:
        if file_path in [c["file"] for c in candidates]:
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
    """
    Scan uploaded Node.js project and return file tree with dependencies.
    """
    files = []
    folders = set()
    dependencies = {"nodejs": [], "has_package_json": False}

    js_extensions = ["*.js", "*.mjs", "*.cjs", "*.ts", "*.tsx", "*.jsx"]
    for ext in js_extensions:
        for js_file in base_path.rglob(ext):
            if "node_modules" in str(js_file):
                continue
            relative_path = js_file.relative_to(base_path)
            files.append(str(relative_path).replace("\\", "/"))

            for parent in relative_path.parents:
                if str(parent) != ".":
                    folders.add(str(parent).replace("\\", "/"))

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
