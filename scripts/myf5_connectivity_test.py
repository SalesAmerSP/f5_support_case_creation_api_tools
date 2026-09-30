#!/usr/bin/env python3
"""Test authentication against F5 Identity Services for MyF5 Case Management.

Supports both Okta and Auth0 authentication endpoints (per K000162308).

Usage:
    # Requires F5_CLIENT_ID & F5_CLIENT_SECRET in env or ~/.f5api_credentials
    python3 scripts/myf5_connectivity_test.py [--profile <profile>]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Authenticate against Identity Service using myf5_scope."""
    args = f5functions.myf5_args()
    print('Testing authentication against F5 Identity Service...')
    f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )


if __name__ == "__main__":
    main()
