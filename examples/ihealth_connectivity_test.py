#!/usr/bin/env python3
"""Test authentication and API connectivity against F5 iHealth.

Supports both Okta and Auth0 authentication endpoints (per K000162308).

Usage:
    python3 examples/ihealth_connectivity_test.py --client-id <id> --client-secret <secret> \
        [--auth-fqdn idp.identity.f5.com] [--api-fqdn ihealth2-api.f5.com]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Authenticate and test reachability of iHealth QKView query endpoint."""
    args = f5functions.ihealth_args()
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='ihealth', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # Verify we can reach the iHealth API
    qkview_id_list = f5functions.ihealth_list_qkview_ids(access_token, api_fqdn=args.api_fqdn)
    if qkview_id_list.status_code != 200:
        raise SystemExit(f'Failed to reach iHealth API.\nStatus code: {qkview_id_list.status_code} Full response: {qkview_id_list.text}')
    print('iHealth API connectivity test successful.')


if __name__ == "__main__":
    main()
