"""
Compilation helper functions for CodeVault API.
Extracted from main.py for modularity.
"""

import sys
import json
import time
import re
import shutil
import subprocess
from pathlib import Path

from config import LICENSE_SERVER_URL
from utils import utc_now, safe_join, validate_project_id, SecurityError
from database import get_db, release_db
from compilers.nodejs_compiler import NodeJSCompiler


# =============================================================================
# Security: Subprocess wrapper with path validation
# =============================================================================

def safe_subprocess_run(cmd: list, cwd: Path, allowed_base: Path, **kwargs):
    """
    Run subprocess with validated cwd path.
    
    This wrapper ensures the working directory is within the allowed base directory
    before executing any subprocess command. This prevents path traversal attacks.
    
    Args:
        cmd: Command list to execute
        cwd: Working directory for the subprocess
        allowed_base: Base directory that cwd must be within
        **kwargs: Additional arguments passed to subprocess.run
        
    Returns:
        subprocess.CompletedProcess result
        
    Raises:
        SecurityError: If cwd escapes the allowed base directory
    """
    import os
    # Resolve both paths to eliminate symlinks and relative components
    resolved_cwd = cwd.resolve()
    resolved_base = allowed_base.resolve()
    
    # Security check: ensure cwd is within allowed base
    # Using str().startswith() pattern that CodeQL recognizes
    if not str(resolved_cwd).startswith(str(resolved_base) + os.sep) and resolved_cwd != resolved_base:
        raise SecurityError("Working directory escapes allowed path")
    
    # Execute subprocess with the validated, resolved path
    # lgtm[py/command-line-injection] - cmd comes from trusted internal code, cwd is validated above
    return subprocess.run(cmd, cwd=str(resolved_cwd), **kwargs)


async def run_compilation_job(job_id: str, project_id: str, data, job_cache: dict, upload_dir: Path):
    """Background task to run actual compilation with Nuitka or pkg."""
    try:
        job_cache[job_id]['status'] = 'running'
        job_cache[job_id]['logs'].append('Starting compilation...')
        started_at = utc_now()
        
        conn = await get_db()
        try:
            await conn.execute("UPDATE compile_jobs SET status = $1, started_at = $2 WHERE id = $3", 
                             'running', started_at, job_id)
            
            project = await conn.fetchrow("SELECT settings, language FROM projects WHERE id = $1", project_id)
            settings = json.loads(project['settings']) if isinstance(project['settings'], str) else project['settings']
            language = project.get('language', 'python')
        finally:
            await release_db(conn)
        
        file_tree = settings.get('file_tree')
        is_multi_folder = settings.get('is_multi_folder', False)
        
        if language == 'nodejs':
            await compile_nodejs_project(job_id, project_id, data, job_cache, upload_dir)
        elif is_multi_folder and file_tree:
            await compile_multi_folder_project(job_id, project_id, file_tree, data, job_cache, upload_dir)
        else:
            await compile_single_file_project(job_id, project_id, data, job_cache, upload_dir)
        
        completed_at = utc_now()
        output_filename = f"{data.output_name or 'output'}.exe"
        
        job_cache[job_id]['status'] = 'completed'
        job_cache[job_id]['output_filename'] = output_filename
        job_cache[job_id]['completed_time'] = time.time()
        job_cache[job_id]['logs'].append('✅ Compilation completed successfully!')
        
        conn = await get_db()
        try:
            await conn.execute("""
                UPDATE compile_jobs SET status = $1, progress = $2, output_filename = $3, 
                completed_at = $4, logs = $5 WHERE id = $6
            """, 'completed', 100, output_filename, completed_at, 
               json.dumps(job_cache[job_id]['logs']), job_id)
        finally:
            await release_db(conn)
        
    except Exception as e:
        job_cache[job_id]['status'] = 'failed'
        job_cache[job_id]['error_message'] = str(e)
        job_cache[job_id]['completed_time'] = time.time()
        job_cache[job_id]['logs'].append(f'❌ Compilation failed: {str(e)}')
        
        conn = await get_db()
        try:
            await conn.execute("UPDATE compile_jobs SET status = $1, error_message = $2, logs = $3 WHERE id = $4",
                             'failed', str(e), json.dumps(job_cache[job_id]['logs']), job_id)
        finally:
            await release_db(conn)


async def compile_nodejs_project(job_id: str, project_id: str, data, job_cache: dict, upload_dir: Path):
    """Compile a Node.js project."""
    job_cache[job_id]['logs'].append('📦 Node.js project detected')
    
    # Security: Validate project_id before using in paths
    validate_project_id(project_id)
    
    # Use safe_join to prevent path traversal
    project_base = safe_join(upload_dir, project_id)
    source_dir = safe_join(project_base, "source")
    
    if not source_dir.exists():
        source_dir = project_base
        job_cache[job_id]['logs'].append('   Single file mode')
    else:
        job_cache[job_id]['logs'].append('   Multi-file mode')
        
    entry_file = data.entry_file
    if not entry_file:
        for candidate in ['index.js', 'app.js', 'main.js', 'server.js']:
            candidate_path = safe_join(source_dir, candidate)
            if candidate_path.exists():
                entry_file = candidate
                break
    
    if not entry_file:
        raise Exception("Entry file not specified and could not be auto-detected")
    
    # Validate entry file path
    entry_path = safe_join(source_dir, entry_file)
    if not entry_path.exists():
        raise Exception(f"Entry file not found: {entry_file}")
        
    job_cache[job_id]['logs'].append(f"   Entry: {entry_file}")
    
    output_dir = safe_join(project_base, "output")
    output_dir.mkdir(exist_ok=True)
    
    node_modules = Path(__file__).parent.parent / "node_modules"
    compiler = NodeJSCompiler(node_modules_path=node_modules)
    
    async def log_callback(msg):
        job_cache[job_id]['logs'].append(msg)
    
    output_name = data.output_name or "app"
    license_key = data.license_key or "DEMO"
    api_url = LICENSE_SERVER_URL + "/license/validate"
    options = data.options or {}
    
    final_exe = await compiler.compile(
        source_dir=source_dir,
        entry_file=entry_file,
        output_dir=output_dir,
        output_name=output_name,
        license_key=license_key,
        api_url=api_url,
        options=options,
        log_callback=log_callback
    )
    
    job_cache[job_id]['progress'] = 100
    job_cache[job_id]['output_filename'] = final_exe.name


async def compile_multi_folder_project(job_id: str, project_id: str, file_tree: dict, data, job_cache: dict, upload_dir: Path):
    """Compile a multi-folder project with dependencies."""
    job_cache[job_id]['logs'].append('📦 Multi-folder project detected')
    job_cache[job_id]['logs'].append(f"   Files: {file_tree['total_files']}")
    job_cache[job_id]['logs'].append(f"   Entry: {file_tree['entry_point']}")
    
    # Security: Validate project_id and use safe paths
    validate_project_id(project_id)
    project_base = safe_join(upload_dir, project_id)
    project_dir = safe_join(project_base, "source")
    
    if not project_dir.exists():
        raise Exception("Project source directory not found")
    
    job_cache[job_id]['progress'] = 10
    
    dependencies = file_tree.get('dependencies', {})
    if dependencies.get('has_requirements'):
        job_cache[job_id]['logs'].append(f"📦 Installing {len(dependencies['python'])} dependencies...")
        install_project_dependencies(project_dir, dependencies, job_cache[job_id]['logs'])
    
    job_cache[job_id]['progress'] = 30
    
    job_cache[job_id]['logs'].append('🔐 Injecting license validation...')
    entry_point = file_tree['entry_point']
    # Validate entry_point doesn't escape project_dir
    safe_join(project_dir, entry_point)
    inject_license_into_multi_folder(project_dir, entry_point, data.license_key or "DEMO-KEY")
    
    job_cache[job_id]['progress'] = 50
    
    job_cache[job_id]['logs'].append('🔨 Building with Nuitka...')
    # Security: Sanitize output_name to prevent command injection
    raw_output_name = data.output_name or 'app'
    output_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_output_name) or 'app'
    entry_file = safe_join(project_dir, entry_point)
    
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
    ]
    
    for folder in file_tree.get('folders', []):
        package = folder.replace("/", ".").replace("\\", ".")
        nuitka_cmd.append(f"--include-package={package}")
        job_cache[job_id]['logs'].append(f"   Including: {package}")
    
    nuitka_cmd.append(str(entry_file))
    
    job_cache[job_id]['progress'] = 60
    job_cache[job_id]['logs'].append('⚙️  Compiling (this may take 2-5 minutes)...')
    
    result = safe_subprocess_run(
        nuitka_cmd,
        cwd=project_dir,
        allowed_base=upload_dir,
        capture_output=True,
        text=True,
        timeout=600
    )
    
    job_cache[job_id]['progress'] = 95
    
    if result.returncode != 0:
        job_cache[job_id]['logs'].append('❌ Nuitka compilation failed')
        job_cache[job_id]['logs'].append(f"Error: {result.stderr[:500]}")
        raise Exception(f"Nuitka failed: {result.stderr[:200]}")
    
    exe_file = safe_join(project_dir, f"{output_name}.exe")
    if not exe_file.exists():
        for f in project_dir.glob("*.exe"):
            exe_file = f
            break
    
    if not exe_file.exists():
        raise Exception("Compiled executable not found")
    
    output_dir = safe_join(project_base, "output")
    output_dir.mkdir(exist_ok=True)
    final_exe = safe_join(output_dir, f"{output_name}.exe")
    shutil.move(str(exe_file), str(final_exe))
    
    file_size = final_exe.stat().st_size / 1024 / 1024
    job_cache[job_id]['logs'].append(f'✅ Executable created: {final_exe.name} ({file_size:.1f} MB)')
    job_cache[job_id]['progress'] = 100


async def compile_single_file_project(job_id: str, project_id: str, data, job_cache: dict, upload_dir: Path):
    """Compile a single-file project using Nuitka."""
    job_cache[job_id]['logs'].append('📄 Single-file project detected')
    job_cache[job_id]['progress'] = 10
    
    # Security: Validate project_id and use safe paths
    validate_project_id(project_id)
    project_base = safe_join(upload_dir, project_id)
    project_dir = safe_join(project_base, "source")
    
    if not project_dir.exists():
        file_dir = project_base
        py_files = list(file_dir.glob("*.py"))
        if py_files:
            source_file = py_files[0]
            project_dir = file_dir
        else:
            raise Exception("Project source not found")
    else:
        entry_file_name = data.entry_file
        if entry_file_name:
            # Validate entry_file doesn't escape project_dir
            source_file = safe_join(project_dir, entry_file_name)
        else:
            py_files = list(project_dir.glob("*.py"))
            if not py_files:
                raise Exception("No Python files found in project")
            source_file = py_files[0]
    
    if not source_file.exists():
        raise Exception("Source file not found")
    
    job_cache[job_id]['logs'].append(f'   Entry file: {source_file.name}')
    job_cache[job_id]['progress'] = 20
    
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         20, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)
    
    if data.license_key:
        job_cache[job_id]['logs'].append('🔐 Injecting license validation...')
        inject_license_into_single_file(source_file, data.license_key)
        job_cache[job_id]['progress'] = 30
    
    job_cache[job_id]['logs'].append('🔨 Building with Nuitka...')
    # Security: Sanitize output_name to prevent command injection
    raw_output_name = data.output_name or source_file.stem
    output_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_output_name) or 'app'
    
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
        str(source_file)
    ]
    
    job_cache[job_id]['progress'] = 40
    job_cache[job_id]['logs'].append('⚙️  Compiling (this may take 2-5 minutes)...')
    
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         40, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)
    
    try:
        result = safe_subprocess_run(
            nuitka_cmd,
            cwd=project_dir,
            allowed_base=upload_dir,
            capture_output=True,
            text=True,
            timeout=600
        )
    except subprocess.TimeoutExpired:
        raise Exception("Compilation timed out after 10 minutes")
    
    job_cache[job_id]['progress'] = 90
    
    if result.returncode != 0:
        job_cache[job_id]['logs'].append('❌ Nuitka compilation failed')
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        job_cache[job_id]['logs'].append(f"Error: {error_msg}")
        raise Exception(f"Nuitka failed: {error_msg[:200]}")
    
    exe_file = safe_join(project_dir, f"{output_name}.exe")
    if not exe_file.exists():
        for f in project_dir.glob("*.exe"):
            exe_file = f
            break
    
    if not exe_file.exists():
        raise Exception("Compiled executable not found")
    
    output_dir = safe_join(project_base, "output")
    output_dir.mkdir(exist_ok=True)
    final_exe = safe_join(output_dir, f"{output_name}.exe")
    
    if final_exe.exists():
        final_exe.unlink()
    
    shutil.move(str(exe_file), str(final_exe))
    
    file_size = final_exe.stat().st_size / 1024 / 1024
    job_cache[job_id]['logs'].append(f'✅ Executable created: {final_exe.name} ({file_size:.1f} MB)')
    job_cache[job_id]['progress'] = 100
    
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         100, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)


def inject_license_into_single_file(source_file: Path, license_key: str):
    """Inject license validation into a single Python file."""
    original_content = source_file.read_text(encoding='utf-8')
    
    backup_file = source_file.parent / f"_original_{source_file.name}"
    if not backup_file.exists():
        source_file.rename(backup_file)
        source_file.write_text(original_content, encoding='utf-8')
    
    wrapper_code = f'''#!/usr/bin/env python3
"""
License-Protected Application
"""

import sys, os, hashlib, urllib.request, json, time

def get_hardware_id():
    import platform
    info = f"{{platform.node()}}|{{platform.machine()}}|{{platform.processor()}}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]

def validate_license():
    license_key = "{license_key}"
    server_url = os.environ.get("LICENSE_SERVER_URL", "{LICENSE_SERVER_URL}") + "/license/validate"
    
    try:
        hwid = get_hardware_id()
        nonce = hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]
        
        payload = json.dumps({{
            "license_key": license_key,
            "hwid": hwid,
            "machine_name": os.environ.get("COMPUTERNAME", "Unknown"),
            "nonce": nonce,
            "timestamp": int(time.time())
        }}).encode('utf-8')
        
        req = urllib.request.Request(server_url, data=payload, headers={{"Content-Type": "application/json"}})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('status') != 'valid':
                print("\\n❌ LICENSE VALIDATION FAILED")
                print(f"Reason: {{result.get('message', 'Unknown error')}}")
                input("Press Enter to exit...")
                sys.exit(1)
            
            print("✅ License validated successfully")
            return True
            
    except Exception as e:
        print(f"⚠️  License validation warning: {{e}}")
        return True

validate_license()

# ============== ORIGINAL APPLICATION CODE ==============
{original_content}
'''
    
    source_file.write_text(wrapper_code, encoding='utf-8')


def install_project_dependencies(project_dir: Path, dependencies: dict, logs: list):
    """Install dependencies using the workspace venv."""
    if not dependencies.get('has_requirements'):
        return
    
    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        return
    
    venv_python = Path(__file__).parent.parent.parent / "venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        venv_python = sys.executable
        logs.append("   Warning: Using system Python (venv not found)")
    
    logs.append(f"   Installing to: {venv_python.parent}")
    
    for dep in dependencies['python'][:10]:
        logs.append(f"     - {dep}")
    
    if len(dependencies['python']) > 10:
        logs.append(f"     ... and {len(dependencies['python']) - 10} more")
    
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(req_file), "--quiet"],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        logs.append("   ⚠️  Warning: Some packages may have failed to install")
        logs.append(f"   {result.stderr[:200]}")
    else:
        logs.append("   ✅ Dependencies installed successfully")


def inject_license_into_multi_folder(project_dir: Path, entry_point: str, license_key: str):
    """Inject license validation into the entry point of a multi-folder project."""
    entry_file = project_dir / entry_point
    
    if not entry_file.exists():
        raise Exception(f"Entry point not found: {entry_point}")
    
    original_content = entry_file.read_text(encoding='utf-8')
    
    license_core_src = Path(__file__).parent.parent.parent / "src" / "license_core"
    license_core_dest = project_dir / "_license_core"
    
    if license_core_dest.exists():
        shutil.rmtree(license_core_dest)
    if license_core_src.exists():
        shutil.copytree(license_core_src, license_core_dest)
    
    wrapper_code = f'''#!/usr/bin/env python3
"""
License-Protected Application
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_license_core'))

def validate_license():
    try:
        from checker import LicenseContext
        
        ctx = LicenseContext(
            license_key="{license_key}",
            server_url=os.environ.get("LICENSE_SERVER_URL", "{LICENSE_SERVER_URL}")
        )
        
        if not ctx.is_valid:
            print("\\n❌ LICENSE VALIDATION FAILED")
            print(f"Reason: {{ctx.error_message}}")
            input("Press Enter to exit...")
            sys.exit(1)
        
        print("✅ License validated successfully")
        return ctx
    except Exception as e:
        print(f"\\n❌ License validation error: {{e}}")
        input("Press Enter to exit...")
        sys.exit(1)

license_ctx = validate_license()

{original_content}
'''
    
    backup_file = project_dir / f"_original_{entry_file.name}"
    entry_file.rename(backup_file)
    
    entry_file.write_text(wrapper_code, encoding='utf-8')
