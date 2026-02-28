
import sys
import os

# Mock the globals that get replaced
license_key = "LIC-TEST"
server_url = "https://api.test.com"
lease_enabled = True
public_key = "MOCK_KEY"
binary_hash = "skip"
heartbeat_interval = 300
app_name = "Test App"
show_branding = True
brand_name = "CodeVault"
brand_url = "https://codevault.dev"
brand_primary_color = "#6366f1"

# Import the template generator
sys.path.append(os.path.join(os.getcwd(), "cli", "templates"))
from unified_license_wrapper import get_license_wrapper

# Generate the wrapper
code = get_license_wrapper(
    license_key=license_key,
    server_url=server_url,
    lease_enabled=lease_enabled,
    public_key=public_key,
    binary_hash=binary_hash,
    heartbeat_interval=heartbeat_interval,
    app_name=app_name,
    show_branding=show_branding,
    brand_name=brand_name,
    brand_url=brand_url,
    brand_primary_color=brand_primary_color
)

# Try to compile and run the code to find NameErrors or SyntaxErrors
try:
    compiled_code = compile(code, "generated_wrapper.py", "exec")
    print("Compilation successful!")
    
    # We won't run it fully because it requires network and GUI, 
    # but we can inspect the byte code or just check for common errors.
except SyntaxError as e:
    print(f"SyntaxError found: {e}")
except Exception as e:
    print(f"Error during compilation: {e}")
