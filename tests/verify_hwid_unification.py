import subprocess
import sys
import os
import hashlib
import platform
import re
import uuid

# Snippet from shared/compiler_utils/hwid.py (Python)
def get_python_hwid():
    components = []
    # 1. MAC Address
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("ipconfig /all", text=True, timeout=5)
            all_macs = re.findall(r"Physical Address[. ]+: ([\w-]+)", output)
            formatted_macs = [m.replace("-", ":").lower() for m in all_macs if m and m != "00-00-00-00-00-00"]
            if formatted_macs:
                components.append(f"mac:{sorted(formatted_macs)[0]}")
        else:
            mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
            if mac and mac != "00:00:00:00:00:00":
                components.append(f"mac:{mac.lower()}")
    except Exception:
        pass

    # 2. CPU Model
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_model, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if cpu_model:
                components.append(f"cpu:{cpu_model.strip()[:32]}")
        except Exception:
            pass
            
        # 3. Disk Serial
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                disk_serial = lines[1].strip()
                if disk_serial and disk_serial != "SerialNumber":
                    components.append(f"disk:{disk_serial}")
        except Exception:
            pass
    
    if components:
        raw = "|".join(components)
        print(f"Python components: {raw}")
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    return "failed"

# Snippet from nodejs_tpl.py (Node.js)
NODE_JS_CODE = r"""
const os = require('os');
const crypto = require('crypto');

function getHWID() {
    const components = [];
    
    try {
        const networkInterfaces = os.networkInterfaces();
        const macs = [];
        for (const name of Object.keys(networkInterfaces)) {
            for (const iface of networkInterfaces[name]) {
                if (!iface.internal && iface.mac && iface.mac !== '00:00:00:00:00:00') {
                    macs.push(iface.mac.toLowerCase());
                }
            }
        }
        if (macs.length > 0) {
            macs.sort();
            components.push('mac:' + macs[0]);
        }
    } catch (e) {}
    
    try {
        const cpus = os.cpus();
        if (cpus && cpus.length > 0 && cpus[0].model) {
            components.push('cpu:' + cpus[0].model.substring(0, 32));
        }
    } catch (e) {}
    
    if (process.platform === 'win32') {
        try {
            const { execSync } = require('child_process');
            try {
                const diskOutput = execSync('wmic diskdrive get serialnumber', { encoding: 'utf8', timeout: 5000 });
                const lines = diskOutput.trim().split('\n');
                if (lines.length > 1) {
                    const diskSerial = lines[1].trim();
                    if (diskSerial && diskSerial !== 'SerialNumber') {
                        components.push('disk:' + diskSerial);
                    }
                }
            } catch (e) {}
        } catch (e) {}
    }
    
    if (components.length > 0) {
        const raw = components.join('|');
        process.stdout.write('Node components: ' + raw + '\n');
        return crypto.createHash('sha256').update(raw).digest('hex').substring(0, 32);
    }
    return "failed";
}

process.stdout.write(getHWID() + '\n');
"""

def get_node_hwid():
    with open("temp_hwid.js", "w", encoding="utf-8") as f:
        f.write(NODE_JS_CODE)
    
    try:
        result = subprocess.check_output(["node", "temp_hwid.js"], text=True)
        lines = result.strip().split("\n")
        print(lines[0]) # Node components
        return lines[1] # Hash
    finally:
        if os.path.exists("temp_hwid.js"):
            os.remove("temp_hwid.js")

if __name__ == "__main__":
    print("Testing HWID Unification...")
    py_hwid = get_python_hwid()
    node_hwid = get_node_hwid()
    
    print(f"Python HWID: {py_hwid}")
    print(f"Node.js HWID: {node_hwid}")
    
    if py_hwid == node_hwid and py_hwid != "failed":
        print("SUCCESS: HWIDs match!")
        sys.exit(0)
    else:
        print("FAILURE: HWIDs do not match or failed!")
        sys.exit(1)
