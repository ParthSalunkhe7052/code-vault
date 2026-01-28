"""
License wrappers for Python and Node.js.
These are injected into the entry files during compilation.

Refactored to use generators in `cli/generators/`.
"""

from generators.python_generator import get_python_wrapper
from generators.nodejs_generator import get_nodejs_wrapper, get_nodejs_wrapper_inline

__all__ = ['get_python_wrapper', 'get_nodejs_wrapper', 'get_nodejs_wrapper_inline']
