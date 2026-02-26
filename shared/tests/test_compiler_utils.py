"""Tests for shared compiler utilities."""

import hashlib
import platform
import pytest
from unittest.mock import patch

from compiler_utils import generate_hwid
from compiler_utils import blacklist
from compiler_utils import signature


from compiler_utils import CACHE_LIMITS
from compiler_utils import CACHE_TTL_DAYS
from compiler_utils import CACHE_EVICTION_THRESHOLD


class TestGenerateHWID:
    """Test HWID generation."""

    def test_generate_hwid_returns_string(self):
        hwid = generate_hwid()
        assert isinstance(hwid, str)
        assert len(hwid) == 32

    def test_generate_hwid_is_hex(self):
        hwid = generate_hwid()
        try:
            int(hwid, 16)
            assert True
        except ValueError:
            pytest.fail("HWID should be a valid hex string")

    def test_generate_hwid_consistent(self):
        hwid1 = generate_hwid()
        hwid2 = generate_hwid()
        assert hwid1 == hwid2


class TestBlacklist:
    """Test module blacklist constants."""

    def test_blacklist_contains_unwanted_modules(self):
        assert "test" in blacklist.PYTHON_BLACKLIST
        assert "unittest" in blacklist.PYTHON_BLACKLIST
        assert "pytest" in blacklist.PYTHON_BLACKLIST
        assert "pdb" in blacklist.PYTHON_BLACKLIST

    def test_blacklist_extended_contains_more(self):
        assert "numpy.tests" in blacklist.PYTHON_BLACKLIST_EXTENDED
        assert "pandas.tests" in blacklist.PYTHON_BLACKLIST_EXTENDED

    def test_turbo_exclusions_contains_encodings(self):
        assert "encodings.cp1006" in blacklist.PYTHON_TURBO_EXCLUSIONS
        assert "encodings.mac_arabic" in blacklist.PYTHON_TURBO_EXCLUSIONS


class TestSignatureVerification:
    """Test Ed25519 signature verification."""

    def test_verify_ed25519_missing_crypto(self):
        with patch("compiler_utils.signature.HAS_CRYPTO", False):
            with pytest.raises(RuntimeError, match="cryptography"):
                signature.verify_ed25519_signature({}, "test_key")

    def test_verify_ed25519_missing_signature(self):
        with patch("compiler_utils.signature.HAS_CRYPTO", True):
            with pytest.raises(ValueError, match="unsigned"):
                signature.verify_ed25519_signature({}, "test_key")

    def test_verify_ed25519_missing_public_key(self):
        with patch("compiler_utils.signature.HAS_CRYPTO", True):
            with pytest.raises(ValueError, match="No public key"):
                signature.verify_ed25519_signature({"signature": "test"}, "")


class TestCacheConfiguration:
    """Test cache configuration constants."""

    def test_cache_limits_defined(self):
        assert "pip" in CACHE_LIMITS
        assert "ccache" in CACHE_LIMITS
        assert "mingw" in CACHE_LIMITS
        assert "nuitka" in CACHE_LIMITS

    def test_cache_ttl_days(self):
        assert CACHE_TTL_DAYS == 14

    def test_cache_eviction_threshold(self):
        assert CACHE_EVICTION_THRESHOLD == 0.9
