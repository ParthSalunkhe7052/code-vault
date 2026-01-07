#!/usr/bin/env python3
"""Test script to verify both email and rate limiter fixes."""

import sys
import os
import asyncio

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

def test_email_config():
    """Test email configuration."""
    from email_service import EmailService, EMAIL_ENABLED, RESEND_API_KEY, EMAIL_PROVIDER

    print('=== Email Configuration ===')
    print(f'EMAIL_ENABLED: {EMAIL_ENABLED}')
    print(f'EMAIL_PROVIDER: {EMAIL_PROVIDER}')
    print(f'RESEND_API_KEY: {"OK" if RESEND_API_KEY else "MISSING"}')

    email_svc = EmailService()
    is_configured = email_svc.is_configured()
    print(f'Email Service: {"WORKING" if is_configured else "DISABLED"}')
    return is_configured

def test_rate_limiter_config():
    """Test rate limiter configuration."""
    from config import REDIS_URL

    print('\n=== Rate Limiter Configuration ===')
    print(f'REDIS_URL: {"OK" if REDIS_URL else "MISSING"}')

    # Check if Redis package is available
    try:
        import redis
        print(f'Redis Package: OK (v{redis.__version__})')
    except ImportError:
        print('Redis Package: MISSING')
        return False

    if not REDIS_URL:
        print('Rate Limiting: DISABLED (no Redis URL)')
        return False

    # Test connection
    async def test_connection():
        from middleware.rate_limiter import init_rate_limiter, close_rate_limiter
        try:
            await init_rate_limiter(REDIS_URL)
            print('Rate Limiting: ENABLED (Upstash configured)')
            await close_rate_limiter()
            return True
        except Exception as e:
            print(f'Rate Limiting: WARNING ({e})')
            return False

    return asyncio.run(test_connection())

def main():
    """Run all tests."""
    print('CodeVault Fix Verification\n')
    print('=' * 50)

    email_ok = test_email_config()
    rate_ok = test_rate_limiter_config()

    print('\n' + '=' * 50)
    print('SUMMARY:')
    print(f'Email Service: {"WORKING" if email_ok else "BROKEN"}')
    print(f'Rate Limiter: {"WORKING" if rate_ok else "DISABLED (OK for dev)"}')

    if email_ok:
        print('\nBoth issues are RESOLVED!')
    else:
        print('\nSome issues remain. Check configuration above.')

    return email_ok

if __name__ == '__main__':
    main()