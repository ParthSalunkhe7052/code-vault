
import os
import sys

# Ensure we can import from server
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "server"))

def test_project_structure():
    """
    Basic "sanity check" to ensure critical directories exist.
    Reflects the "Meta-Code" structure.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    expected_dirs = [
        "server",
        "docs",
        "tests"
    ]
    
    for relative_path in expected_dirs:
        full_path = os.path.join(base_dir, relative_path)
        assert os.path.exists(full_path), f"Missing critical directory: {relative_path}"

def test_no_hardcoded_secrets_in_env_example():
    """
    Example test to remind us not to commit secrets.
    Checks if a .env.example exists and doesn't contain real keys.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    env_example = os.path.join(base_dir, ".env.example")
    
    if os.path.exists(env_example):
        with open(env_example, "r") as f:
            content = f.read()
            # Simple heuristic: if it looks like a real key, fail
            assert "sk_live_" not in content, "Found potential live Stripe key in .env.example"
