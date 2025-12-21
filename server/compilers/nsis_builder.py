"""
NSIS Builder Module for CodeVault
Creates professional Windows installers for Python and Node.js applications
"""

import os
import shutil
import subprocess
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

# Default NSIS installation paths (Windows)
NSIS_PATHS = [
    r"C:\Program Files (x86)\NSIS\makensis.exe",
    r"C:\Program Files\NSIS\makensis.exe",
]


class NSISBuilder:
    """
    Generates professional Windows installers using NSIS (Nullsoft Scriptable Install System)
    
    Supports:
    - Python applications (compiled with Nuitka/PyInstaller)
    - Node.js applications (compiled with yao-pkg)
    - GUI license activation dialogs
    - Desktop/Start Menu shortcuts
    - Uninstaller generation
    - Registry entries for Add/Remove Programs
    """
    
    def __init__(self):
        self.nsis_path = self._find_nsis()
        self.template_dir = Path(__file__).parent / "templates"
        
    def _find_nsis(self) -> Optional[Path]:
        """Find NSIS installation on the system"""
        # Check common paths first
        for path in NSIS_PATHS:
            if os.path.exists(path):
                return Path(path)
        
        # Check PATH
        nsis_in_path = shutil.which("makensis")
        if nsis_in_path:
            return Path(nsis_in_path)
        
        return None
    
    def is_available(self) -> bool:
        """Check if NSIS is available on the system"""
        return self.nsis_path is not None and self.nsis_path.exists()
    
    def get_version(self) -> Optional[str]:
        """Get NSIS version"""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [str(self.nsis_path), "/VERSION"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get NSIS version: {e}")
            return None
    
    async def log(self, message: str, callback: Optional[Callable] = None):
        """Log message and optionally call callback"""
        logger.info(f"[NSISBuilder] {message}")
        print(f"[NSISBuilder] {message}")
        if callback:
            await callback(message)
    
    def _generate_nsis_script(
        self,
        exe_path: Path,
        output_installer: Path,
        config: Dict[str, Any]
    ) -> str:
        """
        Generate NSIS script from template
        
        Args:
            exe_path: Path to the compiled executable
            output_installer: Path for the output installer
            config: Dictionary with installer configuration:
                - app_name: Application name
                - app_version: Application version (e.g., "1.0.0")
                - publisher: Publisher name
                - install_dir: Default installation directory name
                - create_desktop_shortcut: bool
                - create_start_menu: bool
                - icon_path: Optional path to .ico file
                - license_file: Optional path to license.txt
                - include_files: List of additional files to include
        
        Returns:
            Generated NSIS script content
        """
        app_name = config.get("app_name", "MyApp")
        app_version = config.get("app_version", "1.0.0")
        publisher = config.get("publisher", "Unknown Publisher")
        install_dir = config.get("install_dir", app_name)
        create_desktop_shortcut = config.get("create_desktop_shortcut", True)
        create_start_menu = config.get("create_start_menu", True)
        icon_path = config.get("icon_path")
        license_file = config.get("license_file")
        include_files = config.get("include_files", [])
        
        exe_name = exe_path.name
        
        # Build optional sections
        icon_section = f'Icon "{icon_path}"' if icon_path and os.path.exists(icon_path) else ""
        license_section = f'!insertmacro MUI_PAGE_LICENSE "{license_file}"' if license_file and os.path.exists(license_file) else ""
        
        # Build shortcuts section
        shortcuts_section = ""
        if create_desktop_shortcut:
            shortcuts_section += f'''
    CreateShortcut "$DESKTOP\\{app_name}.lnk" "$INSTDIR\\{exe_name}"'''
        
        if create_start_menu:
            shortcuts_section += f'''
    CreateDirectory "$SMPROGRAMS\\{app_name}"
    CreateShortcut "$SMPROGRAMS\\{app_name}\\{app_name}.lnk" "$INSTDIR\\{exe_name}"
    CreateShortcut "$SMPROGRAMS\\{app_name}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"'''
        
        # Build additional files section
        extra_files_section = ""
        for file_path in include_files:
            if os.path.exists(file_path):
                extra_files_section += f'\n    File "{file_path}"'
        
        # Remove shortcuts section for uninstaller
        remove_shortcuts_section = ""
        if create_desktop_shortcut:
            remove_shortcuts_section += f'''
    Delete "$DESKTOP\\{app_name}.lnk"'''
        
        if create_start_menu:
            remove_shortcuts_section += f'''
    RMDir /r "$SMPROGRAMS\\{app_name}"'''
        
        # Generate NSIS script
        script = f'''
; NSIS Installer Script for {app_name}
; Generated by CodeVault Professional Installer System

!include "MUI2.nsh"
!include "FileFunc.nsh"

; Basic Info
Name "{app_name}"
OutFile "{output_installer}"
InstallDir "$PROGRAMFILES\\{install_dir}"
InstallDirRegKey HKLM "Software\\{app_name}" "InstallDir"
RequestExecutionLevel admin

; Version Info
VIProductVersion "{app_version}.0"
VIAddVersionKey "ProductName" "{app_name}"
VIAddVersionKey "CompanyName" "{publisher}"
VIAddVersionKey "FileVersion" "{app_version}"
VIAddVersionKey "ProductVersion" "{app_version}"
VIAddVersionKey "FileDescription" "{app_name} Installer"

; Modern UI Configuration
!define MUI_ABORTWARNING
!define MUI_ICON "${{NSISDIR}}\\Contrib\\Graphics\\Icons\\modern-install.ico"
!define MUI_UNICON "${{NSISDIR}}\\Contrib\\Graphics\\Icons\\modern-uninstall.ico"
{icon_section}

; Pages
!insertmacro MUI_PAGE_WELCOME
{license_section}
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Installation Section
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Main executable
    File "{exe_path}"
    {extra_files_section}
    
    ; Create shortcuts
    {shortcuts_section}
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    
    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayName" "{app_name}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "Publisher" "{publisher}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayVersion" "{app_version}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "NoRepair" 1
    
    ; Get installed size
    ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "EstimatedSize" "$0"
    
    ; Store install dir
    WriteRegStr HKLM "Software\\{app_name}" "InstallDir" "$INSTDIR"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove installed files
    Delete "$INSTDIR\\{exe_name}"
    Delete "$INSTDIR\\Uninstall.exe"
    Delete "$INSTDIR\\license.key"
    
    ; Remove shortcuts
    {remove_shortcuts_section}
    
    ; Remove installation directory (if empty)
    RMDir "$INSTDIR"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
    DeleteRegKey HKLM "Software\\{app_name}"
SectionEnd
'''
        return script.strip()
    
    async def create_installer(
        self,
        exe_path: Path,
        output_dir: Path,
        config: Dict[str, Any],
        log_callback: Optional[Callable] = None
    ) -> Path:
        """
        Create a Windows installer for the given executable
        
        Args:
            exe_path: Path to the compiled executable
            output_dir: Directory to save the installer
            config: Installer configuration dictionary
            log_callback: Optional async callback for logging
        
        Returns:
            Path to the generated installer
        
        Raises:
            Exception if NSIS is not available or compilation fails
        """
        if not self.is_available():
            raise Exception("NSIS is not installed. Please install NSIS from https://nsis.sourceforge.io/")
        
        if not exe_path.exists():
            raise Exception(f"Executable not found: {exe_path}")
        
        await self.log(f"Creating installer for: {exe_path.name}", log_callback)
        
        app_name = config.get("app_name", exe_path.stem)
        installer_name = f"{app_name}_Setup.exe"
        output_installer = output_dir / installer_name
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory for NSIS script
        with tempfile.TemporaryDirectory(prefix="cv_nsis_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy exe to temp directory to avoid path issues with spaces
            temp_exe_path = temp_path / exe_path.name
            shutil.copy2(exe_path, temp_exe_path)
            
            # Copy any additional include files
            for include_file in config.get("include_files", []):
                if os.path.exists(include_file):
                    shutil.copy2(include_file, temp_path / Path(include_file).name)
            
            # Generate NSIS script with relative paths (exe is now in temp dir)
            script_content = self._generate_nsis_script(
                exe_path=Path(exe_path.name),  # Use relative path (exe is in same dir as script)
                output_installer=output_installer,
                config=config
            )
            
            # Write script to temp file
            script_path = temp_path / "installer.nsi"
            script_path.write_text(script_content, encoding="utf-8")
            
            await self.log("Generated NSIS installer script", log_callback)
            
            # Compile with NSIS
            await self.log("Compiling installer with NSIS...", log_callback)
            
            try:
                process = await asyncio.create_subprocess_exec(
                    str(self.nsis_path),
                    str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(temp_path)
                )
                
                # Stream output
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    if decoded_line:
                        await self.log(f"  nsis: {decoded_line}", log_callback)
                
                await process.wait()
                
                if process.returncode != 0:
                    raise Exception(f"NSIS compilation failed with exit code {process.returncode}")
                
            except FileNotFoundError:
                raise Exception(f"NSIS not found at: {self.nsis_path}")
        
        if not output_installer.exists():
            raise Exception("Installer was not created. Check NSIS output for errors.")
        
        installer_size = output_installer.stat().st_size / (1024 * 1024)  # MB
        await self.log(f"✅ Installer created: {output_installer} ({installer_size:.1f} MB)", log_callback)
        
        return output_installer


# Singleton instance for easy access
_nsis_builder: Optional[NSISBuilder] = None

def get_nsis_builder() -> NSISBuilder:
    """Get or create the NSIS builder singleton"""
    global _nsis_builder
    if _nsis_builder is None:
        _nsis_builder = NSISBuilder()
    return _nsis_builder


def check_nsis_available() -> Dict[str, Any]:
    """Check if NSIS is available and return status info"""
    builder = get_nsis_builder()
    return {
        "available": builder.is_available(),
        "path": str(builder.nsis_path) if builder.nsis_path else None,
        "version": builder.get_version()
    }
