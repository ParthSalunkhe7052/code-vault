"""
File browser and selection utilities for CodeVault CLI.

Provides both CLI prompts and GUI file dialogs for selecting source files/folders.
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, List
from codevault_cli.console import get_console, print_error

console = get_console()


def browse_for_file(
    title: str = "Select Project File",
    file_types: Optional[list] = None,
    initial_dir: Optional[str] = None,
) -> Optional[Path]:
    """
    Open a file browser dialog to select a file.

    Args:
        title: Dialog window title
        file_types: List of (description, pattern) tuples, e.g., [("Zip files", "*.zip"), ("All files", "*.*")]
        initial_dir: Starting directory for the dialog

    Returns:
        Selected file path or None if cancelled
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        # Set default file types if not provided
        if file_types is None:
            file_types = [
                ("Zip files", "*.zip"),
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("All files", "*.*"),
            ]

        # Open file dialog
        file_path = filedialog.askopenfilename(
            title=title,
            initialdir=initial_dir or str(Path.home()),
            filetypes=file_types,
        )

        root.destroy()

        if file_path:
            return Path(file_path)
        return None

    except ImportError:
        print_error("Tkinter not available. Please enter path manually.")
        return None
    except Exception as e:
        print_error(f"File dialog error: {e}")
        return None


def browse_for_folder(
    title: str = "Select Project Folder", initial_dir: Optional[str] = None
) -> Optional[Path]:
    """
    Open a folder browser dialog to select a directory.

    Args:
        title: Dialog window title
        initial_dir: Starting directory for the dialog

    Returns:
        Selected folder path or None if cancelled
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        # Open folder dialog
        folder_path = filedialog.askdirectory(
            title=title, initialdir=initial_dir or str(Path.home())
        )

        root.destroy()

        if folder_path:
            return Path(folder_path)
        return None

    except ImportError:
        print_error("Tkinter not available. Please enter path manually.")
        return None
    except Exception as e:
        print_error(f"Folder dialog error: {e}")
        return None


def prompt_for_source(
    project_name: str = "project",
    server_files_info: Optional[Dict] = None,
    recent_paths: Optional[List[Path]] = None,
) -> Optional[Path]:
    """
    Interactive prompt to select source files for building.

    Phase 3: Explicit user choice with file counts and sizes

    Args:
        project_name: Name of the project (for display)
        server_files_info: Info about server files (files_count, size, upload_date)
        recent_paths: List of recently used source paths

    Returns:
        Path to source (zip file or folder) or None if cancelled
    """
    console.print(f"\n[bold cyan]Source Selection for '{project_name}'[/bold cyan]")
    console.print("=" * 60)
    console.print()
    console.print("How do you want to provide source files?")
    console.print()

    # Option 1: Server files (if available)
    if server_files_info:
        file_count = server_files_info.get("file_count", 0)
        size_mb = server_files_info.get("size_mb", 0)
        upload_date = server_files_info.get("upload_date", "Unknown")
        console.print(f"  [1] Use latest files from server (uploaded: {upload_date})")
        console.print(f"      Status: {file_count} files, {size_mb:.1f} MB")
        console.print()

    # Option 2: Local ZIP
    console.print("  [2] Select local ZIP file")
    console.print("      Browse for .zip file on your computer")
    console.print()

    # Option 3: Local folder
    console.print("  [3] Select local project folder")
    console.print("      Browse for project folder on your computer")
    console.print()

    # Option 4: Manual path
    console.print("  [4] Type path manually")
    console.print("      Enter full path to ZIP or folder")
    console.print()

    # Recent files (Phase 6)
    if recent_paths:
        console.print("  [5] Use recent location")
        for i, path in enumerate(recent_paths[:3], 1):
            console.print(f"      [{i}] {path}")
        console.print()

    # Cancel option
    console.print("  [0] Cancel build")
    console.print()

    while True:
        try:
            max_choice = 5 if recent_paths else 4
            if server_files_info:
                choice = console.input(f"Enter your choice (0-{max_choice}): ").strip()
            else:
                choice = console.input(
                    f"Enter your choice (0-{max_choice}, skip 1): "
                ).strip()

            if choice == "1" and server_files_info:
                # Return special marker for server files
                return Path("__SERVER_FILES__")

            elif choice == "2":
                # Browse for zip file with Phase 6 improvements
                console.print("\n[dim]Opening file browser...[/dim]")
                initial_dir = _get_suggested_directory("downloads")
                selected = browse_for_file(
                    title=f"Select {project_name} ZIP File",
                    file_types=[("Zip files", "*.zip"), ("All files", "*.*")],
                    initial_dir=str(initial_dir) if initial_dir else None,
                )
                if selected:
                    # Validate ZIP (Phase 6)
                    if _validate_zip_file(selected):
                        file_count = _count_zip_files(selected)
                        console.print(f"[OK] Selected: {selected}")
                        console.print(f"[OK] Contains {file_count} files")
                        return selected
                    else:
                        print_error(f"Invalid or corrupted ZIP file: {selected}")
                else:
                    console.print("[yellow]No file selected.[/yellow]")

            elif choice == "3":
                # Browse for folder with Phase 6 improvements
                console.print("\n[dim]Opening folder browser...[/dim]")
                initial_dir = _get_suggested_directory("documents")
                selected = browse_for_folder(
                    title=f"Select {project_name} Folder",
                    initial_dir=str(initial_dir) if initial_dir else None,
                )
                if selected:
                    # Count files (Phase 6)
                    file_count = _count_directory_files(selected)
                    console.print(f"[OK] Selected: {selected}")
                    console.print(f"[OK] Contains {file_count} files")
                    return selected
                else:
                    console.print("[yellow]No folder selected.[/yellow]")

            elif choice == "4":
                # Manual entry
                console.print()
                path_str = console.input("Enter the full path: ").strip()
                if path_str:
                    path = Path(path_str)
                    if path.exists():
                        console.print(f"[OK] Path found: {path}")
                        return path
                    else:
                        print_error(f"Path not found: {path}")
                        if confirm_action("Try again?"):
                            continue
                        return None
                else:
                    print_error("No path entered.")

            elif choice == "5" and recent_paths:
                # Recent location submenu
                console.print("\nSelect recent location:")
                for i, path in enumerate(recent_paths[:3], 1):
                    console.print(f"  [{i}] {path}")
                subchoice = console.input("Enter number: ").strip()
                try:
                    idx = int(subchoice) - 1
                    if 0 <= idx < len(recent_paths):
                        selected = recent_paths[idx]
                        if selected.exists():
                            console.print(f"[OK] Using: {selected}")
                            return selected
                        else:
                            print_error(f"Path no longer exists: {selected}")
                    else:
                        print_error("Invalid selection")
                except ValueError:
                    print_error("Invalid input")

            elif choice == "0":
                console.print("\n[yellow]Build cancelled.[/yellow]")
                return None

            else:
                print_error(f"Invalid choice. Please enter 0-{max_choice}.")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Cancelled.[/yellow]")
            return None


def _get_suggested_directory(location_type: str) -> Optional[Path]:
    """Get suggested starting directory for file browser. Phase 6."""
    home = Path.home()
    suggestions = {
        "downloads": home / "Downloads",
        "desktop": home / "Desktop",
        "documents": home / "Documents",
    }
    path = suggestions.get(location_type, home)
    return path if path.exists() else home


def _validate_zip_file(zip_path: Path) -> bool:
    """Validate that a ZIP file is not corrupted. Phase 6."""
    import zipfile

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Try to read the file list
            zf.namelist()
        return True
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


def _count_zip_files(zip_path: Path) -> int:
    """Count files in a ZIP archive."""
    import zipfile

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return len([name for name in zf.namelist() if not name.endswith("/")])
    except Exception:
        return 0


def _count_directory_files(dir_path: Path) -> int:
    """Count files in a directory (excluding common ignored dirs)."""
    ignored = {"__pycache__", "node_modules", ".git", ".env", "dist", "build", "output"}
    count = 0
    try:
        for item in dir_path.rglob("*"):
            if item.is_file() and not any(ig in str(item) for ig in ignored):
                count += 1
    except Exception:
        pass
    return count


def confirm_action(message: str, default: bool = True) -> bool:
    """Simple confirmation prompt."""
    from codevault_cli.interactive import confirm_action as interactive_confirm

    try:
        return interactive_confirm(message, default)
    except:
        # Fallback to simple input
        default_str = "Y/n" if default else "y/N"
        response = console.input(f"{message} ({default_str}): ").strip().lower()
        if not response:
            return default
        return response in ["y", "yes"]


def check_and_use_local_path(
    local_path: str, project_name: str = "project"
) -> Optional[Path]:
    """
    Check if local path exists and ask user if they want to use it.

    Args:
        local_path: The local path from project data
        project_name: Name of the project

    Returns:
        Path if user wants to use it, None otherwise
    """
    if not local_path:
        return None

    path = Path(local_path)
    if not path.exists():
        return None

    console.print("\n[OK] Found local project files:")
    console.print(f"   Location: {path}")
    console.print()

    if confirm_action(f"Use these local files for '{project_name}'?", default=True):
        return path

    return None


def extract_or_use_source(
    source_path: Path, temp_dir: Path
) -> Tuple[Optional[Path], str]:
    """
    Extract zip file or return folder path.

    Args:
        source_path: Path to zip file or folder
        temp_dir: Temporary directory for extraction

    Returns:
        Tuple of (project_dir, error_message)
    """
    import zipfile
    import shutil

    try:
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            # Extract zip file
            console.print(f"[INFO] Extracting ZIP file: {source_path.name}")
            extract_dir = temp_dir / "project"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(source_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            console.print(f"[OK] Extracted to: {extract_dir}")
            return extract_dir, ""

        elif source_path.is_dir():
            # Copy folder to temp location
            console.print("[INFO] Copying project folder...")
            dest_dir = temp_dir / "project"

            def ignore_patterns(path, names):
                return {
                    "__pycache__",
                    "node_modules",
                    ".git",
                    ".env",
                    "dist",
                    "build",
                    "output",
                }

            shutil.copytree(source_path, dest_dir, ignore=ignore_patterns)
            console.print(f"[OK] Copied to: {dest_dir}")
            return dest_dir, ""
        else:
            return (
                None,
                f"Invalid source: {source_path} (must be a .zip file or folder)",
            )

    except zipfile.BadZipFile:
        return None, f"Invalid ZIP file: {source_path}"
    except Exception as e:
        return None, f"Error processing source: {e}"
